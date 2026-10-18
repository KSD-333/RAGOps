"""Observability logging — structured log output for monitoring."""

from __future__ import annotations

from ragops.core.logging import get_logger

logger = get_logger(__name__)


def log_request(trace_id: str, query: str, **kwargs) -> None:
    """Log a RAG request."""
    logger.info("rag_request", trace_id=trace_id, query=query[:100], **kwargs)


def log_response(trace_id: str, latency_ms: float, **kwargs) -> None:
    """Log a RAG response."""
    logger.info("rag_response", trace_id=trace_id, latency_ms=round(latency_ms, 2), **kwargs)


def log_error(trace_id: str, error: str, **kwargs) -> None:
    """Log a RAG error."""
    logger.error("rag_error", trace_id=trace_id, error=error, **kwargs)
