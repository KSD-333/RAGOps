"""Retrieval evaluation metrics — Recall@K, Precision@K, MRR."""

from __future__ import annotations

from ragops.core.logging import get_logger

logger = get_logger(__name__)


def recall_at_k(
    expected_chunks: list[str],
    retrieved_chunks: list[str],
    k: int | None = None,
) -> float:
    """Calculate Recall@K — what fraction of expected chunks were retrieved.

    Recall@K = |expected ∩ retrieved[:k]| / |expected|
    """
    if not expected_chunks:
        return 1.0  # No expected chunks = perfect recall

    top_k = retrieved_chunks[:k] if k else retrieved_chunks
    hits = 0
    for exp in expected_chunks:
        if any(exp == ret or exp in ret or ret in exp for ret in top_k):
            hits += 1
    return hits / len(expected_chunks)


def precision_at_k(
    expected_chunks: list[str],
    retrieved_chunks: list[str],
    k: int | None = None,
) -> float:
    """Calculate Precision@K — what fraction of retrieved chunks are relevant.

    Precision@K = |expected ∩ retrieved[:k]| / K
    """
    top_k = retrieved_chunks[:k] if k else retrieved_chunks
    if not top_k:
        return 0.0

    hits = sum(
        1
        for ret in top_k
        if any(exp == ret or exp in ret or ret in exp for exp in expected_chunks)
    )
    return hits / len(top_k)


def mrr(
    expected_chunks: list[str],
    retrieved_chunks: list[str],
) -> float:
    """Calculate Mean Reciprocal Rank (MRR).

    MRR = 1 / rank_of_first_relevant_result
    """
    if not expected_chunks:
        return 1.0

    for i, ret in enumerate(retrieved_chunks):
        if any(exp == ret or exp in ret or ret in exp for exp in expected_chunks):
            return 1.0 / (i + 1)

    return 0.0


def context_relevance_score(
    query: str,
    retrieved_texts: list[str],
) -> float:
    """Simple context relevance heuristic based on query term overlap.

    For production use, replace with LLM-based relevance scoring.
    """
    if not retrieved_texts or not query:
        return 0.0

    query_terms = set(query.lower().split())
    scores = []

    for text in retrieved_texts:
        text_terms = set(text.lower().split())
        if not text_terms:
            scores.append(0.0)
            continue

        overlap = len(query_terms & text_terms)
        score = overlap / len(query_terms) if query_terms else 0.0
        scores.append(min(score, 1.0))

    return sum(scores) / len(scores) if scores else 0.0
