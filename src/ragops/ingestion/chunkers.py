"""Document chunkers — split clean documents into chunks with metadata.

Flow: CleanDocument → Chunker → DocumentChunk[]

Each chunk preserves enough metadata to answer "Where did this come from?"
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from ragops.core.logging import get_logger
from ragops.core.types import CleanDocument, DocumentChunk

logger = get_logger(__name__)


class BaseChunker(ABC):
    """Interface for document chunkers."""

    @abstractmethod
    def chunk(self, document: CleanDocument, document_id: str, version: str = "v1") -> list[DocumentChunk]:
        """Split a clean document into chunks."""
        ...


class RecursiveChunker(BaseChunker):
    """Recursive text splitter that respects natural boundaries.

    Splits by paragraphs first, then sentences, then words,
    ensuring each chunk stays within the size limit.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._separators = ["\n\n\n", "\n\n", "\n", ". ", " "]

    def chunk(
        self, document: CleanDocument, document_id: str, version: str = "v1"
    ) -> list[DocumentChunk]:
        """Split document text into overlapping chunks."""
        logger.debug("chunking_document", source=document.source, doc_id=document_id)

        texts = self._split_text(document.content, self._separators)
        chunks: list[DocumentChunk] = []

        for i, text in enumerate(texts):
            chunk = DocumentChunk(
                chunk_id=f"{document_id}_chunk_{i:04d}",
                document_id=document_id,
                source=document.source,
                text=text,
                chunk_index=i,
                document_version=version,
                metadata={
                    **document.metadata,
                    "chunk_index": i,
                    "chunk_size": len(text),
                    "total_chunks": len(texts),
                },
            )
            chunks.append(chunk)

        logger.info("chunking_complete", source=document.source, chunks=len(chunks))
        return chunks

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using a hierarchy of separators."""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        # Try each separator in order
        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                return self._merge_parts(parts, sep)

        # Last resort: hard split by character count
        return self._hard_split(text)

    def _merge_parts(self, parts: list[str], separator: str) -> list[str]:
        """Merge small parts together while respecting chunk_size."""
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_length = 0

        for part in parts:
            part = part.strip()
            if not part:
                continue

            part_length = len(part)

            if current_length + part_length + len(separator) > self.chunk_size and current_chunk:
                # Emit current chunk
                chunk_text = separator.join(current_chunk).strip()
                if chunk_text:
                    chunks.append(chunk_text)

                # Handle overlap — keep last portion of current chunk
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_text = separator.join(current_chunk)
                    overlap_start = max(0, len(overlap_text) - self.chunk_overlap)
                    overlap = overlap_text[overlap_start:].strip()
                    current_chunk = [overlap] if overlap else []
                    current_length = len(overlap) if overlap else 0
                else:
                    current_chunk = []
                    current_length = 0

            # If single part exceeds chunk_size, recursively split it
            if part_length > self.chunk_size:
                if current_chunk:
                    chunk_text = separator.join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(chunk_text)
                    current_chunk = []
                    current_length = 0

                sub_chunks = self._hard_split(part)
                chunks.extend(sub_chunks)
            else:
                current_chunk.append(part)
                current_length += part_length + len(separator)

        # Emit remaining
        if current_chunk:
            chunk_text = separator.join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)

        return chunks

    def _hard_split(self, text: str) -> list[str]:
        """Split text by raw character count as last resort."""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i : i + self.chunk_size].strip()
            if chunk:
                chunks.append(chunk)
        return chunks
