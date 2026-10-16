"""Unit tests for rerankers."""

from __future__ import annotations

import pytest
from ragops.core.types import VectorSearchResult
from ragops.retrieval.reranker import NoOpReranker


def test_noop_reranker_sorts_by_score():
    reranker = NoOpReranker()
    results = [
        VectorSearchResult(chunk_id="c1", text="text 1", score=0.4),
        VectorSearchResult(chunk_id="c2", text="text 2", score=0.9),
        VectorSearchResult(chunk_id="c3", text="text 3", score=0.7),
    ]

    reranked = reranker.rerank("test query", results, top_n=2)
    assert len(reranked) == 2
    assert reranked[0].chunk_id == "c2"
    assert reranked[1].chunk_id == "c3"


def test_noop_reranker_handles_empty():
    reranker = NoOpReranker()
    reranked = reranker.rerank("query", [], top_n=5)
    assert reranked == []
