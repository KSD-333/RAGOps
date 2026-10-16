"""Integration tests for ChromaVectorStore."""

from __future__ import annotations

import tempfile
import pytest
from ragops.core.types import DocumentChunk, EmbeddedChunk, QueryEmbedding
from ragops.retrieval.vector_store import ChromaVectorStore


def test_chroma_vector_store_lifecycle() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        store = ChromaVectorStore(collection_name="lifecycle_test_col", persist_dir=tmp_dir)

        # Create test embedded chunks
        dim = 16
        chunk1 = DocumentChunk(
            chunk_id="c1",
            document_id="doc1",
            source="test1.md",
            text="First chunk text about search",
            document_version="v1",
        )
        chunk2 = DocumentChunk(
            chunk_id="c2",
            document_id="doc2",
            source="test2.md",
            text="Second chunk text about storage",
            document_version="v1",
        )

        emb1 = EmbeddedChunk(chunk=chunk1, embedding=[0.1] * dim, embedding_model="mock")
        emb2 = EmbeddedChunk(chunk=chunk2, embedding=[0.9] * dim, embedding_model="mock")

        # 1. Upsert
        count = store.upsert([emb1, emb2])
        assert count == 2
        assert store.count() == 2

        # 2. Search
        query_emb = QueryEmbedding(query="search", vector=[0.12] * dim, model="mock")
        results = store.search(query_emb, top_k=2)
        assert len(results) == 2
        assert results[0].chunk_id in ["c1", "c2"]

        # 3. Delete
        deleted = store.delete(["c1"])
        assert deleted == 1
        assert store.count() == 1
