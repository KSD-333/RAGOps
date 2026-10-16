"""Unit tests for DocumentChunkers."""

from __future__ import annotations

import pytest
from ragops.core.types import CleanDocument
from ragops.ingestion.chunkers import RecursiveChunker


def test_recursive_chunker_splits_content():
    chunker = RecursiveChunker(chunk_size=100, chunk_overlap=20)
    doc = CleanDocument(
        source="test.md",
        content="Paragraph one contains several sentences that talk about architecture. "
                "Paragraph two continues the topic with further detailed information on embeddings and chunking.",
        metadata={"version": "v1"},
    )
    chunks = chunker.chunk(doc, document_id="doc_test")
    assert len(chunks) > 1
    assert chunks[0].document_id == "doc_test"
    assert chunks[0].source == "test.md"
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


def test_recursive_chunker_handles_short_content():
    chunker = RecursiveChunker(chunk_size=500, chunk_overlap=50)
    doc = CleanDocument(
        source="short.md",
        content="Short piece of text.",
        metadata={},
    )
    chunks = chunker.chunk(doc, document_id="doc_short")
    assert len(chunks) == 1
    assert chunks[0].text == "Short piece of text."
    assert chunks[0].chunk_id.startswith("doc_short_chunk_")
