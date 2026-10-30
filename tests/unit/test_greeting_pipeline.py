"""Test intent routing behavior on RAGPipeline end-to-end."""

import os
os.environ["DATABASE_URL"] = "sqlite:///data/ragops.db"

from unittest.mock import MagicMock, patch
from ragops.core.types import QueryRequest
from ragops.rag.pipeline import RAGPipeline


def test_greeting_bypasses_retrieval():
    pipeline = RAGPipeline()
    # Mock retriever to verify it is NEVER called
    pipeline._retriever = MagicMock()
    
    req = QueryRequest(query="hlo bro")
    resp = pipeline.query(req)
    
    # Retriever must not be touched
    pipeline._retriever.retrieve.assert_not_called()
    assert resp.intent == "greeting"
    assert resp.sources == []
    assert resp.answer != ""
    assert "Here are some questions you can ask me:" in resp.answer


def test_smalltalk_thanks_bypasses_retrieval():
    pipeline = RAGPipeline()
    pipeline._retriever = MagicMock()
    
    req = QueryRequest(query="thanks a lot")
    resp = pipeline.query(req)
    
    pipeline._retriever.retrieve.assert_not_called()
    assert resp.intent == "smalltalk"
    assert resp.sources == []
    assert any(w in resp.answer.lower() for w in ["welcome", "help", "glad"])


def test_identity_bypasses_retrieval():
    pipeline = RAGPipeline()
    pipeline._retriever = MagicMock()
    pipeline._retriever.get_document_inventory.return_value = [{"title": "architecture_guide.md"}]
    
    req = QueryRequest(query="who are you")
    resp = pipeline.query(req)
    
    pipeline._retriever.retrieve.assert_not_called()
    assert resp.intent == "identity"
    assert resp.sources == []
    assert "enterprise grounded knowledge assistant" in resp.answer.lower()
