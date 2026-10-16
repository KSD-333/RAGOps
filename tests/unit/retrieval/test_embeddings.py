"""Unit tests for embedding providers."""

from __future__ import annotations

import pytest
from ragops.core.types import DocumentChunk
from ragops.retrieval.embeddings import MockEmbeddingProvider


def test_mock_embedding_provider_dimension_and_consistency():
    provider = MockEmbeddingProvider(dimension=64)
    assert provider.dimension == 64
    assert provider.model_name == "mock-minilm"

    vec1 = provider.embed_text("hello world")
    vec2 = provider.embed_text("hello world")
    assert len(vec1) == 64
    assert vec1 == vec2


def test_mock_embedding_provider_embed_chunks(sample_chunks):
    provider = MockEmbeddingProvider(dimension=32)
    embedded = provider.embed_chunks(sample_chunks)
    assert len(embedded) == len(sample_chunks)
    assert embedded[0].chunk.chunk_id == sample_chunks[0].chunk_id
    assert len(embedded[0].embedding) == 32
    assert embedded[0].embedding_model == "mock-minilm"


def test_mock_embedding_provider_embed_query():
    provider = MockEmbeddingProvider(dimension=128)
    q_emb = provider.embed_query("search query")
    assert q_emb.query == "search query"
    assert len(q_emb.vector) == 128
