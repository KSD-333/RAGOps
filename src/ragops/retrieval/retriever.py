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
    EmbeddedChunk,
    RetrievedChunk,
    RetrievedContext,
    VectorSearchResult,
)
from ragops.retrieval.embeddings import EmbeddingProvider, SentenceTransformerEmbedding
from ragops.retrieval.reranker import CrossEncoderReranker, NoOpReranker, Reranker
from ragops.retrieval.vector_store import ChromaVectorStore, VectorStore

logger = get_logger(__name__)


class Retriever(Protocol):
    """Interface for retrievers — allows swapping implementations."""

    def retrieve(self, query: str, top_k: int = 10) -> RetrievedContext:
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

    def retrieve(self, query: str, top_k: int | None = None) -> RetrievedContext:
        """Full retrieval pipeline: embed query → search → rerank.

        Returns a RetrievedContext with the most relevant chunks.
        """
        start_time = time.perf_counter()
        effective_top_k = top_k or self._top_k

        logger.debug("retrieving", query=query[:80], top_k=effective_top_k)

        # 1. Embed the query
        query_embedding = self._embeddings.embed_query(query)

        # 2. Vector search
        search_results = self._vector_store.search(query_embedding, top_k=effective_top_k)

        if not search_results:
            elapsed = (time.perf_counter() - start_time) * 1000
            return RetrievedContext(
                query=query,
                chunks=[],
                retrieval_latency_ms=elapsed,
            )

        # 3. Rerank
        reranked = self._reranker.rerank(
            query=query,
            results=search_results,
            top_n=self._rerank_top_n,
        )

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
        )

        return RetrievedContext(
            query=query,
            chunks=chunks,
            retrieval_latency_ms=elapsed,
        )

    @property
    def document_count(self) -> int:
        """Number of chunks in the vector store."""
        return self._vector_store.count()
