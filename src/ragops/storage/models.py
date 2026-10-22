"""Database models — SQLAlchemy ORM models for PostgreSQL and SQLite persistence."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

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


class CompanyProfileModel(Base):
    """Dynamic company profile and knowledge grounding.

    Stores real-world enterprise facts:
    - Company name & Group name
    - Industry and corporate description
    - Products, services, and solutions (JSON list or dict)
    - Employee count, structure, and details
    - Locations (headquarters, manufacturing plants, regional offices)
    - Leadership (Current CEO, Managing Directors, Board members)
    - Registered MNC domains & URLs (JSON list of strings)
    - Additional extracted metadata (ratings, certifications, stock symbols, etc.)
    """
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(200), nullable=False, default="")
    group_name = Column(String(200), nullable=False, default="")
    industry = Column(String(100), default="")
    description = Column(Text, default="")
    products = Column(JSON, default=list)  # list of products/services
    employee_details = Column(Text, default="")
    locations = Column(JSON, default=list)  # list of plants / offices / regions
    ceo = Column(String(200), default="")
    directors = Column(JSON, default=list)  # list of directors/key executives
    domains_urls = Column(JSON, default=list)  # list of corporate URLs / branch links
    metadata_json = Column(JSON, default=dict)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CompanySourceModel(Base):
    """Registered official domains, branch portals, and uploaded sources."""
    __tablename__ = "company_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(50), default="default_org", nullable=False, index=True)
    source_type = Column(String(20), nullable=False, default="website")  # 'website' | 'upload'
    source_url = Column(String(500), nullable=True)
    display_name = Column(String(200), nullable=False)
    country_code = Column(String(10), nullable=True)
    language_code = Column(String(10), default="en")
    verification_status = Column(String(20), default="pending", nullable=False)  # 'pending', 'verified', 'rejected'
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    documents = relationship("SourceDocumentModel", back_populates="source", cascade="all, delete-orphan")


class SourceDocumentModel(Base):
    """Retrieved page or uploaded file content with versioning and cryptographic SHA-256 hash."""
    __tablename__ = "source_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(50), default="default_org", nullable=False, index=True)
    source_id = Column(String(36), ForeignKey("company_sources.id", ondelete="CASCADE"), nullable=True, index=True)
    canonical_url = Column(String(500), nullable=True)
    title = Column(String(255), nullable=True)
    content_text = Column(Text, nullable=True)
    content_sha256 = Column(String(64), nullable=False, index=True)
    content_version = Column(Integer, default=1, nullable=False)
    content_language = Column(String(10), default="en")
    country_code = Column(String(10), nullable=True)
    publication_date = Column(String(50), nullable=True)
    fetched_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    processing_status = Column(String(20), default="ready", nullable=False)  # 'pending', 'processing', 'ready', 'failed', 'superseded'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    source = relationship("CompanySourceModel", back_populates="documents")
    candidates = relationship("FactCandidateModel", back_populates="document", cascade="all, delete-orphan")


class FactCandidateModel(Base):
    """Field-level extracted candidate facts awaiting validation or review."""
    __tablename__ = "fact_candidates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(50), default="default_org", nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("source_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    section_key = Column(String(50), nullable=False, index=True)  # 'identity', 'workforce', 'locations', 'clients', 'hubs', 'products', 'overview'
    fact_key = Column(String(100), nullable=False, index=True)  # 'legal_name', 'headquarters', 'employee_count', 'manufacturing_plants', etc.
    scope_key = Column(String(50), default="global", nullable=False, index=True)  # 'global', 'country:IN', 'country:IT'
    proposed_value = Column(JSON, nullable=False)
    normalized_value = Column(JSON, nullable=True)
    validation_status = Column(String(20), default="pending", nullable=False)  # 'pending', 'valid', 'invalid', 'conflicting', 'needs_review'
    review_status = Column(String(20), default="pending", nullable=False)  # 'pending', 'approved', 'rejected', 'needs_changes', 'superseded'
    extractor_version = Column(String(50), default="v1.0")
    extraction_confidence = Column(Float, default=1.0)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document = relationship("SourceDocumentModel", back_populates="candidates")
    evidence = relationship("FactEvidenceModel", back_populates="candidate", cascade="all, delete-orphan")
    decisions = relationship("FactReviewDecisionModel", back_populates="candidate", cascade="all, delete-orphan")


class FactEvidenceModel(Base):
    """Exact evidence sentence/span supporting an extracted fact candidate."""
    __tablename__ = "fact_evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String(36), ForeignKey("fact_candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), nullable=True)
    evidence_text = Column(Text, nullable=False)
    start_offset = Column(Integer, nullable=True)
    end_offset = Column(Integer, nullable=True)
    section_heading = Column(String(200), nullable=True)
    source_url = Column(String(500), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    candidate = relationship("FactCandidateModel", back_populates="evidence")


class CompanyFactModel(Base):
    """Approved company facts serving as immutable, versioned source of truth."""
    __tablename__ = "company_facts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(50), default="default_org", nullable=False, index=True)
    section_key = Column(String(50), nullable=False, index=True)
    fact_key = Column(String(100), nullable=False, index=True)
    scope_key = Column(String(50), default="global", nullable=False, index=True)
    approved_value = Column(JSON, nullable=False)
    source_candidate_id = Column(String(36), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    valid_from = Column(String(50), nullable=True)
    valid_until = Column(String(50), nullable=True)
    approved_by = Column(String(100), default="admin")
    approved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_company_facts_active_scope", "organization_id", "section_key", "fact_key", "scope_key", "is_active"),
    )


class FactReviewDecisionModel(Base):
    """Immutable audit trail of human review decisions."""
    __tablename__ = "fact_review_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(50), default="default_org", nullable=False, index=True)
    candidate_id = Column(String(36), ForeignKey("fact_candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String(100), default="admin", nullable=False)
    decision = Column(String(20), nullable=False)  # 'approved', 'rejected', 'needs_changes'
    submitted_value = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    candidate = relationship("FactCandidateModel", back_populates="decisions")


class PublicationOutboxModel(Base):
    """Transactional publication outbox for reliable, safe vector index updates."""
    __tablename__ = "publication_outbox"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String(50), default="default_org", nullable=False, index=True)
    entity_type = Column(String(50), default="company_fact", nullable=False)  # 'company_fact', 'document_version'
    entity_id = Column(String(36), nullable=False)
    entity_version = Column(Integer, default=1, nullable=False)
    operation = Column(String(20), default="upsert", nullable=False)  # 'upsert', 'delete'
    status = Column(String(20), default="pending", nullable=False, index=True)  # 'pending', 'processing', 'completed', 'failed'
    attempts = Column(Integer, default=0, nullable=False)
    next_attempt_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

