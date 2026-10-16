"""Distributed tracing — track request flows across the RAG pipeline.

Each request gets a trace with spans for each step:
- Query processing
- Embedding
- Vector search
- Reranking
- LLM generation
- Response building
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any, Generator

from ragops.core.logging import get_logger
from ragops.core.types import TraceEvent

logger = get_logger(__name__)


class Tracer:
    """Simple distributed tracer for RAG pipeline observability.

    Records timing and metadata for each step of request processing.
    """

    def __init__(self):
        self._traces: dict[str, list[TraceEvent]] = {}

    def new_trace(self) -> str:
        """Create a new trace and return its ID."""
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        self._traces[trace_id] = []
        return trace_id

    @contextmanager
    def span(
        self,
        trace_id: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Context manager for timing a span within a trace.

        Usage:
            with tracer.span(trace_id, "vector_search", {"top_k": 10}) as span_data:
                results = vector_store.search(...)
                span_data["results_count"] = len(results)
        """
        span_metadata = metadata or {}
        start_time = time.perf_counter()

        try:
            yield span_metadata
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            event = TraceEvent(
                trace_id=trace_id,
                span=name,
                duration_ms=duration_ms,
                metadata=span_metadata,
            )

            if trace_id in self._traces:
                self._traces[trace_id].append(event)

            logger.debug(
                "trace_span",
                trace_id=trace_id,
                span=name,
                duration_ms=round(duration_ms, 2),
            )

    def get_trace(self, trace_id: str) -> list[TraceEvent]:
        """Get all events for a trace."""
        return self._traces.get(trace_id, [])

    def get_trace_summary(self, trace_id: str) -> dict[str, Any]:
        """Get a summary of a trace."""
        events = self.get_trace(trace_id)
        if not events:
            return {}

        total_ms = sum(e.duration_ms for e in events)
        return {
            "trace_id": trace_id,
            "total_duration_ms": round(total_ms, 2),
            "spans": [
                {
                    "name": e.span,
                    "duration_ms": round(e.duration_ms, 2),
                    "metadata": e.metadata,
                }
                for e in events
            ],
        }


# Global tracer instance
_tracer = Tracer()


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    return _tracer
