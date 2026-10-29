"""Unit tests for BM25 sparse search, Reciprocal Rank Fusion (RRF), and doc_type filtering."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest

os.environ["DATABASE_URL"] = "sqlite:///data/ragops.db"

from ragops.core.types import QueryEmbedding, RetrievedContext, VectorSearchResult
from ragops.retrieval.bm25 import BM25Index, reciprocal_rank_fusion, tokenize
from ragops.retrieval.retriever import RAGRetriever


def test_tokenize():
    assert tokenize("Hello World! This is a TEST.") == ["hello", "world", "this", "is", "a", "test"]
    assert tokenize("") == []
    assert tokenize(None) == []


def test_bm25_index_and_doc_type_filter():
    index = BM25Index()
    assert index.is_ready is False

    chunk_ids = ["c1", "c2", "c3"]
    documents = [
        "The security handbook mandates multi-factor authentication for all employees.",
        "Code review guidelines and pull request instructions for developers.",
        "Corporate vacation and leave policy details for employees.",
    ]
    metadatas = [
        {"doc_type": "manual", "source": "security.md"},
        {"doc_type": "code", "source": "guidelines.md"},
        {"doc_type": "policy", "source": "leave.md"},
    ]

    index.build_from_chunks(chunk_ids, documents, metadatas)
    assert index.is_ready is True

    # General search
    results = index.search("authentication employees", top_k=5)
    assert len(results) > 0
    assert results[0].chunk_id == "c1"

    # Search with doc_type filter
    policy_results = index.search("employees", top_k=5, doc_type="policy")
    assert len(policy_results) == 1
    assert policy_results[0].chunk_id == "c3"
    assert policy_results[0].metadata["doc_type"] == "policy"

    # Search with non-matching doc_type
    none_results = index.search("employees", top_k=5, doc_type="governance")
    assert len(none_results) == 0


def test_reciprocal_rank_fusion():
    dense_res = [
        VectorSearchResult(chunk_id="doc_a", text="Alpha text", score=0.9, metadata={"source": "a.md"}),
        VectorSearchResult(chunk_id="doc_b", text="Beta text", score=0.8, metadata={"source": "b.md"}),
        VectorSearchResult(chunk_id="doc_c", text="Gamma text", score=0.7, metadata={"source": "c.md"}),
    ]

    bm25_res = [
        VectorSearchResult(chunk_id="doc_b", text="Beta text", score=12.5, metadata={"source": "b.md"}),
        VectorSearchResult(chunk_id="doc_d", text="Delta text", score=10.2, metadata={"source": "d.md"}),
        VectorSearchResult(chunk_id="doc_a", text="Alpha text", score=8.1, metadata={"source": "a.md"}),
    ]

    fused = reciprocal_rank_fusion(dense_results=dense_res, bm25_results=bm25_res, k=60, top_n=4)

    # doc_a rank in dense = 1, in bm25 = 3 -> RRF = 1/61 + 1/63 ≈ 0.01639 + 0.01587 = 0.03226
    # doc_b rank in dense = 2, in bm25 = 1 -> RRF = 1/62 + 1/61 ≈ 0.01613 + 0.01639 = 0.03252
    # doc_b should be rank 1!
    assert fused[0].chunk_id == "doc_b"
    assert fused[1].chunk_id == "doc_a"
    assert len(fused) == 4

    # Graceful fallback when one list is empty
    assert reciprocal_rank_fusion([], bm25_res) == bm25_res
    assert reciprocal_rank_fusion(dense_res, []) == dense_res


def test_retriever_hybrid_and_doc_type():
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query.return_value = QueryEmbedding(
        query="test", vector=[0.1, 0.2], model="all-MiniLM-L6-v2"
    )

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [
        VectorSearchResult(
            chunk_id="chunk_1",
            text="Policy context",
            score=0.85,
            metadata={"source": "policy.md", "doc_type": "policy"},
        )
    ]
    mock_vector_store.get_all_documents.return_value = {
        "ids": ["chunk_1"],
        "documents": ["Policy context"],
        "metadatas": [{"source": "policy.md", "doc_type": "policy"}],
    }

    mock_reranker = MagicMock()
    mock_reranker.rerank.side_effect = lambda query, results, top_n: results[:top_n]

    retriever = RAGRetriever(
        embedding_provider=mock_embeddings,
        vector_store=mock_vector_store,
        reranker=mock_reranker,
    )
    retriever._hybrid_search = True

    ctx = retriever.retrieve("leave policy", top_k=5, doc_type="Policy")

    assert len(ctx.chunks) == 1
    assert ctx.chunks[0].chunk_id == "chunk_1"
    assert ctx.chunks[0].metadata["doc_type"] == "policy"
    mock_vector_store.search.assert_called_once()
    assert mock_vector_store.search.call_args[1]["doc_type"] == "Policy"
