import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';

export interface ChatMessage {
  role: 'agent' | 'user';
  content: string;
  images?: string[];
  dbId?: number;
  type?: 'text' | 'step' | 'phase_header' | 'procedure_complete' | 'step_clarification' | 'wizard_step';
  timestamp?: string;
  context_source?: string;
}

export interface AssistantSession {
  id: number;
  machine_id?: string;
  title: string;
  timestamp: string;
}

interface CopilotState {
  chatHistory: Record<string, ChatMessage[]>;
  assistantSessions: AssistantSession[];
  activeAssistantSessionId: number | null;
  isAssistantSidebarOpen: boolean;
  exportProgress: {
    isExporting: boolean;
    progress: number;
    status: 'generating' | 'success' | 'error';
    errorMessage?: string;
  };
}

const initialState: CopilotState = {
  chatHistory: {
    'assistant': [
      { role: 'agent', content: '🏭 Central RAG Copilot initialized. Upload a manual and ask any maintenance questions.' }
    ]
  },
  assistantSessions: [],
  activeAssistantSessionId: null,
  isAssistantSidebarOpen: true,
  exportProgress: {
    isExporting: false,
    progress: 0,
    status: 'generating',
  },
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const fetchAssistantSessions = createAsyncThunk(
  'copilot/fetchAssistantSessions',
  async () => {
    const response = await fetch(`${API_BASE}/api/assistant/sessions`);
    if (!response.ok) throw new Error('Failed to fetch sessions');
    return await response.json() as AssistantSession[];
  }
);

export const deleteAssistantSession = createAsyncThunk(
  'copilot/deleteAssistantSession',
  async (sessionId: number) => {
    const response = await fetch(`${API_BASE}/api/assistant/sessions/${sessionId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Failed to delete session');
    return sessionId;
  }
);

export const fetchAssistantHistory = createAsyncThunk(
  'copilot/fetchAssistantHistory',
  async (sessionId: number) => {
    const response = await fetch(`${API_BASE}/api/assistant/sessions/${sessionId}/history`);
    if (!response.ok) throw new Error('Failed to fetch session history');
    const data = await response.json();
    return { sessionId, messages: data };
  }
);

export const inquireAssistant = createAsyncThunk(
  'copilot/inquireAssistant',
  async ({ query, sessionId }: { query: string; sessionId?: number }, { dispatch }) => {
    dispatch(copilotSlice.actions.addChatMessage({
      role: 'user',
      content: query,
      targetId: 'assistant'
    }));

    const response = await fetch(`${API_BASE}/api/assistant`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, session_id: sessionId }),
    });
    if (!response.ok) throw new Error('Assistant failed to respond');

    const data = await response.json();
    if (data.session_id && sessionId !== data.session_id) {
      dispatch(fetchAssistantSessions());
    }

    return data;
  }
);

export const exportAssistantSession = createAsyncThunk(
  'copilot/exportAssistantSession',
  async (sessionId: number, { rejectWithValue, dispatch }) => {
    try {
      dispatch(copilotSlice.actions.setExportProgress({ progress: 5, status: 'generating' }));

      const response = await fetch(`${API_BASE}/api/assistant/sessions/${sessionId}/report`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to generate report: ${response.status} ${errorText}`);
      }

      dispatch(copilotSlice.actions.setExportProgress({ progress: 30, status: 'generating' }));
      const reportData = await response.json();

      dispatch(copilotSlice.actions.setExportProgress({ progress: 50, status: 'generating' }));

      const { generateDiagnosticReport } = await import('../../professionalReportService');
      await generateDiagnosticReport(reportData, (progress) => {
        dispatch(copilotSlice.actions.setExportProgress({ progress: 50 + Math.floor(progress / 2), status: 'generating' }));
      });

      dispatch(copilotSlice.actions.setExportProgress({ progress: 100, status: 'success' }));
      setTimeout(() => {
        dispatch(copilotSlice.actions.resetExportProgress());
      }, 2000);

      return { success: true, sessionId };
    } catch (error: any) {
      dispatch(copilotSlice.actions.setExportProgress({
        progress: 0,
        status: 'error',
        errorMessage: error.message
      }));
      return rejectWithValue(error.message || 'Export failed');
    }
  }
);

const copilotSlice = createSlice({
  name: 'copilot',
  initialState,
  reducers: {
    addChatMessage(state, action: PayloadAction<ChatMessage & { targetId?: string }>) {
      const { targetId, ...msg } = action.payload;
      const key = targetId || 'assistant';
      if (!state.chatHistory[key]) {
        state.chatHistory[key] = [];
      }
      state.chatHistory[key].push(msg);
    },
    setAssistantSidebarOpen(state, action: PayloadAction<boolean>) {
      state.isAssistantSidebarOpen = action.payload;
    },
    setActiveAssistantSessionId(state, action: PayloadAction<number | null>) {
      state.activeAssistantSessionId = action.payload;
      if (action.payload === null) {
        state.chatHistory['assistant'] = [
          { role: 'agent', content: '🏭 Central RAG Copilot initialized. Upload a manual and ask any maintenance questions.' }
        ];
      }
    },
    setExportProgress(state, action: PayloadAction<{ progress: number; status: 'generating' | 'success' | 'error'; errorMessage?: string }>) {
      state.exportProgress = {
        isExporting: true,
        ...action.payload,
      };
    },
    resetExportProgress(state) {
      state.exportProgress = {
        isExporting: false,
        progress: 0,
        status: 'generating',
      };
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAssistantSessions.fulfilled, (state, action) => {
        state.assistantSessions = action.payload;
      })
      .addCase(deleteAssistantSession.fulfilled, (state, action) => {
        state.assistantSessions = state.assistantSessions.filter(s => s.id !== action.payload);
        if (state.activeAssistantSessionId === action.payload) {
          state.activeAssistantSessionId = null;
          state.chatHistory['assistant'] = [
            { role: 'agent', content: '🏭 Central RAG Copilot initialized. Upload a manual and ask any maintenance questions.' }
          ];
        }
      })
      .addCase(fetchAssistantHistory.fulfilled, (state, action) => {
        const { messages } = action.payload;
        state.chatHistory['assistant'] = messages.map((m: any) => ({
          role: m.role,
          content: m.content,
          images: m.images || [],
          timestamp: m.timestamp,
          context_source: m.context_source
        }));
      })
      .addCase(inquireAssistant.fulfilled, (state, action) => {
        const payload = action.payload;
        const msg: ChatMessage = {
          role: 'agent',
          content: payload.content || payload.answer,
          images: payload.images || [],
          timestamp: payload.timestamp,
          context_source: payload.context_source
        };
        if (!state.chatHistory['assistant']) {
          state.chatHistory['assistant'] = [];
        }
        state.chatHistory['assistant'].push(msg);

        if (payload.session_id) {
          state.activeAssistantSessionId = payload.session_id;
        }
      });
  },
});

export const { addChatMessage, setAssistantSidebarOpen, setActiveAssistantSessionId, setExportProgress, resetExportProgress } = copilotSlice.actions;
export default copilotSlice.reducer;
