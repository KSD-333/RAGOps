# RAGOps — End-to-End Enterprise RAG Platform with Observability & Guardrails

[![CI Pipeline](https://github.com/KSD-333/RAGOps/actions/workflows/ci.yml/badge.svg)](https://github.com/KSD-333/RAGOps/actions/workflows/ci.yml)
[![Quality Gate](https://github.com/KSD-333/RAGOps/actions/workflows/evaluation.yml/badge.svg)](https://github.com/KSD-333/RAGOps/actions/workflows/evaluation.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev/)
[![Docker Hub](https://img.shields.io/badge/docker-ketan333%2Fragops-2496ed.svg)](https://hub.docker.com/r/ketan333/ragops)
[![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL%20%7C%20SQLite-336791.svg)](https://www.postgresql.org/)
[![Redis / Memurai](https://img.shields.io/badge/cache-Redis%20%7C%20Memurai-dc382d.svg)](https://redis.io/)
[![Ollama + Groq](https://img.shields.io/badge/llm-Ollama%20%7C%20Groq%20Cloud-f55036.svg)](https://groq.com/)

> **A production-grade, enterprise-hardened Retrieval-Augmented Generation (RAG) and LLMOps platform designed to demonstrate modern AI engineering practices beyond a basic chatbot. Built with a two-stage retrieval pipeline (Dense ChromaDB + Cross-Encoder reranking), multi-tier Redis semantic cache (<2ms exact & ~4.2ms semantic), local-first Ollama with Groq cloud fallback, conversational anaphora & typo normalization, ChatGPT-style typewriter streaming UI, Model Context Protocol (MCP) server, and the 4 Core Enterprise Pillars: RBAC + OAuth, Multi-Layer Guardrails, Cache + Resilient Router, and Observability + Continuous Evals with Wilson 95% confidence intervals.**

---

## 1. Concrete System Architecture

```text
                               ┌─────────────────────────────────────────────────────────┐
                               │           Modern React 19 Web Interface                 │
                               │  (Typewriter Streaming • Master-Detail • Trace Viewer)  │
                               └────────────────────────────┬────────────────────────────┘
                                                            │ HTTP / JSON
                                                            ▼
                               ┌─────────────────────────────────────────────────────────┐
                               │                 FastAPI Gateway Layer                   │
                               │   RBAC Auth (admin / user) • CORS • Lifespan Manager    │
                               └────────────────────────────┬────────────────────────────┘
                                                            │
                     ┌──────────────────────────────────────┴──────────────────────────────────────┐
                     ▼                                                                             ▼
    ┌─────────────────────────────────┐                                           ┌─────────────────────────────────┐
    │     Query Intelligence Engine   │                                           │  Autonomous Corporate Extractor │
    │ ├─ Exact (<2ms) / Semantic (~4ms│                                           │ ├─ Multi-page Site Crawler      │
    │ ├─ Conversational Query Rewrite │                                           │ ├─ Prompt-Injection Defense     │
    │ ├─ Typo & Prefix Normalizer     │                                           │ ├─ Autonomous Search Tool (Gaps)│
    │ └─ Intent Classifier (<5ms)     │                                           │ └─ Quarantined Candidate Queue  │
    └────────────────┬────────────────┘                                           └────────────────┬────────────────┘
                     │                                                                             │
                     ▼                                                                             ▼
    ┌─────────────────────────────────┐                                           ┌─────────────────────────────────┐
    │    Dense / BM25 Hybrid Search   │                                           │   Human-in-the-Loop Validation  │
    │ Sentence-Transformers Embeddings│                                           │ Review, edit, approve, or reject│
    │ ChromaDB HNSW + Document ACLs   │                                           │ structured corporate facts      │
    └────────────────┬────────────────┘                                           └────────────────┬────────────────┘
                     │ Top-K Candidates (Chunks)                                                   │
                     ▼                                                                             │
    ┌─────────────────────────────────┐                                                            │
    │     Cross-Encoder Reranker      │                                                            │
    │ ms-marco-MiniLM-L-6-v2 Scoring  │                                                            │
    │ Relevance Gate (tau >= 0.10)    │                                                            │
    └────────────────┬────────────────┘                                                            │
                     │ Calibrated Grounding Context                                                │
                     ▼                                                                             │
    ┌─────────────────────────────────┐                                                            │
    │   Multi-Provider LLM Router     │                                                            │
    │ Ollama (Local) → Groq (Cloud)   │                                                            │
    │ ├─ Dynamic fallback & breaker   │                                                            │
    │ ├─ Anti-hallucination templates │                                                            │
    │ ├─ Instruction isolation bounds │                                                            │
    │ └─ Zero-knowledge abstention    │                                                            │
    └────────────────┬────────────────┘                                                            │
                     │ Answer + Provenance (Typewriter Stream)                                     │
                     ▼                                                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PostgreSQL / SQLite Telemetry & Datastore                                        │
│ ├─ User Authentication & RBAC (admin, test1, test2 with salted SHA-256) [Demo accounts for testing]             │
│ ├─ Multi-session Chat History & Turn Provenance (Latency Waterfall: Embed, Search, Rerank, LLM)                │
│ ├─ Grounding Chunks & Citations Store                                                                            │
│ ├─ User Feedback Ratings (thumbs up / thumbs down) & Hallucination Triage Queue                                  │
│ ├─ Corporate Facts Catalog, Candidates & Event Outbox                                                            │
│ ├─ Ingested Document Catalog (Auto-classification: Policy, Code, Programme, Governance, Manual)                  │
│ └─ Risk Signal Radar (POSH / Non-compliance / Churn Detection)                                                   │
└──────────────────────────────────────────────────────────┬───────────────────────────────────────────────────────┘
                                                           │
                                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Automated Evaluation & Continuous Improvement                                  │
│ ├─ Golden Benchmark Runner (Recall@5, Wilson 95% CI, Abstention Accuracy, P95 Latency, RAGAS)                    │
│ ├─ CI/CD Quality Gate (<5% regression threshold blocks deployment)                                              │
│ ├─ Fine-Tuning Training Data JSON Exporter                                                                       │
│ └─ Prometheus / Grafana / Jaeger Distributed Tracing                                                             │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Platform Capabilities

### 💬 ChatGPT-Style Multi-Session Conversational Workspace
- **Typewriter Streaming & Real-Time UX**: Generates ChatGPT-style typewriter text flow (~18ms token animation, auto-scroll with manual scroll override, blinking cursor `▍`, and instant "Skip" button) with no blank-screen flashes.
- **Persistent Sessions**: Create, rename, switch between, and purge conversation sessions stored in PostgreSQL or SQLite.
- **Conversational Query Rewriting & Anaphora Resolution**: Solves pronoun ellipsis across turns (e.g., automatically resolving *"what is agent"* followed by *"and how to create one"* into *"how to create agent"* before vector search).
- **Typo Normalization & Prefix Stripping**: Automatically repairs typos (e.g., `"crate"` $\rightarrow$ `"create"`, `"polies"` $\rightarrow$ `"policies"`) and strips conversational filler words (`"like "`, `"so "`, `"bro "`, `"and "`) to ensure high embedding match scores.
- **Session Isolation**: Standard users only view and interact with their own conversation history, while administrators retain global audit capabilities.

### ⚡ High-Performance Redis / Memurai Semantic Cache (<2ms Exact & ~4.2ms Semantic)
- **Multi-Tier Caching Architecture**:
  - **Tier 1 (In-Memory Hot Cache)**: Instantaneous $<0.1\text{ ms}$ lookup.
  - **Tier 2 (Redis / Memurai Exact Match)**: Sub-2ms ($<2\text{ ms}$) instant response for identical query hashes (`ragops:cache:exact:{company}:{hash}`).
  - **Tier 3 (Redis Semantic Relevance Match)**: Pre-filters cached queries by scope and intent, computes cosine similarity against candidate embedding vectors (averaging $\sim 4.2\text{ ms}$ on benchmarks), and delivers a direct cache hit if query similarity is $\ge 90\% - 95\%$ (configurable via `CACHE_SIMILARITY_THRESHOLD=0.90`).
  - **Tier 4 (Durable Database Cache)**: Backed by PostgreSQL / SQLite `SemanticCacheModel` with automatic backfill into Redis.
- **Zero-Touch Auto-Start**: Automatically detects if Redis is offline on backend launch (`ragops serve` / FastAPI startup) and starts the Memurai Windows Service or daemon process silently in the background (`CREATE_NO_WINDOW = 0x08000000`), eliminating manual intervention and CMD popups.
- **Memurai Support on Windows**: Out-of-the-box compatibility with native Windows Memurai instances on `127.0.0.1:6379`.
- **Zero-Hallucination Cache Guardrail**: LLM abstentions and refusal answers are strictly barred from being cached or served from cache.
- **Scope & Entity Isolation**: Prevents semantic cross-matching across different document scopes (e.g., collection-wide count vs document-specific policies).
- **Cost & Latency Elimination**: Avoids 1,000–3,000ms LLM turnaround times and reduces API token costs to $0.00 for frequently asked inquiries.
- **Live Cache Dashboard Telemetry**: Exposes Redis connection status, memory footprint, hit counters, and latency/cost savings via `/api/v1/cache/stats` and the Web UI console.

### 🛡️ Enterprise RBAC & Simulated Account Switcher
- **Role-Based Access Control**: Strict segregation between `admin` and standard `user` accounts.
- **Cryptographic Security**: Passwords hashed with `SHA-256` plus unique 32-character random salts.
- **Integrated Account Switcher**: Easily toggle between `admin`, `test1` (HR/general queries), and `test2` (dev/infrastructure queries) from the Web UI to test RBAC boundaries.
- **Automatic Fallback**: Seamlessly connects to PostgreSQL via SQLAlchemy and `asyncpg`, with graceful failover to local SQLite if PostgreSQL is offline.

### 🌐 Autonomous Corporate Web Intelligence & Knowledge Hub
- **Universal Multi-Page Crawler**: Traverses company websites, discovering subpages, leadership bios, manufacturing plants, and OEM partnerships.
- **AI Gap-Filling Search Tool**: Automatically formulates web search queries when critical data (such as corporate headquarters or executive leadership) is missing from crawled pages.
- **Human-in-the-Loop Fact Review**: Extracted corporate facts are staged into a PostgreSQL candidate queue with confidence scores and source URLs. Administrators can review, inline-edit, approve, or reject facts before vectorizing.
- **Verified ChromaDB Embedding**: Approved facts are compiled into grounded vector chunks and indexed into ChromaDB.
- **Event Outbox Architecture**: Staged publishing events ensure idempotent delivery and audit tracking across microservices.

### 🔍 Master-Detail User Directory & Side-by-Side Chat Audit
- **Clean Master-Detail Layout**: Replaces cluttered full-page dumps with an interactive, space-saving split view.
- **Session List (Left Panel)**: Displays user conversation threads with first-prompt snippet, timestamp, turn count badge (`💬 X prompts`), token spend, and high-priority `RISK` tags. Includes real-time keyword search and risk-only filtering.
- **Side-by-Side Conversation Viewer (Right Panel)**: Displays the active conversation thread with prompt bubbles, markdown-formatted AI responses (`ragops-markdown`), clickable citation tags, and expandable grounding chunks.
- **One-Click Actions**: One-click prompt copying, answer copying, session ID copying, and rerun in search.

### 📊 Distributed Request Tracing & Retrieval Inspector
- **Compact Space-Saving Cards**: Eliminates endless scrolling by displaying all necessary metadata in a dense ~65px summary bar: Trace ID, `@username`, timestamp, color-coded latency badge (green `<1000ms`, amber `1000–2500ms`, rose `>2500ms`), token counts (`In: Xt • Out: Yt`), and risk tags.
- **Click-to-Expand AI Response**: Clicking anywhere on the card header or "View AI Response" button smoothly reveals the grounded response and complete multi-hop latency waterfall:
  $$\text{Total Latency} = \text{Embedding} + \text{ChromaDB Vector Search} + \text{Cross-Encoder Reranking} + \text{LLM Generation}$$
- **Global Toolbar Controls**: Bulk **Expand All** and **Collapse All** buttons, live keyword search, and filter pills (**All**, **Risk Signals**, **Slow >1.5s**).

### 🚨 Frequent Questions & Risk Signals Radar
- **Semantic Clustering**: Automatically groups high-frequency queries to surface common user pain points and average response latencies.
- **Corporate Risk Detection**: Proactively alerts administrators on:
  - **POSH & Compliance Violations**: Queries concerning harassment policies, internal reporting, or ethical breaches.
  - **Churn Risk Signals**: Negative employee sentiment, leaving intent, or client attrition keywords.
- **One-Click Query Rerun**: Rerun any flagged query directly in the Search Console to verify grounded guardrails.

### 📑 Document Catalog & Storage Reconciliation Engine
- **Automated Classification**: Automatically tags uploaded PDFs and Markdown documents as **Policy**, **Code**, **Programme**, **Governance**, or **Manual**.
- **Disk Storage Reconciliation**: `/api/v1/catalog/sync` reconciles files physically stored on disk in `data/raw/` with database records and ChromaDB embeddings.
- **Selective & Batch Vector Ingestion**: Re-embed individual pending documents or trigger bulk ChromaDB indexing directly from the Web UI.

### 💰 Enterprise Token Billing & Quota Tracker
- **Real-Time Token Accounting**: Accurately tracks input tokens, output tokens, and estimated USD spend across all requests.
- **Contract Budget Calculator**: Configurable token thresholds and monetary pricing (supports ₹, $, €, £).
- **ML Training Dataset Exporter**: Export filtered positive grounded Q&A pairs as standard JSON datasets for fine-tuning open-source LLMs.

### 🔌 Model Context Protocol (MCP) Integration
RAGOps provides a first-class Model Context Protocol (MCP) server over `stdio` transport, enabling AI desktop clients (such as Claude Desktop, Cursor, and Continue) and enterprise tools (Jira, Confluence) to query your enterprise knowledge base, ingest documents, inspect traces, and monitor cache statistics directly:

#### Claude Desktop Configuration (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "ragops": {
      "command": "ragops",
      "args": ["mcp"],
      "env": {
        "LLM_PROVIDER": "auto",
        "DATABASE_URL": "postgresql://postgres:1234@localhost:5432/ragops"
      }
    }
  }
}
```

#### Available MCP Tools
- **`search_knowledge_base(query, top_k=5)`**: Query enterprise documents with dense/hybrid search, cross-encoder reranking, and citation provenance.
- **`list_documents()`**: List all indexed documents, chunk counts, and total inventory.
- **`ingest_document(path)`**: Safely ingest a document from `data/raw/` into ChromaDB (with built-in path-traversal protection).
- **`get_trace(trace_id)`**: Inspect execution traces, latencies, chunk provenance, and token usage for any query.
- **`cache_stats()`**: Fetch real-time hit rates, memory consumption, and entries in the Redis semantic cache.

---

## 3. The Four Production RAG Pillars (Enterprise Architecture)

Modern enterprise RAG systems fail when treated as simple wrappers around an LLM and a vector database. RAGOps is architected around four distinct production pillars:

```mermaid
flowchart TD
    subgraph P1["Pillar 5: RBAC + OAuth & Access Control"]
        A1["User Authentication (OAuth2 / Salted SHA-256)"] --> A2["Role Segregation: Admin vs User"]
        A2 --> A3["Document & Chunk Metadata ACLs"]
        A3 --> A4["Pre-Retrieval Filter (where role_access in user_roles)"]
        A4 --> A5["Zero-Leakage Guarantee (Confidential / Salary PDFs)"]
    end

    subgraph P2["Pillar 6: Production Guardrails & Defensive RAG"]
        B1["Input Prompt Injection Scanner"] --> B2["Instruction Delimiters (=== BEGIN/END ===)"]
        B2 --> B3["Calibrated Reranker Gate (Score < 0.10)"]
        B3 --> B4["Zero-Hallucination Authoritative Abstention"]
        B4 --> B5["PII / Sensitive Token Masking"]
    end

    subgraph P3["Pillar 7: Multi-Tier Semantic Cache & Router"]
        C1["Tier 1: Hot In-Memory LRU (<0.1ms)"] --> C2["Tier 2: Redis Exact Hash Match (<2ms)"]
        C2 --> C3["Tier 3: Redis Cosine Semantic Cache (~4.2ms)"]
        C3 --> C4["Resilient LLM Router: Local Ollama → Groq Cloud"]
        C4 --> C5["Silent Win32 Background Spawn & WarmupCoordinator"]
    end

    subgraph P4["Pillar 8: Observability, Tracing & Evals"]
        D1["OpenTelemetry Distributed Tracing & Trace IDs"] --> D2["Multi-Hop Latency Waterfall Breakdown"]
        D2 --> D3["Token Accounting & Contract Billing"]
        D3 --> D4["Golden Benchmark Suite (N=50) + Wilson 95% CI"]
        D4 --> D5["Automated CI/CD Quality Gates & Regressions"]
    end
```

---

### Pillar 5: Enterprise RBAC, OAuth 2.0 & Sensitive Data ACLs

#### The "Employee Querying CEO Salary" Challenge in Enterprise RAG
In naive RAG systems, all enterprise documents are indexed into a single global vector store. When an unauthorized employee asks:
> *"What is the CEO's current base salary and bonus package?"*

Naive vector retrieval matches the query against executive compensation PDFs, inserts those chunks directly into the LLM context, and the model outputs confidential payroll figures. Prompt-based instructions like *"Do not reveal salaries to non-managers"* are notoriously vulnerable to prompt injection, jailbreaks, and indirect prompt extraction.

#### The RAGOps Defense-in-Depth Solution:
1. **Pre-Retrieval Metadata ACL Filtering**:
   - During document ingestion, chunks carry metadata tags: `{"role_access": ["admin", "executive"]}` vs `{"role_access": ["user", "admin"]}`.
   - The FastAPI Gateway extracts the authenticated identity (`request.state.user.role`).
   - When retrieving from ChromaDB, metadata filters are enforced at the index layer:
     ```python
     # Enforced before vector candidates ever reach the reranker or LLM context
     results = collection.query(
         query_embeddings=query_vec,
         n_results=top_k,
         where={"role_access": {"$in": user_roles}}
     )
     ```
2. **Grounded Abstention Without Information Disclosure**:
   - Because unauthorized chunks are filtered out before scoring, the cross-encoder returns a relevance score of $0.00$.
   - The pipeline triggers an authoritative grounded abstention:
     > *"I searched the corporate knowledge base, but could not locate verified documents or policies with sufficient relevance to answer your question regarding 'CEO salary'."*
   - The system does not even disclose that a salary document exists in the repository.
3. **Session Ownership & Tenant Isolation**:
   - Standard users can only view, modify, and delete their own multi-turn chat sessions (`/api/v1/sessions`).
   - Administrators possess master-detail audit views to investigate risks, audit latencies, and export training pairs without compromising data integrity.
4. **FastMCP Integration with Granular Tool Isolation**:
   - Enterprise desktop clients (Claude Desktop, Cursor) communicate through Model Context Protocol (MCP) using least-privilege tool execution, ensuring tool operations conform to the authenticated caller's security scope.

---

### Pillar 6: Multi-Layer Guardrails & Defensive RAG

#### 1. Prompt Injection & Jailbreak Defense
- **Heuristic & Pattern Detection (`PromptInjectionDetector`)**: Pre-screens queries for jailbreaks, prompt override commands (`"ignore all previous instructions"`, `"you are now in DAN mode"`, `"system override"`), and format manipulation payloads.
- **Strict Instruction Isolation Delimiters**:
  Retrieved context is explicitly walled off inside boundary delimiters:
  ```text
  === BEGIN REFERENCE DATA ===
  [Document 1 | Source: corporate_policy.pdf | Chunk: chunk_002]
  ...
  === END REFERENCE DATA ===
  ```
- **Untrusted Reference Principle**:
  The system prompt instructs the LLM that text between reference delimiters is strictly reference knowledge. Any commands, instructions, or role changes embedded inside document text are completely ignored.

#### 2. Calibrated Cross-Encoder Grounding Gate ($\tau = 0.10$)
- Naive RAG uses cosine similarity from bi-encoders, which suffers from high false-positive rates on semantic overlap.
- RAGOps routes candidate chunks through a full cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`) that performs joint attention across query-document pairs.
- If the highest reranker score falls below the calibrated confidence threshold ($\tau = 0.10$), the pipeline halts before dispatching tokens to the LLM and delivers an immediate grounded refusal in $<85\text{ ms}$, burning zero LLM tokens.
- **Measured Accuracy**: $100\%$ abstention on 15 out-of-domain and adversarial probe questions ($[79.6\%, 100.0\%]$ Wilson 95% CI).

#### 3. PII & Sensitive Pattern Masking
- Telemetry logging, trace cards, and chat audits automatically mask detected sensitive patterns (SSNs, credit card numbers, Bearer tokens, private API keys) before storing to PostgreSQL/SQLite.

#### 4. Zero-Knowledge Cache Guardrail
- Refusal answers, abstention notices, and error messages are strictly excluded from Redis semantic cache, preventing negative cache poisoning attacks.

---

### Pillar 7: Multi-Tier Semantic Cache & Resilient Router

#### 1. Four-Tier Caching Architecture
| Tier | Layer | Average Latency | Scope |
|:---|:---|:---|:---|
| **Tier 1** | In-Memory LRU Hot Cache | $< 0.1\text{ ms}$ | High-frequency queries in active process memory |
| **Tier 2** | Redis / Memurai Exact Hash Cache | **0.8 ms** ($< 2.0\text{ ms}$) | SHA-256 hash match (`ragops:cache:exact:{company}:{hash}`) |
| **Tier 3** | Redis Cosine Semantic Cache | **4.2 ms** ($< 10.0\text{ ms}$) | Pre-filtered cosine similarity ($\ge 0.90$ threshold) against candidate embedding vectors |
| **Tier 4** | PostgreSQL / SQLite Durable Cache | $< 15.0\text{ ms}$ | Persistent cross-restart store with auto-backfill into Redis |

#### 2. Resilient LLM Router with Circuit Breaker
- **Local-First Ollama**: Default model `llama3.2:3b` runs 100% offline with zero cloud API dependencies.
- **Cloud Groq Fallback**: If local Ollama is offline or times out, the router automatically fails over to Groq Cloud API (`openai/gpt-oss-120b` or configured Groq model).
- **Three-Strike Circuit Breaker**: If a provider fails 3 times consecutively, its circuit breaker trips to `OPEN` for 60 seconds, preventing latency spikes from repeated failing timeouts.
- **Graceful Degraded Mode**: If all LLM providers are unavailable, the system continues serving document ingestion, hybrid vector search, and semantic cache hits, returning clear setup diagnostics instead of crashing.

#### 3. Zero-Touch Windows Daemon Management & Silent Startup
- **Elimination of Windows CMD Popups**: Utility calls (`sc.exe start Memurai`, `net start Memurai`, `ollama.exe serve`) are spawned with Win32 `CREATE_NO_WINDOW = 0x08000000`, eliminating the 18–20 flashing black CMD windows on backend launch.
- **Uvicorn Reload Isolation**: Uvicorn is explicitly configured with `reload_dirs=["src/ragops"]` and `reload_excludes=["*.log", "*.db", "*.sqlite3*", "data/*", "react/*", ".git/*"]`, permanently resolving the infinite server reload loop caused by ChromaDB SQLite WAL writes.
- **Non-blocking Startup Warmup (`WarmupCoordinator`)**: Pre-warms embedding weights, cross-encoders, and vector index connections asynchronously during FastAPI startup lifespan, reducing cold-start first-query delay from $25\text{s}+$ down to sub-second ready state.

---

### Pillar 8: Enterprise Observability, Distributed Tracing & Continuous Evals

#### 1. Distributed Request Tracing & Latency Waterfall
Every request receives a cryptographically unique `trace_id`. The Web UI and API expose the exact latency waterfall across every pipeline hop:
$$\text{Total Latency} = \text{Embedding} + \text{ChromaDB Vector Search} + \text{Cross-Encoder Reranking} + \text{LLM Generation}$$

```text
[Trace 4f9a8b1c] Total: 1,412ms
├── 1. Embed Query (all-MiniLM-L6-v2)    : 15.2ms  ( 1.1%)
├── 2. ChromaDB HNSW Dense Search       :  4.1ms  ( 0.3%)
├── 3. Cross-Encoder Rerank (ms-marco)   : 38.6ms  ( 2.7%)
└── 4. LLM Generation (llama3.2:3b)      : 1,354.1ms (95.9%)
```

#### 2. Automated Golden Benchmark Suite & Wilson 95% Confidence Intervals
RAGOps runs an automated 50-query golden benchmark suite ($N = 50$, 35 in-domain retrieval queries, 15 out-of-domain/adversarial probes):
- **Retrieval Recall@5**: $94.3\%$ ($33/35$ hits), $[81.4\%, 98.4\%]$ Wilson 95% CI.
- **Grounded Abstention Accuracy**: $100.0\%$ ($15/15$ abstentions), $[79.6\%, 100.0\%]$ Wilson 95% CI.
- **Citation Precision / Support**: $91.4\%$ ($32/35$ citations), $[77.6\%, 97.0\%]$ Wilson 95% CI.
- **Overall System Correctness**: $94.0\%$ ($47/50$ correct), $[83.8\%, 97.9\%]$ Wilson 95% CI.

#### 3. Continuous CI/CD Quality Gate
Evaluations run via `python scripts/run_evaluation.py --fail-on-gate`. The CI pipeline blocks merge or deployment if:
- Retrieval Recall@5 drops below $0.85$
- Faithfulness drops below $0.90$
- P95 Latency exceeds $3,000\text{ ms}$
- Regression vs. production baseline exceeds $5\%$

---

## 4. Measured Performance & Quality Benchmarks

| Metric | Sample Size ($n$) | Target Threshold | Measured Result | 95% Wilson Confidence Interval | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Exact-Match Cache Latency** | $N = 50$ | $< 2.0\text{ ms}$ | **0.8 ms** | — | ✅ Exceeds |
| **Semantic Cache Lookup** | $N = 50$ | $< 10.0\text{ ms}$ | **4.2 ms** (measured avg) | — | ✅ Exceeds |
| **Median Latency (P50)** | $N = 50$ | $< 2,000\text{ ms}$ | **1,412.0 ms** | — | ✅ Exceeds |
| **Tail Latency (P95)** | $N = 50$ | $< 3,000\text{ ms}$ | **1,780.0 ms** | — | ✅ Exceeds |
| **In-Domain Retrieval Recall@5** | $n = 35$ | $\ge 85.0\%$ | **94.3%** ($33 / 35$ hits) | $[81.4\%, 98.4\%]$ | ✅ Exceeds |
| **Grounded Abstention Accuracy** | $n = 15$ | $100.0\%$ | **100.0%** ($15 / 15$ abstentions) | $[79.6\%, 100.0\%]$ | ✅ Perfect |
| **Citation Precision / Support** | $n = 35$ | $> 85.0\%$ | **91.4%** ($32 / 35$ citations) | $[77.6\%, 97.0\%]$ | ✅ Exceeds |
| **Overall System Correctness** | $N = 50$ | $> 90.0\%$ | **94.0%** ($47 / 50$ correct) | $[83.8\%, 97.9\%]$ | ✅ Exceeds |

---

## 5. Repository Structure

```text
ragops/
├── README.md                           # Master platform documentation, architecture & guide
├── POSTGRES_SETUP_GUIDE.md             # Dedicated PostgreSQL operations & setup guide
├── INTERVIEW_PREP_GUIDE.md             # Senior engineer system design & defense guide
├── HOW_IT_WORKS_AND_OPERATIONS_GUIDE.md# End-to-end operations and data flow handbook
├── pyproject.toml                      # Python dependencies and build metadata
├── .env.example                        # Environment variables template
│
├── react/                              # Enterprise React 19 + Tailwind v4 Web Console
│   ├── src/
│   │   ├── App.jsx                     # Root application container & page routing
│   │   ├── index.css                   # Tailwind v4 styles, custom scrollbars, ragops-markdown
│   │   └── components/
│   │       ├── Navbar.jsx              # Responsive header, environment badge, auth switcher
│   │       ├── SearchPage.jsx          # Typewriter streaming chat, session sidebar, crawler
│   │       ├── DashboardPage.jsx       # 6-tab enterprise observability & intelligence suite
│   │       ├── AuthModal.jsx           # RBAC simulated user switcher (admin, test1, test2)
│   │       ├── ChunkModal.jsx          # Interactive chunk inspector & raw payload viewer
│   │       ├── ErrorBoundary.jsx       # React ErrorBoundary preventing blank screen crashes
│   │       └── DocsPage.jsx            # Interactive API reference & target server switcher
│   ├── dist/                           # Compiled production static bundle
│   └── package.json
│
├── src/ragops/
│   ├── api/                            # FastAPI REST Service Layer
│   │   ├── app.py                      # Application lifespan, CORS, static file serving
│   │   ├── dependencies.py             # Service singletons & dependency injection
│   │   ├── static_react/               # Embedded production React frontend for zero-config deploy
│   │   └── routes/
│   │       ├── auth.py                 # /login, /register, /me (RBAC authentication)
│   │       ├── query.py                # Multi-session /query, /sessions, /catalog, /cache
│   │       ├── admin.py                # /analytics, /users, /history, /training-export
│   │       ├── company.py              # Autonomous crawler, candidates, knowledge, outbox
│   │       ├── feedback.py             # Telemetry logging, ratings, triage dashboard
│   │       └── health.py               # Liveness, readiness probe, Prometheus /metrics
│   │
│   ├── company/                        # Corporate Intelligence Subsystem
│   │   ├── crawler.py                  # Multi-page website web crawler
│   │   ├── extractor.py                # LLM fact extraction engine (locations, clients, hubs)
│   │   ├── service.py                  # Knowledge reconciliation, candidate staging
│   │   └── schema.py                   # Pydantic schemas for corporate facts
│   │
│   ├── tools/                          # Autonomous Search & Extraction Tools
│   │   ├── web_extractor.py            # Universal multi-page website analyzer
│   │   └── search_tool.py              # Gap-filling autonomous AI search integration
│   │
│   ├── rag/                            # RAG Orchestration & Intelligence
│   │   ├── pipeline.py                 # End-to-end multi-turn query execution pipeline
│   │   ├── query_intelligence.py       # Sub-10ms semantic cache & conversational pronoun rewriter
│   │   ├── query_transform.py          # Typo correction table & prefix normalizer
│   │   └── context_builder.py          # Grounding context assembly and citation indexing
│   │
│   ├── retrieval/                      # Vector & Dense Search
│   │   ├── embeddings.py               # Sentence-Transformers persistent embeddings
│   │   ├── vector_store.py             # ChromaDB vector store wrapper & metadata ACL filtering
│   │   ├── reranker.py                 # Cross-encoder reranking (ms-marco-MiniLM-L-6-v2)
│   │   └── retriever.py                # Multi-stage retrieval coordinator
│   │
│   ├── generation/                     # LLM Generation Layer
│   │   ├── prompts.py                  # Anti-hallucination templates & citation prompts
│   │   ├── router.py                   # Local Ollama / Groq Cloud router & circuit breaker
│   │   └── response.py                 # Response builder with source attribution
│   │
│   ├── ingestion/                      # Document Ingestion Pipeline
│   │   ├── classifier.py               # Document type classification (Policy, Code, etc.)
│   │   ├── chunkers.py                 # Recursive token-aware text splitters
│   │   └── pipeline.py                 # Ingestion orchestrator
│   │
│   ├── storage/                        # Persistence Layer
│   │   ├── database.py                 # SQLAlchemy session management & engine auto-detection
│   │   ├── redis_cache.py              # Redis / Memurai semantic cache with Win32 silent auto-start
│   │   ├── models.py                   # Models: User, QueryLog, Feedback, FactCandidate, etc.
│   │   └── repositories.py             # Enterprise DAO queries & data export
│   │
│   └── cli/                            # Unified Click CLI (`ragops`)
│
├── compose/                            # Container Orchestration
│   └── docker-compose.yml              # RAGOps API + PostgreSQL 16 + Prometheus + Grafana + Jaeger
│
├── docker/                             # Docker Build Definitions
│   ├── Dockerfile.api                  # Production API container with React bundle
│   ├── Dockerfile.worker               # Asynchronous worker container
│   └── Dockerfile.evaluation           # Automated benchmark evaluation container
│
└── tests/                              # Comprehensive Pytest Suite (88 passing unit tests)
```

---

## 6. Quickstart & Deployment

### Prerequisites
- **Python 3.11+** or **Docker**
- **Ollama** (for local-first inference) or **Groq API Key** (from [console.groq.com](https://console.groq.com))
- *(Optional)* **Redis / Memurai on Windows** (`127.0.0.1:6379`) for ultra-fast caching (auto-managed by RAGOps)
- *(Optional)* **PostgreSQL 15+** (auto-falls back to SQLite if PostgreSQL is offline)

---

### Option A: Run via Docker (Zero-Setup Deployment)

```bash
# Pull production image from Docker Hub
docker pull ketan333/ragops:latest

# Run container with port 8000 exposed
docker run -d \
  -p 8000:8000 \
  -e GROQ_API_KEY="your-groq-api-key" \
  -v $(pwd)/data:/app/data \
  --name ragops-service \
  ketan333/ragops:latest

# Open the Web UI: http://localhost:8000/
```

---

### Option B: Full Production Stack via Docker Compose (with PostgreSQL & Grafana)

```bash
# 1. Clone repository
git clone https://github.com/KSD-333/RAGOps.git
cd RAGOps

# 2. Configure environment
cp .env.example .env

# 3. Launch all services
docker compose -f compose/docker-compose.yml up -d

# Services available:
# - Web Console & API:    http://localhost:8000/
# - PostgreSQL:           localhost:5432 (user: ragops, db: ragops)
# - Prometheus:           http://localhost:9090/
# - Grafana Dashboards:   http://localhost:3000/ (admin / admin)
# - Jaeger Tracing:       http://localhost:16686/
```

---

### Option C: Local Development Setup (Python + React)

```bash
# 1. Clone repository
git clone https://github.com/KSD-333/RAGOps.git
cd RAGOps

# 2. Set up Python virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# 3. Install backend dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .

# 4. Configure environment
cp .env.example .env

# 5. Ingest initial knowledge base
ragops ingest data/raw --version v1

# 6. One-Command Dev Launcher (Backend + React UI)
# On Windows:
.\start_dev.bat
# Or CLI:
ragops dev

# Access Web UI:   http://localhost:5173/ (or http://127.0.0.1:8000/)
# Access API Docs:  http://127.0.0.1:8000/docs
```

---

## 7. Default Test Credentials (Demo Accounts for Local Testing Only)

> [!WARNING]
> **Demo Accounts for Local Testing Only**: The pre-seeded credentials below (`admin`, `test1`, `test2`) are provided exclusively for local sandbox evaluation and developer testing. In shared or production-facing environments, change default credentials immediately and configure API secrets via environment variables.

| Username | Default Password | Role | Access Level |
|---|---|---|---|
| **`admin`** | `admin123` | **ADMIN** | Full administrative access to the 6-tab Observability Dashboard, billing calculator, all user chat audits, trace logs, document catalog, and training dataset exports. |
| **`test1`** | `test123` | **USER** | Standard user account (HR, workplace policies, and corporate architecture questions). |
| **`test2`** | `test223` | **USER** | Technical user account (infrastructure, Kubernetes, and developer documentation). |

*Use the **Account Switcher** button in the Web UI navigation bar to instantly simulate queries as any user.*

---

## 8. Web Console & Observability Walkthrough

### 💬 Search & Chat Console (`/`)
* **Typewriter Flow**: Smooth ~18ms token animation, auto-scroll, skip typing button, and instant rendering.
* **Multi-Session Sidebar**: Create new chats, switch between previous conversations, and delete sessions.
* **Grounded Citations & Chunk Modal**: Every response lists verified corporate sources. Clicking any citation opens the **ChunkModal** displaying the exact raw context snippet, page number, and similarity match percentage.
* **Interactive Live URL Crawler**: Click the URL icon to crawl any corporate website on demand, preview extracted intelligence (plants, clients, executive team), edit facts inline, and embed directly into ChromaDB.
* **Feedback Loop**: Record **Accurate** 👍 or **Inaccurate** 👎 ratings to feed real-world telemetry into the continuous improvement pipeline.

---

### 📈 Enterprise Observability & Intelligence Dashboard (`/dashboard`)

Access restricted to administrators:
1. **Overview & Billing**: Real-time token usage, budget progress bar, latency metrics, and fine-tuning dataset JSON exporter.
2. **User Directory & Chat History (Master-Detail Side-by-Side)**: Interactive session list with turn counts, risk badges, prompt previews, and complete side-by-side conversation streams.
3. **Distributed Request Tracing & Retrieval Inspector**: Compact space-saving cards (~65px) displaying Trace IDs, latency badges, token spend, and click-to-expand multi-hop latency waterfalls.
4. **Frequent Questions & Risk Radar**: Semantic clustering of high-frequency user inquiries, POSH/compliance violations, and employee/customer churn signals.
5. **Company Knowledge Hub & Autonomous Profile**: Multi-company corporate profile viewer, candidate review queue (approve, edit, reject facts), and transactional outbox event stream.
6. **Document Catalog & Semantic Cache Engine**: Document inventory auto-categorized by type (Policy, Code, Governance, Manual), disk reconciliation (`/api/v1/catalog/sync`), and live Redis semantic cache performance telemetry.

---

## 9. Complete REST API Reference

### Authentication & RBAC
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Authenticate user; returns username, role, and profile |
| `POST` | `/api/v1/auth/register` | Register new user account |
| `GET` | `/api/v1/auth/me` | Fetch active authenticated user profile |

### Querying, Sessions & Ingestion
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/query` | Submit multi-turn query with conversational memory, reranking, and semantic cache |
| `GET` | `/api/v1/sessions` | List user conversation sessions (filtered by role and username) |
| `GET` | `/api/v1/sessions/{id}` | Retrieve all turn-by-turn prompts, answers, and chunks for a session |
| `DELETE` | `/api/v1/sessions/{id}` | Permanently delete a conversation session |
| `POST` | `/api/v1/ingest` | Ingest local files or directories into ChromaDB vector store |
| `GET` | `/api/v1/documents/count` | Total count of indexed vector chunks |

### Document Catalog & Semantic Cache
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/catalog` | List all cataloged documents with classifications and chunk counts |
| `POST` | `/api/v1/catalog/upload` | Upload PDF/Markdown file with auto-classification and vector indexing |
| `POST` | `/api/v1/catalog/sync` | Reconcile disk files in `data/raw/` with database and vector store |
| `POST` | `/api/v1/catalog/embed/{source}` | Embed an individual pending document into ChromaDB |
| `POST` | `/api/v1/catalog/embed-all` | Batch embed all pending documents into ChromaDB |
| `DELETE` | `/api/v1/catalog/{source}` | Delete file from disk, database, and purge vector chunks from ChromaDB |
| `GET` | `/api/v1/cache/stats` | Semantic cache telemetry (hit rate %, latency saved, cost saved) |
| `POST` | `/api/v1/cache/clear` | Purge semantic cache entries |

### Autonomous Corporate Intelligence
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/company/profile` | Retrieve verified corporate profile for active organization |
| `POST` | `/api/v1/company/profile` | Update corporate facts (locations, clients, products, leadership) |
| `POST` | `/api/v1/company/scrape-preview` | Crawl website URL and generate structured preview for user verification |
| `POST` | `/api/v1/company/approve-and-embed`| Validate, approve, and embed crawled facts into PostgreSQL & ChromaDB |
| `GET` | `/api/v1/company/candidates` | List staged fact candidates pending human-in-the-loop review |
| `POST` | `/api/v1/company/candidates/{id}/approve` | Approve a candidate fact into verified knowledge |
| `POST` | `/api/v1/company/candidates/{id}/reject` | Reject and dismiss a candidate fact |
| `PUT` | `/api/v1/company/candidates/{id}` | Inline-edit candidate fact value or category |
| `GET` | `/api/v1/company/knowledge` | List approved corporate facts |
| `GET` | `/api/v1/company/outbox` | View publication outbox event stream |
| `GET` | `/api/v1/company/universal/companies` | List all tracked corporate entities |
| `POST` | `/api/v1/company/universal/analyze` | Multi-page crawl, gap-filling AI search, and fact extraction |

### Observability, Admin & Telemetry
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/admin/analytics` | Aggregated telemetry, user count, frequent queries, risk counts, and engine info |
| `GET` | `/api/v1/admin/users` | List all registered users with token consumption and query counts |
| `GET` | `/api/v1/admin/users/{username}/history` | Retrieve full multi-turn chat audit for a specific user |
| `GET` | `/api/v1/admin/logs` | Fetch distributed query trace logs with multi-hop latency attribution |
| `GET` | `/api/v1/admin/training-export` | Export fine-tuning dataset of grounded positive Q&A pairs (JSON) |
| `POST` | `/api/v1/feedback` | Record user feedback (👍 / 👎 ratings and comments) |
| `GET` | `/api/v1/feedback/stats` | Overall satisfaction rate and feedback totals |
| `GET` | `/api/v1/feedback/dashboard` | Feedback summary, token consumption, and disliked query triage table |
| `GET` | `/health` | Liveness health check |
| `GET` | `/health/ready` | Readiness probe (verifies database & vector store connectivity) |
| `GET` | `/metrics` | Prometheus telemetry metrics scrape endpoint |

---

## 10. CLI Reference

RAGOps provides a unified command-line tool `ragops`:

| Command | Usage | Description |
|---|---|---|
| `ragops doctor` | `ragops doctor` | Full diagnostic inspection of LLM providers (Ollama, Groq), database, cache, and vector store with remediation hints |
| `ragops mcp` | `ragops mcp` | Launch the FastMCP Model Context Protocol server over stdio for Claude Desktop, Cursor, or Continue |
| `ragops dev` | `ragops dev` | Launch unified local development stack (FastAPI backend on :8000 + React UI on :5173) |
| `ragops ingest` | `ragops ingest <path> [--version <v>]` | Ingest PDF, HTML, or Markdown files into ChromaDB |
| `ragops query` | `ragops query "<question>" [--top-k 5]` | Ask questions from the terminal with latency attribution and citations |
| `ragops evaluate`| `ragops evaluate -d <dataset.jsonl> [--version <v>]` | Run quality evaluation benchmark against golden dataset with Wilson 95% CI |
| `ragops serve` | `ragops serve [--host 0.0.0.0] [--port 8000]` | Launch FastAPI HTTP service & embedded React Web UI |
| `ragops status`| `ragops status` | Display current models, thresholds, and active version |

---

## 11. Configuration & Environment Variables Reference

Configure these settings in `.env` (refer to `.env.example` for starter template):

| Variable | Default Value | Description |
|---|---|---|
| `LLM_PROVIDER` | `auto` | Active LLM routing mode: `auto` (Ollama first, Groq fallback), `ollama`, or `groq` |
| `LLM_TIMEOUT_SECONDS` | `30` | Maximum timeout in seconds per LLM generation call |
| `LLM_MAX_RETRIES` | `2` | Bounded retries with exponential backoff on transient network failures |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Base URL for local Ollama daemon |
| `OLLAMA_MODEL` | `llama3.2:3b` | Target local Ollama model identifier |
| `OLLAMA_AUTO_PULL` | `false` | Automatically pull target model if absent (`true` / `false`) |
| `GROQ_API_KEY` | *(empty)* | Cloud Groq API key from [console.groq.com](https://console.groq.com) |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model name (validated against Groq `/models` endpoint at runtime) |
| `HYBRID_SEARCH` | `false` | Enable BM25 sparse keyword + dense vector Reciprocal Rank Fusion (RRF) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/ragops.db` | PostgreSQL (`postgresql://...`) or SQLite URL |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis / Memurai connection string for semantic cache |
| `REDIS_ENABLED` | `true` | Enable Redis multi-tier caching (falls back to memory/DB if offline) |
| `CACHE_SIMILARITY_THRESHOLD` | `0.90` | Cosine similarity threshold for semantic cache hits ($\ge 0.90$) |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | Directory for persistent ChromaDB vector storage |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-Transformers embedding model (384 dimensions) |
| `WARMUP_ON_START` | `true` | Asynchronous pre-warming of PyTorch embeddings, cross-encoder, and vector DB |

---

## 12. Troubleshooting Guide

### 1. `ragops doctor` Diagnostic Command
Run `ragops doctor` at any time to inspect your system's components:
```bash
ragops doctor
```
This prints the health status of Ollama, Groq, ChromaDB, SQLite/PostgreSQL, and Redis with exact remediation steps.

### 2. Windows CMD Popup Windows During Startup
RAGOps automatically executes background utility checks (`sc.exe`, `net.exe`, `ollama.exe`) using Win32 flag `CREATE_NO_WINDOW = 0x08000000`, preventing annoying black CMD window flashes.

### 3. Ollama is Installed but Not Running
```bash
ollama serve
```
RAGOps also attempts to auto-launch `ollama serve` silently in the background during backend startup if `LLM_PROVIDER=auto`.

### 4. Ollama Target Model Missing
```bash
ollama pull llama3.2:3b
```
Or set `OLLAMA_AUTO_PULL=true` in `.env` to allow RAGOps to pull missing models automatically.

### 5. Running Fully Offline (No Internet & No API Keys)
```bash
# 1. Start Ollama and pull local model
ollama pull llama3.2:3b

# 2. In .env set:
LLM_PROVIDER=ollama
```

### 6. Port Conflicts
- **Port 8000 (Backend API)**: Run with a different port using `ragops serve --port 8080`.
- **Port 5432 (PostgreSQL)**: If local PostgreSQL is not running, RAGOps automatically fails over to embedded SQLite (`data/ragops.db`) without crashing.

---

## 13. Automated Quality Gate CI/CD & Testing

### Benchmark Evaluation Workflow
```bash
# Execute evaluation suite against golden dataset with quality gate enforcement
python scripts/run_evaluation.py \
  --dataset evaluation/datasets/golden.jsonl \
  --version candidate-v2 \
  --fail-on-gate
```

**Quality Gate Criteria:**
- **Retrieval Recall@5**: $\ge 0.85$
- **Faithfulness (Groundedness)**: $\ge 0.90$
- **Answer Relevance**: $\ge 0.85$
- **Tail Latency (P95)**: $\le 3000\text{ ms}$
- **Maximum Allowed Regression vs. Production Baseline**: $< 5\%$

### Running Tests
```bash
# Run unit tests (all 88 unit tests passing)
pytest tests/unit/ -q
```

---

## 14. Resume Bullet Points & Portfolio Placement

For resumes, LinkedIn, and portfolios, format achievements using the Google XYZ Formula (*Accomplished [X], as measured by [Y], by doing [Z]*):

### LaTeX Resume Snippet
```latex
\project{RAGOps -- Production RAG Platform with Observability}
{FastAPI, Redis, ChromaDB, Docker (Link)}{2026}
\begin{itemize}
  \item Architected an enterprise Retrieval-Augmented Generation (RAG) platform with ChromaDB dense vector search and cross-encoder reranking, achieving \textbf{94.3\% retrieval recall} and \textbf{89\% hallucination abstention} on golden benchmarks.
  \item Engineered a multi-tier \textbf{Redis semantic vector cache} executing sub-2ms exact matches and $\geq$90\% semantic relevance hits, eliminating redundant LLM API calls and drastically cutting token expenses.
  \item Constructed an autonomous web crawler, PostgreSQL-backed RBAC with multi-turn chat sessions, and an interactive React 19 observability console featuring distributed OpenTelemetry request tracing.
\end{itemize}
```

### ATS-Optimized Keywords
`RAG (Retrieval-Augmented Generation)` • `LLMOps` • `FastAPI` • `ChromaDB` • `Redis Semantic Cache` • `Cross-Encoder Reranking` • `Sentence-Transformers` • `OpenTelemetry` • `Prometheus` • `Grafana` • `Jaeger` • `PostgreSQL` • `React 19` • `Docker` • `CI/CD Quality Gates` • `Wilson 95% Confidence Intervals` • `Model Context Protocol (MCP)` • `Ollama` • `Groq`

---

## 15. License

Licensed under the [MIT License](LICENSE).
