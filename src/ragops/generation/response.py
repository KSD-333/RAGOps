"""Response builder — combines LLM output with retrieval metadata.

Flow: LLMResponse + RetrievedContext + Metadata → RAGResponse

Creates the final response with citations and provenance.
"""

from __future__ import annotations

from ragops.core.logging import get_logger
from ragops.core.types import (
    LLMResponse,
    RAGResponse,
    RetrievedChunk,
    RetrievedContext,
    Source,
)

logger = get_logger(__name__)


class ResponseBuilder:
    """Build the final RAGResponse from LLM output and retrieved context."""

    def _is_abstention(self, text: str) -> bool:
        """Check if the answer indicates the knowledge base lacks information."""
        text_lower = text.lower()
        abstention_patterns = [
            "do not contain",
            "does not contain",
            "no information",
            "not mentioned",
            "cannot find",
            "cannot answer",
            "none of which address",
            "not provide any information",
            "insufficient information",
            "not enough information",
        ]
        return any(p in text_lower for p in abstention_patterns)

    def _select_sources(
        self,
        answer: str,
        chunks: list[RetrievedChunk],
    ) -> list[Source]:
        """Select only verified supporting sources.
        
        If the answer is an abstention, returns an empty list.
        Otherwise filters to only cited or top relevant chunks.
        """
        if not chunks or self._is_abstention(answer):
            return []

        answer_lower = answer.lower()
        explicit_cited_chunks = []
        high_relevance_chunks = []
        seen_sources = set()

        for i, chunk in enumerate(chunks, start=1):
            source_name = chunk.source.lower()

            # Check if this document name or label is explicitly cited in the answer
            is_explicitly_cited = (
                source_name in answer_lower
                or f"document {i}" in answer_lower
                or f"document {i}" in answer_lower
                or f"document[{i}]" in answer_lower
                or f"【document {i}】" in answer_lower
                or f"【document {i}】" in answer_lower
            )

            if is_explicitly_cited:
                explicit_cited_chunks.append(chunk)

            # Relevance score threshold (calibrated score >= 0.20 or raw logit >= -4.5)
            if chunk.score >= 0.20 or chunk.score >= -4.5:
                high_relevance_chunks.append(chunk)

        # Prefer explicitly cited chunks, otherwise fallback to top relevant chunks
        if explicit_cited_chunks:
            selected_chunks = explicit_cited_chunks
        elif high_relevance_chunks:
            selected_chunks = high_relevance_chunks[:2]
        else:
            selected_chunks = chunks[:2]

        sources: list[Source] = []
        for chunk in selected_chunks:
            source_key = (chunk.source, chunk.chunk_id)
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append(
                    Source(
                        document=chunk.source,
                        chunk_id=chunk.chunk_id,
                        page=chunk.metadata.get("page_number"),
                        section=chunk.metadata.get("section"),
                        text=getattr(chunk, "text", ""),
                        score=round(float(getattr(chunk, "score", 0.0)), 4),
                    )
                )

        return sources

    def build(
        self,
        llm_response: LLMResponse,
        retrieved_context: RetrievedContext,
        trace_id: str = "",
    ) -> RAGResponse:
        """Combine LLM response with source citations.

        Extracts source metadata from verified chunks and attaches them
        to the response for provenance tracking.
        """
        sources = self._select_sources(llm_response.text, retrieved_context.chunks)

        input_tokens = llm_response.input_tokens
        output_tokens = llm_response.output_tokens
        total_tokens = input_tokens + output_tokens

        # Fallback estimation if provider returned 0 tokens
        if total_tokens == 0 and llm_response.text:
            est_input = max(1, len(getattr(retrieved_context, "query", "") or "") // 4 + sum(len(c.text) for c in retrieved_context.chunks) // 4)
            est_output = max(1, len(llm_response.text) // 4)
            input_tokens = est_input
            output_tokens = est_output
            total_tokens = est_input + est_output

        cost_usd = round(((input_tokens * 0.05 + output_tokens * 0.08) / 1_000_000), 6)

        response = RAGResponse(
            query=getattr(retrieved_context, "query", ""),
            answer=llm_response.text,
            sources=sources,
            trace_id=trace_id,
            metadata={
                "model": llm_response.model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                "generation_latency_ms": round(llm_response.latency_ms, 2),
                "retrieval_latency_ms": round(retrieved_context.retrieval_latency_ms, 2),
                "embed_latency_ms": round(retrieved_context.embed_latency_ms, 2),
                "search_latency_ms": round(retrieved_context.search_latency_ms, 2),
                "rerank_latency_ms": round(retrieved_context.rerank_latency_ms, 2),
                "total_latency_ms": round(
                    llm_response.latency_ms + retrieved_context.retrieval_latency_ms, 2
                ),
                "chunks_retrieved": len(retrieved_context.chunks),
                "retrieved_chunks": [
                    {
                        "chunk_id": c.chunk_id,
                        "document_id": getattr(c, "document_id", ""),
                        "source": getattr(c, "source", ""),
                        "page": c.metadata.get("page") if hasattr(c, "metadata") and c.metadata else None,
                        "score": round(float(getattr(c, "score", 0.0)), 4),
                        "text": c.text[:300],
                    }
                    for c in retrieved_context.chunks
                ],
            },
        )

        logger.debug(
            "response_built",
            trace_id=trace_id,
            sources=len(sources),
            total_latency_ms=response.metadata["total_latency_ms"],
        )

        return response
