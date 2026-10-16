"""Embedding provider — converts text to vectors.

Flow: text → EmbeddingProvider → vector

This module owns the text → vector transformation.
It should NOT know about LLM prompts, API requests, or evaluation.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

import numpy as np

from ragops.core.config import get_settings
from ragops.core.exceptions import EmbeddingError
from ragops.core.logging import get_logger
from ragops.core.types import DocumentChunk, EmbeddedChunk, QueryEmbedding

logger = get_logger(__name__)


class EmbeddingProvider(Protocol):
    """Interface for embedding providers."""

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""
        ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple text strings."""
        ...

    @property
    def model_name(self) -> str:
        """Name of the embedding model."""
        ...

    @property
    def dimension(self) -> int:
        """Dimension of the embedding vectors."""
        ...


class SentenceTransformerEmbedding:
    """Embedding provider using sentence-transformers.

    Uses all-MiniLM-L6-v2 by default — fast, accurate, 384-dim vectors.
    """

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self._model_name = model_name or settings.embedding.model
        self._dimension = settings.embedding.dimension
        self._model = None
        self._mock: MockEmbeddingProvider | None = None

    def _load_model(self):
        """Lazy load the sentence transformer model."""
        if self._model is None and self._mock is None:
            logger.info("loading_embedding_model", model=self._model_name)
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
            except ImportError:
                logger.warning(
                    "sentence_transformers_not_installed_fallback_to_mock",
                    msg="sentence-transformers is not installed. Using MockEmbeddingProvider.",
                )
                self._mock = MockEmbeddingProvider(dimension=self._dimension, model_name=self._model_name)
            except Exception as e:
                raise EmbeddingError(
                    f"Failed to load embedding model: {self._model_name}",
                    details={"error": str(e)},
                ) from e

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""
        self._load_model()
        if self._mock is not None:
            return self._mock.embed_text(text)
        try:
            embedding = self._model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            raise EmbeddingError(f"Failed to embed text: {e}") from e

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple text strings in a batch."""
        if not texts:
            return []

        self._load_model()
        if self._mock is not None:
            return self._mock.embed_texts(texts)
        try:
            embeddings = self._model.encode(
                texts, normalize_embeddings=True, show_progress_bar=len(texts) > 50
            )
            return embeddings.tolist()
        except Exception as e:
            raise EmbeddingError(f"Failed to batch embed: {e}") from e



    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[EmbeddedChunk]:
        """Embed a list of document chunks."""
        texts = [chunk.text for chunk in chunks]
        vectors = self.embed_texts(texts)

        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=vector,
                embedding_model=self._model_name,
            )
            for chunk, vector in zip(chunks, vectors)
        ]

    def embed_query(self, query: str) -> QueryEmbedding:
        """Embed a query string."""
        vector = self.embed_text(query)
        return QueryEmbedding(
            query=query,
            vector=vector,
            model=self._model_name,
        )


class MockEmbeddingProvider:
    """Deterministic mock embedding provider for tests."""

    def __init__(self, dimension: int = 384, model_name: str = "mock-minilm"):
        self._dimension = dimension
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        # Deterministic feature hashing (term + bigram frequency)
        words = [w.strip(".,!?:;\"'()[]{}<>-") for w in text.lower().split() if w.strip(".,!?:;\"'()[]{}<>-")]
        vec = [0.0] * self._dimension
        for w in words:
            idx = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % self._dimension
            vec[idx] += 1.0
        for i in range(len(words) - 1):
            bigram = f"{words[i]}_{words[i+1]}"
            idx = int(hashlib.md5(bigram.encode("utf-8")).hexdigest(), 16) % self._dimension
            vec[idx] += 1.5
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]

    def embed_chunks(self, chunks: list[DocumentChunk]) -> list[EmbeddedChunk]:
        return [
            EmbeddedChunk(
                chunk=chunk,
                embedding=self.embed_text(chunk.text),
                embedding_model=self._model_name,
            )
            for chunk in chunks
        ]

    def embed_query(self, query: str) -> QueryEmbedding:
        return QueryEmbedding(
            query=query,
            vector=self.embed_text(query),
            model=self._model_name,
        )

