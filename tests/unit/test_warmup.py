"""Tests for WarmupCoordinator and /health/ready probe."""

import asyncio
import os
os.environ["DATABASE_URL"] = "sqlite:///data/ragops.db"

from unittest.mock import patch

from ragops.core.warmup import WarmupCoordinator


def test_warmup_coordinator_get_state():
    coordinator = WarmupCoordinator()
    state = coordinator.get_state()
    assert state["status"] == "pending"
    assert "took_ms" in state
    assert "stages" in state


def test_warmup_coordinator_run():
    coordinator = WarmupCoordinator()
    with patch("ragops.retrieval.embeddings.SentenceTransformerEmbedding.embed_text", return_value=[0.1]*384), \
         patch("ragops.retrieval.reranker.CrossEncoderReranker.rerank", return_value=[]), \
         patch("ragops.retrieval.reranker.CrossEncoderReranker._load_model"), \
         patch("ragops.retrieval.vector_store.ChromaVectorStore.search", return_value=[]), \
         patch("ragops.retrieval.vector_store.ChromaVectorStore.count", return_value=5), \
         patch("ragops.generation.providers.router.LLMRouter.get_active_provider_name", return_value="groq"), \
         patch("ragops.generation.providers.groq_provider.GroqProvider.health_check", return_value={"reachable": True}):
        
        state = asyncio.run(coordinator.run_warmup())
        assert state["status"] == "ready"
        assert "embedder" in state["stages"]
        assert "reranker" in state["stages"]
        assert "chroma" in state["stages"]
        assert "llm" in state["stages"]
        assert state["took_ms"] >= 0.0
