# RAGOps — End-to-End RAG Platform with Observability

[![CI Pipeline](https://github.com/KSD-333/RAGOps/actions/workflows/ci.yml/badge.svg)](https://github.com/KSD-333/RAGOps/actions/workflows/ci.yml)
[![Quality Gate](https://github.com/KSD-333/RAGOps/actions/workflows/evaluation.yml/badge.svg)](https://github.com/KSD-333/RAGOps/actions/workflows/evaluation.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev/)
[![Docker Hub](https://img.shields.io/badge/docker-ketan333%2Fragops-2496ed.svg)](https://hub.docker.com/r/ketan333/ragops)
[![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL%20%7C%20SQLite-336791.svg)](https://www.postgresql.org/)

> **An end-to-end RAG platform with observability, runs locally via Docker or Python. Features dense vector retrieval + optional BM25 hybrid search, cross-encoder reranking, multi-provider LLM routing (local Ollama with Groq cloud fallback and degraded mode), multi-session conversational memory, sub-2ms exact match & ~4.2ms semantic caching, autonomous corporate web crawling with prompt-injection defense, PostgreSQL/SQLite telemetry, distributed request tracing, Model Context Protocol (MCP) server, and automated CI/CD quality gates with Wilson 95% confidence intervals.**

---

## 1. Concrete System Architecture

```text
                               ┌─────────────────────────────────────────────────────────┐
                               │           Modern React 19 Web Interface                 │
                               │  (Search Studio • Master-Detail Audit • Trace Viewer)   │
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
    │ └─ Intent Classifier (Routing)  │                                           │ ├─ Autonomous Search Tool (Gaps)│
    │                                 │                                           │ └─ Quarantined Candidate Queue  │
    └────────────────┬────────────────┘                                           └────────────────┬────────────────┘
                     │                                                                             │
                     ▼                                                                             ▼
    ┌─────────────────────────────────┐                                           ┌─────────────────────────────────┐
    │    Dense / BM25 Hybrid Search   │                                           │   Human-in-the-Loop Validation  │
    │ Sentence-Transformers Embeddings│                                           │ Review, edit, approve, or reject│
    │ ChromaDB HNSW Index + BM25 RRF  │                                           │ structured corporate facts      │
    └────────────────┬────────────────┘                                           └────────────────┬────────────────┘
                     │ Top-K Candidates (Chunks)                                                   │
                     ▼                                                                             │
    ┌─────────────────────────────────┐                                                            │
    │     Cross-Encoder Reranker      │                                                            │
    │ ms-marco-MiniLM-L-6-v2 Scoring  │                                                            │
    └────────────────┬────────────────┘                                                            │
                     │ Calibrated Grounding Context                                                │
                     ▼                                                                             │
    ┌─────────────────────────────────┐                                                            │
    │   Multi-Provider LLM Router     │                                                            │
    │ Ollama (Local) → Groq (Cloud)   │                                                            │
    │ ├─ Dynamic fallback & circuit br│                                                            │
    │ ├─ Anti-hallucination templates │                                                            │
    │ ├─ Instruction isolation delimiters                                                          │
    │ └─ Zero-knowledge abstention    │                                                            │
    └────────────────┬────────────────┘                                                            │
                     │ Answer + Provenance                                                         │
                     ▼                                                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PostgreSQL / SQLite Telemetry & Datastore                                        │
│ ├─ User Authentication & RBAC (admin, test1, test2 with salted SHA-256) [Demo accounts for local testing only]  │
│ ├─ Multi-session Chat History & Turn Provenance (Latency Waterfall: Embed, Search, Rerank, LLM)                │
│ ├─ Grounding Chunks & Citations Store                                                                            │
│ ├─ User Feedback Ratings (👍 / 👎) & Hallucination Triage Queue                                                  │
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
- **Persistent Sessions**: Create, rename, switch between, and purge conversation sessions stored in PostgreSQL or SQLite.
- **Conversational Query Rewriting**: Solves coreference ambiguity and pronoun ellipsis across turns (e.g., automatically resolving *"Where are they located?"* into *"Where are the manufacturing plants located?"* before vector search).
- **Session Isolation**: Standard users only view and interact with their own conversation history, while administrators retain global audit capabilities.

### ⚡ High-Performance Redis / Memurai Semantic Cache (<2ms Exact & ~4.2ms Semantic)
- **Multi-Tier Caching Architecture**:
  - **Tier 1 (In-Memory Hot Cache)**: Instantaneous $<0.1\text{ ms}$ lookup.
  - **Tier 2 (Redis / Memurai Exact Match)**: Sub-2ms ($<2\text{ ms}$) instant response for identical query hashes (`ragops:cache:exact:{company}:{hash}`).
  - **Tier 3 (Redis Semantic Relevance Match)**: Pre-filters cached queries by scope and intent, computes cosine similarity against candidate embedding vectors (averaging $\sim 4.2\text{ ms}$ on benchmarks), and delivers a direct cache hit if query similarity is $\ge 90\% - 95\%$ (configurable via `CACHE_SIMILARITY_THRESHOLD=0.90`).
  - **Tier 4 (Durable Database Cache)**: Backed by PostgreSQL / SQLite `SemanticCacheModel` with automatic backfill into Redis.
- **Zero-Touch Auto-Start**: Automatically detects if Redis is offline on backend launch (`ragops serve` / FastAPI startup) and starts the Memurai Windows Service or daemon process in the background, eliminating manual intervention.
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
RAGOps provides a first-class Model Context Protocol (MCP) server over `stdio` transport, enabling AI desktop clients (such as Claude Desktop, Cursor, and Continue) to query your enterprise knowledge base, ingest documents, inspect traces, and monitor cache statistics directly:

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

## 3. Measured Performance & Quality Benchmarks

All metrics below are measured against a **repeatable 50-query golden benchmark suite** ($N = 50$, comprising 35 in-domain retrieval queries and 15 out-of-domain / adversarial abstention tests). For binomial quality metrics, 95% Wilson score confidence intervals are explicitly reported alongside sample sizes ($n$) to provide mathematically rigorous bounds:

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

> [!NOTE]
> Exact-match cache lookups return in sub-2ms ($<2\text{ ms}$), delivering immediate answers at $\$0.00$ token cost. When semantic cache is probed, candidate vector similarity computation averages $4.2\text{ ms}$. If neither hits, the query executes through the complete RAG pipeline.

### Per-Stage Latency Breakdown (Average over $N=50$)
* **Exact-Match Cache Hit**: `0.8 ms` (returns immediately with 0 tokens consumed)
* **Semantic Cache Lookup**: `4.2 ms` (measured average across benchmark runs)
* **Query Embedding** (`all-MiniLM-L6-v2`): `15.2 ms`
* **ChromaDB HNSW Vector Search**: `4.1 ms`
* **Cross-Encoder Reranking** (`ms-marco-MiniLM-L-6-v2`): `38.6 ms`
* **LLM Generation** (`Groq Llama-3.1-70B` / `Ollama llama3.2:3b`): `1,354.1 ms`
* **Total End-to-End Latency**: `~1.41 s`

---

## 4. Repository Structure

```text
ragops/
├── README.md                           # Comprehensive platform documentation & guide
├── POSTGRES_SETUP_GUIDE.md             # Dedicated PostgreSQL operations & setup guide
├── INTERVIEW_PREP_GUIDE.md             # System design & architecture deep dive
├── pyproject.toml                      # Python dependencies and build metadata
├── .env.example                        # Environment variables template
│
├── react/                              # Enterprise React 19 + Tailwind v4 Web Console
│   ├── src/
│   │   ├── App.jsx                     # Root application container & page routing
│   │   ├── index.css                   # Tailwind v4 styles, custom scrollbars, ragops-markdown
│   │   └── components/
│   │       ├── Navbar.jsx              # Responsive header, environment badge, auth switcher
│   │       ├── SearchPage.jsx          # ChatGPT-style workspace, live crawler modal, streaming chat
│   │       ├── DashboardPage.jsx       # 6-tab enterprise observability & intelligence suite
│   │       ├── AuthModal.jsx           # RBAC simulated user switcher (admin, test1, test2)
│   │       ├── ChunkModal.jsx          # Interactive chunk inspector & raw payload viewer
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
│   │   └── context_builder.py          # Grounding context assembly and citation indexing
│   │
│   ├── retrieval/                      # Vector & Dense Search
│   │   ├── embeddings.py               # Sentence-Transformers persistent embeddings
│   │   ├── vector_store.py             # ChromaDB vector store wrapper
│   │   ├── reranker.py                 # Cross-encoder reranking (ms-marco-MiniLM-L-6-v2)
│   │   └── retriever.py                # Multi-stage retrieval coordinator
│   │
│   ├── generation/                     # LLM Generation Layer
│   │   ├── prompts.py                  # Anti-hallucination templates & citation prompts
│   │   └── response.py                 # Response builder with source attribution
│   │
│   ├── ingestion/                      # Document Ingestion Pipeline
│   │   ├── classifier.py               # Document type classification (Policy, Code, etc.)
│   │   ├── chunkers.py                 # Recursive token-aware text splitters
│   │   └── pipeline.py                 # Ingestion orchestrator
│   │
│   ├── storage/                        # Persistence Layer
│   │   ├── database.py                 # SQLAlchemy session management & engine auto-detection
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
└── tests/                              # Comprehensive Pytest Suite
```

---

## 5. Quickstart & Deployment

### Prerequisites
- **Python 3.11+** or **Docker**
- **Groq API Key** (Free at [console.groq.com](https://console.groq.com))
- *(Optional)* **Redis / Memurai on Windows** (`127.0.0.1:6379`) for ultra-fast sub-2ms caching (defaults to in-memory/DB cache if offline)
- *(Optional)* **PostgreSQL 15+** (defaults automatically to local SQLite if PostgreSQL is not running)

---

### Option A: Run via Docker (Zero-Setup Deployment)

Pull and run the official image with both backend and pre-compiled React frontend:

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

# Open the Web UI in your browser:
# http://localhost:8000/
```

---

### Option B: Full Production Stack via Docker Compose (with PostgreSQL & Grafana)

Launch the complete stack (FastAPI backend + React frontend + PostgreSQL 16 + Prometheus + Grafana + Jaeger):

```bash
# 1. Clone repository
git clone https://github.com/KSD-333/RAGOps.git
cd RAGOps

# 2. Configure environment
cp .env.example .env
# Edit .env and insert your GROQ_API_KEY

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
# On macOS / Linux:
source .venv/bin/activate
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.venv\Scripts\activate.bat

# 3. Install backend dependencies
pip install --upgrade pip
pip install -r requirements.txt
# (Optional: For tests, linting, and development)
pip install -r requirements-dev.txt
pip install -e .

# 4. Configure environment
cp .env.example .env
# Insert your GROQ_API_KEY and (optional) DATABASE_URL

# 5. Ingest initial knowledge base
ragops ingest data/raw --version v1

# 6. One-Command Full Stack Launcher (Backend + React UI)
# Windows:
.\start_dev.bat
# Or CLI:
ragops dev

# (Alternatively, run individually:)
# Terminal 1 - Backend API:
ragops serve --port 8000 --reload

# Terminal 2 - React Web UI:
cd react
npm install
npm run dev
# Access API Docs:  http://127.0.0.1:8000/docs
# Access React UI:   http://localhost:5173/
```

---

## 6. Default Test Credentials (Demo Accounts for Local Testing Only)

> [!WARNING]
> **Demo Accounts for Local Testing Only**: The pre-seeded credentials below (`admin`, `test1`, `test2`) are provided exclusively for local sandbox evaluation and developer testing. In shared or production-facing environments, change default credentials immediately and configure API secrets via environment variables.

RAGOps auto-seeds three test accounts on first launch:

| Username | Default Password | Role | Access Level |
|---|---|---|---|
| **`admin`** | `admin123` | **ADMIN** | Full administrative access to the 6-tab Observability Dashboard, billing calculator, all user chat audits, trace logs, document catalog, and training dataset exports. |
| **`test1`** | `test123` | **USER** | Standard user account (HR, workplace policies, and corporate architecture questions). |
| **`test2`** | `test223` | **USER** | Technical user account (infrastructure, Kubernetes, and developer documentation). |

*Use the **Account Switcher** button in the Web UI navigation bar to instantly simulate queries as any user.*

---

## 7. Web Console & Observability Walkthrough

### 💬 Search & Chat Console (`/`)
* **Multi-Session Sidebar**: Create new chats, switch between previous conversations, and delete sessions.
* **Conversational Stream**: Multi-turn dialogue with markdown rendering (`ragops-markdown`), syntax-highlighted code blocks, tables, and lists.
* **Grounded Citations & Chunk Modal**: Every response lists verified corporate sources. Clicking any citation opens the **ChunkModal** displaying the exact raw context snippet, page number, and similarity match percentage.
* **Interactive Live URL Crawler**: Click the URL icon to crawl any corporate website on demand, preview extracted intelligence (plants, clients, executive team), edit facts inline, and embed directly into ChromaDB.
* **Feedback Loop**: Record **Accurate** 👍 or **Inaccurate** 👎 ratings to feed real-world telemetry into the continuous improvement pipeline.

---

### 📈 Enterprise Observability & Intelligence Dashboard (`/dashboard`)

Access restricted to administrators:

#### 1. Overview & Billing
* **Top KPI Counters**: Total queries served, token spend (input vs. output), positive feedback rate, P50 & P95 latencies, and database engine status (`PostgreSQL` or `SQLite`).
* **Contract Budget Calculator**: Configure contractual token volume and plan pricing. Displays accrued spend, remaining tokens, and cost per query with an interactive visual progress bar.
* **Fine-Tuning Dataset Exporter**: Download grounded positive Q&A pairs as standard JSON training datasets for model fine-tuning.

#### 2. User Directory & Chat History (Master-Detail Side-by-Side)
* **Registered Users List**: User cards showing username, role badge, query count, and token spend.
* **Interactive Sessions List**: Searchable list of chat sessions with prompt previews, timestamps, turn counts, and risk badges.
* **Side-by-Side Chat Viewer**: Click any session to inspect its conversational stream side-by-side with user prompt bubbles, AI responses, citations, inspectable grounding chunks, and latency attribution.

#### 3. Distributed Request Tracing & Retrieval Inspector (Compact Space-Saving Cards)
* **High-Density Trace Cards**: Compact summary rows showing Trace ID, `@username`, timestamp, color-coded latency badge, token counts, risk tags, and query text.
* **Click-to-Expand Details**: Smoothly expands to reveal the full AI response and the multi-hop latency waterfall breakdown:
  - **Embedding** (`embed_latency_ms`)
  - **ChromaDB Vector Search** (`search_latency_ms`)
  - **Cross-Encoder Reranker** (`rerank_latency_ms`)
  - **LLM Generation** (`generation_latency_ms`)
* **Global Controls**: Bulk **Expand All** and **Collapse All** buttons, live query/user search, and filter pills (**All**, **Risk Signals**, **Slow >1.5s**).

#### 4. Frequent Questions & Risk Radar
* **Semantic Query Clustering**: Identifies recurring questions across all users with occurrence count and average latency.
* **Risk & Churn Signals**: Identifies policy/compliance inquiries (e.g. POSH policy, internal complaints) and employee/customer churn sentiment.

#### 5. Company Knowledge Hub & Autonomous Profile
* **Universal Multi-Company Intelligence**: Switch between tracked companies or trigger autonomous web crawls.
* **Candidate Review Queue**: Staged fact candidates with confidence ratings and source URLs; approve, edit, or reject facts.
* **Approved Corporate Facts**: Grounded structured facts with provenance tracking.
* **Outbox Event Publisher**: Transactional outbox event stream verifying fact dissemination.

#### 6. Document Catalog & Semantic Cache Engine
* **Auto-Classified Catalog**: View all indexed documents categorized by type (Policy, Code, Programme, Governance, Manual) with file sizes and chunk counts.
* **Storage Reconciliation**: Click **Sync Storage with Disk** to align physical files in `data/raw/` with database records.
* **On-Demand Embedding**: Single-document and batch **Embed All Pending** actions into ChromaDB.
* **Semantic Cache Performance**: Live telemetry tracking cache hit rate %, cumulative latency saved in seconds, and token charges avoided in USD.

---

## 8. Complete REST API Reference

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

## 9. CLI Reference

RAGOps provides a unified command-line tool `ragops`:

| Command | Usage | Description |
|---|---|---|
| `ragops doctor` | `ragops doctor` | Run full diagnostic inspection of LLM providers (Ollama, Groq), database, cache, and vector store with remediation hints |
| `ragops mcp` | `ragops mcp` | Launch the FastMCP Model Context Protocol server over stdio for Claude Desktop, Cursor, or Continue |
| `ragops dev` | `ragops dev` | Launch unified local development stack (FastAPI backend on :8000 + React UI on :5173) |
| `ragops ingest` | `ragops ingest <path> [--version <v>]` | Ingest PDF, HTML, or Markdown files into ChromaDB |
| `ragops query` | `ragops query "<question>" [--top-k 5]` | Ask questions from the terminal with latency attribution and citations |
| `ragops evaluate`| `ragops evaluate -d <dataset.jsonl> [--version <v>]` | Run quality evaluation benchmark against golden dataset with Wilson 95% CI |
| `ragops serve` | `ragops serve [--host 0.0.0.0] [--port 8000]` | Launch FastAPI HTTP service & embedded React Web UI |
| `ragops status`| `ragops status` | Display current models, thresholds, and active version |

---

## 10. Multi-Provider LLM Architecture (Local-First Ollama & Cloud Groq)

RAGOps provides an intelligent, resilient LLM routing subsystem designed to operate smoothly whether running fully offline or cloud-connected:

```text
               ┌────────────────────────────────────────────────────────┐
               │              LLM Query / Stream Request                │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │           LLMRouter (Auto / Ollama / Groq)             │
               └───────────┬────────────────────────────────┬───────────┘
                           │                                │
            1. Try Local   │                                │ 2. Fallback on Error
            Ollama First   ▼                                ▼
              ┌───────────────────────────┐    ┌───────────────────────────┐
              │    OllamaProvider         │    │      GroqProvider         │
              │ • Model: llama3.2:3b      │    │ • Cloud API (LLaMA 3.3)   │
              │ • Auto background spawn   │    │ • Bearer authentication   │
              │ • 3-strike circuit breaker│    │ • 3-strike circuit breaker│
              └────────────┬──────────────┘    └────────────┬──────────────┘
                           │ Both Fail                      │
                           └─────────────────┬──────────────┘
                                             ▼
                               ┌───────────────────────────┐
                               │       Degraded Mode       │
                               │ • Retrieval & Cache active│
                               │ • Vector search works     │
                               │ • Clear setup instructions│
                               └───────────────────────────┘
```

### Routing & Circuit Breaker Logic
1. **Auto Detection (`LLM_PROVIDER=auto`)**:
   - Probes local Ollama (`http://localhost:11434/api/tags`).
   - If Ollama CLI is installed but the server is stopped, RAGOps attempts to spawn `ollama serve` in the background and polls for readiness.
   - If the configured model (`OLLAMA_MODEL`) is missing, it either pulls it automatically (`OLLAMA_AUTO_PULL=true`) or logs the exact command to pull (`ollama pull llama3.2:3b`).
   - If Ollama is unavailable or missing models, the router automatically falls back to Groq Cloud API.
2. **Dynamic Request-Level Fallback**:
   - If the active provider encounters a network timeout, connection reset, or 5xx error mid-request, RAGOps retries with exponential backoff and automatically falls back to the alternate provider.
   - The query execution trace logs `provider_used`, `fallback_used: true`, and `provider_error`.
3. **Circuit Breaker**:
   - 3 consecutive failures trips the provider's circuit breaker to `OPEN` for 60 seconds, preventing latency spikes from repeated failing calls before probing again.
4. **Graceful Degraded Mode**:
   - If neither Ollama nor Groq is available, RAGOps starts anyway without crashing. Document ingestion, BM25/vector search, and semantic cache lookups remain 100% operational, and generation endpoints return clear, actionable configuration instructions.

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

---

## 12. Troubleshooting Guide

### 1. `ragops doctor` Diagnostic Command
Run `ragops doctor` at any time to inspect your system's components:
```bash
ragops doctor
```
This prints the health status of Ollama, Groq, ChromaDB, SQLite/PostgreSQL, and Redis with exact remediation steps.

### 2. Ollama is Installed but Not Running
If `ragops doctor` reports Ollama is installed but not running:
```bash
ollama serve
```
RAGOps also attempts to auto-launch `ollama serve` in the background during backend startup if `LLM_PROVIDER=auto`.

### 3. Ollama Target Model Missing
If Ollama is running but `llama3.2:3b` is missing:
```bash
ollama pull llama3.2:3b
```
Or set `OLLAMA_AUTO_PULL=true` in your `.env` to allow RAGOps to pull missing models automatically.

### 4. Groq API Key Errors (HTTP 401 or 429)
- **HTTP 401 Unauthorized**: Check that `GROQ_API_KEY` in `.env` contains a valid key from [console.groq.com](https://console.groq.com). RAGOps masks all keys in logs and diagnostics.
- **HTTP 429 Rate Limit**: Groq free tier rate limits reset quickly. The circuit breaker will pause calls for 60 seconds. Alternatively, install Ollama for unlimited local inference.

### 5. Running Fully Offline (No Internet & No API Keys)
RAGOps runs 100% offline using Ollama:
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
# Run complete test suite (unit, integration, and E2E)
pytest tests/ -v
```

---

## 14. License

Licensed under the [MIT License](LICENSE).
