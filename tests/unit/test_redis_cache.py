"""Unit tests for RedisSemanticCache and QueryIntelligenceEngine Redis integration."""

import pytest
from unittest.mock import MagicMock, patch

from ragops.core.types import RAGResponse, Source
from ragops.rag.query_intelligence import QueryIntent, QueryIntelligenceEngine, is_abstention_text
from ragops.storage.redis_cache import RedisSemanticCache, cosine_similarity


def test_cosine_similarity():
    """Verify cosine similarity calculation."""
    # Identical vectors
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v2), 0.001) == 1.0

    # Orthogonal vectors
    v3 = [0.0, 1.0, 0.0]
    assert pytest.approx(cosine_similarity(v1, v3), 0.001) == 0.0

    # High similarity (>0.95)
    v4 = [0.99, 0.05, 0.0]
    sim = cosine_similarity(v1, v4)
    assert sim >= 0.95


def test_abstention_detection():
    """Verify abstentions are detected and never cached."""
    assert is_abstention_text("The documents do not contain any information on this topic.")
    assert is_abstention_text("I am sorry, but there is insufficient information in the context.")
    assert is_abstention_text("Cannot answer this question based on provided context.")
    assert not is_abstention_text("Under the POSH policy, complaints must be submitted within 3 months.")


def test_redis_cache_exact_and_semantic_flow():
    """Verify storing in Redis and retrieving via exact and semantic match."""
    cache = RedisSemanticCache.get_instance()
    if not cache.is_available():
        pytest.skip("Redis / Memurai is not currently running.")

    company = "TestCorp"
    cache_key = "test_posh_123"
    scope = "document_specific"
    intent = "policy_lookup"
    target_entity = "policy"
    query = "What is the POSH complaint window?"
    embedding = [0.1] * 384
    answer_text = "Complaints must be submitted to the Internal Committee within 3 months."

    # Clear test key
    cache.delete_entry(cache_key, company=company, scope=scope, intent=intent)

    # Store
    stored = cache.store_cache(
        company=company,
        cache_key=cache_key,
        scope=scope,
        intent=intent,
        target_entity=target_entity,
        query=query,
        query_vector=embedding,
        response_dict={
            "answer": answer_text,
            "citations": [{"document": "POSH_Policy.pdf", "page": 4}],
            "chunks_sent": [],
            "model": "groq",
        },
    )
    assert stored is True

    # 1. Exact Hit
    exact = cache.get_exact(company, cache_key)
    assert exact is not None
    assert exact["answer"] == answer_text
    assert len(exact["citations"]) == 1

    # 2. Semantic Hit (90% - 95% similarity)
    similar_vector = [0.1005] * 384  # Extremely close vector (>99% similarity)
    sem_hit, sim = cache.search_semantic(
        company=company,
        scope=scope,
        intent=intent,
        query_vector=similar_vector,
        threshold=0.90,
    )
    assert sem_hit is not None
    assert sim >= 0.95
    assert sem_hit["answer"] == answer_text

    # 3. Semantic Miss (orthogonal / different vector)
    unrelated_vector = [-0.1 if i % 2 == 0 else 0.1 for i in range(384)]
    sem_miss, sim_low = cache.search_semantic(
        company=company,
        scope=scope,
        intent=intent,
        query_vector=unrelated_vector,
        threshold=0.92,
    )
    assert sem_miss is None
    assert sim_low < 0.90

    # Clean up
    cache.delete_entry(cache_key, company=company, scope=scope, intent=intent)


class DummyEmbedding:
    def embed_query(self, text):
        return [0.1] * 384


def test_query_intelligence_redis_integration():
    """Verify QueryIntelligenceEngine uses Redis for exact and semantic hits."""
    engine = QueryIntelligenceEngine(embedding_provider=DummyEmbedding())
    intent = QueryIntent(
        intent_type="policy_lookup",
        scope="document_specific",
        target_entity="policy",
        is_rewritten=False,
        original_query="What is the POSH complaint window?",
        rewritten_query="What is the POSH complaint window?",
    )

    rag_response = RAGResponse(
        query="What is the POSH complaint window?",
        answer="Under the corporate POSH policy, complaints must be submitted within 90 days.",
        sources=[Source(chunk_id="chk_01", document="POSH.pdf", score=0.95)],
        trace_id="test_trace",
        metadata={"model": "groq"},
    )

    # Store in cache
    engine.store_in_cache(
        query="What is the POSH complaint window?",
        intent=intent,
        response=rag_response,
    )

    # Check cache hit (exact match)
    cached = engine.check_cache("What is the POSH complaint window?", intent)
    assert cached is not None
    assert cached.metadata["cache_hit"] is True
    assert "redis" in cached.metadata.get("cache_tier", "") or "memory" in cached.metadata.get("cache_tier", "")
    assert "90 days" in cached.answer


def test_abstention_never_cached():
    """Ensure abstention responses are rejected from being saved to cache."""
    engine = QueryIntelligenceEngine(embedding_provider=DummyEmbedding())
    intent = QueryIntent(
        intent_type="general",
        scope="general",
        target_entity="all",
        is_rewritten=False,
        original_query="Random query",
        rewritten_query="Random query",
    )

    abstention_response = RAGResponse(
        query="Random query",
        answer="I am sorry, the documents provided do not contain information on this topic.",
        sources=[],
        trace_id="test_abstain",
        metadata={"model": "groq"},
    )

    # Storing abstention should be a no-op
    engine.store_in_cache(
        query="Random query",
        intent=intent,
        response=abstention_response,
    )

    # Cache check should return None
    result = engine.check_cache("Random query", intent)
    assert result is None


def test_ensure_redis_running():
    """Verify ensure_redis_running detects running instance or cleanly falls back."""
    from ragops.storage.redis_cache import ensure_redis_running
    result = ensure_redis_running(timeout_secs=0.5)
    assert isinstance(result, bool)

