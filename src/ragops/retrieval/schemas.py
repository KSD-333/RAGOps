"""Retrieval schemas — request/response models for retrieval operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request to search the vector store."""
    query: str
    top_k: int = 10
    filters: dict = Field(default_factory=dict)
    similarity_threshold: float = 0.0


class RerankerConfig(BaseModel):
    """Configuration for the reranker."""
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    top_n: int = 5
    batch_size: int = 32
