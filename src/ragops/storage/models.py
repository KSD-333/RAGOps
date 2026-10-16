"""Database models — SQLAlchemy ORM models for persistent storage."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


class DocumentModel(Base):
    """Track ingested documents."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(100), unique=True, nullable=False, index=True)
    source = Column(String(500), nullable=False)
    version = Column(String(50), default="v1")
    chunk_count = Column(Integer, default=0)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FeedbackModel(Base):
    """Store user feedback."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feedback_id = Column(String(100), unique=True, nullable=False, index=True)
    trace_id = Column(String(100), nullable=False, index=True)
    rating = Column(String(20), nullable=False)
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    evaluated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
