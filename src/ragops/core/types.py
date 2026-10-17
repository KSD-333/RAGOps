"""Core types — shared data contracts between all modules.

These Pydantic models form the "language" modules use to communicate.
No module should pass raw vendor-specific objects across boundaries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class DocumentFormat(str, Enum):
    """Supported document formats for ingestion."""
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"


class FeedbackRating(str, Enum):
    """User feedback rating."""
    POSITIVE = "positive"
    NEGATIVE = "negative"


class PromotionStatus(str, Enum):
    """Quality gate promotion decision."""
    PASS = "pass"
    FAIL = "fail"


# =============================================================================
# Ingestion Types
# =============================================================================

class RawDocument(BaseModel):
    """Output of a Loader — raw extracted content before cleaning."""
    source: str
    content: str
    format: DocumentFormat
    metadata: dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CleanDocument(BaseModel):
    """Output of the Cleaner — cleaned text ready for chunking."""
    source: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """Output of the Chunker — a single chunk with full provenance."""
    chunk_id: str = Field(default_factory=lambda: f"chunk_{uuid.uuid4().hex[:12]}")
    document_id: str
    source: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_index: int = 0
    document_version: str = "v1"


class Document(BaseModel):
    """Top-level document record for tracking."""
    document_id: str = Field(default_factory=lambda: f"doc_{uuid.uuid4().hex[:12]}")
    source: str
    version: str = "v1"
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    chunk_count: int = 0


# =============================================================================
# Embedding Types
# =============================================================================

class EmbeddedChunk(BaseModel):
    """A document chunk with its embedding vector."""
    chunk: DocumentChunk
    embedding: list[float]
    embedding_model: str

    class Config:
        arbitrary_types_allowed = True


# =============================================================================
# Retrieval Types
# =============================================================================

class VectorSearchResult(BaseModel):
    """Raw result from vector store search."""
    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    """A chunk returned by the retriever (post-reranking)."""
    chunk_id: str
    document_id: str
    text: str
    score: float
    source: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedContext(BaseModel):
    """Complete retrieval result — the contract between retrieval and RAG."""
    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    retrieval_latency_ms: float = 0.0
    embed_latency_ms: float = 0.0
    search_latency_ms: float = 0.0
    rerank_latency_ms: float = 0.0



# =============================================================================
# Query Types
# =============================================================================

class QueryRequest(BaseModel):
    """Incoming user query from the API."""
    query: str
    session_id: str = Field(default_factory=lambda: f"session_{uuid.uuid4().hex[:8]}")
    filters: dict[str, Any] = Field(default_factory=dict)
    top_k: int = 10


class ProcessedQuery(BaseModel):
    """Output of query transformation."""
    original: str
    search_query: str
    filters: dict[str, Any] = Field(default_factory=dict)


class QueryEmbedding(BaseModel):
    """Query with its embedding vector."""
    query: str
    vector: list[float]
    model: str


# =============================================================================
# Generation Types
# =============================================================================

class PromptContext(BaseModel):
    """Input to the prompt builder — query + retrieved context strings."""
    query: str
    context: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)


class LLMResponse(BaseModel):
    """Raw LLM response with usage metadata."""
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0


class Source(BaseModel):
    """A cited source in a RAG response."""
    document: str
    chunk_id: str
    page: int | None = None
    section: str | None = None


class RAGResponse(BaseModel):
    """The complete RAG response — returned to the user."""
    answer: str
    sources: list[Source] = Field(default_factory=list)
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:12]}")
    metadata: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Evaluation Types
# =============================================================================

class EvaluationSample(BaseModel):
    """A single evaluation example from the golden dataset."""
    question: str
    expected_answer: str = ""
    expected_chunks: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationOutput(BaseModel):
    """Output from running the RAG pipeline on one evaluation sample."""
    question: str
    expected_answer: str
    actual_answer: str
    expected_chunks: list[str] = Field(default_factory=list)
    retrieved_chunks: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


class EvaluationResult(BaseModel):
    """Aggregate evaluation metrics for a RAG version."""
    dataset_version: str
    rag_version: str
    retrieval_recall: float = 0.0
    retrieval_precision: float = 0.0
    mrr: float = 0.0
    context_relevance: float = 0.0
    faithfulness: float = 0.0
    answer_relevance: float = 0.0
    citation_accuracy: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    sample_count: int = 0
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PromotionDecision(BaseModel):
    """Quality gate output — promote or reject a candidate version."""
    status: PromotionStatus
    candidate_version: str
    production_version: str = ""
    reasons: list[str] = Field(default_factory=list)
    candidate_metrics: dict[str, float] = Field(default_factory=dict)
    production_metrics: dict[str, float] = Field(default_factory=dict)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Observability Types
# =============================================================================

class TraceEvent(BaseModel):
    """A single trace span event for observability."""
    trace_id: str
    span: str
    duration_ms: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Feedback Types
# =============================================================================

class FeedbackRecord(BaseModel):
    """User feedback on a RAG response."""
    feedback_id: str = Field(default_factory=lambda: f"fb_{uuid.uuid4().hex[:12]}")
    trace_id: str
    rating: FeedbackRating
    comment: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
