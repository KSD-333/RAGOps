import React, { useState } from 'react';
import {
  BookOpen,
  Code2,
  Server,
  Globe,
  Cpu,
  Database,
  CheckCircle2,
  Copy,
  Check,
  ExternalLink,
  Layers,
  Zap,
  ArrowRight,
  ShieldCheck,
  Terminal,
  Activity,
  AlertCircle,
  FileCode2,
  Maximize2
} from 'lucide-react';

export default function DocsPage({ apiBaseUrl, setApiBaseUrl }) {
  const [docView, setDocView] = useState('guide'); // 'guide' | 'swagger'
  const [selectedEndpoint, setSelectedEndpoint] = useState('query');
  const [activeCodeTab, setActiveCodeTab] = useState('curl');
  const [copiedCode, setCopiedCode] = useState(false);
  const [customUrlInput, setCustomUrlInput] = useState(apiBaseUrl || '');
  const [pingStatus, setPingStatus] = useState(null); // { ok: bool, latency: number, message: string }
  const [pinging, setPinging] = useState(false);

  // Compute live Swagger URL
  const swaggerUrl = apiBaseUrl
    ? `${apiBaseUrl}/docs`
    : (typeof window !== 'undefined' && window.location.port === '5173' ? 'http://127.0.0.1:8000/docs' : '/docs');

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleSaveApiUrl = (e) => {
    e.preventDefault();
    const clean = customUrlInput.trim().replace(/\/+$/, '');
    setApiBaseUrl(clean);
    localStorage.setItem('ragops_api_base_url', clean);
    alert(`Active API target updated to: ${clean || 'Local Origin (/)'}`);
  };

  const handlePingServer = async () => {
    setPinging(true);
    setPingStatus(null);
    const target = customUrlInput.trim().replace(/\/+$/, '') || (typeof window !== 'undefined' && window.location.port === '5173' ? 'http://127.0.0.1:8000' : window.location.origin);
    const start = performance.now();
    try {
      const res = await fetch(`${target}/health/ready`, { signal: AbortSignal.timeout(6000) });
      const elapsed = Math.round(performance.now() - start);
      if (res.ok) {
        const json = await res.json();
        setPingStatus({
          ok: true,
          latency: elapsed,
          message: `Connected! Server is ready. Model: ${json.model || 'Groq'} (${elapsed}ms)`,
        });
      } else {
        setPingStatus({
          ok: false,
          latency: elapsed,
          message: `Server returned HTTP ${res.status}. Check endpoint availability.`,
        });
      }
    } catch (err) {
      setPingStatus({
        ok: false,
        latency: 0,
        message: `Connection failed: ${err.message}. Verify host URL and CORS headers.`,
      });
    } finally {
      setPinging(false);
    }
  };

  // Endpoint reference definitions
  const endpoints = [
    {
      id: 'query',
      method: 'POST',
      path: '/api/v1/query',
      title: 'Execute RAG Query with Citation Provenance',
      desc: 'Submits user question to hybrid retriever (ChromaDB + SentenceTransformers), applies CrossEncoder reranking, and generates grounded answer with Groq LLaMA 3.1 70B.',
      reqBody: `{
  "query": "What is the minimum Retrieval Recall@5 threshold for promotion?",
  "top_k": 5,
  "filters": {}
}`,
      respBody: `{
  "answer": "The minimum Retrieval Recall@5 threshold for promotion is 0.85...",
  "sources": [
    {
      "document": "evaluation/quality_gates.md",
      "chunk_id": "chunk_7",
      "score": 0.942,
      "text": "Quality Gate Promotion Thresholds: Retrieval Recall@5 >= 0.85..."
    }
  ],
  "trace_id": "trace_1729294800_91",
  "metadata": {
    "embed_latency_ms": 14.2,
    "search_latency_ms": 11.5,
    "rerank_latency_ms": 28.3,
    "generation_latency_ms": 1180.0,
    "total_latency_ms": 1234.0,
    "input_tokens": 842,
    "output_tokens": 124
  }
}`,
      curl: `curl -X POST "${apiBaseUrl || 'http://127.0.0.1:8000'}/api/v1/query" \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "What is the minimum Retrieval Recall@5 threshold for promotion?",
    "top_k": 5
  }'`,
      python: `import httpx

response = httpx.post(
    "${apiBaseUrl || 'http://127.0.0.1:8000'}/api/v1/query",
    json={
        "query": "What is the minimum Retrieval Recall@5 threshold for promotion?",
        "top_k": 5
    },
    timeout=30.0
)
data = response.json()
print("Answer:", data["answer"])
print("Latency ms:", data["metadata"]["total_latency_ms"])
for src in data["sources"]:
    print(f"- {src['document']} (Score: {src['score']})")`,
      javascript: `const response = await fetch("${apiBaseUrl || 'http://127.0.0.1:8000'}/api/v1/query", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    query: "What is the minimum Retrieval Recall@5 threshold for promotion?",
    top_k: 5
  })
});

const data = await response.json();
console.log("Answer:", data.answer);
console.log("Sources:", data.sources);`,
    },
    {
      id: 'feedback',
      method: 'POST',
      path: '/api/v1/feedback',
      title: 'Submit User Feedback (Continuous Improvement)',
      desc: 'Records real-world thumbs up/down user feedback, query text, and optional user comments to persistent JSONL audit logs.',
      reqBody: `{
  "trace_id": "trace_1729294800_91",
  "query": "What is the default embedding model in RAGOps?",
  "rating": "positive",
  "comment": "Accurate and grounded in documents"
}`,
      respBody: `{
  "status": "success",
  "message": "Feedback recorded successfully"
}`,
      curl: `curl -X POST "${apiBaseUrl || 'http://127.0.0.1:8000'}/api/v1/feedback" \\
  -H "Content-Type: application/json" \\
  -d '{
    "trace_id": "trace_1729294800_91",
    "query": "What is the default embedding model in RAGOps?",
    "rating": "positive",
    "comment": "Accurate and grounded in documents"
  }'`,
      python: `import httpx

httpx.post(
    "${apiBaseUrl || 'http://127.0.0.1:8000'}/api/v1/feedback",
    json={
        "trace_id": "trace_1729294800_91",
        "query": "What is the default embedding model in RAGOps?",
        "rating": "positive",
        "comment": "Accurate and grounded in documents"
    }
)`,
      javascript: `await fetch("${apiBaseUrl || 'http://127.0.0.1:8000'}/api/v1/feedback", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    trace_id: "trace_1729294800_91",
    query: "What is the default embedding model in RAGOps?",
    rating: "positive",
    comment: "Accurate and grounded in documents"
  })
});`,
    },
    {
      id: 'dashboard',
      method: 'GET',
      path: '/api/v1/feedback/dashboard',
      title: 'Fetch Observability & Billing Telemetry',
      desc: 'Retrieves aggregated operational telemetry including cumulative input/output tokens, total queries, latency statistics (P50/P95), and logged disliked queries for triage.',
      reqBody: null,
      respBody: `{
  "total_queries": 42,
  "tokens_input": 28410,
  "tokens_output": 5120,
  "total_tokens": 33530,
  "positive_rate": 0.95,
  "positive": 19,
  "negative": 1,
  "documents_indexed": 95,
  "latency_stats": {
    "p50": 1320.0,
    "p95": 1412.0
  },
  "disliked_queries": []
}`,
      curl: `curl -X GET "${apiBaseUrl || 'http://127.0.0.1:8000'}/api/v1/feedback/dashboard"`,
      python: `import httpx

resp = httpx.get("${apiBaseUrl || 'http://127.0.0.1:8000'}/api/v1/feedback/dashboard")
dashboard = resp.json()
print("Cumulative Tokens:", dashboard["total_tokens"])
print("P95 Latency:", dashboard["latency_stats"]["p95"])`,
      javascript: `const res = await fetch("${apiBaseUrl || 'http://127.0.0.1:8000'}/api/v1/feedback/dashboard");
const dashboard = await res.json();
console.log("Telemetry:", dashboard);`,
    },
    {
      id: 'health',
      method: 'GET',
      path: '/health/ready',
      title: 'Container Readiness Probe',
      desc: 'Probes readiness for container orchestrators (Kubernetes / Docker) ensuring ChromaDB is accessible and SentenceTransformers/CrossEncoder models are warmed up.',
      reqBody: null,
      respBody: `{
  "status": "ready",
  "environment": "production",
  "model": "llama-3.1-70b-versatile"
}`,
      curl: `curl -X GET "${apiBaseUrl || 'http://127.0.0.1:8000'}/health/ready"`,
      python: `import httpx

resp = httpx.get("${apiBaseUrl || 'http://127.0.0.1:8000'}/health/ready")
print("Status:", resp.json()["status"])`,
      javascript: `const res = await fetch("${apiBaseUrl || 'http://127.0.0.1:8000'}/health/ready");
const data = await res.json();
console.log("Ready:", data.status === "ready");`,
    },
  ];

  const currentEndpoint = endpoints.find((e) => e.id === selectedEndpoint) || endpoints[0];

  return (
    <div className="space-y-8 animate-in fade-in duration-200">

      {/* Top Header & Sub-Nav Switcher */}
      <div className="border-b border-white/10 pb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white font-['Outfit'] flex items-center gap-3">
            <BookOpen className="w-7 h-7 text-cyan-400" />
            <span>Developer Documentation &amp; API Reference</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-3xl">
            Complete API specifications, interactive Swagger console, multi-environment configuration (Local vs. 24/7 Cloud), and architecture guide.
          </p>
        </div>

        {/* View Switcher: Guide vs. Embedded Swagger */}
        <div className="flex items-center gap-2">
          <div className="flex items-center p-1 bg-white/[0.04] border border-white/10 rounded-xl">
            <button
              onClick={() => setDocView('guide')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${docView === 'guide'
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                : 'text-slate-400 hover:text-white'
                }`}
            >
              <FileCode2 className="w-3.5 h-3.5" />
              <span>Guide &amp; Schemas</span>
            </button>

            <button
              onClick={() => setDocView('swagger')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${docView === 'swagger'
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                : 'text-slate-400 hover:text-white'
                }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Live Swagger UI</span>
            </button>
          </div>

          <a
            href={swaggerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-xs font-semibold transition-all cursor-pointer"
          >
            <span>Open in New Tab</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* =========================================================================
           VIEW 1: EMBEDDED SWAGGER UI IFRAME
           ========================================================================= */}
      {docView === 'swagger' && (
        <div className="bg-[#0f1422] border border-white/10 rounded-2xl p-4 shadow-2xl space-y-3 animate-in fade-in duration-150">
          <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-white/10">
            <div className="flex items-center gap-2 text-white font-medium">
              <Terminal className="w-4 h-4 text-cyan-400" />
              <span>Live Interactive OpenAPI Console &bull; <span className="font-mono text-cyan-300">{swaggerUrl}</span></span>
            </div>
            <a
              href={swaggerUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-colors"
            >
              <span>Full Screen</span>
              <Maximize2 className="w-3 h-3" />
            </a>
          </div>

          <iframe
            src={swaggerUrl}
            title="FastAPI Swagger Documentation"
            className="w-full h-[800px] rounded-xl border border-white/10 bg-white"
          />
        </div>
      )}

      {/* =========================================================================
           VIEW 2: GUIDE & CODE REFERENCE
           ========================================================================= */}
      {docView === 'guide' && (
        <div className="space-y-10">

          {/* Section 1: Live Cloud Backend & Local Development Switcher */}
          <div className="bg-[#0f1422] border border-white/10 rounded-2xl p-6 shadow-xl space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/5 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500 to-indigo-600 text-white shadow-lg shadow-cyan-500/20">
                  <Globe className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white font-['Outfit']">
                    Live Cloud Backend &amp; Local Development Switcher
                  </h2>
                  <p className="text-xs text-slate-400">
                    Switch the active API server between your local development machine and your 24/7 live production cloud host.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Active API Target:</span>
                <span className="text-xs font-mono px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 font-semibold">
                  {apiBaseUrl ? apiBaseUrl : 'Local Server (Relative /)'}
                </span>
              </div>
            </div>

            {/* Server Target Form */}
            <form onSubmit={handleSaveApiUrl} className="bg-[#090d16] border border-white/10 rounded-xl p-4 space-y-3">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <div className="flex-1">
                  <label className="text-[11px] text-slate-400 block mb-1">
                    API Base URL (Leave empty for Localhost / Proxy; Enter Cloud URL for Live 24/7 Backend):
                  </label>
                  <input
                    type="text"
                    value={customUrlInput}
                    onChange={(e) => setCustomUrlInput(e.target.value)}
                    placeholder="e.g. https://ragops-api.onrender.com or http://127.0.0.1:8000"
                    className="w-full bg-[#0f1422] border border-white/10 rounded-lg px-3.5 py-2 text-xs font-mono text-white placeholder:text-slate-600 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="flex items-end gap-2 pt-2 sm:pt-0">
                  <button
                    type="button"
                    onClick={handlePingServer}
                    disabled={pinging}
                    className="px-4 py-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-200 border border-white/10 text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer"
                  >
                    <Activity className={`w-3.5 h-3.5 ${pinging ? 'animate-spin text-cyan-400' : 'text-slate-400'}`} />
                    <span>{pinging ? 'Pinging...' : 'Test Ping'}</span>
                  </button>

                  <button
                    type="submit"
                    className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors cursor-pointer"
                  >
                    Save Server Target
                  </button>
                </div>
              </div>

              {/* Quick preset switches */}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="text-[11px] text-slate-500">Quick Presets:</span>
                <button
                  type="button"
                  onClick={() => { setCustomUrlInput(''); setApiBaseUrl(''); localStorage.setItem('ragops_api_base_url', ''); }}
                  className="text-[11px] px-2.5 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/10 cursor-pointer"
                >
                  💻 Local Server (Relative /)
                </button>
                <button
                  type="button"
                  onClick={() => { const url = 'http://127.0.0.1:8000'; setCustomUrlInput(url); setApiBaseUrl(url); localStorage.setItem('ragops_api_base_url', url); }}
                  className="text-[11px] px-2.5 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/10 cursor-pointer"
                >
                  ⚡ Localhost (http://127.0.0.1:8000)
                </button>
              </div>

              {pingStatus && (
                <div className={`p-3 rounded-lg border text-xs flex items-center gap-2 ${pingStatus.ok
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                  }`}>
                  {pingStatus.ok ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" /> : <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />}
                  <span>{pingStatus.message}</span>
                </div>
              )}
            </form>
          </div>

          {/* Section 2: Complete Interactive API Reference */}
          <div className="bg-[#0f1422] border border-white/10 rounded-2xl p-6 shadow-xl space-y-6">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/20">
                <Code2 className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white font-['Outfit']">
                  Complete Interactive API Reference
                </h2>
                <p className="text-xs text-slate-400">
                  Executable code snippets in cURL, Python, and JavaScript for every production endpoint.
                </p>
              </div>
            </div>

            {/* Endpoint Selector Tabs */}
            <div className="flex flex-wrap gap-2">
              {endpoints.map((ep) => (
                <button
                  key={ep.id}
                  onClick={() => setSelectedEndpoint(ep.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-mono transition-all cursor-pointer ${selectedEndpoint === ep.id
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                    : 'bg-[#090d16] text-slate-400 hover:text-white border border-white/10'
                    }`}
                >
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${ep.method === 'POST' ? 'bg-cyan-500/20 text-cyan-300' : 'bg-emerald-500/20 text-emerald-300'
                    }`}>
                    {ep.method}
                  </span>
                  <span>{ep.path}</span>
                </button>
              ))}
            </div>

            {/* Selected Endpoint Details */}
            <div className="bg-[#090d16] border border-white/10 rounded-xl p-5 space-y-5">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold font-mono ${currentEndpoint.method === 'POST' ? 'bg-cyan-500/20 text-cyan-300' : 'bg-emerald-500/20 text-emerald-300'
                    }`}>
                    {currentEndpoint.method}
                  </span>
                  <span className="font-mono text-sm text-white font-semibold">{currentEndpoint.path}</span>
                </div>
                <h3 className="text-base font-bold text-white font-['Outfit'] mt-1">{currentEndpoint.title}</h3>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{currentEndpoint.desc}</p>
              </div>

              {/* Code Snippets Section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400 font-medium">Select Language:</span>
                    {['curl', 'python', 'javascript'].map((lang) => (
                      <button
                        key={lang}
                        onClick={() => setActiveCodeTab(lang)}
                        className={`text-xs px-2.5 py-1 rounded font-mono uppercase transition-colors cursor-pointer ${activeCodeTab === lang
                          ? 'bg-indigo-500/20 text-cyan-300 border border-indigo-500/40'
                          : 'text-slate-400 hover:text-white'
                          }`}
                      >
                        {lang}
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={() => handleCopy(currentEndpoint[activeCodeTab])}
                    className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-xs text-slate-300 border border-white/10 transition-colors cursor-pointer"
                  >
                    {copiedCode ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedCode ? 'Copied' : 'Copy Snippet'}</span>
                  </button>
                </div>

                <pre className="bg-[#06080e] border border-white/10 rounded-xl p-4 text-xs font-mono text-slate-200 overflow-x-auto leading-relaxed">
                  <code>{currentEndpoint[activeCodeTab]}</code>
                </pre>
              </div>

              {/* Request & Response Schemas */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pt-2">
                {currentEndpoint.reqBody && (
                  <div>
                    <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block mb-2">
                      Request Payload (JSON)
                    </span>
                    <pre className="bg-[#06080e] border border-white/10 rounded-xl p-3.5 text-[11px] font-mono text-cyan-300 overflow-x-auto">
                      <code>{currentEndpoint.reqBody}</code>
                    </pre>
                  </div>
                )}

                <div>
                  <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block mb-2">
                    Response Payload (JSON)
                  </span>
                  <pre className="bg-[#06080e] border border-white/10 rounded-xl p-3.5 text-[11px] font-mono text-emerald-300 overflow-x-auto">
                    <code>{currentEndpoint.respBody}</code>
                  </pre>
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: Tech Stack & Architecture Deep Dive */}
          <div className="bg-[#0f1422] border border-white/10 rounded-2xl p-6 shadow-xl space-y-6">
            <div className="flex items-center gap-3 border-b border-white/5 pb-4">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/20">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white font-['Outfit']">
                  Production Stack &amp; Architecture Deep Dive
                </h2>
                <p className="text-xs text-slate-400">
                  Why RAGOps is engineered for low latency, zero hallucinations, and continuous feedback.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="bg-[#090d16] border border-white/10 rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
                  <Zap className="w-4 h-4" />
                  <span>Sentence Transformers</span>
                </div>
                <div className="text-xs font-mono text-white">all-MiniLM-L6-v2 (384d)</div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Computes fast, high-density embeddings on CPU in ~14ms. Eliminates external API rate limits and network roundtrips during vectorization.
                </p>
              </div>

              <div className="bg-[#090d16] border border-white/10 rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-cyan-400 font-semibold text-sm">
                  <Cpu className="w-4 h-4" />
                  <span>Cross-Encoder Reranker</span>
                </div>
                <div className="text-xs font-mono text-white">ms-marco-MiniLM-L-6-v2</div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Performs full cross-attention across candidate chunks. Boosts Retrieval Recall@5 to 92%+ and filters out irrelevant document noise before LLM prompting.
                </p>
              </div>

              <div className="bg-[#090d16] border border-white/10 rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                  <Database className="w-4 h-4" />
                  <span>Vector Database</span>
                </div>
                <div className="text-xs font-mono text-white">ChromaDB Persistent HNSW</div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Cosine similarity search using Hierarchical Navigable Small World graphs for sub-15ms nearest-neighbor candidate retrieval across large knowledge bases.
                </p>
              </div>

              <div className="bg-[#090d16] border border-white/10 rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
                  <Zap className="w-4 h-4" />
                  <span>Groq LPU Inference</span>
                </div>
                <div className="text-xs font-mono text-white">LLaMA 3.1 70B Versatile</div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Hardware-accelerated Language Processing Units delivering 500+ tokens/second. Sub-1.4s generation latency with strict provenance citations.
                </p>
              </div>

              <div className="bg-[#090d16] border border-white/10 rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-rose-400 font-semibold text-sm">
                  <ShieldCheck className="w-4 h-4" />
                  <span>Zero Hallucination Guardrail</span>
                </div>
                <div className="text-xs font-mono text-white">Grounded Abstention Prompting</div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  When documents do not contain evidence for a question, the model safely abstains rather than making up answers.
                </p>
              </div>

              <div className="bg-[#090d16] border border-white/10 rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-purple-400 font-semibold text-sm">
                  <Activity className="w-4 h-4" />
                  <span>Evaluation Quality Gates</span>
                </div>
                <div className="text-xs font-mono text-white">CI/CD Regression Blocker</div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Automated Golden Dataset benchmark tests Recall@5, Faithfulness, and P95 latency in GitHub Actions before code can be promoted.
                </p>
              </div>
            </div>
          </div>

        </div>
      )}

    </div>
  );
}
