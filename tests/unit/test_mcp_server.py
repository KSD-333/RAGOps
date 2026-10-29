"""Unit tests for RAGOps FastMCP server and tools."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

os.environ["DATABASE_URL"] = "sqlite:///data/ragops.db"

from ragops.core.types import RAGResponse, Source
from ragops.mcp_server import check_mcp_available, create_mcp_server, run_stdio


@pytest.fixture
def mcp_tools():
    """Retrieve the registered tools from the MCP server instance."""
    server = create_mcp_server()
    if hasattr(server, "_tool_manager") and hasattr(server._tool_manager, "_tools"):
        return {name: tool.fn for name, tool in server._tool_manager._tools.items()}
    elif hasattr(server, "_tools"):
        return {name: tool.fn if hasattr(tool, "fn") else tool for name, tool in server._tools.items()}
    raise RuntimeError("Could not find tool registry on MCP server")


def test_mcp_available():
    assert check_mcp_available() is True


def test_search_knowledge_base_validation(mcp_tools):
    search_fn = mcp_tools["search_knowledge_base"]

    # Empty query
    res = search_fn("")
    assert res["status"] == "error"
    assert "empty" in res["error"].lower()

    # Too long query (>1000)
    long_q = "a" * 1005
    res = search_fn(long_q)
    assert res["status"] == "error"
    assert "maximum" in res["error"].lower() or "1000" in res["error"]


def test_search_knowledge_base_success(mcp_tools):
    search_fn = mcp_tools["search_knowledge_base"]

    mock_resp = RAGResponse(
        query="What is RAGOps?",
        answer="RAGOps is a production RAG platform.",
        sources=[
            Source(
                document="architecture_guide.md",
                chunk_id="chunk_1",
                text="RAGOps architecture overview",
                score=0.95,
            )
        ],
        metadata={
            "provider_used": "groq",
            "fallback_used": False,
            "cache_hit": False,
            "total_latency_ms": 120.5,
        },
    )

    with patch("ragops.rag.pipeline.RAGPipeline.query", return_value=mock_resp):
        res = search_fn("What is RAGOps?", top_k=3)
        assert res["status"] == "success"
        assert res["answer"] == "RAGOps is a production RAG platform."
        assert res["provider_used"] == "groq"
        assert res["citations"][0]["document_name"] == "architecture_guide.md"
        assert res["latency_ms"] == 120.5


def test_list_documents(mcp_tools):
    list_fn = mcp_tools["list_documents"]

    with patch("ragops.retrieval.retriever.RAGRetriever.get_document_inventory", return_value=["guide.md", "handbook.pdf"]):
        with patch("ragops.retrieval.retriever.RAGRetriever.get_document_chunk_counts", return_value={"guide.md": 5, "handbook.pdf": 10}):
            with patch("ragops.retrieval.retriever.RAGRetriever.document_count", 15):
                res = list_fn()
                assert res["status"] == "success"
                assert res["total_documents"] == 2
                assert res["total_chunks"] == 15
                assert len(res["documents"]) == 2
                assert res["documents"][0]["document_name"] == "guide.md"
                assert res["documents"][0]["chunks"] == 5


def test_ingest_document_path_traversal_blocked(mcp_tools):
    ingest_fn = mcp_tools["ingest_document"]

    # Traversal attempting to escape data/raw
    res = ingest_fn("../../etc/passwd")
    assert res["status"] == "error"
    assert "Path traversal detected" in res["error"] or "Access denied" in res["error"]

    res2 = ingest_fn("C:/Windows/System32/calc.exe")
    assert res2["status"] == "error"
    assert "Path traversal detected" in res2["error"] or "Access denied" in res2["error"]


def test_ingest_document_not_found(mcp_tools):
    ingest_fn = mcp_tools["ingest_document"]

    res = ingest_fn("non_existent_file_12345.pdf")
    assert res["status"] == "error"
    assert "not found" in res["error"].lower()


def test_get_trace(mcp_tools):
    trace_fn = mcp_tools["get_trace"]

    # Invalid empty trace_id
    res = trace_fn("")
    assert res["status"] == "error"

    # Non-existent trace
    with patch("ragops.storage.repositories.ChatRepository.get_trace", return_value=None):
        res = trace_fn("trace_non_existent")
        assert res["status"] == "not_found"

    # Existing trace
    mock_trace = {
        "trace_id": "trace_valid_123",
        "query": "Hello",
        "answer": "Hi there",
        "provider": "ollama",
        "total_latency_ms": 50.0,
    }
    with patch("ragops.storage.repositories.ChatRepository.get_trace", return_value=mock_trace):
        res = trace_fn("trace_valid_123")
        assert res["status"] == "success"
        assert res["trace"]["trace_id"] == "trace_valid_123"
        assert res["trace"]["provider"] == "ollama"


def test_cache_stats(mcp_tools):
    cache_fn = mcp_tools["cache_stats"]

    mock_stats = {
        "redis_connected": True,
        "total_cached_entries": 42,
        "exact_hits": 10,
        "semantic_hits": 5,
    }
    with patch("ragops.storage.redis_cache.RedisSemanticCache.get_stats", return_value=mock_stats):
        res = cache_fn()
        assert res["status"] == "success"
        assert res["stats"]["total_cached_entries"] == 42
        assert res["stats"]["redis_connected"] is True
