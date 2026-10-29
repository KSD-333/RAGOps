"""BM25 sparse search and Reciprocal Rank Fusion (RRF) for hybrid retrieval.

Integrates with ChromaDB vector search to combine keyword lexical matching
with semantic dense embeddings.
"""

from __future__ import annotations

import re
from typing import Any
from ragops.core.logging import get_logger
from ragops.core.types import VectorSearchResult

logger = get_logger(__name__)

# Check rank_bm25 availability
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    BM25Okapi = None
    BM25_AVAILABLE = False


def is_bm25_available() -> bool:
    """Return whether the rank_bm25 library is installed."""
    return BM25_AVAILABLE


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words/terms for BM25 indexing."""
    if not text:
        return []
    return re.findall(r"\w+", text.lower())


class BM25Index:
    """In-memory BM25 index built over corpus chunks."""

    def __init__(self) -> None:
        self._bm25: Any | None = None
        self._chunk_ids: list[str] = []
        self._documents: list[str] = []
        self._metadatas: list[dict[str, Any]] = []

    @property
    def is_ready(self) -> bool:
        return self._bm25 is not None and len(self._documents) > 0

    def build_from_chunks(
        self,
        chunk_ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Build or refresh the BM25 index with current corpus chunks."""
        if not BM25_AVAILABLE or not documents:
            self._bm25 = None
            self._chunk_ids = []
            self._documents = []
            self._metadatas = []
            return

        try:
            tokenized_corpus = [tokenize(doc) for doc in documents]
            self._bm25 = BM25Okapi(tokenized_corpus)
            self._chunk_ids = list(chunk_ids)
            self._documents = list(documents)
            self._metadatas = list(metadatas)
            logger.info("bm25_index_built", chunk_count=len(documents))
        except Exception as e:
            logger.warning("bm25_build_failed", error=str(e))
            self._bm25 = None

    def search(
        self,
        query: str,
        top_k: int = 20,
        doc_type: str | None = None,
    ) -> list[VectorSearchResult]:
        """Perform lexical BM25 search with optional doc_type filtering."""
        if not self.is_ready:
            return []

        tokens = tokenize(query)
        if not tokens:
            return []

        try:
            scores = self._bm25.get_scores(tokens)
            indexed_scores = [(idx, score) for idx, score in enumerate(scores) if score > 0]
            indexed_scores.sort(key=lambda x: x[1], reverse=True)

            target_doc_type = doc_type.strip().lower() if doc_type else None
            results: list[VectorSearchResult] = []

            for idx, score in indexed_scores:
                meta = self._metadatas[idx] if idx < len(self._metadatas) else {}
                if target_doc_type:
                    chunk_type = str(meta.get("doc_type", "")).strip().lower()
                    if chunk_type != target_doc_type:
                        continue

                results.append(
                    VectorSearchResult(
                        chunk_id=self._chunk_ids[idx],
                        text=self._documents[idx],
                        score=float(score),
                        metadata=meta,
                    )
                )
                if len(results) >= top_k:
                    break

            return results
        except Exception as e:
            logger.warning("bm25_search_failed", error=str(e))
            return []


def reciprocal_rank_fusion(
    dense_results: list[VectorSearchResult],
    bm25_results: list[VectorSearchResult],
    k: int = 60,
    top_n: int = 20,
) -> list[VectorSearchResult]:
    """Merge dense vector search results and sparse BM25 results using Reciprocal Rank Fusion.

    Score formula: RRF(d) = sum(1 / (k + rank_i(d)))
    """
    if not bm25_results:
        return dense_results[:top_n]
    if not dense_results:
        return bm25_results[:top_n]

    scores: dict[str, float] = {}
    chunk_map: dict[str, VectorSearchResult] = {}

    # 1. Score dense results (1-based rank)
    for rank, item in enumerate(dense_results, start=1):
        chunk_id = item.chunk_id
        chunk_map[chunk_id] = item
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

    # 2. Score BM25 results (1-based rank)
    for rank, item in enumerate(bm25_results, start=1):
        chunk_id = item.chunk_id
        if chunk_id not in chunk_map:
            chunk_map[chunk_id] = item
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

    # 3. Sort by fused score descending
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    fused_results: list[VectorSearchResult] = []
    for chunk_id, fused_score in sorted_items[:top_n]:
        orig = chunk_map[chunk_id]
        fused_results.append(
            VectorSearchResult(
                chunk_id=orig.chunk_id,
                text=orig.text,
                score=round(fused_score, 6),
                metadata=orig.metadata,
            )
        )

    return fused_results

