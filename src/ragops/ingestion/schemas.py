"""Ingestion schemas — request/response models for the ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ragops.core.types import DocumentFormat


class IngestionRequest(BaseModel):
    """Request to ingest documents from a file path or directory."""
    path: str
    document_version: str = "v1"
    metadata: dict = Field(default_factory=dict)
    format: DocumentFormat | None = None  # Auto-detect if None

    @property
    def resolved_path(self) -> Path:
        return Path(self.path).resolve()


class IngestionResult(BaseModel):
    """Result of an ingestion operation."""
    documents_processed: int = 0
    chunks_created: int = 0
    chunks_embedded: int = 0
    errors: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
