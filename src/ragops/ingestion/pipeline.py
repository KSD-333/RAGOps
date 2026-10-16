"""Ingestion pipeline — orchestrates the full document ingestion lifecycle.

Flow: Document Source → Loader → Cleaner → Chunker → DocumentChunk[]

This module coordinates the ingestion steps but delegates to each component.
After chunking, it hands off to the retrieval module for embedding + storage.
"""

import hashlib
import uuid
from pathlib import Path

from ragops.core.config import get_settings
from ragops.core.exceptions import IngestionError, UnsupportedFormatError
from ragops.core.logging import get_logger
from ragops.core.types import DocumentChunk, DocumentFormat, RawDocument
from ragops.ingestion.cleaners import DocumentCleaner
from ragops.ingestion.chunkers import RecursiveChunker
from ragops.ingestion.loaders import BaseLoader
from ragops.ingestion.loaders.html import HTMLLoader
from ragops.ingestion.loaders.markdown import MarkdownLoader
from ragops.ingestion.loaders.pdf import PDFLoader
from ragops.ingestion.schemas import IngestionRequest, IngestionResult

logger = get_logger(__name__)


class IngestionPipeline:
    """Full ingestion pipeline: load → clean → chunk.

    Automatically selects the correct loader based on file extension.
    Returns DocumentChunk[] ready for embedding.
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        settings = get_settings()

        self._loaders: list[BaseLoader] = [
            PDFLoader(),
            HTMLLoader(),
            MarkdownLoader(),
        ]
        self._cleaner = DocumentCleaner()
        self._chunker = RecursiveChunker(
            chunk_size=chunk_size or settings.ingestion.chunk_size,
            chunk_overlap=chunk_overlap or settings.ingestion.chunk_overlap,
        )

    def _get_loader(self, file_path: Path) -> BaseLoader:
        """Find a loader that supports this file type."""
        for loader in self._loaders:
            if loader.supports(file_path):
                return loader
        raise UnsupportedFormatError(
            f"No loader for file type: {file_path.suffix}",
            details={"path": str(file_path)},
        )

    def ingest_file(
        self,
        file_path: Path,
        document_version: str = "v1",
        metadata: dict | None = None,
        version: str | None = None,
    ) -> list[DocumentChunk]:
        """Ingest a single file through the full pipeline.

        Returns a list of DocumentChunk objects ready for embedding.
        """
        eff_version = version or document_version
        file_path = Path(file_path).resolve()
        logger.info("ingesting_file", path=str(file_path), version=eff_version)

        # 1. Load
        loader = self._get_loader(file_path)
        raw_doc = loader.load(file_path)

        # Merge user metadata
        if metadata:
            raw_doc.metadata.update(metadata)

        # 2. Clean
        clean_doc = self._cleaner.clean(raw_doc)

        # 3. Chunk
        doc_hash = hashlib.sha256(f"{file_path.name}:{eff_version}".encode("utf-8")).hexdigest()[:12]
        document_id = f"doc_{doc_hash}"
        chunks = self._chunker.chunk(clean_doc, document_id, eff_version)

        logger.info(
            "ingestion_complete",
            source=file_path.name,
            doc_id=document_id,
            chunks=len(chunks),
        )
        return chunks

    def ingest_directory(
        self,
        directory: Path,
        document_version: str = "v1",
        metadata: dict | None = None,
        version: str | None = None,
    ) -> IngestionResult:
        """Ingest all supported files from a directory.

        Returns an IngestionResult with counts and any errors.
        """
        eff_version = version or document_version
        directory = Path(directory).resolve()
        logger.info("ingesting_directory", path=str(directory), version=eff_version)

        if not directory.is_dir():
            raise IngestionError(f"Not a directory: {directory}")


        result = IngestionResult()
        supported_extensions = {".pdf", ".html", ".htm", ".md", ".markdown"}

        for file_path in sorted(directory.rglob("*")):
            if file_path.suffix.lower() not in supported_extensions:
                continue

            try:
                chunks = self.ingest_file(file_path, document_version, metadata)
                result.documents_processed += 1
                result.chunks_created += len(chunks)

                if chunks:
                    result.document_ids.append(chunks[0].document_id)

            except Exception as e:
                error_msg = f"Failed to ingest {file_path.name}: {e}"
                logger.error("ingestion_error", file=str(file_path), error=str(e))
                result.errors.append(error_msg)

        logger.info(
            "directory_ingestion_complete",
            documents=result.documents_processed,
            chunks=result.chunks_created,
            errors=len(result.errors),
        )
        return result

    def ingest(self, request: IngestionRequest) -> IngestionResult:
        """Ingest based on an IngestionRequest — handles files and directories."""
        path = request.resolved_path

        if path.is_file():
            chunks = self.ingest_file(path, request.document_version, request.metadata)
            return IngestionResult(
                documents_processed=1,
                chunks_created=len(chunks),
                document_ids=[chunks[0].document_id] if chunks else [],
            )
        elif path.is_dir():
            return self.ingest_directory(path, request.document_version, request.metadata)
        else:
            raise IngestionError(f"Path not found: {path}")
