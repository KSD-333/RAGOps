"""Shared pytest fixtures for RAGOps unit, integration, and E2E tests."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import pytest
from fastapi.testclient import TestClient

from ragops.api.app import create_app
from ragops.core.types import (
    CleanDocument,
    DocumentChunk,
    LLMResponse,
    RawDocument,
    RetrievedChunk,
    RetrievedContext,
)
from ragops.generation.llm import MockLLMClient


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    """Set up safe test environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("GROQ_API_KEY", "test_groq_api_key_12345")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    monkeypatch.setenv("CHROMA_COLLECTION_NAME", "test_collection")
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setenv("CHROMA_PERSIST_DIR", temp_dir)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{temp_dir}/test.db")


@pytest.fixture
def sample_raw_doc() -> RawDocument:
    from ragops.core.types import DocumentFormat
    return RawDocument(
        source="architecture_guide.md",
        format=DocumentFormat.MARKDOWN,
        content="# RAGOps Architecture\n\nRAGOps is a production-grade RAG platform.\n\nIt features evaluation and tracing.",
        metadata={"author": "Team", "version": "v1"},
    )


@pytest.fixture
def sample_clean_doc() -> CleanDocument:
    return CleanDocument(
        source="architecture_guide.md",
        content="RAGOps is a production-grade RAG platform. It features evaluation and tracing.",
        metadata={"author": "Team", "version": "v1"},
    )


@pytest.fixture
def sample_chunks() -> list[DocumentChunk]:
    return [
        DocumentChunk(
            chunk_id="chunk_001",
            document_id="doc_arch",
            source="architecture_guide.md",
            document_version="v1",
            text="RAGOps uses Sentence Transformers all-MiniLM-L6-v2 embeddings.",
            chunk_index=0,
            metadata={"source": "architecture_guide.md"},
        ),
        DocumentChunk(
            chunk_id="chunk_002",
            document_id="doc_arch",
            source="architecture_guide.md",
            document_version="v1",
            text="ChromaDB provides persistent vector search capability.",
            chunk_index=1,
            metadata={"source": "architecture_guide.md"},
        ),
    ]


@pytest.fixture
def sample_retrieved_context() -> RetrievedContext:
    chunks = [
        RetrievedChunk(
            chunk_id="chunk_001",
            document_id="doc_arch",
            source="architecture_guide.md",
            text="RAGOps uses Sentence Transformers all-MiniLM-L6-v2 embeddings.",
            score=0.92,
            metadata={"source": "architecture_guide.md"},
        ),
        RetrievedChunk(
            chunk_id="chunk_002",
            document_id="doc_arch",
            source="architecture_guide.md",
            text="ChromaDB provides persistent vector search capability.",
            score=0.88,
            metadata={"source": "architecture_guide.md"},
        ),
    ]
    return RetrievedContext(query="What is RAGOps?", chunks=chunks, retrieval_latency_ms=12.5)



@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    return MockLLMClient()


@pytest.fixture
def api_client() -> TestClient:
    app = create_app()
    return TestClient(app)
