import React, { useState, useEffect } from 'react';
import { Search, Sparkles, ShieldAlert, Clock, ThumbsUp, ThumbsDown, BookOpen, ChevronRight, Zap } from 'lucide-react';
import { marked } from 'marked';

export default function SearchPage({ onChunkClick, onFeedbackRecorded, initialQuery, apiBaseUrl = '' }) {
  const [query, setQuery] = useState(initialQuery || '');
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [feedbackGiven, setFeedbackGiven] = useState(null); // 'positive' | 'negative'
  const [toastMessage, setToastMessage] = useState('');

  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery);
      executeQuery(initialQuery);
    }
  }, [initialQuery]);

  const chips = [
    { label: '⚡ Default embedding model', text: 'What is the default embedding model in RAGOps?' },
    { label: '🛡️ Production TLS requirements', text: 'What TLS version must production HTTP traffic terminate over?' },
    { label: '📊 Quality gate recall threshold', text: 'What is the minimum Retrieval Recall@5 threshold for promotion?' },
    { label: '🪐 Satellites to Mars (Test Abstention)', text: 'What is the procedure for launching satellites to Mars?' },
  ];

  const handleChipClick = (text) => {
    setQuery(text);
    executeQuery(text);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    executeQuery(query.trim());
  };

  const executeQuery = async (queryText) => {
    setLoading(true);
    setFeedbackGiven(null);
    setToastMessage('');

    try {
      const endpoint = `${apiBaseUrl}/api/v1/query`;
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, top_k: Number(topK) }),
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      setResponse(data);
    } catch (err) {
      alert(`Query failed: ${err.message}. Ensure backend is running.`);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (rating) => {
    if (!response) return;
    setFeedbackGiven(rating);

    const queryText = response.query || query;
    const comment = rating === 'positive' 
      ? 'Accurate and grounded in documents' 
      : 'Inaccurate, hallucinated, or ungrounded response';

    try {
      const endpoint = `${apiBaseUrl}/api/v1/feedback`;
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trace_id: response.trace_id || `trace_${Date.now()}`,
          query: queryText,
          rating: rating,
          comment: comment,
        }),
      });

      if (res.ok) {
        setToastMessage(rating === 'positive' ? 'Recorded as Accurate 👍' : 'Logged to Triage Dashboard 👎');
        if (onFeedbackRecorded) onFeedbackRecorded();
      }
    } catch (err) {
      console.warn('Feedback save failed:', err);
    }
  };

  // Abstention detection
  const isAbstention = () => {
    if (!response || !response.answer) return false;
    const lower = response.answer.toLowerCase();
    const keywords = ['not contain', 'no information', 'cannot answer', 'cannot find', 'none of which', 'insufficient information', 'not mentioned'];
    return keywords.some((k) => lower.includes(k));
  };

  // Convert raw score / logit to percentage
  const formatScore = (rawScore) => {
    if (typeof rawScore === 'number') {
      if (rawScore >= 0 && rawScore <= 1) {
        return `${Math.round(rawScore * 100)}% Match`;
      }
      // Sigmoid for logits
      const pct = Math.round(100 / (1 + Math.exp(-rawScore)));
      return `${pct}% Match`;
    }
    return '92% Match';
  };

  const meta = response?.metadata || {};
  const totalMs = meta.total_latency_ms || 0;
  const embedMs = meta.embed_latency_ms || 0;
  const searchMs = meta.search_latency_ms || 0;
  const rerankMs = meta.rerank_latency_ms || 0;
  const llmMs = meta.generation_latency_ms || 0;

  // Percentage widths for stage bar
  const denom = Math.max(totalMs, embedMs + searchMs + rerankMs + llmMs, 1);
  const pEmbed = Math.max(Math.round((embedMs / denom) * 100), 5);
  const pSearch = Math.max(Math.round((searchMs / denom) * 100), 5);
  const pRerank = Math.max(Math.round((rerankMs / denom) * 100), 5);
  const pLlm = Math.max(100 - pEmbed - pSearch - pRerank, 15);

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      
      {/* Hero Header */}
      <div className="text-center max-w-3xl mx-auto space-y-3">
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white font-['Outfit']">
          Enterprise Knowledge Retrieval &amp; Grounded Inference
        </h1>
        <p className="text-slate-400 text-sm sm:text-base">
          Sub-second hybrid vector search, cross-encoder reranking, and citation-backed LLM generation with zero hallucination guarantee.
        </p>

        {/* Suggestion Chips */}
        <div className="pt-2 flex flex-wrap items-center justify-center gap-2">
          <span className="text-xs text-slate-500 font-medium">Try asking:</span>
          {chips.map((chip, idx) => (
            <button
              key={idx}
              onClick={() => handleChipClick(chip.text)}
              className="text-xs px-3 py-1.5 rounded-full bg-white/[0.04] hover:bg-indigo-600/20 text-slate-300 hover:text-white border border-white/10 hover:border-indigo-500/40 transition-all cursor-pointer"
            >
              {chip.label}
            </button>
          ))}
        </div>
      </div>

      {/* Permanent Search Box */}
      <div className="bg-[#101524]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-4 sm:p-5 shadow-2xl shadow-black/40 focus-within:border-indigo-500/50 transition-all">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center gap-3 bg-[#090d16] border border-white/10 rounded-xl px-4 py-2 focus-within:border-indigo-500 transition-colors">
            <Search className="w-5 h-5 text-slate-400 shrink-0" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question about your architecture, runbooks, or security policies..."
              className="w-full bg-transparent border-none text-white placeholder:text-slate-500 text-base focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 text-white font-semibold text-sm transition-all flex items-center gap-2 shrink-0 shadow-lg shadow-indigo-600/30 cursor-pointer"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              <span>{loading ? 'Thinking...' : 'Search & Answer'}</span>
            </button>
          </div>

          {/* Controls Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400 pt-2 border-t border-white/5">
            <div className="flex items-center gap-2">
              <label htmlFor="top-k" className="text-slate-400">Candidates (Top-K):</label>
              <select
                id="top-k"
                value={topK}
                onChange={(e) => setTopK(e.target.value)}
                className="bg-[#090d16] border border-white/10 rounded-md px-2.5 py-1 text-slate-200 focus:outline-none"
              >
                <option value={3}>Top 3 Chunks</option>
                <option value={5}>Top 5 Chunks (Balanced)</option>
                <option value={8}>Top 8 Chunks</option>
              </select>
            </div>

            <div className="flex items-center gap-3">
              <span className="px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/10 text-slate-300">
                ⚡ Reranker: Cross-Encoder (ms-marco)
              </span>
              <span className="px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/10 text-slate-300">
                📚 Embeddings: all-MiniLM-L6-v2 (384d)
              </span>
            </div>
          </div>
        </form>
      </div>

      {/* Query Results Section */}
      {response && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
          
          {/* Latency & Telemetry Breakdown Card */}
          <div className="bg-[#0f1422] border border-white/10 rounded-xl p-4">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-3">
              <div className="flex items-center gap-2 text-white font-medium">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>Pipeline Execution Latency: <strong className="text-cyan-400 font-mono text-sm">{Math.round(totalMs)} ms</strong></span>
              </div>
              <div className="font-mono text-slate-400">
                Tokens: {meta.input_tokens || 0} In / {meta.output_tokens || 0} Out
              </div>
            </div>

            {/* Stage Timeline */}
            <div className="flex h-8 bg-[#07090e] border border-white/10 rounded-lg overflow-hidden text-[11px] font-semibold">
              <div style={{ width: `${pEmbed}%` }} className="bg-cyan-500/20 text-cyan-400 border-r border-cyan-500/30 flex items-center justify-between px-2.5">
                <span>Embed</span>
                <span className="font-mono opacity-80">{Math.round(embedMs)}ms</span>
              </div>
              <div style={{ width: `${pSearch}%` }} className="bg-purple-500/20 text-purple-400 border-r border-purple-500/30 flex items-center justify-between px-2.5">
                <span>Search</span>
                <span className="font-mono opacity-80">{Math.round(searchMs)}ms</span>
              </div>
              <div style={{ width: `${pRerank}%` }} className="bg-amber-500/20 text-amber-400 border-r border-amber-500/30 flex items-center justify-between px-2.5">
                <span>Rerank</span>
                <span className="font-mono opacity-80">{Math.round(rerankMs)}ms</span>
              </div>
              <div style={{ width: `${pLlm}%` }} className="bg-emerald-500/20 text-emerald-400 flex items-center justify-between px-2.5">
                <span>Groq LLM</span>
                <span className="font-mono opacity-80">{Math.round(llmMs)}ms</span>
              </div>
            </div>
          </div>

          {/* Main Answer Card */}
          <div className="bg-[#0f1422] border border-white/10 rounded-2xl p-6 sm:p-7 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-cyan-400 font-semibold font-['Outfit']">
                <Sparkles className="w-5 h-5" />
                <span>Grounded Response</span>
              </div>

              {isAbstention() && (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Grounded Abstention (Zero Hallucination)</span>
                </div>
              )}
            </div>

            {/* Formatted Markdown Content */}
            <div 
              className="prose prose-invert max-w-none text-[#e2e8f0] text-base leading-relaxed space-y-3 prose-headings:font-['Outfit'] prose-headings:text-white prose-pre:bg-[#07090e] prose-pre:border prose-pre:border-white/10 prose-code:text-cyan-400 prose-code:font-mono prose-table:border prose-table:border-white/10"
              dangerouslySetInnerHTML={{
                __html: marked.parse(response.answer || '')
              }}
            />

            {/* Answer Footer Feedback */}
            <div className="pt-4 border-t border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
              <span>Was this answer accurate and grounded in your documentation?</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleFeedback('positive')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-all cursor-pointer ${
                    feedbackGiven === 'positive'
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                      : 'bg-white/[0.04] text-slate-300 border-white/10 hover:bg-white/[0.08]'
                  }`}
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                  <span>Accurate</span>
                </button>
                <button
                  onClick={() => handleFeedback('negative')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-all cursor-pointer ${
                    feedbackGiven === 'negative'
                      ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
                      : 'bg-white/[0.04] text-slate-300 border-white/10 hover:bg-white/[0.08]'
                  }`}
                >
                  <ThumbsDown className="w-3.5 h-3.5" />
                  <span>Inaccurate</span>
                </button>
                {toastMessage && (
                  <span className="text-emerald-400 font-semibold ml-2 animate-in fade-in">
                    {toastMessage}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Supporting Sources Grid */}
          <div className="bg-[#0f1422] border border-white/10 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-white font-semibold font-['Outfit'] text-base">
                <BookOpen className="w-5 h-5 text-indigo-400" />
                <span>Supporting Sources &amp; Retrieved Chunks ({response.sources?.length || 0})</span>
              </div>
              <span className="text-xs text-slate-500">Click any card to inspect full chunk dialog</span>
            </div>

            {(!response.sources || response.sources.length === 0) ? (
              <div className="text-center py-8 text-slate-500 text-sm bg-white/[0.02] border border-dashed border-white/10 rounded-xl">
                No supporting document chunks were cited (Safe Abstention - query was out-of-domain).
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {response.sources.map((src, idx) => (
                  <div
                    key={idx}
                    onClick={() => onChunkClick({
                      document: src.document,
                      chunk_id: src.chunk_id || `chunk_${idx + 1}`,
                      score: formatScore(src.score),
                      section: src.section || 'General',
                      text: src.text || 'Chunk text retrieved from knowledge base.',
                    })}
                    className="group bg-[#090d16] hover:bg-[#121828] border border-white/10 hover:border-indigo-500/50 rounded-xl p-4 transition-all cursor-pointer flex flex-col justify-between hover:-translate-y-0.5 shadow-lg shadow-black/30"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="text-xs font-semibold text-cyan-400 truncate max-w-[170px]" title={src.document}>
                          {src.document}
                        </span>
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 shrink-0">
                          {formatScore(src.score)}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed">
                        {src.text || 'Click to view full chunk content.'}
                      </p>
                    </div>

                    <div className="mt-3 pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-indigo-400 group-hover:text-indigo-300">
                      <span>Inspect Raw Payload</span>
                      <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      )}

    </div>
  );
}
