"""Unit tests for RAGRetriever."""

from __future__ import annotations

import tempfile
import pytest
from ragops.retrieval.embeddings import MockEmbeddingProvider
from ragops.retrieval.reranker import NoOpReranker
from ragops.retrieval.retriever import RAGRetriever
from ragops.retrieval.vector_store import ChromaVectorStore


def test_retriever_index_and_retrieve(sample_chunks):
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = ChromaVectorStore(collection_name="test_retriever_col", persist_dir=tmp_dir)
        provider = MockEmbeddingProvider(dimension=384)
        reranker = NoOpReranker()

        retriever = RAGRetriever(
            embedding_provider=provider,
            vector_store=store,
            reranker=reranker,
            use_reranker=False,
        )

        # Index chunks
        indexed = retriever.index(sample_chunks)
        assert indexed == len(sample_chunks)
        assert retriever.document_count == len(sample_chunks)

        # Retrieve context
        context = retriever.retrieve("Sentence Transformers embeddings", top_k=2)
        assert len(context.chunks) <= 2
        assert context.query == "Sentence Transformers embeddings"
        assert context.retrieval_latency_ms >= 0
