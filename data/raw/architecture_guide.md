# RAGOps Architecture and Design Specification

## Overview
RAGOps is a production-grade Retrieval-Augmented Generation (RAG) platform with integrated evaluation, distributed observability, automated quality gates, and continuous feedback loops.

## Core Components
1. **API Gateway / Service Layer**:
   - Built on FastAPI with asynchronous lifespan management.
   - Thin presentation layer routing requests to the RAG pipeline.
   - Comprehensive middleware for request tracing, latency monitoring, and CORS handling.

2. **Ingestion Engine**:
   - Multi-format document loading supporting Markdown, PDF, and HTML.
   - Text cleaning pipeline to strip boilerplate, normalize whitespace, and sanitize encoding.
   - Character and token-aware sliding window chunking with configurable overlap.

3. **Hybrid Retrieval Subsystem**:
   - Dense vector embeddings generated via Sentence Transformers (default: `all-MiniLM-L6-v2`, 384 dimensions).
   - High-performance vector persistence using ChromaDB.
   - Cross-encoder reranking via `cross-encoder/ms-marco-MiniLM-L-6-v2` for context refinement.

4. **Generation & Orchestration**:
   - Groq API integration supporting fast inference with LLaMA 3.1 70B and Mixtral.
   - Strict prompt templates enforcing context grounding and citation generation.
   - Query transformation for retrieval optimization while retaining verbatim queries.

5. **Evaluation Subsystem**:
   - Retrieval metrics: Recall@K, Precision@K, Mean Reciprocal Rank (MRR), Context Relevance.
   - Generation metrics: Answer Relevance, Faithfulness/Groundedness, Citation Accuracy.
   - LLM-as-a-judge scoring engine alongside deterministic heuristic evaluators.

6. **Observability & Telemetry**:
   - OpenTelemetry span instrumentation across query transformation, vector search, reranker, and generation.
   - Prometheus metrics for latency percentiles (P50, P95, P99), throughput, error rates, and token consumption.
   - Structured JSON logging with correlated trace identifiers.
