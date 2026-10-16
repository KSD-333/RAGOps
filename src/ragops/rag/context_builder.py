"""Context builder — prepares retrieved chunks for the LLM prompt.

Flow: Query + RetrievedContext → ContextBuilder → PromptContext

Controls:
- Context ordering
- Maximum context length
- Deduplication
- Citation references
"""

from __future__ import annotations

from ragops.core.logging import get_logger
from ragops.core.types import PromptContext, RetrievedContext

logger = get_logger(__name__)


class ContextBuilder:
    """Build the prompt context from retrieved chunks.

    Handles deduplication, length limits, and metadata formatting
    to create the optimal context for the LLM.
    """

    def __init__(self, max_context_length: int = 4000, max_chunks: int = 5):
        self._max_context_length = max_context_length
        self._max_chunks = max_chunks

    def build(self, query: str, retrieved_context: RetrievedContext) -> PromptContext:
        """Build PromptContext from retrieved chunks.

        Deduplicates chunks, respects length limits, and formats
        source metadata for citation in the prompt.
        """
        chunks = retrieved_context.chunks[: self._max_chunks]

        # Deduplicate by text content
        seen_texts: set[str] = set()
        unique_chunks = []
        for chunk in chunks:
            text_key = chunk.text.strip()[:200]  # First 200 chars as dedup key
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                unique_chunks.append(chunk)

        # Respect maximum context length
        context_texts: list[str] = []
        source_metadata: list[dict] = []
        current_length = 0

        for chunk in unique_chunks:
            if current_length + len(chunk.text) > self._max_context_length:
                # Truncate last chunk to fit
                remaining = self._max_context_length - current_length
                if remaining > 100:  # Only include if meaningful amount left
                    context_texts.append(chunk.text[:remaining] + "...")
                    source_metadata.append({
                        "source": chunk.source,
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.document_id,
                        "score": chunk.score,
                        **{k: v for k, v in chunk.metadata.items()
                           if k in ("section", "page_number")},
                    })
                break

            context_texts.append(chunk.text)
            source_metadata.append({
                "source": chunk.source,
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "score": chunk.score,
                **{k: v for k, v in chunk.metadata.items()
                   if k in ("section", "page_number")},
            })
            current_length += len(chunk.text)

        prompt_context = PromptContext(
            query=query,
            context=context_texts,
            sources=source_metadata,
        )

        logger.debug(
            "context_built",
            chunks_used=len(context_texts),
            total_length=current_length,
        )

        return prompt_context
