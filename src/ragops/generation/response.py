"""Response builder — combines LLM output with retrieval metadata.

Flow: LLMResponse + RetrievedContext + Metadata → RAGResponse

Creates the final response with citations and provenance.
"""

from __future__ import annotations

from ragops.core.logging import get_logger
from ragops.core.types import (
    LLMResponse,
    RAGResponse,
    RetrievedContext,
    Source,
)

logger = get_logger(__name__)


class ResponseBuilder:
    """Build the final RAGResponse from LLM output and retrieved context."""

    def build(
        self,
        llm_response: LLMResponse,
        retrieved_context: RetrievedContext,
        trace_id: str = "",
    ) -> RAGResponse:
        """Combine LLM response with source citations.

        Extracts source metadata from retrieved chunks and attaches them
        to the response for provenance tracking.
        """
        # Build source citations from retrieved chunks
        sources: list[Source] = []
        seen_sources = set()

        for chunk in retrieved_context.chunks:
            source_key = (chunk.source, chunk.chunk_id)
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append(
                    Source(
                        document=chunk.source,
                        chunk_id=chunk.chunk_id,
                        page=chunk.metadata.get("page_number"),
                        section=chunk.metadata.get("section"),
                    )
                )

        response = RAGResponse(
            answer=llm_response.text,
            sources=sources,
            trace_id=trace_id,
            metadata={
                "model": llm_response.model,
                "input_tokens": llm_response.input_tokens,
                "output_tokens": llm_response.output_tokens,
                "generation_latency_ms": round(llm_response.latency_ms, 2),
                "retrieval_latency_ms": round(retrieved_context.retrieval_latency_ms, 2),
                "total_latency_ms": round(
                    llm_response.latency_ms + retrieved_context.retrieval_latency_ms, 2
                ),
                "chunks_retrieved": len(retrieved_context.chunks),
            },
        )

        logger.debug(
            "response_built",
            trace_id=trace_id,
            sources=len(sources),
            total_latency_ms=response.metadata["total_latency_ms"],
        )

        return response
