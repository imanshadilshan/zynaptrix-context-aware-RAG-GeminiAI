import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { addChatMessage } from './copilotSlice';

interface IngestionState {
  isUploading: boolean;
  uploadStatus: string | null;
  error: string | null;
}

const initialState: IngestionState = {
  isUploading: false,
  uploadStatus: null,
  error: null,
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const uploadManual = createAsyncThunk(
  'ingestion/uploadManual',
  async (payload: { manualId: string; file: File }, { dispatch }) => {
    const formData = new FormData();
    formData.append("manual_id", payload.manualId);
    formData.append("file", payload.file);

    const response = await fetch(`${API_BASE}/api/rag/ingest-manual`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Upload failed');
    }
    
    // Side effect: Notify chat of successful vector ingestion
    dispatch(addChatMessage({ 
        role: 'agent', 
        content: `📚 Technical manual "${payload.manualId}" successfully ingested and vectorized in Neon DB.` 
    }));
    
    return payload.manualId;
  }
);

const ingestionSlice = createSlice({
  name: 'ingestion',
  initialState,
  reducers: {
    clearUploadStatus(state) {
      state.uploadStatus = null;
      state.error = null;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(uploadManual.pending, (state) => {
        state.isUploading = true;
        state.uploadStatus = "Uploading to AI Ingestion Pipeline...";
      })
      .addCase(uploadManual.fulfilled, (state) => {
        state.isUploading = false;
        state.uploadStatus = "Ingestion Successful!";
      })
      .addCase(uploadManual.rejected, (state, action) => {
        state.isUploading = false;
        state.error = action.error.message || 'Upload failed';
        state.uploadStatus = `Error: ${state.error}`;
      });
  },
});

export const { clearUploadStatus } = ingestionSlice.actions;
export default ingestionSlice.reducer;
