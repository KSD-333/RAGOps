# RAGOps — Enterprise Retrieval-Augmented Generation & Observability Platform

[![CI Pipeline](https://github.com/KSD-333/RAGOps/actions/workflows/ci.yml/badge.svg)](https://github.com/KSD-333/RAGOps/actions/workflows/ci.yml)
[![Quality Gate](https://github.com/KSD-333/RAGOps/actions/workflows/evaluation.yml/badge.svg)](https://github.com/KSD-333/RAGOps/actions/workflows/evaluation.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev/)
[![Docker Hub](https://img.shields.io/badge/docker-ketan333%2Fragops-2496ed.svg)](https://hub.docker.com/r/ketan333/ragops)
[![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL%20%7C%20SQLite-336791.svg)](https://www.postgresql.org/)
[![Redis / Memurai](https://img.shields.io/badge/cache-Redis%20%7C%20Memurai-dc382d.svg)](https://redis.io/)
[![Ollama + Groq](https://img.shields.io/badge/llm-Ollama%20%7C%20Groq%20Cloud-f55036.svg)](https://groq.com/)

**RAGOps** is a production-grade, enterprise-hardened Retrieval-Augmented Generation (RAG) platform and LLMOps execution environment. It bridges the gap between proof-of-concept AI chatbots and mission-critical enterprise systems by enforcing strict role-based access controls (RBAC), multi-tier semantic caching, two-stage vector and cross-encoder retrieval, zero-hallucination guardrails, distributed request tracing, and automated regression quality gates.

---

## Table of Contents

- [1. System Architecture](#1-system-architecture)
  - [High-Level System Topology](#high-level-system-topology)
  - [End-to-End Query Execution Lifecycle](#end-to-end-query-execution-lifecycle)
  - [Autonomous Corporate Extractor & Human-in-the-Loop Pipeline](#autonomous-corporate-extractor--human-in-the-loop-pipeline)
- [2. Core Enterprise Pillars](#2-core-enterprise-pillars)
  - [Pillar 1: Enterprise RBAC, OAuth 2.0 & Sensitive Document ACLs](#pillar-1-enterprise-rbac-oauth-20--sensitive-document-acls)
  - [Pillar 2: Defensive Guardrails & Anti-Hallucination Gate](#pillar-2-defensive-guardrails--anti-hallucination-gate)
  - [Pillar 3: Multi-Tier Semantic Cache & Resilient LLM Router](#pillar-3-multi-tier-semantic-cache--resilient-llm-router)
  - [Pillar 4: Observability, Distributed Tracing & Continuous Evals](#pillar-4-observability-distributed-tracing--continuous-evals)
- [3. Key Platform Capabilities](#3-key-platform-capabilities)
- [4. Model Context Protocol (MCP) Integration](#4-model-context-protocol-mcp-integration)
- [5. Performance & Quality Benchmarks](#5-performance--quality-benchmarks)
- [6. Repository Structure](#6-repository-structure)
- [7. Quickstart & Deployment](#7-quickstart--deployment)
  - [Option A: Standalone Docker Deployment](#option-a-standalone-docker-deployment)
  - [Option B: Full Production Stack via Docker Compose](#option-b-full-production-stack-via-docker-compose)
  - [Option C: Local Development Environment](#option-c-local-development-environment)
- [8. Default Development Credentials](#8-default-development-credentials)
- [9. Complete REST API Reference](#9-complete-rest-api-reference)
- [10. CLI Reference](#10-cli-reference)
- [11. Configuration & Environment Variables](#11-configuration--environment-variables)
- [12. Production Operations & Troubleshooting](#12-production-operations--troubleshooting)
- [13. Security & Hardening Policy](#13-security--hardening-policy)
- [14. License](#14-license)

---

## 1. System Architecture

RAGOps separates **query-time inference**, **multi-tier caching**, **document ingestion**, and **telemetry logging** into decoupled, fault-tolerant subsystems.

### High-Level System Topology

```mermaid
flowchart TB
    subgraph Clients["Client & Integration Layer"]
        UI["React 19 Web Console\n(Typewriter UI • Master-Detail • Trace Viewer)"]
        MCP["Model Context Protocol (MCP)\n(Claude Desktop • Cursor • Continue • IDEs)"]
        SDK["External Systems / REST API\n(Jira • Confluence • Microservices)"]
    end

    subgraph Gateway["API Gateway & Security Layer (FastAPI)"]
        AUTH["RBAC & OAuth Authenticator\n(Salted SHA-256 / Session Token / Role ACL)"]
        ROUTER["FastAPI Application Router\n(Rate Limiting • CORS • Lifespan Manager)"]
        WARM["WarmupCoordinator\n(Async Pre-warming PyTorch & Vector Index)"]
    end

    subgraph QueryEngine["Query Intelligence & Caching Subsystem"]
        TRANSFORM["Query Normalizer & Rewriter\n(Typo Correction • Anaphora Resolution)"]
        L1["L1: In-Memory Hot LRU (<0.1ms)"]
        L2["L2: Redis Exact Hash Match (<2ms)"]
        L3["L3: Redis Cosine Semantic Cache (~4.2ms)"]
    end

    subgraph Retrieval["Two-Stage Retrieval Pipeline"]
        DENSE["Stage 1: Dense Vector Search\nSentence-Transformers (384-d) + ChromaDB HNSW\n(Metadata Pre-Filter: where role_access in user_roles)"]
        RERANK["Stage 2: Cross-Encoder Reranker\nms-marco-MiniLM-L-6-v2 (Joint Attention)\nConfidence Gate (tau >= 0.10)"]
    end

    subgraph Generation["LLM Routing & Guardrails"]
        PROMPT["Instruction Isolation Boundary\n=== BEGIN/END REFERENCE DATA ==="]
        LLMROUTER["Resilient LLM Router & Circuit Breaker\nPrimary: Local Ollama (llama3.2:3b)\nFallback: Cloud Groq (gpt-oss-120b)"]
        ABSTAIN["Zero-Hallucination Abstention Gate\n(Score < 0.10 -> Authoritative Refusal in <85ms)"]
    end

    subgraph Persistence["Storage & Telemetry Backbone"]
        DB[(PostgreSQL 16 / SQLite Engine\nUsers • Sessions • Chats • Corporate Facts • Candidates)]
        CACHE[(Redis / Memurai Cache\nExact Query Hashes • Normalized Embeddings)]
        VDB[(ChromaDB Vector Store\nPartitioned Collections • Persistent HNSW Index)]
        OUTBOX["Transactional Event Outbox\n(Idempotent Vector Sync Worker)"]
    end

    subgraph Observability["Continuous Observability & Evals"]
        OTEL["OpenTelemetry Distributed Tracing\n(Unique Trace IDs • Hop-by-Hop Latency Waterfall)"]
        METRICS["Prometheus Metrics & Grafana Dashboards\n(/metrics • P50/P95 Latency • Hit Rates)"]
        EVAL["Golden Benchmark Runner\n(Recall@5 • Wilson 95% CI • CI/CD Quality Gate)"]
    end

    UI --> AUTH
    MCP --> AUTH
    SDK --> AUTH
    AUTH --> ROUTER
    ROUTER --> TRANSFORM

    TRANSFORM --> L1
    L1 -. Miss .-> L2
    L2 -. Miss .-> L3
    L3 -. Hit (>=0.90) .-> UI
    L3 -. Miss .-> DENSE

    DENSE --> RERANK
    RERANK -- Score < 0.10 --> ABSTAIN
    ABSTAIN --> DB
    ABSTAIN --> UI

    RERANK -- Score >= 0.10 --> PROMPT
    PROMPT --> LLMROUTER
    LLMROUTER --> UI

    ROUTER --> DB
    ROUTER --> CACHE
    DENSE --> VDB
    OUTBOX --> VDB

    ROUTER --> OTEL
    ROUTER --> METRICS
    DB --> EVAL
```

---

### End-to-End Query Execution Lifecycle

The sequence below illustrates the sub-second decision matrix executed for every user question:

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant GW as API Gateway (FastAPI)
    participant QI as Query Intelligence & Cache
    participant VDB as ChromaDB Vector Store
    participant RK as Cross-Encoder Reranker
    participant LLM as LLM Router (Ollama/Groq)
    participant DB as PostgreSQL / SQLite Telemetry

    User->>GW: POST /api/v1/query (prompt, session_id, token)
    GW->>GW: Validate RBAC Role & Session Ownership
    GW->>QI: Normalize Typos & Resolve Anaphora ("and how to create one")
    
    QI->>QI: Check L1 Memory & L2 Redis Exact Hash (<2ms)
    alt Exact Cache Hit
        QI-->>User: Return Cached Answer (Sub-2ms)
    else Cache Miss
        QI->>QI: Check L3 Redis Semantic Similarity (Cosine >= 0.90)
        alt Semantic Cache Hit
            QI-->>User: Return Semantic Match (~4.2ms)
        else Complete Miss
            QI->>VDB: Query Vector Embedding with Metadata ACL Filter
            VDB-->>RK: Return Top-K Candidates (Chunks)
            RK->>RK: Compute Joint Cross-Attention Scores
            
            alt Maximum Score < tau (0.10)
                RK-->>GW: Low Relevance Confidence
                GW->>DB: Log Zero-Token Abstention
                GW-->>User: Return Authoritative Grounded Abstention (<85ms)
            else High Confidence Score (>= 0.10)
                RK->>LLM: Pack Grounding Chunks inside Instruction Isolation
                LLM->>LLM: Stream Generated Tokens with Verified Citations
                LLM-->>GW: Generation Complete
                GW->>QI: Store Valid Turn in Redis Semantic Cache
                GW->>DB: Record Trace, Latencies, Citations & Token Usage
                GW-->>User: Stream Response to Typewriter UI
            end
        end
    end
```

---

### Autonomous Corporate Extractor & Human-in-the-Loop Pipeline

RAGOps features an autonomous corporate intelligence subsystem that traverses enterprise domains, discovers infrastructure facts, and stages them through a review-before-publish workflow:

```mermaid
flowchart LR
    subgraph IngestionSource["Data Ingestion Sources"]
        WEB["Enterprise Websites\n(Deep Crawl Engine)"]
        PDF["Local Documents & PDFs\n(Policy, Code, Governance, Manual)"]
        SEARCH["Autonomous Search Tool\n(Fills Information Gaps Live)"]
    end

    subgraph ExtractionStage["Extraction & Normalization"]
        EXTRACT["LLM Fact Extractor\n(Executive Bios, Plants, OEM Clients)"]
        CHUNK["Token-Aware Semantic Chunker\n(512 tokens • 50-token overlap)"]
    end

    subgraph HumanInTheLoop["Human-in-the-Loop Validation"]
        QUEUE["Quarantined Candidate Queue\n(PostgreSQL FactCandidateModel)"]
        REVIEW{"Admin Console Review\n(Approve • Edit • Reject)"}
        OUTBOX["Transactional Event Outbox\n(Guaranteed At-Least-Once Delivery)"]
    end

    subgraph ProductionStore["Active Vector Knowledge Base"]
        CHROMA["ChromaDB HNSW Vector Store\n(Grounded Enterprise Citations)"]
        RELATIONAL["PostgreSQL Knowledge Catalog\n(Versioned Corporate Intelligence)"]
    end

    WEB --> EXTRACT
    SEARCH --> EXTRACT
    PDF --> CHUNK

    EXTRACT --> QUEUE
    CHUNK --> OUTBOX
    QUEUE --> REVIEW

    REVIEW -- Approved / Edited --> OUTBOX
    REVIEW -- Rejected --> DISMISS["Purged from Queue"]
    OUTBOX --> CHROMA
    OUTBOX --> RELATIONAL
```

---

## 2. Core Enterprise Pillars

Modern enterprise RAG systems fail when treated as simple wrappers around an LLM and a vector database. RAGOps is architected around four distinct production pillars:

```mermaid
flowchart TD
    subgraph P1["Pillar 1: RBAC + OAuth & Access Control"]
        A1["User Authentication (OAuth2 / Salted SHA-256)"] --> A2["Role Segregation: Admin vs User"]
        A2 --> A3["Document & Chunk Metadata ACLs"]
        A3 --> A4["Pre-Retrieval Filter (where role_access in user_roles)"]
        A4 --> A5["Zero-Leakage Guarantee (Confidential / Salary PDFs)"]
    end

    subgraph P2["Pillar 2: Production Guardrails & Defensive RAG"]
        B1["Input Prompt Injection Scanner"] --> B2["Instruction Delimiters (=== BEGIN/END ===)"]
        B2 --> B3["Calibrated Reranker Gate (Score < 0.10)"]
        B3 --> B4["Zero-Hallucination Authoritative Abstention"]
        B4 --> B5["PII / Sensitive Token Masking"]
    end

    subgraph P3["Pillar 3: Multi-Tier Semantic Cache & Router"]
        C1["Tier 1: Hot In-Memory LRU (<0.1ms)"] --> C2["Tier 2: Redis Exact Hash Match (<2ms)"]
        C2 --> C3["Tier 3: Redis Cosine Semantic Cache (~4.2ms)"]
        C3 --> C4["Resilient LLM Router: Local Ollama → Groq Cloud"]
        C4 --> C5["Silent Win32 Background Spawn & WarmupCoordinator"]
    end

    subgraph P4["Pillar 4: Observability, Tracing & Evals"]
        D1["OpenTelemetry Distributed Tracing & Trace IDs"] --> D2["Multi-Hop Latency Waterfall Breakdown"]
        D2 --> D3["Token Accounting & Contract Billing"]
        D3 --> D4["Golden Benchmark Suite (N=50) + Wilson 95% CI"]
        D4 --> D5["Automated CI/CD Quality Gates & Regressions"]
    end
```

---

### Pillar 1: Enterprise RBAC, OAuth 2.0 & Sensitive Document ACLs

#### The "Unauthorized Salary Inquiry" Challenge in Enterprise RAG
In naive RAG implementations, all corporate documents reside in a shared vector database. When an unauthorized user submits:
> *"What is the CEO's current compensation and bonus package?"*

Naive vector retrieval retrieves executive compensation chunks and inserts them directly into the LLM context. System prompt instructions (e.g., *"Do not disclose executive compensation"*) are easily bypassed using prompt injection or indirect role-play attacks.

#### The RAGOps Defense-in-Depth Solution:
1. **Pre-Retrieval Index-Layer ACL Filtering**:
   During document ingestion, vector chunks are tagged with access metadata: `{"role_access": ["admin", "executive"]}` vs `{"role_access": ["user", "admin"]}`.
   The API gateway extracts the authenticated identity and applies metadata filters directly inside the ChromaDB query:
   ```python
   # Evaluated inside ChromaDB before chunks ever reach the reranker or LLM context
   results = collection.query(
       query_embeddings=query_vec,
       n_results=top_k,
       where={"role_access": {"$in": user_roles}}
   )
   ```
2. **Grounded Abstention Without Information Disclosure**:
   Because unauthorized chunks are filtered out at the vector index layer, the cross-encoder returns a relevance score of $0.00$. The pipeline halts immediately:
   > *"I searched the corporate knowledge base, but could not locate verified documents or policies with sufficient relevance to answer your question regarding 'CEO salary'."*
   The system never discloses that a confidential salary document exists.
3. **Session Ownership & Tenant Isolation**:
   Standard users are restricted to viewing and managing their own conversation sessions (`/api/v1/sessions`). Administrators retain global audit capabilities.

---

### Pillar 2: Defensive Guardrails & Anti-Hallucination Gate

1. **Prompt Injection & Adversarial Defense (`PromptInjectionDetector`)**:
   Pre-screens all incoming queries for jailbreak signatures (`"ignore all previous instructions"`, `"system override"`, `"DAN mode"`).
2. **Instruction Isolation Delimiters**:
   Retrieved context is walled off inside explicit boundary delimiters:
   ```text
   === BEGIN REFERENCE DATA ===
   [Document 1 | Source: corporate_policy.pdf | Chunk: chunk_002]
   ...
   === END REFERENCE DATA ===
   ```
   The system prompt enforces the **Untrusted Reference Principle**: all text between delimiters is treated strictly as passive data. Embedded instructions or prompt manipulation within documents are ignored.
3. **Calibrated Cross-Encoder Grounding Gate ($\tau = 0.10$)**:
   Queries and candidate chunks pass through a cross-encoder (`ms-marco-MiniLM-L-6-v2`) computing joint attention across query-document pairs. If the top candidate score falls below $\tau = 0.10$, the request halts in $<85\text{ ms}$, returning an authoritative refusal and consuming $0$ LLM tokens.
4. **Zero-Knowledge Cache Guardrail**:
   Refusal answers, abstention notices, and error messages are strictly excluded from the Redis semantic cache to prevent negative cache poisoning.

---

### Pillar 3: Multi-Tier Semantic Cache & Resilient LLM Router

#### Multi-Tier Caching Architecture

| Tier | Layer | Measured Latency | Scope |
|:---|:---|:---|:---|
| **Tier 1** | In-Memory LRU Hot Cache | $< 0.1\text{ ms}$ | High-frequency queries in active memory |
| **Tier 2** | Redis / Memurai Exact Match | **0.8 ms** ($< 2.0\text{ ms}$) | SHA-256 hash match (`ragops:cache:exact:{company}:{hash}`) |
| **Tier 3** | Redis Cosine Semantic Cache | **4.2 ms** ($< 10.0\text{ ms}$) | Cosine similarity ($\ge 0.90$) against candidate embeddings |
| **Tier 4** | PostgreSQL / SQLite Durable Cache | $< 15.0\text{ ms}$ | Persistent cross-restart store with auto-backfill into Redis |

#### Resilient LLM Router with Circuit Breaker
- **Local-First Ollama**: Default model `llama3.2:3b` runs completely offline with zero external cloud dependencies.
- **Cloud Groq Fallback**: If local Ollama is offline or times out, the router automatically fails over to Groq Cloud API (`openai/gpt-oss-120b`).
- **Three-Strike Circuit Breaker**: If a provider fails 3 consecutive times, its circuit breaker opens for 60 seconds, preventing latency spikes from repeated connection timeouts.
- **Graceful Degraded Mode**: If all LLM providers are unavailable, the platform continues serving vector searches, document ingestion, and semantic cache hits, providing actionable diagnostic logs.

#### Non-Blocking Startup Warmup (`WarmupCoordinator`)
During application lifespan initialization, `WarmupCoordinator` pre-warms PyTorch embedding weights, cross-encoders, and database connections asynchronously in a background thread. This eliminates first-query cold-start latency, bringing initial query response times from $>25\text{s}$ down to sub-second speeds.

---

### Pillar 4: Observability, Distributed Tracing & Continuous Evals

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

#### 2. Golden Benchmark Suite with Wilson 95% Confidence Intervals
RAGOps includes an automated 50-query golden benchmark suite ($N = 50$, 35 in-domain retrieval queries, 15 out-of-domain/adversarial probes):
- **Retrieval Recall@5**: $94.3\%$ ($33/35$ hits), $[81.4\%, 98.4\%]$ Wilson 95% CI.
- **Grounded Abstention Accuracy**: $100.0\%$ ($15/15$ abstentions), $[79.6\%, 100.0\%]$ Wilson 95% CI.
- **Citation Precision / Support**: $91.4\%$ ($32/35$ citations), $[77.6\%, 97.0\%]$ Wilson 95% CI.
- **Overall System Correctness**: $94.0\%$ ($47/50$ correct), $[83.8\%, 97.9\%]$ Wilson 95% CI.

#### 3. Continuous CI/CD Quality Gate
Automated evaluations run via `python scripts/run_evaluation.py --fail-on-gate`. The CI pipeline automatically blocks deployment if:
- Retrieval Recall@5 falls below $0.85$
- Faithfulness falls below $0.90$
- P95 Latency exceeds $3,000\text{ ms}$
- Quality regression vs. production baseline exceeds $5\%$

---

## 3. Key Platform Capabilities

- **Typewriter Streaming & Real-Time UX**: Generates ChatGPT-style typewriter text flow (~18ms token animation, auto-scroll with manual override, blinking cursor `▍`, and instant "Skip" button) with seamless light and dark mode support.
- **Conversational Memory & Query Rewriting**: Solves multi-turn pronoun ellipsis (e.g., resolving *"what is agent"* followed by *"and how to create one"* into *"how to create agent"* before vector search).
- **Typo Normalization & Prefix Stripping**: Automatically repairs input typos (e.g., `"crate"` $\rightarrow$ `"create"`, `"polies"` $\rightarrow$ `"policies"`) and strips conversational fillers (`"like "`, `"so "`, `"bro "`, `"and "`) to ensure high embedding match scores.
- **Full Theme Support (Light & Dark Mode)**: High-contrast surfaces conforming to WCAG 2.1 AAA contrast ratios across all chat bubbles, citations, and 6 administrative dashboard views.
- **Document Catalog & Disk Storage Reconciliation**: Automatically classifies documents as **Policy**, **Code**, **Programme**, **Governance**, or **Manual**, with disk sync (`/api/v1/catalog/sync`) to reconcile physical files in `data/raw/` with ChromaDB and database records.
- **Corporate Risk Radar**: Proactively flags compliance, POSH, and employee/customer churn risk signals from query logs for administrator review.
- **Token Accounting & Spending Telemetry**: Real-time token consumption tracking and contract budget calculation across all registered user accounts.
- **Fine-Tuning Dataset Exporter**: Export filtered positive grounded Q&A pairs as standard JSON datasets for LLM fine-tuning.

---

## 4. Model Context Protocol (MCP) Integration

RAGOps provides a first-class Model Context Protocol (MCP) server over `stdio` transport, allowing AI desktop environments (Claude Desktop, Cursor, Continue) to interact directly with your enterprise knowledge base:

### Claude Desktop Configuration (`claude_desktop_config.json`)

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

### Available MCP Tools

| Tool | Parameters | Description |
|---|---|---|
| `search_knowledge_base` | `query: str, top_k: int = 5` | Query enterprise knowledge base with dense/hybrid search, cross-encoder reranking, and citation provenance |
| `list_documents` | — | List all cataloged documents, classifications, and total chunk inventory |
| `ingest_document` | `path: str` | Ingest local PDF or Markdown file from `data/raw/` into ChromaDB (with path-traversal protection) |
| `get_trace` | `trace_id: str` | Retrieve execution trace, multi-hop latencies, chunks sent, and token usage for any query |
| `cache_stats` | — | Fetch real-time hit rate %, memory consumption, and cache entry count from Redis |

---

## 5. Performance & Quality Benchmarks

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

## 6. Repository Structure

```text
ragops/
├── README.md                           # Master platform architecture & production operations guide
├── POSTGRES_SETUP_GUIDE.md             # Dedicated PostgreSQL operations & setup handbook
├── HOW_IT_WORKS_AND_OPERATIONS_GUIDE.md# End-to-end data flow & pipeline operational runbook
├── pyproject.toml                      # Python build configuration and dependencies
├── .env.example                        # Complete environment variables template
│
├── react/                              # Enterprise React 19 + Tailwind CSS Frontend
│   ├── src/
│   │   ├── App.jsx                     # Root application container & page routing
│   │   ├── index.css                   # Theme definitions, custom scrollbars, ragops-markdown
│   │   └── components/
│   │       ├── Navbar.jsx              # Responsive header, theme toggle, auth switcher
│   │       ├── SearchPage.jsx          # Typewriter streaming chat, session sidebar, web crawler
│   │       ├── DashboardPage.jsx       # 6-tab enterprise observability & administration suite
│   │       ├── AuthModal.jsx           # RBAC simulated user switcher (admin, test1, test2)
│   │       ├── ChunkModal.jsx          # Grounded chunk inspector & raw payload viewer
│   │       ├── ErrorBoundary.jsx       # Application ErrorBoundary preventing UI crashes
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
│   │   ├── crawler.py                  # Multi-page web crawler
│   │   ├── extractor.py                # LLM fact extraction engine (plants, clients, leadership)
│   │   ├── service.py                  # Knowledge reconciliation & candidate staging
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
│   │   ├── reranker.py                 # Cross-encoder reranker (ms-marco-MiniLM-L-6-v2)
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

## 7. Quickstart & Deployment

### Prerequisites
- **Python 3.11+** or **Docker**
- **Ollama** (for local-first inference) or **Groq Cloud API Key** (from [console.groq.com](https://console.groq.com))
- *(Optional)* **Redis / Memurai on Windows** (`127.0.0.1:6379`) for ultra-fast caching (auto-managed by RAGOps)
- *(Optional)* **PostgreSQL 15+** (auto-falls back to SQLite if PostgreSQL is offline)

---

### Option A: Standalone Docker Deployment

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

# Access the Web UI: http://localhost:8000/
```

---

### Option B: Full Production Stack via Docker Compose

```bash
# 1. Clone repository
git clone https://github.com/KSD-333/RAGOps.git
cd RAGOps

# 2. Configure environment
cp .env.example .env

# 3. Launch full microservices stack
docker compose -f compose/docker-compose.yml up -d

# Endpoints:
# - Web Console & API:    http://localhost:8000/
# - PostgreSQL:           localhost:5432 (user: ragops, db: ragops)
# - Prometheus:           http://localhost:9090/
# - Grafana Dashboards:   http://localhost:3000/ (admin / admin)
# - Jaeger Tracing:       http://localhost:16686/
```

---

### Option C: Local Development Environment

```bash
# 1. Clone repository
git clone https://github.com/KSD-333/RAGOps.git
cd RAGOps

# 2. Create and activate virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .

# 4. Configure environment
cp .env.example .env

# 5. Ingest initial knowledge base
ragops ingest data/raw --version v1

# 6. Launch development servers
# On Windows:
.\start_dev.bat
# Or CLI:
ragops dev

# Access Web UI:   http://localhost:5173/ (or http://127.0.0.1:8000/)
# Access API Docs:  http://127.0.0.1:8000/docs
```

---

## 8. Default Development Credentials

> [!WARNING]
> **Development Sandbox Accounts**: The credentials below are pre-seeded exclusively for local evaluation, integration testing, and RBAC boundary simulation. In staging and production environments, configure authentication secrets via environment variables and update default passwords immediately.

| Username | Default Password | Role | Access Scope |
|---|---|---|---|
| **`admin`** | `admin123` | **ADMIN** | Full administrative access to the 6-tab Observability Dashboard, billing telemetry, all user chat audits, trace logs, document catalog, and training dataset exports. |
| **`test1`** | `test123` | **USER** | Standard user account (HR, workplace policies, and corporate architecture documents). |
| **`test2`** | `test223` | **USER** | Technical user account (infrastructure, Kubernetes, and developer documentation). |

*Use the **Account Switcher** button in the Web UI navigation bar to instantly simulate queries as any user role.*

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

RAGOps provides a unified command-line interface `ragops`:

| Command | Usage | Description |
|---|---|---|
| `ragops doctor` | `ragops doctor` | Diagnostic inspection of LLM providers (Ollama, Groq), database, cache, and vector store with remediation steps |
| `ragops mcp` | `ragops mcp` | Launch FastMCP Model Context Protocol server over stdio for Claude Desktop, Cursor, or Continue |
| `ragops dev` | `ragops dev` | Launch unified local development stack (FastAPI backend on :8000 + React UI on :5173) |
| `ragops ingest` | `ragops ingest <path> [--version <v>]` | Ingest PDF, HTML, or Markdown files into ChromaDB |
| `ragops query` | `ragops query "<question>" [--top-k 5]` | Ask questions from the terminal with latency attribution and citations |
| `ragops evaluate`| `ragops evaluate -d <dataset.jsonl> [--version <v>]` | Run quality evaluation benchmark against golden dataset with Wilson 95% CI |
| `ragops serve` | `ragops serve [--host 0.0.0.0] [--port 8000]` | Launch FastAPI HTTP service & embedded React Web UI |
| `ragops status`| `ragops status` | Display current models, thresholds, and active version |

---

## 11. Configuration & Environment Variables

Configure these settings in `.env` (refer to `.env.example` for the complete template):

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
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/ragops.db` | PostgreSQL (`postgresql+asyncpg://...`) or SQLite URL |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Redis / Memurai connection string for semantic cache |
| `REDIS_ENABLED` | `true` | Enable Redis multi-tier caching (gracefully falls back if offline) |
| `CACHE_SIMILARITY_THRESHOLD` | `0.90` | Cosine similarity threshold for semantic cache hits ($\ge 0.90$) |
| `CHROMA_PERSIST_DIR` | `./data/chroma` | Directory for persistent ChromaDB vector storage |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-Transformers embedding model (384 dimensions) |
| `WARMUP_ON_START` | `true` | Asynchronous pre-warming of PyTorch embeddings, cross-encoder, and vector DB |

---

## 12. Production Operations & Troubleshooting

### 1. Diagnostic Health Check (`ragops doctor`)
Run `ragops doctor` at any time to inspect your system's operational health:
```bash
ragops doctor
```
This tests connectivity to Ollama, Groq Cloud, ChromaDB, SQLite/PostgreSQL, and Redis, providing actionable remediation commands if any component is degraded.

### 2. Windows Daemon Management & Silent Startup
RAGOps automatically executes background utility calls (`sc.exe start Memurai`, `net start Memurai`, `ollama.exe serve`) using the Win32 flag `CREATE_NO_WINDOW = 0x08000000`, preventing CMD window popups on application launch.

### 3. Server Auto-Reload Loop Prevention
Uvicorn is explicitly configured with `reload_dirs=["src/ragops"]` and `reload_excludes=["*.log", "*.db", "*.sqlite3*", "data/*", "react/*", ".git/*"]`, permanently resolving reload loops caused by SQLite WAL writes from ChromaDB.

### 4. Running Fully Offline
To run in an air-gapped or offline environment:
```bash
# Pull model while online once
ollama pull llama3.2:3b

# In .env set:
LLM_PROVIDER=ollama
```

### 5. Automated CI/CD Regression Quality Gate
```bash
# Execute evaluation suite against golden dataset with quality gate enforcement
python scripts/run_evaluation.py \
  --dataset evaluation/datasets/golden.jsonl \
  --version candidate-v2 \
  --fail-on-gate
```

**Quality Gate Thresholds:**
- **Retrieval Recall@5**: $\ge 0.85$
- **Faithfulness (Groundedness)**: $\ge 0.90$
- **Answer Relevance**: $\ge 0.85$
- **Tail Latency (P95)**: $\le 3000\text{ ms}$
- **Maximum Allowed Regression vs. Production Baseline**: $< 5\%$

### 6. Executing Unit Tests
```bash
# Run complete test suite (all unit tests passing)
pytest tests/unit/ -q
```

---

## 13. Security & Hardening Policy

1. **Least-Privilege Containerization**: Production Docker containers execute under unprivileged user contexts (`appuser:appgroup`).
2. **Path-Traversal Protections**: Ingestion and catalog APIs strictly validate file paths against canonical base directories, preventing directory traversal attacks.
3. **Database Security**: Authentication uses individual random 32-character salts per user with SHA-256 password hashing.
4. **Data Sanitization**: PII, credentials, and API tokens are automatically masked in trace logs and telemetry databases.

---

## 14. License

RAGOps is open-source software licensed under the [MIT License](LICENSE).
