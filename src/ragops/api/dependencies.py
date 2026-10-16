"""Dependency injection — provide shared services to API routes."""

from __future__ import annotations

from functools import lru_cache

from ragops.feedback.service import FeedbackService
from ragops.rag.pipeline import RAGPipeline
from ragops.retrieval.retriever import RAGRetriever
from ragops.observability.metrics import get_metrics


@lru_cache(maxsize=1)
def get_rag_pipeline() -> RAGPipeline:
    """Get or create the RAG pipeline singleton."""
    return RAGPipeline()


@lru_cache(maxsize=1)
def get_feedback_service() -> FeedbackService:
    """Get or create the feedback service singleton."""
    return FeedbackService()


def get_retriever() -> RAGRetriever:
    """Get the retriever from the pipeline."""
    return get_rag_pipeline().retriever
