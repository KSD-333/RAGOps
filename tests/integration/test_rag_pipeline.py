"""Integration tests for the complete RAGPipeline."""

from __future__ import annotations

import tempfile
import pytest
from ragops.core.types import DocumentChunk, QueryRequest
from ragops.generation.llm import MockLLMClient
from ragops.rag.pipeline import RAGPipeline
from ragops.retrieval.embeddings import MockEmbeddingProvider
from ragops.retrieval.reranker import NoOpReranker
from ragops.retrieval.retriever import RAGRetriever
from ragops.retrieval.vector_store import ChromaVectorStore


def test_rag_pipeline_end_to_end_query():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Build components
        store = ChromaVectorStore(collection_name="pipeline_test_col", persist_dir=tmp_dir)
        provider = MockEmbeddingProvider(dimension=64)
        retriever = RAGRetriever(
            embedding_provider=provider,
            vector_store=store,
            reranker=NoOpReranker(),
            use_reranker=False,
        )

        # Index knowledge chunk
        chunk = DocumentChunk(
            chunk_id="chunk_arch_1",
            document_id="doc_arch",
            source="architecture.md",
            text="RAGOps provides evaluation, observability, and quality gates.",
            document_version="v1",
        )
        retriever.index([chunk])

        # Initialize pipeline with MockLLMClient
        pipeline = RAGPipeline(
            retriever=retriever,
            llm_client=MockLLMClient(),
        )

        request = QueryRequest(query="What does RAGOps provide?", top_k=1)
        response = pipeline.query(request)

        assert response.answer is not None
        assert len(response.answer) > 0
        assert len(response.sources) >= 1
        assert response.sources[0].document == "architecture.md"
        assert response.trace_id.startswith("trace_")
        assert "model" in response.metadata
