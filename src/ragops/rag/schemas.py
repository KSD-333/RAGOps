"""RAG schemas — request/response models for the RAG pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RAGConfig(BaseModel):
    """Runtime configuration for the RAG pipeline."""
    top_k: int = 10
    rerank_top_n: int = 5
    temperature: float = 0.1
    max_tokens: int = 2048
    include_citations: bool = True
    max_context_chunks: int = 5
