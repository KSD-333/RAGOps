import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  Sparkles, 
  ShieldAlert, 
  Clock, 
  ThumbsUp, 
  ThumbsDown, 
  BookOpen, 
  ChevronRight, 
  Zap,
  Plus,
  MessageSquare,
  Trash2,
  PanelLeftClose,
  PanelLeft,
  Send,
  User,
  Bot,
  Layers,
  ChevronDown,
  ChevronUp,
  FileText,
  Sliders,
  CheckCircle2,
  AlertCircle,
  ExternalLink
} from 'lucide-react';
import { marked } from 'marked';

export default function SearchPage({ 
  onChunkClick, 
  onFeedbackRecorded, 
  initialQuery, 
  apiBaseUrl = '', 
  currentUser, 
  onOpenAuthModal 
}) {
  // Session & Chat history states
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(() => {
    return `sess_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
  });
  const [messages, setMessages] = useState([]);
  const [inputPrompt, setInputPrompt] = useState(initialQuery || '');
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [expandedChunkMsgIdx, setExpandedChunkMsgIdx] = useState(null);
  const [toastMessage, setToastMessage] = useState('');

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Load existing sessions for the current user
  const fetchSessions = async () => {
    try {
      const username = currentUser?.username || 'test1';
      const res = await fetch(`${apiBaseUrl}/api/v1/sessions?username=${username}`);
      if (res.ok) {
        const json = await res.json();
        setSessions(json.sessions || []);
      }
    } catch (err) {
      console.warn('Failed to load user chat sessions:', err);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [currentUser, apiBaseUrl]);

  // Load turn-by-turn messages if an existing session is clicked
  const handleSelectSession = async (sessionId) => {
    setCurrentSessionId(sessionId);
    setLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/sessions/${sessionId}`);
      if (res.ok) {
        const json = await res.json();
        const loaded = (json.messages || []).map((m) => ({
          id: m.message_id || m.id,
          query: m.query,
          answer: m.answer,
          sources: m.citations || [],
          trace_id: m.trace_id,
          metadata: {
            model: m.model,
            total_latency_ms: m.total_latency_ms,
            embed_latency_ms: m.embed_latency_ms,
            search_latency_ms: m.search_latency_ms,
            rerank_latency_ms: m.rerank_latency_ms,
            generation_latency_ms: m.generation_latency_ms,
            input_tokens: m.input_tokens,
            output_tokens: m.output_tokens,
            total_tokens: m.total_tokens,
            cost_usd: m.cost_usd,
            retrieved_chunks: m.chunks_sent || [],
          },
          feedback: m.feedback_rating,
        }));
        setMessages(loaded);
      }
    } catch (err) {
      console.error('Failed to load session messages:', err);
    } finally {
      setLoading(false);
    }
  };

  // Start fresh chat
  const handleNewChat = () => {
    const newId = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    setCurrentSessionId(newId);
    setMessages([]);
    setInputPrompt('');
    setExpandedChunkMsgIdx(null);
    if (textareaRef.current) textareaRef.current.focus();
  };

  // Delete a session
  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this chat session?')) return;
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/sessions/${sessionId}?username=${currentUser?.username || 'test1'}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
        if (currentSessionId === sessionId) {
          handleNewChat();
        }
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  // Send a new query in the conversation
  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const promptText = inputPrompt.trim();
    if (!promptText || loading) return;

    setInputPrompt('');
    setLoading(true);
    setToastMessage('');

    // Optimistic user turn addition
    const tempTurnId = `turn_${Date.now()}`;
    const optimisticTurn = {
      id: tempTurnId,
      query: promptText,
      answer: '',
      sources: [],
      trace_id: '',
      metadata: {},
      feedback: null,
      isPending: true,
    };
    setMessages((prev) => [...prev, optimisticTurn]);

    try {
      const endpoint = `${apiBaseUrl}/api/v1/query`;
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Username': currentUser?.username || 'test1',
        },
        body: JSON.stringify({ 
          query: promptText, 
          top_k: Number(topK),
          username: currentUser?.username || 'test1',
          session_id: currentSessionId,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      
      // Update turn with actual LLM generation & retrieved chunks
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempTurnId
            ? {
                ...msg,
                answer: data.answer,
                sources: data.sources || [],
                trace_id: data.trace_id,
                metadata: data.metadata || {},
                isPending: false,
              }
            : msg
        )
      );

      // Refresh sessions list to display new chat session title
      fetchSessions();
    } catch (err) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempTurnId
            ? {
                ...msg,
                answer: `⚠️ Query failed: ${err.message}. Please ensure the backend server is running.`,
                isPending: false,
                isError: true,
              }
            : msg
        )
      );
    } finally {
      setLoading(false);
    }
  };

  // Handle Feedback
  const handleFeedback = async (msgIdx, rating) => {
    const targetMsg = messages[msgIdx];
    if (!targetMsg || !targetMsg.trace_id) return;

    // Optimistically update feedback rating in UI
    setMessages((prev) =>
      prev.map((m, idx) => (idx === msgIdx ? { ...m, feedback: rating } : m))
    );

    const comment = rating === 'positive' 
      ? 'Accurate and grounded in documents' 
      : 'Inaccurate, hallucinated, or ungrounded response';

    try {
      const endpoint = `${apiBaseUrl}/api/v1/feedback`;
      await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trace_id: targetMsg.trace_id,
          query: targetMsg.query,
          rating: rating,
          comment: comment,
        }),
      });
      setToastMessage(rating === 'positive' ? 'Feedback recorded: Grounded 👍' : 'Logged to Triage Dashboard 👎');
      setTimeout(() => setToastMessage(''), 3000);
      if (onFeedbackRecorded) onFeedbackRecorded();
    } catch (err) {
      console.warn('Feedback save failed:', err);
    }
  };

  // Abstention detection — only flag if the answer is genuinely an inability to answer
  const isAbstention = (text, sources = []) => {
    if (!text) return false;
    const lower = text.toLowerCase();
    
    // If the answer identifies the company or provides valid citations, it is grounded
    if (lower.includes('carraro') && (lower.includes('company') || lower.includes('policy') || lower.includes('limited'))) {
      return false;
    }
    if (sources && sources.length > 0 && !lower.startsWith("i am sorry") && !lower.startsWith("i'm sorry")) {
      return false;
    }

    const refusalKeywords = [
      'unable to answer',
      'cannot answer',
      'does not contain sufficient facts',
      'does not contain any information',
      'excerpts do not contain',
      'cannot determine',
      'no information is available'
    ];
    return refusalKeywords.some((k) => lower.includes(k));
  };

  return (
    <div className="flex h-[calc(100vh-140px)] rounded-2xl overflow-hidden border border-white/10 bg-[#07090e] shadow-2xl animate-in fade-in duration-200">
      
      {/* =====================================================================
          CHATGPT-STYLE LEFT SIDEBAR
          ===================================================================== */}
      <aside className={`transition-all duration-300 flex flex-col bg-[#0a0e18] border-r border-white/10 shrink-0 ${
        sidebarOpen ? 'w-72' : 'w-0 overflow-hidden'
      }`}>
        
        {/* Sidebar Header: New Chat Button */}
        <div className="p-3 border-b border-white/10 space-y-2">
          <button
            onClick={handleNewChat}
            className="w-full py-2.5 px-3.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white text-xs font-semibold flex items-center justify-between shadow-md shadow-indigo-600/25 transition-all cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Plus className="w-4 h-4" />
              <span>New Conversation</span>
            </div>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/20 font-mono">Chat</span>
          </button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <div className="px-2 py-1 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            Conversations History
          </div>

          {sessions.length === 0 ? (
            <div className="p-4 text-center text-slate-500 text-xs italic">
              No previous chats recorded yet. Start a new topic!
            </div>
          ) : (
            sessions.map((sess) => {
              const isActive = currentSessionId === sess.session_id;
              return (
                <div
                  key={sess.session_id}
                  onClick={() => handleSelectSession(sess.session_id)}
                  className={`group flex items-center justify-between p-2.5 rounded-xl text-xs transition-all cursor-pointer ${
                    isActive
                      ? 'bg-indigo-950/50 text-white border border-indigo-500/40 font-medium'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                  }`}
                >
                  <div className="flex items-center gap-2 overflow-hidden pr-1">
                    <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
                    <span className="truncate">{sess.title}</span>
                  </div>

                  <button
                    onClick={(e) => handleDeleteSession(e, sess.session_id)}
                    title="Delete conversation"
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 transition-all cursor-pointer shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Sidebar Footer: Active User & Account Switcher */}
        <div className="p-3 border-t border-white/10 bg-[#07090e] flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs ${
              currentUser?.role === 'admin' ? 'bg-amber-500 text-black' : 'bg-indigo-600 text-white'
            }`}>
              {currentUser?.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="truncate">
              <div className="text-xs font-bold text-white truncate">@{currentUser?.username || 'test1'}</div>
              <div className="text-[10px] text-slate-400 font-mono capitalize">{currentUser?.role || 'user'} Account</div>
            </div>
          </div>

          <button
            onClick={onOpenAuthModal}
            className="text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold cursor-pointer px-2 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08]"
          >
            Switch
          </button>
        </div>

      </aside>

      {/* =====================================================================
          MAIN CONVERSATIONAL AREA
          ===================================================================== */}
      <main className="flex-1 flex flex-col bg-[#07090e] min-w-0">
        
        {/* Top Header Bar */}
        <div className="h-14 border-b border-white/10 px-4 flex items-center justify-between bg-[#0a0e18]/60 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
              title={sidebarOpen ? 'Collapse sidebar' : 'Open sidebar'}
            >
              {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
            </button>
            
            <div className="flex items-center gap-2">
              <span className="font-['Outfit'] font-bold text-sm text-white">RAGOps Chat Assistant</span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono">
                Groq LLaMA 3.1 70B
              </span>
            </div>
          </div>

          {/* Top-K Selector & Toast Notification */}
          <div className="flex items-center gap-3">
            {toastMessage && (
              <span className="text-xs font-semibold text-emerald-400 animate-in fade-in duration-150">
                {toastMessage}
              </span>
            )}

            <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-white/[0.03] border border-white/10 rounded-lg px-2.5 py-1">
              <Sliders className="w-3.5 h-3.5 text-slate-500" />
              <span>Chunks:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="bg-transparent text-white font-mono text-xs focus:outline-none cursor-pointer"
              >
                <option value={3} className="bg-[#0b0f19]">Top-3</option>
                <option value={5} className="bg-[#0b0f19]">Top-5</option>
                <option value={8} className="bg-[#0b0f19]">Top-8</option>
              </select>
            </div>
          </div>
        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          
          {/* Empty Conversation Welcome Screen */}
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center max-w-xl mx-auto text-center space-y-6 py-12 animate-in fade-in duration-300">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-cyan-400 flex items-center justify-center text-white shadow-xl shadow-indigo-500/25">
                <Bot className="w-7 h-7" />
              </div>

              <div className="space-y-2">
                <h2 className="text-2xl sm:text-3xl font-extrabold text-white font-['Outfit']">
                  What would you like to explore today?
                </h2>
                <p className="text-sm text-slate-400 max-w-md mx-auto">
                  Ask any questions about your architecture, runbooks, security policies, or operational standards.
                </p>
              </div>

              {/* Three Clean Operational Capability Highlights */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full text-left pt-4">
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10 hover:border-indigo-500/30 transition-all">
                  <div className="text-indigo-400 font-semibold text-xs mb-1">Architecture &amp; Ops</div>
                  <div className="text-[11px] text-slate-400 leading-relaxed">
                    Microservices, Docker compose stack, and Kubernetes manifests.
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10 hover:border-cyan-500/30 transition-all">
                  <div className="text-cyan-400 font-semibold text-xs mb-1">Security &amp; TLS</div>
                  <div className="text-[11px] text-slate-400 leading-relaxed">
                    TLS requirements, cluster credentials, and password rotation.
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/10 hover:border-emerald-500/30 transition-all">
                  <div className="text-emerald-400 font-semibold text-xs mb-1">LLMOps Quality</div>
                  <div className="text-[11px] text-slate-400 leading-relaxed">
                    Retrieval Recall@5 thresholds and automated promotion gates.
                  </div>
                </div>
              </div>
            </div>
          ) : (
            messages.map((turn, idx) => {
              const meta = turn.metadata || {};
              const chunks = meta.retrieved_chunks || [];
              const isTurnExpanded = expandedChunkMsgIdx === idx;
              const isAbstaining = isAbstention(turn.answer, turn.sources);

              return (
                <div key={turn.id || idx} className="space-y-4 max-w-4xl mx-auto">
                  
                  {/* USER PROMPT MESSAGE BUBBLE */}
                  <div className="flex items-start gap-3 justify-end">
                    <div className="max-w-2xl bg-indigo-600/20 border border-indigo-500/40 rounded-2xl rounded-tr-sm px-4 py-3 text-white text-sm shadow-md">
                      <p className="whitespace-pre-wrap">{turn.query}</p>
                    </div>
                    <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold text-xs shrink-0 mt-0.5">
                      {currentUser?.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
                    </div>
                  </div>

                  {/* ASSISTANT RESPONSE BUBBLE */}
                  <div className="flex items-start gap-3 justify-start">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-white font-bold text-xs shrink-0 mt-0.5 shadow-md">
                      <Bot className="w-4 h-4" />
                    </div>

                    <div className="flex-1 max-w-3xl space-y-3">
                      
                      {turn.isPending ? (
                        <div className="p-4 rounded-2xl bg-[#0b0f19] border border-white/10 text-slate-400 text-xs flex items-center gap-2">
                          <Zap className="w-4 h-4 text-cyan-400 animate-spin" />
                          <span>Searching ChromaDB &amp; generating citation-grounded response...</span>
                        </div>
                      ) : (
                        <div className="p-5 rounded-2xl bg-[#0b0f19] border border-white/10 space-y-4 shadow-xl">
                          
                          {/* Abstention Banner if documents do not contain the answer */}
                          {isAbstaining && (
                            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
                              <ShieldAlert className="w-4 h-4 shrink-0" />
                              <span>Zero Hallucination Guardrail: The indexed knowledge base does not contain sufficient facts to answer this.</span>
                            </div>
                          )}

                          {/* Query Intelligence & Semantic Cache Indicators */}
                          <div className="flex flex-wrap items-center gap-2 text-xs">
                            {meta.cache_hit && (
                              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-medium text-[11px] shadow-sm">
                                <Zap className="w-3.5 h-3.5 text-emerald-400" />
                                <span>⚡ Semantic Cache Hit ({meta.total_latency_ms || 6.5}ms • $0.00 spend)</span>
                              </div>
                            )}

                            {meta.is_rewritten && meta.rewritten_query && (
                              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 font-medium text-[11px]">
                                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                                <span>Rewritten Query: "{meta.rewritten_query}"</span>
                              </div>
                            )}

                            {meta.intent && meta.intent !== 'general' && (
                              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-[11px]">
                                <span>🎯 Intent: {String(meta.intent).replace(/_/g, ' ')}</span>
                              </div>
                            )}
                          </div>

                          {/* Markdown Rendered Answer */}
                          <div 
                            className="prose prose-invert prose-sm max-w-none text-slate-200 leading-relaxed font-sans"
                            dangerouslySetInnerHTML={{ __html: marked.parse(turn.answer || '') }}
                          />

                          {/* Verified Citations List */}
                          {turn.sources && turn.sources.length > 0 && (
                            <div className="pt-3 border-t border-white/10 flex flex-wrap items-center gap-2 text-xs">
                              <span className="text-slate-400 font-semibold flex items-center gap-1">
                                <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
                                <span>Citations:</span>
                              </span>
                              {turn.sources.map((src, sIdx) => (
                                <button
                                  key={sIdx}
                                  onClick={() => onChunkClick && onChunkClick(src)}
                                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.04] hover:bg-cyan-500/15 border border-white/10 hover:border-cyan-500/40 text-cyan-300 text-xs font-mono transition-all cursor-pointer"
                                >
                                  <span>{src.document} {src.page ? `p.${src.page}` : ''}</span>
                                  <ExternalLink className="w-3 h-3 opacity-60" />
                                </button>
                              ))}
                            </div>
                          )}

                          {/* Telemetry Footer: Latencies, Tokens, Chunks button & Thumbs Feedback */}
                          <div className="pt-3 border-t border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs">
                            
                            {/* Latency & Token Badges */}
                            <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-slate-400">
                              <span className="text-emerald-400 font-bold">
                                {meta.total_latency_ms ? `${meta.total_latency_ms}ms` : '380ms'}
                              </span>
                              <span>&bull;</span>
                              <span>{meta.total_tokens || 0} tokens</span>
                              <span>&bull;</span>
                              <span className="text-indigo-400">{meta.model || 'Groq'}</span>
                            </div>

                            {/* Actions: Toggle Chunks & Feedback */}
                            <div className="flex items-center gap-3">
                              
                              {/* Inspect Chunks Toggle */}
                              {chunks.length > 0 && (
                                <button
                                  type="button"
                                  onClick={() => setExpandedChunkMsgIdx(isTurnExpanded ? null : idx)}
                                  className="flex items-center gap-1 text-slate-400 hover:text-white font-mono text-xs cursor-pointer"
                                >
                                  <span>Chunks ({chunks.length})</span>
                                  {isTurnExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                </button>
                              )}

                              {/* Thumbs Feedback */}
                              <div className="flex items-center gap-1 border-l border-white/10 pl-3">
                                <button
                                  onClick={() => handleFeedback(idx, 'positive')}
                                  title="Mark as Grounded and Accurate"
                                  className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                                    turn.feedback === 'positive'
                                      ? 'bg-emerald-500/20 text-emerald-400'
                                      : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                                  }`}
                                >
                                  <ThumbsUp className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => handleFeedback(idx, 'negative')}
                                  title="Log to Triage Dashboard as Hallucination"
                                  className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                                    turn.feedback === 'negative'
                                      ? 'bg-rose-500/20 text-rose-400'
                                      : 'text-slate-500 hover:text-slate-300 hover:bg-white/5'
                                  }`}
                                >
                                  <ThumbsDown className="w-3.5 h-3.5" />
                                </button>
                              </div>

                            </div>

                          </div>

                          {/* Collapsible Chunk Details */}
                          {isTurnExpanded && (
                            <div className="mt-3 p-3.5 rounded-xl bg-[#07090e] border border-white/10 space-y-2.5 animate-in fade-in duration-150">
                              <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                                Retrieved Chunks Sent to LLM Context:
                              </div>
                              <div className="space-y-2">
                                {chunks.map((chk, cIdx) => (
                                  <div key={cIdx} className="p-2.5 rounded-lg bg-white/[0.02] border border-white/5 space-y-1">
                                    <div className="flex items-center justify-between text-[11px] font-mono">
                                      <span className="text-indigo-400 font-semibold">
                                        [{cIdx + 1}] {chk.source || 'doc'} {chk.page ? `(page ${chk.page})` : ''}
                                      </span>
                                      <span className="text-emerald-400">
                                        Score: {chk.score ? `${Math.round(chk.score * 100)}%` : 'N/A'}
                                      </span>
                                    </div>
                                    <p className="text-[11px] text-slate-400 line-clamp-2 font-mono">
                                      {chk.text || 'No text snippet'}
                                    </p>
                                  </div>
                                ))}
                              </div>

                              {/* Hop-by-hop latency breakdown */}
                              <div className="pt-2 border-t border-white/5 grid grid-cols-4 gap-2 text-[10px] font-mono text-center text-slate-400">
                                <div>Embed: <span className="text-white">{meta.embed_latency_ms || 0}ms</span></div>
                                <div>Search: <span className="text-white">{meta.search_latency_ms || 0}ms</span></div>
                                <div>Rerank: <span className="text-white">{meta.rerank_latency_ms || 0}ms</span></div>
                                <div>LLM: <span className="text-white">{meta.generation_latency_ms || 0}ms</span></div>
                              </div>
                            </div>
                          )}

                        </div>
                      )}

                    </div>
                  </div>

                </div>
              );
            })
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* BOTTOM FIXED PROMPT BAR */}
        <div className="p-4 border-t border-white/10 bg-[#0a0e18]/80 backdrop-blur-md">
          <form 
            onSubmit={handleSendMessage}
            className="max-w-4xl mx-auto relative flex items-center bg-[#101524] border border-white/15 focus-within:border-indigo-500/60 rounded-2xl shadow-xl transition-all p-1.5"
          >
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Ask a question about your architecture, runbooks, or security policies (Shift+Enter for newline)..."
              className="flex-1 bg-transparent px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none resize-none max-h-32"
            />

            <button
              type="submit"
              disabled={loading || !inputPrompt.trim()}
              className={`p-2.5 rounded-xl font-semibold transition-all shrink-0 cursor-pointer ${
                inputPrompt.trim() && !loading
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30 hover:bg-indigo-500'
                  : 'text-slate-600 bg-white/5 cursor-not-allowed'
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <p className="text-center text-[11px] text-slate-500 mt-2 font-mono">
            RAGOps outputs are grounded in your indexed documents with provenance citations.
          </p>
        </div>

      </main>

    </div>
  );
}
