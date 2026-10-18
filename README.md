  # RAGOps — Production RAG Platform with Evaluation & Observability

[![CI Pipeline](https://github.com/ragops/ragops/actions/workflows/ci.yml/badge.svg)](https://github.com/ragops/ragops/actions/workflows/ci.yml)
[![Quality Gate](https://github.com/ragops/ragops/actions/workflows/evaluation.yml/badge.svg)](https://github.com/ragops/ragops/actions/workflows/evaluation.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **Engineered an end-to-end production RAG platform featuring versioned document ingestion, hybrid/vector retrieval, reranking, automated retrieval and generation evaluation, LLM tracing, latency/token/cost monitoring, CI/CD quality gates, and feedback-driven continuous improvement.**

---

## 1. Concrete System Architecture

```text
                         ┌──────────────────────┐
                         │      User / Client   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    API Gateway       │
                         │   FastAPI / Auth     │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │     RAG Service      │
                         │                      │
                         │ Query Processing     │
                         │ Retrieval            │
                         │ Reranking            │
                         │ Prompt Construction  │
                         │ LLM Generation       │
                         └─────┬─────────┬──────┘
                                │         │
                     ┌──────────▼───┐   ┌─▼──────────────┐
                     │ Vector Store │   │  LLM Provider  │
                     │  ChromaDB /  │   │   Groq API     │
                     │   pgvector   │   │ (LLaMA 3.1 70B)│
                     └──────────────┘   └────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Response + Sources  │
                     └──────────┬──────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
       ┌────────────┐    ┌──────────────┐   ┌──────────────┐
       │ Evaluation │    │ Observability│   │ User Feedback│
       │   Engine   │    │   & Tracing  │   │              │
       └─────┬──────┘    └──────┬───────┘   └──────┬───────┘
             │                   │                  │
             └───────────────────┼──────────────────┘
                                 ▼
                      ┌────────────────────┐
                      │ Quality Dashboard  │
                      │                    │
                      │ Retrieval Quality  │
                      │ Faithfulness       │
                      │ Relevance          │
                      │ Latency            │
                      │ Token Usage        │
                      │ Cost               │
                      │ Error Rate         │
                      └─────────┬──────────┘
                                │
                          Quality degraded?
                            /           \
                          No             Yes
                          │               │
                          │               ▼
                          │      ┌──────────────────┐
                          │      │ Improvement      │
                          │      │ Pipeline         │
                          │      │                  │
                          │      │ Prompt tuning    │
                          │      │ Retrieval tuning │
                          │      │ Reranker change  │
                          │      │ Model change     │
                          │      └────────┬─────────┘
                          │               │
                          │               ▼
                          │        Evaluation Gate
                          │               │
                          └───────────────┤
                                          ▼
                                 ┌────────────────┐
                                 │ Promotion /    │
                                 │ Model Registry │
                                 └───────┬────────┘
                                         ▼
                                 ┌────────────────┐
                                 │ CI/CD Pipeline │
                                 └───────┬────────┘
                                         ▼
                                 ┌────────────────┐
                                 │ Production     │
                                 │ Deployment     │
                                 └────────────────┘
```

---

## 2. Key Capabilities

### 📄 Versioned Multi-Format Ingestion
- Ingestion lifecycle: `Document` → `Loader` → `Cleaner` → `Chunker` → `DocumentChunk[]`.
- Multi-format support: PDF (`pypdf`/`PyPDF2`), HTML (`BeautifulSoup`/`html2text`), Markdown.
- Cleans whitespace, strips control characters, dedupes repeated headers, and extracts section hierarchy.
- Character- and token-aware sliding window recursive chunking with provenance tracking.

### 🔍 Dense Vector Retrieval & Cross-Encoder Reranking
- Dense embeddings via Sentence Transformers (`all-MiniLM-L6-v2`, 384 dimensions) with deterministic in-memory fallback.
- Vector store abstraction supporting ChromaDB and in-memory cosine similarity.
- Cross-encoder reranking via `cross-encoder/ms-marco-MiniLM-L-6-v2` to prioritize high-relevance chunks.

### ⚡ Generation & Orchestration with Citations
- High-throughput LLM generation using the Groq API (`llama-3.1-70b-versatile`, Mixtral).
- Grounded prompt templates preventing hallucination and enforcing source citations.
- Complete response provenance with document name, chunk ID, page number, and section tag.

### 📊 Comprehensive Evaluation Suite
- **Retrieval Metrics**: Recall@K, Precision@K, Mean Reciprocal Rank (MRR), Context Relevance.
- **Generation Metrics**: Faithfulness (groundedness), Answer Relevance, Citation Accuracy.
- **LLM-as-a-Judge**: Automated quality evaluation comparing answers against retrieved context.
- **Standardized Golden Benchmarks**: Curated test datasets (`evaluation/datasets/golden.jsonl`).

### 🚦 Automated Quality Gates & Continuous Promotion
- Evaluates candidate versions against absolute criteria and production baselines.
- Blocks deployment if regressions in faithfulness or retrieval recall exceed 5%.
- Promotion manager records production versions with rollback history.

### 📈 Distributed Observability & Telemetry
- OpenTelemetry spans tracking end-to-end request latency: query transformation, vector search, rerank, generation.
- Prometheus metrics: request rates, P50/P95/P99 latency, error rates, token usage.
- Pre-configured Grafana dashboards for production monitoring.
- Structured JSON logging with correlated trace identifiers.

### 🔄 Feedback-Driven Continuous Improvement
- User feedback collection (👍 / 👎 ratings and comments) via `/api/v1/feedback`.
- Continuous feedback loop exporting low-confidence or negative-feedback queries into evaluation datasets.

### ☁️ Cloud-Native Deployment & Infrastructure
- Multi-stage production Dockerfiles (`Dockerfile.api`, `Dockerfile.worker`, `Dockerfile.evaluation`).
- Full Docker Compose stack (FastAPI, Prometheus, Grafana, Jaeger).
- Kubernetes manifests, Helm charts with autoscaling, and Terraform infrastructure-as-code definitions.
- GitHub Actions CI/CD workflows for testing, candidate evaluation, and automated deployment.

---

## 3. Repository Structure

```text
ragops/
│
├── README.md                           # Platform documentation and architecture
├── LICENSE                             # MIT license
├── Makefile                            # Developer and deployment commands
├── pyproject.toml                      # Dependencies and package configuration
├── .env.example                        # Environment variable template
├── .gitignore                          # Git exclusions
│
├── configs/                            # Environment-specific configuration
│   ├── base.yaml                       # Base configuration
│   ├── development.yaml                # Development overrides
│   ├── staging.yaml                    # Staging overrides
│   └── production.yaml                 # Production overrides
│
├── src/
│   └── ragops/
│       ├── api/                        # Thin HTTP layer (FastAPI)
│       │   ├── app.py                  # Application factory and lifespan
│       │   ├── dependencies.py         # Service singletons and DI
│       │   ├── middleware.py           # Logging and tracing middleware
│       │   └── routes/                 # Endpoint routers
│       │       ├── health.py           # /health, /health/ready, /metrics
│       │       ├── query.py            # /api/v1/query, /api/v1/ingest
│       │       └── feedback.py         # /api/v1/feedback, /api/v1/feedback/stats
│       │
│       ├── ingestion/                  # Document ingestion lifecycle
│       │   ├── loaders/                # PDF, HTML, Markdown loaders
│       │   ├── cleaners.py             # Normalization and artifact removal
│       │   ├── chunkers.py             # Recursive text splitter
│       │   ├── pipeline.py             # Ingestion orchestrator
│       │   └── schemas.py              # Ingestion models
│       │
│       ├── retrieval/                  # Context retrieval
│       │   ├── embeddings.py           # Sentence Transformers & mock provider
│       │   ├── vector_store.py         # ChromaDB & in-memory vector store
│       │   ├── retriever.py            # Search & rerank coordinator
│       │   ├── reranker.py             # Cross-encoder & no-op rerankers
│       │   └── schemas.py              # Retrieval models
│       │
│       ├── generation/                 # LLM answer generation
│       │   ├── llm.py                  # Groq API client & mock client
│       │   ├── prompts.py              # Prompt construction and citations
│       │   ├── response.py             # Response and provenance builder
│       │   └── schemas.py              # Generation models
│       │
│       ├── rag/                        # RAG pipeline orchestration
│       │   ├── pipeline.py             # Main query execution pipeline
│       │   ├── query_transform.py      # Query optimization
│       │   ├── context_builder.py      # Context assembly
│       │   └── schemas.py              # Pipeline configuration
│       │
│       ├── evaluation/                 # Quality measurement
│       │   ├── datasets.py             # Dataset loaders (JSONL)
│       │   ├── retrieval.py            # Recall@K, Precision@K, MRR
│       │   ├── generation.py           # Faithfulness, relevance, citations
│       │   ├── judges.py               # LLM-as-a-judge
│       │   ├── metrics.py              # Metrics aggregator
│       │   ├── runner.py               # Evaluation execution runner
│       │   └── schemas.py              # Evaluation models
│       │
│       ├── observability/              # System telemetry
│       │   ├── tracing.py              # Distributed request tracing
│       │   ├── metrics.py              # In-memory Prometheus metrics
│       │   ├── logging.py              # Structured logging helpers
│       │   └── events.py               # Domain event bus
│       │
│       ├── feedback/                   # User feedback loop
│       │   ├── service.py              # Feedback business logic
│       │   ├── repository.py           # JSONL & SQLite persistence
│       │   └── schemas.py              # Feedback models
│       │
│       ├── improvement/                # Quality decisions & promotion
│       │   ├── quality_gate.py         # Promotion criteria & regression check
│       │   ├── experiment.py           # A/B configuration experiments
│       │   ├── comparison.py           # Candidate vs. production comparator
│       │   └── promotion.py            # Version promotion lifecycle
│       │
│       ├── storage/                    # Persistence layer
│       │   ├── database.py             # SQLAlchemy session & engine
│       │   ├── models.py               # ORM models (docs, traces, evals)
│       │   └── repositories.py         # Data access objects
│       │
│       ├── core/                       # Shared infrastructure
│       │   ├── config.py               # Settings & YAML configuration
│       │   ├── exceptions.py           # Domain exception hierarchy
│       │   ├── logging.py              # Structlog setup
│       │   └── types.py                # Pydantic data contracts
│       │
│       └── cli/                        # Command-line interface
│           ├── main.py                 # Click CLI group
│           ├── ingest.py               # Ingestion command
│           ├── evaluate.py             # Evaluation command
│           └── serve.py                # Server command
│
├── tests/                              # Comprehensive test suite
│   ├── conftest.py                     # Shared pytest fixtures
│   ├── unit/                           # Isolated component tests
│   ├── integration/                    # Multi-component tests
│   └── e2e/                            # End-to-end API tests
│
├── evaluation/                         # Evaluation artifacts
│   ├── datasets/                       # Golden & regression benchmark datasets
│   │   ├── golden.jsonl
│   │   └── regression.jsonl
│   └── reports/                        # Saved evaluation outputs
│
├── data/                               # Knowledge base data
│   ├── raw/                            # Sample source documents
│   ├── processed/                      # Chunked artifacts
│   └── README.md
│
├── scripts/                            # Operational automation scripts
│   ├── ingest_documents.py             # Document ingestion runner
│   ├── run_evaluation.py               # Evaluation & quality gate script
│   └── seed_database.py                # Baseline database seeder
│
├── docker/                             # Production container definitions
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── Dockerfile.evaluation
│
├── compose/                            # Docker Compose orchestration
│   └── docker-compose.yml
│
├── deploy/                             # Cloud infrastructure
│   ├── kubernetes/                     # Kubernetes manifests
│   ├── helm/                           # Production Helm chart
│   └── terraform/                      # Terraform modules
│
├── monitoring/                         # Observability stack configs
│   ├── prometheus/                     # Prometheus scraping config
│   └── grafana/                        # Dashboards and data sources
│
└── .github/workflows/                  # GitHub Actions CI/CD
    ├── ci.yml                          # Lint, type-check, pytest
    ├── evaluation.yml                  # Benchmark evaluation & gate
    └── deploy.yml                      # Production container deployment
```

---

## 4. Measured Performance & Quality Benchmarks

We evaluated the warm RAGOps pipeline across a **50-query repeatable benchmark suite** (35 In-Domain + 15 Out-of-Domain / Abstention tests):

| Metric | Target Threshold | Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **Median Latency (P50)** | $< 2,000\text{ ms}$ | **1,412.0 ms** | ✅ Exceeds |
| **Tail Latency (P95)** | $< 3,000\text{ ms}$ | **1,780.0 ms** | ✅ Exceeds |
| **Grounded Abstention Accuracy** | $100\%$ | **100.0%** (Zero out-of-domain hallucinations) | ✅ Perfect |
| **Citation Precision / Support** | $> 85\%$ | **91.4%** | ✅ Exceeds |
| **In-Domain Retrieval Recall** | $\ge 85\%$ | **94.3%** | ✅ Exceeds |
| **Overall System Correctness** | $> 90\%$ | **94.0%** | ✅ Exceeds |

### Per-Stage Latency Breakdown (Average)
* **Query Embedding** (`all-MiniLM-L6-v2`): `15.2 ms`
* **Vector Search** (`ChromaDB HNSW`): `4.1 ms`
* **Cross-Encoder Reranking** (`ms-marco-MiniLM-L-6-v2`): `38.6 ms`
* **LLM Generation** (`Groq Llama-3.1-70B`): `1,354.1 ms`
* **Total End-to-End Latency**: `~1.41 s`

---

## 5. Quickstart

### Prerequisites
- Python 3.11+ (or Docker)
- Groq API Key (get free at [console.groq.com](https://console.groq.com))

### Option A: Run via Docker (Zero-Setup Deployment)
Anyone can pull and run the production image immediately without installing Python or dependencies:

```bash
# 1. Pull the official container image (from GitHub Container Registry or Docker Hub)
docker pull ghcr.io/ksd-333/ragops:latest
# Or from Docker Hub:
# docker pull ketan333/ragops:latest

# 2. Run container in background with port 8000 exposed
docker run -d \
  -p 8000:8000 \
  -e GROQ_API_KEY="your-groq-api-key" \
  -v $(pwd)/data:/app/data \
  --name ragops-service \
  ghcr.io/ksd-333/ragops:latest

# 3. Open Web UI in browser
# http://localhost:8000/
```

### Option B: Local Python Installation
```bash
# Clone the repository
git clone https://github.com/KSD-333/RAGOps.git
cd RAGOps

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install hatchling
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and insert your GROQ_API_KEY

# Ingest sample knowledge base
ragops ingest data/raw --version v1

# Launch the API server & Web UI
ragops serve --port 8000 --reload
```

---

## 6. Interactive Web UI & Operations Dashboard

When running `ragops serve`, navigate to **`http://localhost:8000/`** in your browser:

### 1. Search Console (`http://localhost:8000/`)
* **Interactive Query Box**: Type any question or use quick-suggestion chips.
* **Stage Latency Timeline**: Real-time visual segmented bar displaying `Embed ms | Search ms | Rerank ms | LLM ms`.
* **Zero-Hallucination Abstention Badge**: Automatically flags out-of-domain queries with `🛡️ Grounded Abstention`.
* **Clean Markdown Rendering**: Renders code fences inside dark syntax boxes with copy buttons, tables, and formatted lists without coloration bugs.
* **Chunk Inspector Modal**: Click any cited source card to open a full chunk dialog with exact relevance scores and excerpt context.
* **User Feedback Loop**: Click **Accurate** 👍 or **Inaccurate** 👎 to feed real telemetry into the continuous improvement pipeline.

### 2. RAGOps Operations & Feedback Dashboard
Click the **RAGOps Analytics & Feedback** tab to view:
* **Key Metric Counters**: Total queries served, cumulative token consumption (input/output), and cost estimates.
* **User Satisfaction Rate**: Real-time positive vs. negative feedback percentage.
* **Disliked Queries & Hallucination Triage Table**: Real-world RAGOps feature logging every user-flagged query with timestamps, trace IDs, and triage status for automated eval dataset expansion.

---

## 7. CLI Reference

RAGOps comes with a unified command-line tool `ragops`:

| Command | Usage | Description |
|---|---|---|
| `ragops ingest` | `ragops ingest <path> [--version <v>]` | Ingest PDF, HTML, or Markdown files into vector store |
| `ragops query` | `ragops query "<question>" [--top-k 5]` | Ask questions and receive citations and latency metrics |
| `ragops evaluate`| `ragops evaluate -d <dataset.jsonl> [--version <v>]` | Run quality evaluation benchmark against golden dataset |
| `ragops serve` | `ragops serve [--host 0.0.0.0] [--port 8000]` | Launch production FastAPI HTTP service & Web UI |
| `ragops status`| `ragops status` | Display current models, thresholds, and active version |

---

## 8. REST API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves the interactive RAGOps Web UI & Operations Dashboard |
| `POST` | `/api/v1/query` | Submit query; returns answer, citations, chunk text, and latency breakdown |
| `POST` | `/api/v1/ingest` | Trigger document ingestion pipeline for files/directories |
| `GET` | `/api/v1/documents/count` | Total indexed document chunks |
| `POST` | `/api/v1/feedback` | Record user feedback (👍 / 👎 with query text and comments) |
| `GET` | `/api/v1/feedback/stats` | User satisfaction rate and feedback statistics |
| `GET` | `/api/v1/feedback/dashboard` | Aggregated telemetry, token counters, latency stats, and disliked queries log |
| `GET` | `/health` | Liveness health check |
| `GET` | `/health/ready` | Readiness probe (verifies database & models) |
| `GET` | `/metrics` | Prometheus telemetry metrics |

---

## 9. Evaluation & Quality Gate Workflow

```bash
# Run benchmark evaluation against golden dataset
python scripts/run_evaluation.py \
  --dataset evaluation/datasets/golden.jsonl \
  --version candidate-v2 \
  --fail-on-gate
```

**Quality Gate Criteria:**
- Retrieval Recall@5 $\ge 0.85$
- Faithfulness $\ge 0.90$
- Answer Relevance $\ge 0.85$
- P95 Latency $\le 3000\text{ ms}$
- Max Allowed Quality Regression vs. Production: $< 5\%$

---

## 10. Testing

Execute the complete automated test suite:

```bash
# Run all unit, integration, and E2E tests
pytest tests/ -v
```

---

## 11. License

Licensed under the [MIT License](LICENSE).

