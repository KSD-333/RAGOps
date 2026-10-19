"""Database models — SQLAlchemy ORM models for PostgreSQL and SQLite persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


class UserModel(Base):
    """User account model supporting role-based access and authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    salt = Column(String(64), nullable=False)
    role = Column(String(20), default="user", nullable=False)  # "admin" | "user"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    messages = relationship("ChatMessageModel", back_populates="user", cascade="all, delete-orphan")


class ChatMessageModel(Base):
    """Production-grade telemetry and chat history record.

    Stores complete end-to-end provenance:
    - User identification & session binding
    - Token consumption (prompt, completion, total, cost)
    - Full chunk payload sent to LLM (IDs, doc names, page, similarity score, text snippets)
    - Latency per hop (embed, vector search, rerank, generation, total)
    - Citations and user feedback
    - ML readiness flags: intent, category, churn risk, POSH/policy risk, training readiness
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(100), unique=True, nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    trace_id = Column(String(100), nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(50), nullable=False, index=True)

    query = Column(Text, nullable=False)
    answer = Column(Text, default="", nullable=False)
    model = Column(String(100), default="", nullable=False)

    # Token & Cost Metrics
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    cost_usd = Column(Float, default=0.0, nullable=False)

    # Per-Hop Latency Telemetry (ms)
    embed_latency_ms = Column(Float, default=0.0, nullable=False)
    search_latency_ms = Column(Float, default=0.0, nullable=False)
    rerank_latency_ms = Column(Float, default=0.0, nullable=False)
    generation_latency_ms = Column(Float, default=0.0, nullable=False)
    total_latency_ms = Column(Float, default=0.0, nullable=False)

    # Retrieval Context & Citations (JSON/JSONB)
    chunks_sent = Column(JSON, default=list, nullable=False)
    citations = Column(JSON, default=list, nullable=False)

    # User Feedback
    feedback_rating = Column(String(20), nullable=True)  # "positive" | "negative" | None
    feedback_comment = Column(Text, default="")

    # Semantic Cache & Query Intelligence Telemetry
    cache_hit = Column(Boolean, default=False, nullable=False, index=True)
    rewritten_query = Column(Text, default="", nullable=False)
    cache_latency_saved_ms = Column(Float, default=0.0, nullable=False)

    # Analytics, Churn & Policy Risk Signals (Future ML Training)
    category = Column(String(50), default="general", nullable=False)
    intent = Column(String(100), default="information_retrieval", nullable=False)
    sentiment_score = Column(Float, default=0.0, nullable=False)
    churn_risk_flag = Column(Boolean, default=False, nullable=False, index=True)
    policy_risk_flag = Column(Boolean, default=False, nullable=False, index=True)
    training_ready = Column(Boolean, default=False, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = relationship("UserModel", back_populates="messages")

    __table_args__ = (
        Index("idx_chat_username_created", "username", "created_at"),
        Index("idx_chat_user_id_created", "user_id", "created_at"),
        Index("idx_chat_risk_created", "policy_risk_flag", "churn_risk_flag", "created_at"),
    )


class DocumentModel(Base):
    """Track ingested documents and catalog classifications."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(100), unique=True, nullable=False, index=True)
    source = Column(String(500), nullable=False, index=True)
    title = Column(String(255), default="", nullable=False)
    doc_type = Column(String(50), default="other", nullable=False, index=True)  # policy, code, programme, governance, manual, other
    category = Column(String(100), default="General Corporate", nullable=False, index=True)
    is_policy = Column(Boolean, default=False, nullable=False, index=True)
    governance_level = Column(String(50), default="Operational", nullable=False)
    version = Column(String(50), default="v1")
    chunk_count = Column(Integer, default=0)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SemanticCacheModel(Base):
    """Production semantic and deterministic answer cache.

    Guarantees safety gates:
    - Never caches or reuses answers on similarity alone
    - Scope and intent must match
    - Knowledge base fingerprint / collection version must match
    """
    __tablename__ = "semantic_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(128), unique=True, nullable=False, index=True)
    normalized_query = Column(Text, nullable=False)
    original_query = Column(Text, nullable=False)
    embedding_json = Column(JSON, nullable=True)  # List[float] embedding for cosine similarity
    intent = Column(String(50), default="general", nullable=False, index=True)
    scope = Column(String(50), default="single_document", nullable=False, index=True)
    target_entity = Column(String(50), default="", nullable=False)
    answer = Column(Text, nullable=False)
    citations = Column(JSON, default=list, nullable=False)
    chunks_sent = Column(JSON, default=list, nullable=False)
    kb_fingerprint = Column(String(64), default="v1", nullable=False, index=True)
    hit_count = Column(Integer, default=0, nullable=False)
    last_hit_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class FeedbackModel(Base):
    """Store user feedback."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feedback_id = Column(String(100), unique=True, nullable=False, index=True)
    trace_id = Column(String(100), nullable=False, index=True)
    rating = Column(String(20), nullable=False)
    comment = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EvaluationModel(Base):
    """Store evaluation results."""
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_version = Column(String(100), nullable=False)
    rag_version = Column(String(50), nullable=False)
    retrieval_recall = Column(Float, default=0.0)
    faithfulness = Column(Float, default=0.0)
    answer_relevance = Column(Float, default=0.0)
    citation_accuracy = Column(Float, default=0.0)
    p95_latency_ms = Column(Float, default=0.0)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    sample_count = Column(Integer, default=0)
    evaluated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TraceModel(Base):
    """Store request traces for observability."""
    __tablename__ = "traces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trace_id = Column(String(100), unique=True, nullable=False, index=True)
    query = Column(Text, nullable=False)
    answer = Column(Text, default="")
    model = Column(String(100), default="")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    retrieval_latency_ms = Column(Float, default=0.0)
    generation_latency_ms = Column(Float, default=0.0)
    total_latency_ms = Column(Float, default=0.0)
    chunks_retrieved = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
