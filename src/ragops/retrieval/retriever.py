"""Retriever — orchestrates embedding + vector search + reranking.

Flow: Query → Embedding → Vector Search → Reranking → RetrievedContext

This is the main entry point for the retrieval module.
Returns a clean RetrievedContext abstraction to the RAG pipeline.
"""

from __future__ import annotations

import time
from typing import Protocol

from ragops.core.config import get_settings
from ragops.core.logging import get_logger
from ragops.core.types import (
    DocumentChunk,
    RetrievedChunk,
    RetrievedContext,
)
from ragops.retrieval.embeddings import EmbeddingProvider, SentenceTransformerEmbedding
from ragops.retrieval.reranker import CrossEncoderReranker, NoOpReranker, Reranker
from ragops.retrieval.vector_store import ChromaVectorStore, VectorStore
from ragops.retrieval.bm25 import BM25Index, is_bm25_available, reciprocal_rank_fusion

logger = get_logger(__name__)


class Retriever(Protocol):
    """Interface for retrievers — allows swapping implementations."""

    def retrieve(self, query: str, top_k: int = 10, doc_type: str | None = None) -> RetrievedContext:
        """Retrieve relevant context for a query."""
        ...

    def index(self, chunks: list[DocumentChunk]) -> int:
        """Index document chunks (embed + store). Returns count."""
        ...


class RAGRetriever:
    """Production retriever: embed → search → rerank → return context.

    Implements the full retrieval flow with configurable components.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
        reranker: Reranker | None = None,
        use_reranker: bool = True,
    ):
        settings = get_settings()

        self._embeddings = embedding_provider or SentenceTransformerEmbedding()
        self._vector_store = vector_store or ChromaVectorStore()

        if use_reranker:
            self._reranker = reranker or CrossEncoderReranker()
        else:
            self._reranker = NoOpReranker()

        self._top_k = settings.retrieval.top_k
        self._rerank_top_n = settings.retrieval.rerank_top_n
        self._hybrid_search = settings.retrieval.hybrid_search
        self._bm25_index = BM25Index()
        self._bm25_initialized = False

    def _ensure_bm25_ready(self) -> None:
        """Lazily build BM25 index from vector store chunks if hybrid search is enabled."""
        if self._bm25_initialized or not self._hybrid_search:
            return
        try:
            if hasattr(self._vector_store, "get_all_documents"):
                docs_data = self._vector_store.get_all_documents()
                if docs_data.get("ids"):
                    self._bm25_index.build_from_chunks(
                        docs_data["ids"],
                        docs_data["documents"],
                        docs_data["metadatas"],
                    )
            self._bm25_initialized = True
        except Exception as e:
            logger.warning("bm25_index_init_failed_falling_back_to_dense", error=str(e))
            self._bm25_initialized = False

    def index(self, chunks: list[DocumentChunk]) -> int:
        """Embed and store document chunks in the vector store.

        Flow: DocumentChunk[] → Embedding → VectorStore
        """
        if not chunks:
            return 0

        logger.info("indexing_chunks", count=len(chunks))

        # Embed all chunks
        embedded_chunks = self._embeddings.embed_chunks(chunks)

        # Store in vector database
        count = self._vector_store.upsert(embedded_chunks)

        logger.info("indexing_complete", indexed=count)
        return count

    index_chunks = index

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        doc_type: str | None = None,
    ) -> RetrievedContext:
        """Full retrieval pipeline: embed query → search (dense or hybrid BM25+RRF) → rerank.

        Returns a RetrievedContext with the most relevant chunks.
        """
        start_time = time.perf_counter()
        effective_top_k = top_k or self._top_k

        logger.debug("retrieving", query=query[:80], top_k=effective_top_k, doc_type=doc_type)

        # 1. Embed the query
        t_embed_start = time.perf_counter()
        query_embedding = self._embeddings.embed_query(query)
        embed_ms = (time.perf_counter() - t_embed_start) * 1000

        # 2. Dense search (fetch candidate pool)
        t_search_start = time.perf_counter()
        candidate_k = max(effective_top_k * 2, 10)
        dense_results = self._vector_store.search(
            query_embedding, top_k=candidate_k, doc_type=doc_type
        )

        # 3. Optional Hybrid Search: BM25 + Reciprocal Rank Fusion
        candidate_pool = dense_results
        if self._hybrid_search:
            try:
                self._ensure_bm25_ready()
                if self._bm25_index.is_ready:
                    bm25_results = self._bm25_index.search(
                        query=query, top_k=candidate_k, doc_type=doc_type
                    )
                    candidate_pool = reciprocal_rank_fusion(
                        dense_results=dense_results,
                        bm25_results=bm25_results,
                        k=60,
                        top_n=candidate_k,
                    )
            except Exception as hybrid_err:
                logger.warning("hybrid_fusion_failed_fallback_to_dense", error=str(hybrid_err))
                candidate_pool = dense_results

        search_ms = (time.perf_counter() - t_search_start) * 1000

        if not candidate_pool:
            elapsed = (time.perf_counter() - start_time) * 1000
            return RetrievedContext(
                query=query,
                chunks=[],
                retrieval_latency_ms=elapsed,
                embed_latency_ms=round(embed_ms, 2),
                search_latency_ms=round(search_ms, 2),
                rerank_latency_ms=0.0,
            )

        # 4. Cross-Encoder Rerank
        t_rerank_start = time.perf_counter()
        rerank_top_n = min(effective_top_k, self._rerank_top_n)
        reranked = self._reranker.rerank(
            query=query,
            results=candidate_pool,
            top_n=rerank_top_n,
        )
        rerank_ms = (time.perf_counter() - t_rerank_start) * 1000

        # 4. Convert to RetrievedChunk
        chunks = [
            RetrievedChunk(
                chunk_id=result.chunk_id,
                document_id=result.metadata.get("document_id", ""),
                text=result.text,
                score=result.score,
                source=result.metadata.get("source", ""),
                metadata=result.metadata,
            )
            for result in reranked
        ]

        elapsed = (time.perf_counter() - start_time) * 1000

        logger.info(
            "retrieval_complete",
            query=query[:50],
            results=len(chunks),
            latency_ms=round(elapsed, 2),
            embed_ms=round(embed_ms, 2),
            search_ms=round(search_ms, 2),
            rerank_ms=round(rerank_ms, 2),
        )

        return RetrievedContext(
            query=query,
            chunks=chunks,
            retrieval_latency_ms=elapsed,
            embed_latency_ms=round(embed_ms, 2),
            search_latency_ms=round(search_ms, 2),
            rerank_latency_ms=round(rerank_ms, 2),
        )

    @property
    def document_count(self) -> int:
        """Number of chunks in the vector store."""
        return self._vector_store.count()

    def get_document_inventory(self) -> list[str]:
        """Get sorted list of all unique document sources indexed in the vector store."""
        if hasattr(self._vector_store, "_collection") and self._vector_store._collection is not None:
            try:
                from pathlib import Path
                data = self._vector_store._collection.get(include=["metadatas"])
                sources = set()
                for m in data.get("metadatas", []):
                    if m and "source" in m:
                        sources.add(Path(m["source"]).name)
                return sorted(sources)
            except Exception as e:
                logger.warning("failed_to_fetch_collection_inventory", error=str(e))
        return []

    def get_document_chunk_counts(self) -> dict[str, int]:
        """Get mapping of document filename -> count of chunks in vector store."""
        counts: dict[str, int] = {}
        if hasattr(self._vector_store, "_collection") and self._vector_store._collection is not None:
            try:
                from pathlib import Path
                from collections import Counter
                data = self._vector_store._collection.get(include=["metadatas"])
                tally = Counter()
                for m in data.get("metadatas", []):
                    if m and "source" in m:
                        tally[Path(m["source"]).name] += 1
                return dict(tally)
            except Exception as e:
                logger.warning("failed_to_fetch_collection_chunk_counts", error=str(e))
        return counts

    def delete_document_chunks(self, source: str) -> int:
        """Delete all chunks belonging to a document from ChromaDB vector store.
        
        Matches exact source, basename, or path variants.
        """
        deleted = 0
        if hasattr(self._vector_store, "_collection") and self._vector_store._collection is not None:
            try:
                from pathlib import Path
                target_name = Path(source).name.lower()
                data = self._vector_store._collection.get(include=["metadatas"])
                ids_to_delete = []
                for chunk_id, m in zip(data.get("ids", []), data.get("metadatas", [])):
                    if m and "source" in m:
                        src_name = Path(m["source"]).name.lower()
                        if src_name == target_name or m["source"] == source:
                            ids_to_delete.append(chunk_id)
                if ids_to_delete:
                    self._vector_store._collection.delete(ids=ids_to_delete)
                    deleted = len(ids_to_delete)
                    logger.info("deleted_chunks_for_document", source=source, count=deleted)
            except Exception as e:
                logger.warning("failed_to_delete_document_chunks", source=source, error=str(e))
        return deleted

