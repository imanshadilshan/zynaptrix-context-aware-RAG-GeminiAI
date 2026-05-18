"use client"

import React, { useState, useEffect, useRef, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Send, 
  Bot, 
  User, 
  Download,
  AlertTriangle,
  CheckCircle2,
  Hammer,
  Menu,
  Sparkles,
  HelpCircle,
  FileText
} from 'lucide-react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '../store/store';
import { 
  fetchAssistantSessions, 
  setActiveAssistantSessionId, 
  inquireAssistant, 
  exportAssistantSession,
  resetExportProgress,
  fetchAssistantHistory
} from '../store/slices/copilotSlice';
import { fetchMachines } from '../store/slices/machineSlice';
import AssistantSidebar from '../components/AssistantSidebar';
import AssistantMachineSelector from '../components/AssistantMachineSelector';
import ExportProgressModal from '../components/ExportProgressModal';

export default function CentralRAGWorkspace() {
  const dispatch = useDispatch<AppDispatch>();
  
  // State from Redux
  const { 
    chatHistory, 
    activeAssistantSessionId, 
    isAssistantSidebarOpen,
    assistantMachineId,
    exportProgress
  } = useSelector((state: RootState) => state.copilot);
  const { machines } = useSelector((state: RootState) => state.machines);
  
  // Local UI States
  const [query, setQuery] = useState('');
  const [isMounted, setIsMounted] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsMounted(true);
    dispatch(fetchMachines());
    dispatch(fetchAssistantSessions());
  }, [dispatch]);

  // Scroll to bottom when chat updates
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, activeAssistantSessionId]);

  const activeMessages = useMemo(() => {
    return chatHistory['assistant'] || [];
  }, [chatHistory]);

  const handleSend = () => {
    if (!query.trim()) return;
    const finalQuery = query;
    setQuery('');
    
    dispatch(inquireAssistant({
      query: finalQuery,
      machineId: assistantMachineId || undefined,
      sessionId: activeAssistantSessionId || undefined
    }));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickAction = (actionText: string) => {
    dispatch(inquireAssistant({
      query: actionText,
      machineId: assistantMachineId || undefined,
      sessionId: activeAssistantSessionId || undefined
    }));
  };

  // Convert raw text into markdown, inlining [IMAGE_N] references
  const renderMessageContent = (text: string, images?: string[]) => {
    let processedText = text || "";
    
    // Safety Critique Highlights
    const hasSafetyAlert = processedText.toLowerCase().includes("[safety_alert]") || 
                           processedText.toLowerCase().includes("loto") ||
                           processedText.toLowerCase().includes("ppe");
    
    if (images && images.length > 0) {
      images.forEach((url, idx) => {
        const tag = new RegExp(`\\[IMAGE[_\s-]?${idx}\\]`, 'gi');
        processedText = processedText.replace(tag, `\n\n![Technical Diagram Ref ${idx+1}](${url})\n\n`);
      });
    }

    return (
      <div className="flex flex-col gap-3">
        {hasSafetyAlert && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex gap-3 text-amber-200">
            <AlertTriangle className="text-amber-500 shrink-0" size={20} />
            <div className="text-xs">
              <span className="font-black uppercase tracking-wider block mb-1">Safety Critic Compliance Warning</span>
              Ensure Lockout/Tagout (LOTO) procedures are fully engaged. Confirm proper Personal Protective Equipment (PPE) is active before continuing.
            </div>
          </div>
        )}

        <div className="markdown-content">
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]} 
            components={{ 
              img: ({node, ...props}) => (
                <div className="flex flex-col items-center my-4 group">
                  <img 
                    {...props} 
                    className="max-w-full md:max-w-2xl max-h-80 object-contain rounded-xl border border-slate-700 shadow-2xl transition-all duration-300 hover:scale-[1.02]" 
                  />
                  <span className="text-[10px] text-slate-500 mt-2 font-bold uppercase tracking-wider">{props.alt || "Diagram Crop"}</span>
                </div>
              )
            }}
          >
            {processedText}
          </ReactMarkdown>
        </div>
      </div>
    );
  };

  const activeSessionTitle = useMemo(() => {
    if (!activeAssistantSessionId) return "New Maintenance Query";
    const session = machines.find(m => m.machine_id === assistantMachineId);
    return session ? `Copilot: ${session.name} Session` : "Copilot Dialog";
  }, [activeAssistantSessionId, assistantMachineId, machines]);

  if (!isMounted) return null;

  return (
    <div className="flex h-[calc(100vh-73px)] overflow-hidden text-slate-200 relative">
      
      {/* Dynamic Sidebar Container */}
      <AssistantSidebar />

      {/* Primary Chat Box Workspace */}
      <div className="flex-1 flex flex-col h-full bg-[#030712]/30 backdrop-blur-md relative">
        
        {/* Workspace Top Header Bar */}
        <div className="border-b border-slate-800 px-6 py-4 flex items-center justify-between bg-slate-950/80 backdrop-blur-md z-10 shadow-lg">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600/10 p-2 rounded-xl border border-blue-500/20 text-blue-400">
              <Sparkles size={16} />
            </div>
            <div>
              <h2 className="text-sm font-black text-white uppercase tracking-wider">{activeSessionTitle}</h2>
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-0.5">Gemini 2.5 Multi-Agent Engine</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <AssistantMachineSelector />
            
            {activeAssistantSessionId && (
              <button
                onClick={() => dispatch(exportAssistantSession(activeAssistantSessionId))}
                className="flex items-center gap-2 px-4 py-2 bg-slate-900 border border-slate-800 hover:border-blue-500/40 rounded-xl text-xs font-black uppercase tracking-wider text-slate-300 transition-all hover:scale-105 active:scale-95 shadow-md"
              >
                <Download size={14} className="text-blue-500" />
                Export PDF
              </button>
            )}
          </div>
        </div>

        {/* Message Feed Canvas */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-slate-800">
          {activeMessages.map((msg, index) => {
            const isAgent = msg.role === 'agent';
            return (
              <div 
                key={`msg-${index}`} 
                className={`flex gap-4 max-w-4xl ${isAgent ? 'mr-auto' : 'ml-auto flex-row-reverse'}`}
              >
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border shadow-lg ${
                  isAgent 
                    ? 'bg-blue-600/10 border-blue-500/30 text-blue-400' 
                    : 'bg-emerald-600/10 border-emerald-500/30 text-emerald-400'
                }`}>
                  {isAgent ? <Bot size={16} /> : <User size={16} />}
                </div>

                <div className={`p-5 rounded-2xl border text-sm leading-relaxed shadow-xl relative ${
                  isAgent 
                    ? 'bg-slate-900/60 border-slate-800/80 rounded-tl-none' 
                    : 'bg-slate-850 border-slate-800 rounded-tr-none'
                }`}>
                  {renderMessageContent(msg.content, msg.images)}
                  
                  {isAgent && msg.context_source && (
                    <span className="absolute bottom-2 right-4 text-[8px] font-black uppercase tracking-widest text-slate-600 bg-slate-950/40 px-2 py-0.5 rounded-lg border border-slate-800">
                      Context: {msg.context_source}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
          <div ref={chatEndRef} />
        </div>

        {/* Dynamic Quick Actions Suggestion Tray */}
        {activeMessages.length <= 1 && (
          <div className="px-6 py-2 flex flex-wrap gap-2 justify-center max-w-3xl mx-auto">
            <button 
              onClick={() => handleQuickAction("Generate a full maintenance manual checklist.")}
              className="px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-blue-500/40 rounded-xl text-[10px] font-black uppercase tracking-wider text-slate-400 hover:text-white transition-all"
            >
              🛠️ Checklist Manual
            </button>
            <button 
              onClick={() => handleQuickAction("What are the core LOTO safety rules for these pumps?")}
              className="px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-amber-500/40 rounded-xl text-[10px] font-black uppercase tracking-wider text-slate-400 hover:text-white transition-all"
            >
              ⚠️ Safety Requirements
            </button>
            <button 
              onClick={() => handleQuickAction("Show structural components and diagrams.")}
              className="px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-teal-500/40 rounded-xl text-[10px] font-black uppercase tracking-wider text-slate-400 hover:text-white transition-all"
            >
              📊 Inspect Diagrams
            </button>
          </div>
        )}

        {/* Dialogue Input Footer Tray */}
        <div className="p-6 border-t border-slate-850 bg-slate-950/80 backdrop-blur-md">
          <div className="max-w-4xl mx-auto relative flex items-center gap-3">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about maintenance procedures or manuals..."
              className="w-full bg-[#070b19] border border-slate-800 focus:border-blue-500/50 rounded-2xl py-3 pl-4 pr-16 text-sm text-slate-200 placeholder-slate-600 outline-none transition-all resize-none shadow-2xl"
              rows={1}
              style={{ maxHeight: '120px' }}
            />
            <button
              onClick={handleSend}
              disabled={!query.trim()}
              className="absolute right-3 p-2 bg-blue-600 disabled:bg-slate-800 text-white disabled:text-slate-600 rounded-xl transition-all hover:scale-105 active:scale-95 shadow-lg flex items-center justify-center cursor-pointer"
            >
              <Send size={16} />
            </button>
          </div>
          <p className="text-center text-[9px] font-bold uppercase tracking-widest text-slate-600 mt-2">
            AI-generated responses can be compiled as professional diagnostic reports.
          </p>
        </div>

      </div>

      {/* Export Report Progress Modal */}
      <ExportProgressModal 
        isOpen={exportProgress.isExporting}
        progress={exportProgress.progress}
        status={exportProgress.status}
        errorMessage={exportProgress.errorMessage}
        onClose={() => dispatch(resetExportProgress())}
      />

    </div>
  );
}
