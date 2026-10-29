"""Vector store — interface + ChromaDB implementation.

Flow:
  - Upsert: EmbeddedChunk → VectorStore.upsert() → persisted
  - Search: QueryEmbedding → VectorStore.search() → VectorSearchResult[]

The implementation hides whether you're using ChromaDB, Qdrant, FAISS, or pgvector.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import numpy as np


from ragops.core.config import get_settings
from ragops.core.exceptions import VectorStoreError
from ragops.core.logging import get_logger
from ragops.core.types import (
    EmbeddedChunk,
    QueryEmbedding,
    VectorSearchResult,
)

logger = get_logger(__name__)


class VectorStore(Protocol):
    """Interface for vector stores — swap implementations without changing RAG pipeline."""

    def upsert(self, chunks: list[EmbeddedChunk]) -> int:
        """Upsert embedded chunks into the store. Returns count of upserted items."""
        ...

    def search(
        self,
        query_embedding: QueryEmbedding,
        top_k: int = 10,
        where: dict[str, Any] | None = None,
        doc_type: str | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar chunks. Returns ranked results."""
        ...

    def delete(self, chunk_ids: list[str]) -> int:
        """Delete chunks by IDs. Returns count of deleted items."""
        ...

    def count(self) -> int:
        """Return total number of stored chunks."""
        ...


class InMemoryVectorStore:
    """In-memory vector store with optional JSON file persistence.

    Used for testing, lightweight deployments, and when ChromaDB is not installed.
    """

    def __init__(self, persist_path: str | Path | None = None):
        self._persist_path = Path(persist_path) if persist_path else None
        self._chunks: dict[str, EmbeddedChunk] = {}
        if self._persist_path and self._persist_path.exists():
            self._load()

    def _load(self) -> None:
        try:
            import json
            raw_text = self._persist_path.read_text(encoding="utf-8")
            if not raw_text.strip():
                return
            data = json.loads(raw_text)
            for item in data:
                chunk = EmbeddedChunk.model_validate(item)
                self._chunks[chunk.chunk.chunk_id] = chunk
            logger.info("loaded_vectors_from_disk", count=len(self._chunks), path=str(self._persist_path))
        except Exception as e:
            logger.warning("failed_loading_vectors_from_disk", error=str(e))

    def _save(self) -> None:
        if self._persist_path:
            try:
                import json
                self._persist_path.parent.mkdir(parents=True, exist_ok=True)
                data = [chunk.model_dump() for chunk in self._chunks.values()]
                self._persist_path.write_text(
                    json.dumps(data, indent=2, default=str), encoding="utf-8"
                )
            except Exception as e:
                logger.warning("failed_saving_vectors_to_disk", error=str(e))

    def upsert(self, chunks: list[EmbeddedChunk]) -> int:
        for chunk in chunks:
            self._chunks[chunk.chunk.chunk_id] = chunk
        self._save()
        return len(chunks)

    def search(
        self, query_embedding: QueryEmbedding, top_k: int = 10
    ) -> list[VectorSearchResult]:
        if not self._chunks:
            return []

        q_vec = np.array(query_embedding.vector, dtype=float)
        q_norm = np.linalg.norm(q_vec) or 1.0

        results: list[VectorSearchResult] = []
        for chunk_id, echunk in self._chunks.items():
            doc_vec = np.array(echunk.embedding, dtype=float)
            doc_norm = np.linalg.norm(doc_vec) or 1.0
            similarity = float(np.dot(q_vec, doc_vec) / (q_norm * doc_norm))
            meta = {
                "document_id": echunk.chunk.document_id,
                "source": echunk.chunk.source,
                "chunk_index": echunk.chunk.chunk_index,
                "document_version": echunk.chunk.document_version,
                "embedding_model": echunk.embedding_model,
                **echunk.chunk.metadata,
            }
            results.append(
                VectorSearchResult(
                    chunk_id=chunk_id,
                    text=echunk.chunk.text,
                    score=similarity,
                    metadata=meta,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def delete(self, chunk_ids: list[str]) -> int:
        count = 0
        for cid in chunk_ids:
            if cid in self._chunks:
                del self._chunks[cid]
                count += 1
        if count > 0:
            self._save()
        return count

    def count(self) -> int:
        return len(self._chunks)


class ChromaVectorStore:
    """ChromaDB-backed vector store implementation with resilient fallback.

    Uses persistent local storage when chromadb is available, and falls back
    to in-memory storage if chromadb is not installed.
    """

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str | None = None,
    ):
        settings = get_settings()
        self._persist_dir = persist_dir or settings.chroma.persist_dir
        self._collection_name = collection_name or settings.chroma.collection_name
        self._fallback_store: InMemoryVectorStore | None = None

        logger.info(
            "initializing_chroma",
            persist_dir=self._persist_dir,
            collection=self._collection_name,
        )

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings_

            self._client = chromadb.PersistentClient(
                path=self._persist_dir,
                settings=ChromaSettings_(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except ImportError:
            logger.warning(
                "chromadb_not_installed_fallback_to_in_memory",
                msg="Install chromadb for persistent vector storage.",
            )
            persist_file = Path(self._persist_dir) / f"{self._collection_name}_vectors.json"
            self._fallback_store = InMemoryVectorStore(persist_path=persist_file)
        except Exception as e:
            logger.warning("chromadb_init_failed_fallback_to_in_memory", error=str(e))
            persist_file = Path(self._persist_dir) / f"{self._collection_name}_vectors.json"
            self._fallback_store = InMemoryVectorStore(persist_path=persist_file)



    def upsert(self, chunks: list[EmbeddedChunk]) -> int:
        """Upsert embedded chunks into ChromaDB."""
        if not chunks:
            return 0

        if self._fallback_store is not None:
            return self._fallback_store.upsert(chunks)

        try:
            ids = [chunk.chunk.chunk_id for chunk in chunks]
            embeddings = [chunk.embedding for chunk in chunks]
            documents = [chunk.chunk.text for chunk in chunks]
            metadatas = [
                {
                    "document_id": chunk.chunk.document_id,
                    "source": chunk.chunk.source,
                    "chunk_index": chunk.chunk.chunk_index,
                    "document_version": chunk.chunk.document_version,
                    "embedding_model": chunk.embedding_model,
                    **{
                        k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                        for k, v in chunk.chunk.metadata.items()
                        if k not in ("page_details", "headings")
                    },
                }
                for chunk in chunks
            ]

            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            logger.info("upserted_chunks", count=len(chunks))
            return len(chunks)

        except Exception as e:
            raise VectorStoreError(f"Failed to upsert chunks: {e}") from e

    def get_all_documents(self) -> dict[str, list]:
        """Fetch all ids, text documents, and metadatas stored in ChromaDB."""
        if self._fallback_store is not None:
            return self._fallback_store.get_all_documents()
        try:
            data = self._collection.get(include=["documents", "metadatas"])
            return {
                "ids": data.get("ids", []),
                "documents": data.get("documents", []),
                "metadatas": data.get("metadatas", []),
            }
        except Exception as e:
            logger.warning("chroma_get_all_documents_failed", error=str(e))
            return {"ids": [], "documents": [], "metadatas": []}

    def search(
        self,
        query_embedding: QueryEmbedding,
        top_k: int = 10,
        where: dict[str, Any] | None = None,
        doc_type: str | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar chunks using cosine similarity with optional metadata filtering."""
        if self._fallback_store is not None:
            return self._fallback_store.search(
                query_embedding, top_k=top_k, where=where, doc_type=doc_type
            )

        try:
            query_where: dict[str, Any] = dict(where) if where else {}
            if doc_type:
                query_where["doc_type"] = doc_type.strip().lower()

            count = self._collection.count() or top_k
            results = self._collection.query(
                query_embeddings=[query_embedding.vector],
                n_results=min(top_k, count),
                where=query_where if query_where else None,
                include=["documents", "metadatas", "distances"],
            )

            search_results: list[VectorSearchResult] = []

            if results["ids"] and results["ids"][0]:
                for i, chunk_id in enumerate(results["ids"][0]):
                    # ChromaDB returns distances; convert to similarity scores
                    distance = results["distances"][0][i] if results["distances"] else 0
                    score = 1.0 - distance  # cosine distance → similarity

                    text = results["documents"][0][i] if results["documents"] else ""
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}

                    search_results.append(
                        VectorSearchResult(
                            chunk_id=chunk_id,
                            text=text,
                            score=score,
                            metadata=metadata,
                        )
                    )

            logger.debug("vector_search", query=query_embedding.query[:50], results=len(search_results))
            return search_results

        except Exception as e:
            raise VectorStoreError(f"Vector search failed: {e}") from e

    def delete(self, chunk_ids: list[str]) -> int:
        """Delete chunks by their IDs."""
        if not chunk_ids:
            return 0

        if self._fallback_store is not None:
            return self._fallback_store.delete(chunk_ids)

        try:
            self._collection.delete(ids=chunk_ids)
            logger.info("deleted_chunks", count=len(chunk_ids))
            return len(chunk_ids)
        except Exception as e:
            raise VectorStoreError(f"Failed to delete chunks: {e}") from e

    def count(self) -> int:
        """Return total number of stored chunks."""
        if self._fallback_store is not None:
            return self._fallback_store.count()
        return self._collection.count()

    def reset(self) -> None:
        """Delete and recreate the collection. USE WITH CAUTION."""
        if self._fallback_store is not None:
            self._fallback_store = InMemoryVectorStore()
            return
        logger.warning("resetting_vector_store", collection=self._collection_name)
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

