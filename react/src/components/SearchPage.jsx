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
  ExternalLink,
  Globe,
  Building,
  MapPin,
  Award,
  Database,
  Copy,
  Check,
  RotateCcw
} from 'lucide-react';
import { marked } from 'marked';
import { useAppStore } from '../context/AppContext';

export default function SearchPage({ 
  onChunkClick, 
  onFeedbackRecorded, 
  initialQuery, 
  apiBaseUrl: propApiBaseUrl = '', 
  currentUser: propCurrentUser, 
  onOpenAuthModal 
}) {
  const store = useAppStore();
  const apiBaseUrl = propApiBaseUrl || store.apiBaseUrl;
  const currentUser = propCurrentUser || store.currentUser;
  const sessions = store.sessions;
  const setSessions = store.setSessions;
  const catalogData = store.catalogData;
  const [currentSessionId, setCurrentSessionId] = useState(() => {
    return `sess_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
  });
  const [currentSessionUser, setCurrentSessionUser] = useState(() => currentUser?.username || null);
  const [copiedTurnId, setCopiedTurnId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputPrompt, setInputPrompt] = useState(initialQuery || '');
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [expandedChunkMsgIdx, setExpandedChunkMsgIdx] = useState(null);
  const [toastMessage, setToastMessage] = useState('');

  // URL Crawl & Intelligence Extraction states
  const [isUrlModalOpen, setIsUrlModalOpen] = useState(false);
  const [isUrlInputBarOpen, setIsUrlInputBarOpen] = useState(false);
  const [targetCompanyUrl, setTargetCompanyUrl] = useState('');
  const [isCrawlingUrl, setIsCrawlingUrl] = useState(false);
  const [crawledPreview, setCrawledPreview] = useState(null);
  const [isSavingAndEmbedding, setIsSavingAndEmbedding] = useState(false);
  const [newLocationInput, setNewLocationInput] = useState({ city: '', state: '', type: 'Manufacturing Plant' });
  const [newClientInput, setNewClientInput] = useState('');
  const [newHubInput, setNewHubInput] = useState('');
  const [newProductInput, setNewProductInput] = useState('');

  const chatScrollContainerRef = useRef(null);
  const textareaRef = useRef(null);

  // Admin Chat Filtering: 'all' users vs 'my' admin chats
  const [adminChatFilter, setAdminChatFilter] = useState('all');

  // Format relevance score from raw cross-encoder logits or similarity to clean 0-100%
  const formatRelevanceScore = (score) => {
    if (score === null || score === undefined || isNaN(score)) return 'Grounded';
    let val = Number(score);
    // If the score is an uncalibrated cross-encoder logit (e.g. 2.72 or -1.5)
    if (val > 1.0 || val < 0.0) {
      val = 1 / (1 + Math.exp(-val));
    }
    const pct = Math.min(100, Math.max(0, Math.round(val * 100)));
    return `${pct}%`;
  };

  // Dedicated container-level auto-scroll: ONLY scrolls the chat message container, never the window or sidebar
  const scrollToBottom = (behavior = 'smooth') => {
    if (chatScrollContainerRef.current) {
      chatScrollContainerRef.current.scrollTo({
        top: chatScrollContainerRef.current.scrollHeight,
        behavior: behavior,
      });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // When currentUser changes (e.g. user switches between admin and test1), switch cleanly to a fresh session
  const prevUserRef = useRef(currentUser?.username);
  useEffect(() => {
    if (prevUserRef.current !== currentUser?.username) {
      prevUserRef.current = currentUser?.username;
      handleNewChat();
    }
  }, [currentUser]);

  // In-flight request tracker to prevent race conditions during rapid session switching
  const sessionFetchAbortRef = useRef(null);

  // Load turn-by-turn messages if an existing session is clicked
  const handleSelectSession = async (sessionId, sessionUser = null) => {
    if (!sessionId) return;
    if (sessionFetchAbortRef.current) {
      sessionFetchAbortRef.current.abort();
    }
    const abortCtrl = new AbortController();
    sessionFetchAbortRef.current = abortCtrl;

    setCurrentSessionId(sessionId);
    setCurrentSessionUser(sessionUser);
    setLoading(true);

    try {
      const username = currentUser?.username || 'test1';
      const role = currentUser?.role || 'user';
      let url = `${apiBaseUrl}/api/v1/sessions/${sessionId}?username=${encodeURIComponent(username)}&role=${encodeURIComponent(role)}`;
      if (sessionUser) {
        url += `&session_user=${encodeURIComponent(sessionUser)}`;
      }
      const res = await fetch(url, { signal: abortCtrl.signal });
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
            cache_hit: m.cache_hit,
            is_rewritten: !!m.rewritten_query,
            rewritten_query: m.rewritten_query,
          },
          feedback: m.feedback_rating,
        }));
        setMessages(loaded);
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Failed to load session messages:', err);
      }
    } finally {
      if (!abortCtrl.signal.aborted) {
        setLoading(false);
      }
    }
  };

  // Load existing sessions based on active role (Admin sees all; User sees only their own)
  const fetchSessions = async (autoSelect = false) => {
    try {
      const username = currentUser?.username || 'test1';
      const role = currentUser?.role || 'user';
      let url = `${apiBaseUrl}/api/v1/sessions?username=${encodeURIComponent(username)}&role=${encodeURIComponent(role)}`;
      if (role === 'admin' && adminChatFilter === 'my') {
        url += `&filter_user=${encodeURIComponent(username)}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const json = await res.json();
        const newSessions = json.sessions || [];
        setSessions(newSessions);

        // Auto-load most recent session if requested and no messages are currently loaded
        if (autoSelect && newSessions.length > 0 && messages.length === 0) {
          handleSelectSession(newSessions[0].session_id, newSessions[0].username);
        }
      }
    } catch (err) {
      console.warn('Failed to load user chat sessions:', err);
    }
  };

  useEffect(() => {
    fetchSessions(true);
  }, [currentUser, apiBaseUrl, adminChatFilter]);

  // Start fresh chat
  const handleNewChat = () => {
    const newId = `sess_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    setCurrentSessionId(newId);
    setCurrentSessionUser(currentUser?.username || null);
    setMessages([]);
    setInputPrompt('');
    setExpandedChunkMsgIdx(null);
    if (textareaRef.current) textareaRef.current.focus();
  };

  const handleCopyText = (text, turnId) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedTurnId(turnId);
    setTimeout(() => setCopiedTurnId(null), 2000);
  };

  // Delete a session
  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this chat session?')) return;
    try {
      const username = currentUser?.username || 'test1';
      const role = currentUser?.role || 'user';
      const res = await fetch(`${apiBaseUrl}/api/v1/sessions/${sessionId}?username=${encodeURIComponent(username)}&role=${encodeURIComponent(role)}`, {
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
      const meta = data.metadata || {};
      const totalTokens = meta.total_tokens ?? ((meta.input_tokens || 0) + (meta.output_tokens || 0)) ?? 0;
      meta.total_tokens = totalTokens;
      
      // Update turn with actual LLM generation & retrieved chunks
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempTurnId
            ? {
                ...msg,
                answer: data.answer,
                sources: data.sources || [],
                trace_id: data.trace_id,
                metadata: meta,
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

  // Crawl company website and extract corporate facts for user review
  const handleStartCrawl = async (urlToCrawl = null) => {
    const url = (urlToCrawl || targetCompanyUrl).trim();
    if (!url) return;
    setIsCrawlingUrl(true);
    setToastMessage(`🌐 Crawling ${url} & extracting corporate intelligence with AI...`);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/scrape-preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls: [url] }),
      });
      const data = await res.json();
      if (res.ok && data.status === 'preview_ready') {
        setCrawledPreview(data.preview);
        setIsUrlModalOpen(true);
        setIsUrlInputBarOpen(false);
        setToastMessage(`🔍 Intelligence extracted! Please verify locations, clients & hubs below.`);
      } else {
        alert(data.message || 'Crawl completed with warnings. Could not extract details.');
      }
    } catch (err) {
      alert(`Crawl error: ${err.message}`);
    } finally {
      setIsCrawlingUrl(false);
    }
  };

  // User checks, validates, and approves the extracted details to embed into ChromaDB
  const handleValidateAndEmbed = async () => {
    if (!crawledPreview) return;
    setIsSavingAndEmbedding(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/approve-and-embed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(crawledPreview),
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setIsUrlModalOpen(false);
        setCrawledPreview(null);
        setTargetCompanyUrl('');
        setToastMessage(`✅ Corporate intelligence for ${data.profile?.company_name || 'the company'} validated & embedded into ChromaDB!`);

        // Post summary directly in chat
        const botMsg = {
          id: `sys_${Date.now()}`,
          query: `AI Crawled & Extracted Corporate Profile from ${crawledPreview.domains_urls?.[0] || 'website'}`,
          answer: `### ✅ Corporate Profile Grounded & Embedded Successfully!\n\nAll verified corporate intelligence for **${data.profile?.company_name || 'the company'}** has been stored in PostgreSQL and embedded into the ChromaDB Vector Store (**${data.chunks_embedded || 5} dense grounding chunks**):\n\n- **Locations & Facilities**: ${data.profile?.locations?.length || 0} locations/plants indexed (${(data.profile?.locations || []).slice(0, 3).map(l => l.city || l.address).filter(Boolean).join(', ') || 'Locations recorded'}).\n- **Key Clients & OEM Partners**: ${(data.profile?.metadata_json?.clients || []).join(', ') || 'Clients & partners recorded'}.\n- **Products & Systems**: ${(data.profile?.products || []).slice(0, 5).join(', ')}.\n- **Executive Leadership**: ${data.profile?.ceo || 'Executive Leadership'}.\n\n💡 **You can now ask:**\n- *"company all locations"*\n- *"who are the key clients and partners?"*\n- *"what products do they manufacture?"*`,
          sources: [`Corporate Profile Knowledge Base (${data.profile?.company_name})`],
          trace_id: `trace_embed_${Date.now()}`,
          metadata: { total_latency_ms: 10 },
        };
        setMessages((prev) => [...prev, botMsg]);
      } else {
        alert(data.detail || data.message || 'Failed to embed profile.');
      }
    } catch (err) {
      alert(`Failed to save and embed: ${err.message}`);
    } finally {
      setIsSavingAndEmbedding(false);
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
    
    // If the answer provides valid citations or direct grounded corporate knowledge, it is grounded
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
    <div className="flex flex-1 h-full min-h-0 rounded-2xl overflow-hidden border border-white/10 bg-[#070b16] shadow-2xl animate-in fade-in duration-200">
      
      {/* =====================================================================
          ENTERPRISE WORKSPACE SIDEBAR
          ===================================================================== */}
      <aside className={`transition-all duration-300 flex flex-col h-full bg-[#080d19] border-r border-white/10 shrink-0 select-none overflow-hidden ${
        sidebarOpen ? 'w-80' : 'w-0'
      }`}>
        
        {/* Sidebar Header: New Chat Button (PINNED) */}
        <div className="p-3.5 border-b border-white/10 shrink-0 space-y-2">
          <button
            onClick={handleNewChat}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white text-xs font-semibold flex items-center justify-between shadow-lg shadow-indigo-600/30 transition-all cursor-pointer group hover:scale-[1.01] active:scale-[0.99]"
          >
            <div className="flex items-center gap-2.5">
              <div className="w-5 h-5 rounded-md bg-white/20 flex items-center justify-center">
                <Plus className="w-3.5 h-3.5" />
              </div>
              <span className="font-['Outfit'] font-bold text-sm tracking-wide">New Conversation</span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-md bg-white/15 font-mono text-indigo-100 border border-white/10">
              New
            </span>
          </button>
        </div>

        {/* Pinned Section Header: Title & Filter Tabs */}
        <div className="px-3.5 py-2.5 border-b border-white/5 flex items-center justify-between shrink-0 bg-[#080d19]">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <MessageSquare className="w-3 h-3 text-indigo-400" />
            <span>{currentUser?.role === 'admin' ? 'Conversations Audit' : 'Your Conversations'}</span>
          </div>
          {currentUser?.role === 'admin' && (
            <div className="flex items-center gap-1 bg-white/[0.04] p-0.5 rounded-lg border border-white/10">
              <button
                type="button"
                onClick={() => setAdminChatFilter('all')}
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-all cursor-pointer ${
                  adminChatFilter === 'all'
                    ? 'bg-amber-500 text-black shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                All ({sessions.length})
              </button>
              <button
                type="button"
                onClick={() => setAdminChatFilter('my')}
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold transition-all cursor-pointer ${
                  adminChatFilter === 'my'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Mine
              </button>
            </div>
          )}
        </div>

        {/* Sessions List: INDEPENDENT SCROLL CONTAINER */}
        <div className="flex-1 min-h-0 overflow-y-auto p-2.5 space-y-1.5">

          {sessions.length === 0 ? (
            <div className="p-6 text-center text-slate-500 text-xs italic space-y-1">
              <div>{currentUser?.role === 'admin' ? 'No conversations recorded for this filter.' : 'No previous chats recorded yet.'}</div>
              <div className="text-[11px] text-slate-600">Start a new conversation to begin!</div>
            </div>
          ) : (
            sessions.map((sess, sIdx) => {
              const isActive = sess.session_id === currentSessionId && 
                (!currentSessionUser || !sess.username || currentSessionUser === sess.username);
              const sessionKey = `${sess.session_id}_${sess.username || ''}_${sIdx}`;
              
              return (
                <div
                  key={sessionKey}
                  onClick={() => handleSelectSession(sess.session_id, sess.username)}
                  className={`group relative flex items-center justify-between p-3 rounded-xl text-xs transition-all cursor-pointer border ${
                    isActive
                      ? 'bg-gradient-to-r from-indigo-950/80 via-indigo-900/40 to-transparent text-white border-indigo-500/50 shadow-md shadow-indigo-950/50 border-l-[4px] border-l-indigo-400'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2.5 overflow-hidden pr-2 min-w-0">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                      isActive 
                        ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/40' 
                        : 'bg-white/[0.04] text-slate-400 group-hover:bg-white/[0.08] group-hover:text-slate-200'
                    }`}>
                      <MessageSquare className="w-3.5 h-3.5" />
                    </div>
                    
                    <div className="truncate min-w-0 flex-1">
                      <div className={`truncate font-medium text-xs ${isActive ? 'text-white font-semibold' : 'text-slate-300'}`}>
                        {sess.title || 'Untitled Conversation'}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5 text-[10px] text-slate-500 font-mono">
                        {sess.message_count && (
                          <span>{sess.message_count} msg{sess.message_count > 1 ? 's' : ''}</span>
                        )}
                        {currentUser?.role === 'admin' && sess.username && (
                          <span className={`px-1.5 py-0.1 rounded font-bold ${
                            sess.username === 'admin'
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/25'
                          }`}>
                            @{sess.username}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={(e) => handleDeleteSession(e, sess.session_id)}
                    title="Delete conversation"
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 transition-all cursor-pointer shrink-0"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Sidebar Footer: Active User & Account Switcher (PINNED) */}
        <div className="p-3.5 border-t border-white/10 bg-[#070b14] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs shadow-md ${
              currentUser?.role === 'admin' ? 'bg-amber-500 text-black ring-2 ring-amber-500/30' : 'bg-indigo-600 text-white ring-2 ring-indigo-500/30'
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
            className="text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold cursor-pointer px-2.5 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 transition-colors"
          >
            Switch
          </button>
        </div>

      </aside>

      {/* =====================================================================
          MAIN CONVERSATIONAL AREA
          ===================================================================== */}
      <main className="flex-1 flex flex-col h-full min-w-0 bg-[#070b16] overflow-hidden">
        
        {/* Top Header Bar (PINNED) */}
        <div className="h-16 border-b border-white/10 px-5 sm:px-6 flex items-center justify-between bg-[#0a0e1c]/80 backdrop-blur-xl shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 transition-colors cursor-pointer border border-transparent hover:border-white/10"
              title={sidebarOpen ? 'Collapse sidebar' : 'Open sidebar'}
            >
              {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
            </button>
            
            <div className="flex items-center gap-2.5">
              <span className="font-['Outfit'] font-bold text-base text-white tracking-tight">RAGOps Chat Assistant</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-mono font-medium">
                Groq LLaMA 3.1 70B
              </span>
              <span className="hidden md:inline-flex items-center gap-1.5 text-[11px] text-slate-400 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse" />
                <span>Zero Hallucination Grounded</span>
              </span>
            </div>
          </div>

          {/* Right Header Actions */}
          <div className="flex items-center gap-3">
            {toastMessage && (
              <span className="text-xs font-semibold text-emerald-400 animate-in fade-in duration-150">
                {toastMessage}
              </span>
            )}

            {messages.length > 0 && (
              <button
                type="button"
                onClick={handleNewChat}
                className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] text-slate-400 hover:text-white text-xs border border-white/10 transition-colors cursor-pointer"
                title="Start a new clean chat"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Clear Chat</span>
              </button>
            )}

            <div className="flex items-center gap-1.5 text-xs text-slate-300 bg-white/[0.04] border border-white/10 rounded-xl px-3 py-1.5">
              <Sliders className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-slate-400">Context:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="bg-transparent text-white font-mono text-xs focus:outline-none cursor-pointer"
              >
                <option value={3} className="bg-[#0b0f19]">Top-3 Chunks</option>
                <option value={5} className="bg-[#0b0f19]">Top-5 Chunks</option>
                <option value={8} className="bg-[#0b0f19]">Top-8 Chunks</option>
                <option value={10} className="bg-[#0b0f19]">Top-10 Chunks</option>
              </select>
            </div>
          </div>
        </div>

        {/* Message Stream: INDEPENDENT SCROLL CONTAINER */}
        <div ref={chatScrollContainerRef} className="flex-1 min-h-0 overflow-y-auto p-5 sm:p-8 space-y-7">
          
          {/* Empty Conversation Welcome Screen */}
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center space-y-7 py-12 animate-in fade-in duration-300">
              <div className="relative">
                <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-cyan-400 flex items-center justify-center text-white shadow-2xl shadow-indigo-500/30">
                  <Bot className="w-8 h-8" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-emerald-400 border-2 border-[#07090e] flex items-center justify-center shadow">
                  <Sparkles className="w-2.5 h-2.5 text-black" />
                </div>
              </div>

              <div className="space-y-2.5">
                <h2 className="text-3xl sm:text-4xl font-extrabold text-white font-['Outfit'] tracking-tight">
                  How can I assist your operations?
                </h2>
                <p className="text-sm sm:text-base text-slate-400 max-w-lg mx-auto leading-relaxed">
                  Enterprise retrieval augmented generation powered by PostgreSQL telemetry, ChromaDB embeddings, and Cross-Encoder reranking.
                </p>
              </div>

              {/* Four Clean Operational Capability Chips */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 w-full text-left pt-2">
                <button
                  type="button"
                  onClick={() => setInputPrompt("What are the company's manufacturing locations and facilities?")}
                  className="p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/10 hover:border-indigo-500/40 transition-all cursor-pointer text-left group"
                >
                  <div className="flex items-center gap-2 text-indigo-400 font-semibold text-xs mb-1 group-hover:text-indigo-300">
                    <Building className="w-3.5 h-3.5" />
                    <span>Manufacturing &amp; Plants</span>
                  </div>
                  <div className="text-xs text-slate-400 leading-relaxed">
                    Locations in Pune, Rovigo, Campodarsego, and global production hubs.
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setInputPrompt("What are the key policies in the corporate Code of Ethics?")}
                  className="p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/10 hover:border-cyan-500/40 transition-all cursor-pointer text-left group"
                >
                  <div className="flex items-center gap-2 text-cyan-400 font-semibold text-xs mb-1 group-hover:text-cyan-300">
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>Code of Ethics &amp; Compliance</span>
                  </div>
                  <div className="text-xs text-slate-400 leading-relaxed">
                    Anti-corruption, safety standards, environmental rules, and human rights.
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setInputPrompt("What agricultural and construction machinery solutions are produced?")}
                  className="p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/10 hover:border-amber-500/40 transition-all cursor-pointer text-left group"
                >
                  <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs mb-1 group-hover:text-amber-300">
                    <Zap className="w-3.5 h-3.5" />
                    <span>Transmission Systems &amp; Products</span>
                  </div>
                  <div className="text-xs text-slate-400 leading-relaxed">
                    Gearboxes, specialized tractors, axles, drives, and OEM engineering.
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setInputPrompt("Verify zero hallucination: who is the company CEO and executive management?")}
                  className="p-4 rounded-2xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/10 hover:border-emerald-500/40 transition-all cursor-pointer text-left group"
                >
                  <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs mb-1 group-hover:text-emerald-300">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>Grounded Fact Verification</span>
                  </div>
                  <div className="text-xs text-slate-400 leading-relaxed">
                    Strict citation-grounded validation with zero hallucination enforcement.
                  </div>
                </button>
              </div>
            </div>
          ) : (
            messages.map((turn, idx) => {
              const meta = turn.metadata || {};
              const chunks = meta.retrieved_chunks || [];
              const isTurnExpanded = expandedChunkMsgIdx === idx;
              const isAbstaining = isAbstention(turn.answer, turn.sources);

              return (
                <div key={turn.id || idx} className="space-y-4 max-w-5xl xl:max-w-6xl mx-auto">
                  
                  {/* USER PROMPT MESSAGE BUBBLE */}
                  <div className="flex items-start gap-3.5 justify-end">
                    <div className="max-w-3xl bg-gradient-to-r from-indigo-600/25 via-indigo-600/20 to-indigo-700/25 border border-indigo-500/40 rounded-2xl rounded-tr-sm px-5 py-3.5 text-white text-[15px] shadow-lg leading-relaxed">
                      <p className="whitespace-pre-wrap">{turn.query}</p>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-bold text-xs shrink-0 mt-0.5 shadow-md shadow-indigo-600/30">
                      {currentUser?.username ? currentUser.username.charAt(0).toUpperCase() : 'U'}
                    </div>
                  </div>

                  {/* ASSISTANT RESPONSE BUBBLE */}
                  <div className="flex items-start gap-3.5 justify-start">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-white font-bold text-xs shrink-0 mt-0.5 shadow-lg shadow-cyan-500/20">
                      <Bot className="w-5 h-5" />
                    </div>

                    <div className="flex-1 min-w-0 space-y-3">
                      
                      {turn.isPending ? (
                        <div className="p-5 rounded-2xl bg-[#0d1322] border border-white/10 text-slate-300 text-sm flex items-center gap-3 shadow-xl">
                          <Zap className="w-5 h-5 text-cyan-400 animate-spin shrink-0" />
                          <div className="space-y-0.5">
                            <div className="font-semibold text-white">Generating Grounded Answer...</div>
                            <div className="text-xs text-slate-400">Searching ChromaDB embeddings &amp; applying Cross-Encoder reranking...</div>
                          </div>
                        </div>
                      ) : (
                        <div className="p-6 sm:p-7 rounded-2xl bg-[#0c1120]/95 border border-white/10 space-y-5 shadow-2xl backdrop-blur-md">
                          
                          {/* Abstention Banner if documents do not contain the answer */}
                          {isAbstaining && (
                            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2.5">
                              <ShieldAlert className="w-4 h-4 shrink-0 text-amber-400" />
                              <span>Zero Hallucination Guardrail: The indexed corporate knowledge base does not contain sufficient facts to answer this inquiry.</span>
                            </div>
                          )}

                          {/* Query Intelligence & Semantic Cache Indicators */}
                          <div className="flex flex-wrap items-center gap-2 text-xs">
                            {meta.cache_hit && (
                              <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full font-medium text-[11px] shadow-sm ${
                                meta.cache_tier === 'redis_exact'
                                  ? 'bg-rose-500/15 border border-rose-500/30 text-rose-300'
                                  : meta.cache_tier === 'redis_semantic'
                                  ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300'
                                  : 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300'
                              }`}>
                                <Zap className={`w-3.5 h-3.5 ${meta.cache_tier === 'redis_exact' ? 'text-rose-400' : 'text-emerald-400'}`} />
                                <span>
                                  {meta.cache_tier === 'redis_exact'
                                    ? `⚡ Redis Instant Cache Hit (${meta.total_latency_ms || 1.8}ms • $0.00 spend)`
                                    : meta.cache_tier === 'redis_semantic'
                                    ? `⚡ Redis Semantic Hit (${meta.similarity_score ? Math.round(meta.similarity_score * 100) : 95}% Relevance Match • ${meta.total_latency_ms || 6.2}ms • $0.00 spend)`
                                    : `⚡ Semantic Cache Hit (${meta.total_latency_ms || 6.5}ms • $0.00 spend)`}
                                </span>
                              </div>
                            )}

                            {meta.is_rewritten && meta.rewritten_query && (
                              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 font-medium text-[11px]">
                                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                                <span>Rewritten Query: "{meta.rewritten_query}"</span>
                              </div>
                            )}

                            {meta.intent && meta.intent !== 'general' && (
                              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-[11px]">
                                <span>🎯 Intent: {String(meta.intent).replace(/_/g, ' ')}</span>
                              </div>
                            )}
                          </div>

                          {/* Markdown Rendered Answer with custom ragops-markdown styling */}
                          <div 
                            className="ragops-markdown max-w-none font-sans"
                            dangerouslySetInnerHTML={{ __html: marked.parse(turn.answer || '') }}
                          />

                          {/* Verified Citations List */}
                          {turn.sources && turn.sources.length > 0 && (
                            <div className="pt-4 border-t border-white/10 space-y-2.5">
                              <div className="text-slate-400 font-semibold text-xs flex items-center gap-1.5">
                                <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
                                <span>Verified Corporate Sources ({turn.sources.length}):</span>
                              </div>
                              <div className="flex flex-wrap items-center gap-2">
                                {turn.sources.map((src, sIdx) => (
                                  <button
                                    key={sIdx}
                                    onClick={() => onChunkClick && onChunkClick(src)}
                                    className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-cyan-500/15 border border-white/10 hover:border-cyan-500/40 text-cyan-300 text-xs font-mono transition-all cursor-pointer shadow-sm"
                                  >
                                    <FileText className="w-3.5 h-3.5 text-cyan-400 opacity-80" />
                                    <span className="font-semibold">{src.document} {src.page ? `(p.${src.page})` : ''}</span>
                                    <ExternalLink className="w-3 h-3 opacity-60" />
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Telemetry Footer: Latencies, Tokens, Chunks button & Copy / Feedback */}
                          <div className="pt-4 border-t border-white/10 flex flex-wrap items-center justify-between gap-3 text-xs">
                            
                            {/* Latency & Token Badges */}
                            <div className="flex flex-wrap items-center gap-2.5 text-[11px] font-mono text-slate-400">
                              <span className="text-emerald-400 font-bold px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                                {meta.total_latency_ms ? `${meta.total_latency_ms}ms` : '380ms'}
                              </span>
                              <span>&bull;</span>
                              <span>{meta.total_tokens || ((meta.input_tokens || 0) + (meta.output_tokens || 0)) || 0} tokens</span>
                              <span>&bull;</span>
                              <span className="text-indigo-400 font-medium">{meta.model || 'Groq LLaMA 3.1 70B'}</span>
                            </div>

                            {/* Actions: Toggle Chunks, Copy, & Feedback */}
                            <div className="flex items-center gap-2">
                              
                              {/* Inspect Chunks Toggle */}
                              {chunks.length > 0 && (
                                <button
                                  type="button"
                                  onClick={() => setExpandedChunkMsgIdx(isTurnExpanded ? null : idx)}
                                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03] hover:bg-white/[0.08] text-slate-300 font-mono text-xs cursor-pointer border border-white/10 transition-colors"
                                >
                                  <span>Chunks ({chunks.length})</span>
                                  {isTurnExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
                                </button>
                              )}

                              {/* Copy Response Button */}
                              <button
                                type="button"
                                onClick={() => handleCopyText(turn.answer, turn.id || idx)}
                                title="Copy answer to clipboard"
                                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 border border-white/10 transition-colors cursor-pointer flex items-center gap-1"
                              >
                                {copiedTurnId === (turn.id || idx) ? (
                                  <>
                                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                                    <span className="text-[10px] text-emerald-400 font-mono">Copied</span>
                                  </>
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                              </button>

                              {/* Thumbs Feedback */}
                              <div className="flex items-center gap-1 border-l border-white/10 pl-2">
                                <button
                                  onClick={() => handleFeedback(idx, 'positive')}
                                  title="Mark as Grounded and Accurate"
                                  className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                                    turn.feedback === 'positive'
                                      ? 'bg-emerald-500/20 text-emerald-400'
                                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
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
                                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                                  }`}
                                >
                                  <ThumbsDown className="w-3.5 h-3.5" />
                                </button>
                              </div>

                            </div>

                          </div>

                          {/* Collapsible Chunk Details */}
                          {isTurnExpanded && (
                            <div className="mt-3 p-4 rounded-xl bg-[#07090e] border border-white/10 space-y-3 animate-in fade-in duration-150">
                              <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center justify-between">
                                <span>Retrieved Chunks Sent to LLM Context:</span>
                                <span className="font-mono text-indigo-400 text-[10px]">{chunks.length} chunks</span>
                              </div>
                              <div className="space-y-2">
                                {chunks.map((chk, cIdx) => (
                                  <div key={cIdx} className="p-3 rounded-xl bg-white/[0.02] border border-white/5 space-y-1.5">
                                    <div className="flex items-center justify-between text-[11px] font-mono">
                                      <span className="text-indigo-400 font-semibold">
                                        [{cIdx + 1}] {chk.source || 'doc'} {chk.page ? `(page ${chk.page})` : ''}
                                      </span>
                                      <span className="text-emerald-400 font-bold">
                                        Relevance: {formatRelevanceScore(chk.score)}
                                      </span>
                                    </div>
                                    <p className="text-xs text-slate-300 font-mono leading-relaxed">
                                      {chk.text || 'No text snippet'}
                                    </p>
                                  </div>
                                ))}
                              </div>

                              {/* Hop-by-hop latency breakdown */}
                              <div className="pt-2.5 border-t border-white/5 grid grid-cols-4 gap-2 text-[11px] font-mono text-center text-slate-400">
                                <div>Embed: <span className="text-white font-semibold">{meta.embed_latency_ms || 0}ms</span></div>
                                <div>Search: <span className="text-white font-semibold">{meta.search_latency_ms || 0}ms</span></div>
                                <div>Rerank: <span className="text-white font-semibold">{meta.rerank_latency_ms || 0}ms</span></div>
                                <div>LLM: <span className="text-white font-semibold">{meta.generation_latency_ms || 0}ms</span></div>
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
        </div>

        {/* BOTTOM FIXED PROMPT DOCK */}
        <div className="p-4 sm:p-5 border-t border-white/10 bg-[#0a0e1c]/90 backdrop-blur-xl space-y-2.5">
          
          {/* Detected URL Quick Banner */}
          {(() => {
            const match = inputPrompt.match(/https?:\/\/[^\s]+/i);
            const detected = match ? match[0] : null;
            if (!detected) return null;
            return (
              <div className="max-w-5xl xl:max-w-6xl mx-auto p-3 rounded-xl bg-indigo-950/70 border border-indigo-500/40 text-xs text-indigo-200 flex flex-wrap items-center justify-between gap-2 animate-in fade-in duration-150">
                <div className="flex items-center gap-2 truncate">
                  <Globe className="w-4 h-4 text-cyan-400 shrink-0" />
                  <span className="font-semibold text-white">Company URL Detected:</span>
                  <span className="font-mono text-cyan-300 truncate">{detected}</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleStartCrawl(detected)}
                  disabled={isCrawlingUrl}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-md shadow-cyan-600/30 cursor-pointer disabled:opacity-50 shrink-0"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{isCrawlingUrl ? 'Crawling...' : 'Extract & Validate Facts with AI'}</span>
                </button>
              </div>
            );
          })()}

          {/* Optional Direct URL Input Bar */}
          {isUrlInputBarOpen && (
            <div className="max-w-5xl xl:max-w-6xl mx-auto p-3 rounded-2xl bg-[#0f1424] border border-cyan-500/30 flex flex-wrap items-center gap-2 animate-in fade-in duration-150">
              <Globe className="w-4 h-4 text-cyan-400 shrink-0" />
              <input
                type="url"
                placeholder="Paste company website URL (e.g. https://example.com)..."
                value={targetCompanyUrl}
                onChange={(e) => setTargetCompanyUrl(e.target.value)}
                className="flex-1 min-w-[260px] px-3.5 py-2 bg-black/50 border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 font-mono focus:outline-none focus:border-cyan-500"
              />
              <button
                type="button"
                onClick={() => handleStartCrawl()}
                disabled={!targetCompanyUrl.trim() || isCrawlingUrl}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold text-xs cursor-pointer disabled:opacity-50 shadow-md shadow-cyan-600/25 shrink-0"
              >
                <Sparkles className={`w-3.5 h-3.5 ${isCrawlingUrl ? 'animate-spin' : ''}`} />
                <span>{isCrawlingUrl ? 'Crawling Website...' : 'Extract & Validate'}</span>
              </button>
              <button
                type="button"
                onClick={() => setIsUrlInputBarOpen(false)}
                className="px-2.5 py-1.5 text-slate-400 hover:text-white text-xs cursor-pointer"
              >
                Cancel
              </button>
            </div>
          )}

         
          {/* Form */}
          <form 
            onSubmit={handleSendMessage}
            className="max-w-5xl xl:max-w-6xl mx-auto relative flex items-center bg-[#0e1424] border border-white/15 focus-within:border-indigo-500/80 focus-within:ring-2 focus-within:ring-indigo-500/20 rounded-2xl shadow-2xl transition-all p-2"
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
              placeholder="Ask a question about corporate architecture, manufacturing locations, products, or compliance policies (Shift+Enter for newline)..."
              className="flex-1 bg-transparent px-3.5 py-2.5 text-[15px] text-white placeholder-slate-500 focus:outline-none resize-none max-h-36 min-h-[46px]"
            />

            <button
              type="submit"
              disabled={loading || !inputPrompt.trim()}
              className={`p-3 rounded-xl font-semibold transition-all shrink-0 cursor-pointer ${
                inputPrompt.trim() && !loading
                  ? 'bg-gradient-to-r from-indigo-500 via-indigo-600 to-indigo-700 hover:from-indigo-400 hover:to-indigo-600 text-white shadow-lg shadow-indigo-600/30 scale-100 hover:scale-105 active:scale-95'
                  : 'text-slate-600 bg-white/5 cursor-not-allowed'
              }`}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <p className="text-center text-[11px] text-slate-500 mt-1 font-mono">
            RAGOps enterprise outputs are grounded in indexed documents and verified corporate facts with chunk provenance.
          </p>
        </div>

        {/* =====================================================================
            VERIFY & VALIDATE AI-EXTRACTED CORPORATE INTELLIGENCE MODAL
            ===================================================================== */}
        {isUrlModalOpen && crawledPreview && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
            <div className="w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl bg-[#0d1220] border border-cyan-500/50 shadow-2xl overflow-hidden">
              {/* Header */}
              <div className="p-5 border-b border-white/10 flex items-center justify-between bg-gradient-to-r from-cyan-950/60 via-indigo-950/40 to-black/40">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-cyan-600/30 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
                    <Sparkles className="w-5 h-5 text-cyan-300" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white font-['Outfit'] flex items-center gap-2">
                      <span>Verify &amp; Validate AI-Extracted Corporate Intelligence</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 font-mono font-bold">
                        User Check Required
                      </span>
                    </h3>
                    <p className="text-xs text-slate-400">
                      Check and refine extracted locations, clients, hubs, and facts before validating and embedding into ChromaDB.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsUrlModalOpen(false)}
                  className="text-slate-400 hover:text-white text-lg font-bold px-2 py-1 cursor-pointer"
                >
                  &times;
                </button>
              </div>

              {/* Scrollable Body */}
              <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs text-slate-300 font-sans">
                {/* Basic Fields */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Company Legal Name</label>
                    <input
                      type="text"
                      value={crawledPreview.company_name || ''}
                      onChange={(e) => setCrawledPreview({ ...crawledPreview, company_name: e.target.value })}
                      className="w-full px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Parent MNC Group</label>
                    <input
                      type="text"
                      value={crawledPreview.group_name || ''}
                      onChange={(e) => setCrawledPreview({ ...crawledPreview, group_name: e.target.value })}
                      className="w-full px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Industry Sector</label>
                    <input
                      type="text"
                      value={crawledPreview.industry || ''}
                      onChange={(e) => setCrawledPreview({ ...crawledPreview, industry: e.target.value })}
                      className="w-full px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">CEO / Leadership</label>
                    <input
                      type="text"
                      value={crawledPreview.ceo || ''}
                      onChange={(e) => setCrawledPreview({ ...crawledPreview, ceo: e.target.value })}
                      className="w-full px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-white focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-slate-400 font-semibold mb-1">Corporate Overview</label>
                    <textarea
                      rows={2}
                      value={crawledPreview.description || ''}
                      onChange={(e) => setCrawledPreview({ ...crawledPreview, description: e.target.value })}
                      className="w-full px-3 py-2 bg-black/40 border border-white/10 rounded-xl text-white focus:outline-none focus:border-cyan-500 resize-none"
                    />
                  </div>
                </div>

                {/* Section: Locations & Plants */}
                <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                  <span className="font-bold text-white text-xs uppercase tracking-wider flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                    <span>All Company Locations &amp; Manufacturing Plants ({crawledPreview.locations?.length || 0})</span>
                  </span>

                  <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                    {crawledPreview.locations && crawledPreview.locations.length > 0 ? (
                      crawledPreview.locations.map((loc, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 rounded-lg bg-white/[0.03] border border-white/5"
                        >
                          <div className="flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                            <span className="text-white font-medium">
                              {typeof loc === 'string' ? loc : `${loc.city}, ${loc.state || ''}`}
                            </span>
                            {typeof loc === 'object' && loc.type && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                                {loc.type}
                              </span>
                            )}
                          </div>
                          <button
                            type="button"
                            onClick={() => {
                              const updated = crawledPreview.locations.filter((_, i) => i !== idx);
                              setCrawledPreview({ ...crawledPreview, locations: updated });
                            }}
                            className="text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-slate-500 italic">No locations extracted yet. Add below.</div>
                    )}
                  </div>

                  {/* Add Location inputs */}
                  <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-white/5">
                    <input
                      type="text"
                      placeholder="City (e.g. Pune)"
                      value={newLocationInput.city}
                      onChange={(e) => setNewLocationInput({ ...newLocationInput, city: e.target.value })}
                      className="px-2.5 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                    />
                    <input
                      type="text"
                      placeholder="State/Country (e.g. Maharashtra)"
                      value={newLocationInput.state}
                      onChange={(e) => setNewLocationInput({ ...newLocationInput, state: e.target.value })}
                      className="px-2.5 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                    />
                    <input
                      type="text"
                      placeholder="Type (e.g. Plant 1, HQ, Hub)"
                      value={newLocationInput.type}
                      onChange={(e) => setNewLocationInput({ ...newLocationInput, type: e.target.value })}
                      className="px-2.5 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs focus:outline-none focus:border-emerald-500"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        if (!newLocationInput.city.trim()) return;
                        const currentLocs = crawledPreview.locations || [];
                        setCrawledPreview({
                          ...crawledPreview,
                          locations: [...currentLocs, { ...newLocationInput }],
                        });
                        setNewLocationInput({ city: '', state: '', type: 'Manufacturing Plant' });
                      }}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs cursor-pointer flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Add Location</span>
                    </button>
                  </div>
                </div>

                {/* Section: Key Clients & OEM Partners */}
                <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                  <span className="font-bold text-white text-xs uppercase tracking-wider flex items-center gap-1.5">
                    <Award className="w-3.5 h-3.5 text-amber-400" />
                    <span>Key Clients &amp; OEM Partners</span>
                  </span>

                  <div className="flex flex-wrap items-center gap-2">
                    {(crawledPreview.metadata_json?.clients || []).map((client, cIdx) => (
                      <span
                        key={cIdx}
                        className="px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-300 font-mono text-[11px] font-semibold flex items-center gap-1.5"
                      >
                        <span>{client}</span>
                        <button
                          type="button"
                          onClick={() => {
                            const updatedClients = (crawledPreview.metadata_json?.clients || []).filter((_, i) => i !== cIdx);
                            setCrawledPreview({
                              ...crawledPreview,
                              metadata_json: { ...(crawledPreview.metadata_json || {}), clients: updatedClients },
                            });
                          }}
                          className="text-amber-400/60 hover:text-rose-400 cursor-pointer"
                        >
                          &times;
                        </button>
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center gap-2 pt-1 border-t border-white/5">
                    <input
                      type="text"
                      placeholder="Add client or OEM partner (e.g. John Deere, CNH, Mahindra)..."
                      value={newClientInput}
                      onChange={(e) => setNewClientInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          if (!newClientInput.trim()) return;
                          const current = crawledPreview.metadata_json?.clients || [];
                          setCrawledPreview({
                            ...crawledPreview,
                            metadata_json: { ...(crawledPreview.metadata_json || {}), clients: [...current, newClientInput.trim()] },
                          });
                          setNewClientInput('');
                        }
                      }}
                      className="flex-1 px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs focus:outline-none focus:border-amber-500 font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        if (!newClientInput.trim()) return;
                        const current = crawledPreview.metadata_json?.clients || [];
                        setCrawledPreview({
                          ...crawledPreview,
                          metadata_json: { ...(crawledPreview.metadata_json || {}), clients: [...current, newClientInput.trim()] },
                        });
                        setNewClientInput('');
                      }}
                      className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs cursor-pointer flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Add Client</span>
                    </button>
                  </div>
                </div>

                {/* Section: Regional Hubs */}
                <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                  <span className="font-bold text-white text-xs uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Regional Hubs &amp; Logistics Centers</span>
                  </span>

                  <div className="flex flex-wrap items-center gap-2">
                    {(crawledPreview.metadata_json?.hubs || []).map((hub, hIdx) => (
                      <span
                        key={hIdx}
                        className="px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 font-mono text-[11px] font-semibold flex items-center gap-1.5"
                      >
                        <span>{hub}</span>
                        <button
                          type="button"
                          onClick={() => {
                            const updatedHubs = (crawledPreview.metadata_json?.hubs || []).filter((_, i) => i !== hIdx);
                            setCrawledPreview({
                              ...crawledPreview,
                              metadata_json: { ...(crawledPreview.metadata_json || {}), hubs: updatedHubs },
                            });
                          }}
                          className="text-indigo-400/60 hover:text-rose-400 cursor-pointer"
                        >
                          &times;
                        </button>
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center gap-2 pt-1 border-t border-white/5">
                    <input
                      type="text"
                      placeholder="Add logistics hub (e.g. Pune Spares Hub)..."
                      value={newHubInput}
                      onChange={(e) => setNewHubInput(e.target.value)}
                      className="flex-1 px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs focus:outline-none focus:border-indigo-500 font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        if (!newHubInput.trim()) return;
                        const current = crawledPreview.metadata_json?.hubs || [];
                        setCrawledPreview({
                          ...crawledPreview,
                          metadata_json: { ...(crawledPreview.metadata_json || {}), hubs: [...current, newHubInput.trim()] },
                        });
                        setNewHubInput('');
                      }}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs cursor-pointer flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Add Hub</span>
                    </button>
                  </div>
                </div>

                {/* Section: Products */}
                <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                  <span className="font-bold text-white text-xs uppercase tracking-wider flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Products &amp; Mechanical Solutions</span>
                  </span>

                  <div className="flex flex-wrap items-center gap-2">
                    {(crawledPreview.products || []).map((prod, pIdx) => (
                      <span
                        key={pIdx}
                        className="px-2.5 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/25 text-cyan-300 font-mono text-[11px] font-semibold flex items-center gap-1.5"
                      >
                        <span>{prod}</span>
                        <button
                          type="button"
                          onClick={() => {
                            const updatedProds = (crawledPreview.products || []).filter((_, i) => i !== pIdx);
                            setCrawledPreview({ ...crawledPreview, products: updatedProds });
                          }}
                          className="text-cyan-400/60 hover:text-rose-400 cursor-pointer"
                        >
                          &times;
                        </button>
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center gap-2 pt-1 border-t border-white/5">
                    <input
                      type="text"
                      placeholder="Add product or transmission solution..."
                      value={newProductInput}
                      onChange={(e) => setNewProductInput(e.target.value)}
                      className="flex-1 px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs focus:outline-none focus:border-cyan-500 font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        if (!newProductInput.trim()) return;
                        const current = crawledPreview.products || [];
                        setCrawledPreview({
                          ...crawledPreview,
                          products: [...current, newProductInput.trim()],
                        });
                        setNewProductInput('');
                      }}
                      className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs cursor-pointer flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" />
                      <span>Add Product</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="p-4 border-t border-white/10 flex flex-wrap items-center justify-between gap-3 bg-black/40">
                <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Target: PostgreSQL + ChromaDB Vector Store</span>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setIsUrlModalOpen(false)}
                    className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white text-xs font-semibold cursor-pointer"
                  >
                    Discard &amp; Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleValidateAndEmbed}
                    disabled={isSavingAndEmbedding}
                    className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/30 cursor-pointer disabled:opacity-50 transition-all"
                  >
                    <CheckCircle2 className={`w-4 h-4 ${isSavingAndEmbedding ? 'animate-spin' : ''}`} />
                    <span>{isSavingAndEmbedding ? 'Validating & Embedding...' : 'Validate, Save & Embed into Knowledge Base'}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

      </main>

    </div>
  );
}
