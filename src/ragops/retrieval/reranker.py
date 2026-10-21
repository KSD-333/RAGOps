"""Reranker — reorder retrieved results by relevance.

Flow: VectorSearchResult[] → Reranker → RankedChunk[]

The reranker's only job is answering: "Which retrieved chunks are most relevant?"
It does NOT generate answers.
"""

from __future__ import annotations

from typing import Protocol

from ragops.core.config import get_settings
from ragops.core.logging import get_logger
from ragops.core.types import VectorSearchResult

logger = get_logger(__name__)


class Reranker(Protocol):
    """Interface for rerankers."""

    def rerank(
        self,
        query: str,
        results: list[VectorSearchResult],
        top_n: int = 5,
    ) -> list[VectorSearchResult]:
        """Rerank results by relevance to the query."""
        ...


class CrossEncoderReranker:
    """Reranker using a cross-encoder model.

    Uses ms-marco-MiniLM-L-6-v2 by default — fast and accurate for re-ranking.
    """

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self._model_name = model_name or settings.retrieval.reranker_model
        self._model = None  # Lazy load
        self._mock = False

    def _load_model(self):
        """Lazy-load the cross-encoder model."""
        if self._model is None and not self._mock:
            try:
                from sentence_transformers import CrossEncoder
                logger.info("loading_reranker_model", model=self._model_name)
                try:
                    self._model = CrossEncoder(self._model_name)
                except Exception as first_err:
                    logger.warning("cross_encoder_gpu_load_failed_falling_back_to_cpu", error=str(first_err))
                    self._model = CrossEncoder(self._model_name, device="cpu")
            except ImportError:
                logger.warning(
                    "sentence_transformers_not_installed_reranker_fallback",
                    msg="sentence-transformers is not installed. Using score-based fallback.",
                )
                self._mock = True

    def rerank(
        self,
        query: str,
        results: list[VectorSearchResult],
        top_n: int = 5,
    ) -> list[VectorSearchResult]:
        """Rerank results using cross-encoder scoring."""
        if not results:
            return []

        self._load_model()
        if self._mock:
            return sorted(results, key=lambda r: r.score, reverse=True)[:top_n]

        # Create query-document pairs for the cross-encoder
        pairs = [(query, result.text) for result in results]

        try:
            scores = self._model.predict(pairs)

            # Attach reranker scores
            scored_results = []
            for result, score in zip(results, scores):
                reranked = VectorSearchResult(
                    chunk_id=result.chunk_id,
                    text=result.text,
                    score=float(score),
                    metadata={**result.metadata, "original_score": result.score},
                )
                scored_results.append(reranked)

            # Sort by reranker score descending and take top_n
            scored_results.sort(key=lambda r: r.score, reverse=True)
            top_results = scored_results[:top_n]

            logger.debug(
                "reranking_complete",
                query=query[:50],
                input_count=len(results),
                output_count=len(top_results),
            )
            return top_results

        except Exception as e:
            logger.error("reranking_failed", error=str(e))
            # Fallback: return top_n by original score
            return sorted(results, key=lambda r: r.score, reverse=True)[:top_n]


class NoOpReranker:
    """Passthrough reranker — returns top_n results by original score.

    Useful for development/testing or when reranking adds too much latency.
    """

    def rerank(
        self,
        query: str,
        results: list[VectorSearchResult],
        top_n: int = 5,
    ) -> list[VectorSearchResult]:
        """Return top_n results sorted by original score."""
        sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
        return sorted_results[:top_n]
