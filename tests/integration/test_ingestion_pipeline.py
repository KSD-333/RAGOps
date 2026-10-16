"""Integration tests for IngestionPipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from ragops.ingestion.pipeline import IngestionPipeline


def test_ingestion_pipeline_ingest_file():
    pipeline = IngestionPipeline(chunk_size=120, chunk_overlap=20)

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Production Architecture\n\nRAGOps orchestrates ingestion, retrieval, and generation.\n"
                "It attaches citations to answers and tracks latency with OpenTelemetry.")
        f_path = Path(f.name)

    try:
        chunks = pipeline.ingest_file(f_path, document_version="v1.0")
        assert len(chunks) >= 1
        assert chunks[0].source == f_path.name
        assert chunks[0].document_version == "v1.0"
        assert len(chunks[0].text) > 0
    finally:
        f_path.unlink()


def test_ingestion_pipeline_ingest_directory():
    pipeline = IngestionPipeline(chunk_size=150, chunk_overlap=30)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        (tmp_path / "doc1.md").write_text("# Doc 1\nContent for document one with sufficient detail.", encoding="utf-8")
        (tmp_path / "doc2.html").write_text("<html><body><p>Doc 2 content with details.</p></body></html>", encoding="utf-8")

        result = pipeline.ingest_directory(tmp_path, document_version="v2.0")
        assert result.documents_processed == 2

        assert result.chunks_created >= 2
        assert len(result.errors) == 0
