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

## 4. Quickstart

### Prerequisites
- Python 3.11+
- Groq API Key (get free at [console.groq.com](https://console.groq.com))

### 1. Installation
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
```

### 2. Configure Environment
```bash
cp .env.example .env
```
Edit `.env` and insert your `GROQ_API_KEY`:
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.1-70b-versatile
```

### 3. Initialize & Ingest Knowledge Base
```bash
# Seed database with baseline metrics and sample documents
python scripts/seed_database.py

# Ingest documents from data/raw
ragops ingest data/raw --version v1
```

### 4. Query the System via CLI
```bash
ragops query "What is the default embedding model in RAGOps?"
```

### 5. Run API Server
```bash
ragops serve --port 8000 --reload
```
Interactive API documentation: **http://localhost:8000/docs**

---

## 5. CLI Reference

RAGOps comes with a unified command-line tool `ragops`:

| Command | Usage | Description |
|---|---|---|
| `ragops ingest` | `ragops ingest <path> [--version <v>]` | Ingest PDF, HTML, or Markdown files into vector store |
| `ragops query` | `ragops query "<question>" [--top-k 5]` | Ask questions and receive citations and latency metrics |
| `ragops evaluate`| `ragops evaluate -d <dataset.jsonl> [--version <v>]` | Run quality evaluation benchmark against golden dataset |
| `ragops serve` | `ragops serve [--host 0.0.0.0] [--port 8000]` | Launch production FastAPI HTTP service |
| `ragops status`| `ragops status` | Display current models, thresholds, and active version |

---

## 6. REST API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/query` | Submit query; returns answer, citations, and trace ID |
| `POST` | `/api/v1/ingest` | Trigger document ingestion pipeline for files/directories |
| `GET` | `/api/v1/documents/count` | Total indexed document chunks |
| `POST` | `/api/v1/feedback` | Record user feedback (👍 / 👎 with comments) |
| `GET` | `/api/v1/feedback/stats` | User satisfaction rate and feedback statistics |
| `GET` | `/health` | Liveness health check |
| `GET` | `/health/ready` | Readiness probe (verifies database & models) |
| `GET` | `/metrics` | Prometheus telemetry metrics |

---

## 7. Evaluation & Quality Gate Workflow

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

## 8. Running Full Observability Stack

Launch the complete stack (FastAPI, Prometheus, Grafana, Jaeger) in Docker:

```bash
make docker-up
```

- **FastAPI API**: http://localhost:8000/docs
- **Prometheus UI**: http://localhost:9090
- **Grafana Dashboards**: http://localhost:3000 (user: `admin`, pass: `admin`)
- **Jaeger Tracing UI**: http://localhost:16686

---

## 9. Testing

Execute the complete automated test suite:

```bash
# Run all unit, integration, and E2E tests
pytest tests/ -v
```

---

## 10. License

Licensed under the [MIT License](LICENSE).
