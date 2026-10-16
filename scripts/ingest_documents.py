#!/usr/bin/env python3
"""Script to ingest raw documents into the RAGOps vector store."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Ensure src is on sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from ragops.core.logging import setup_logging, get_logger
from ragops.ingestion.pipeline import IngestionPipeline
from ragops.retrieval.retriever import RAGRetriever

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into RAGOps vector store.")
    parser.add_argument(
        "--path",
        type=str,
        default="data/raw",
        help="Path to directory or file to ingest (default: data/raw)",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v1",
        help="Version tag for the ingested documents (default: v1)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Chunk size in characters (default: 512)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=50,
        help="Chunk overlap in characters (default: 50)",
    )

    args = parser.parse_args()
    setup_logging("INFO")

    target_path = Path(args.path)
    if not target_path.is_absolute():
        target_path = (root_dir / target_path).resolve()

    if not target_path.exists():
        logger.error("target_path_not_found", path=str(target_path))
        sys.exit(1)

    logger.info("starting_ingestion", path=str(target_path), version=args.version)

    pipeline = IngestionPipeline(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    retriever = RAGRetriever(use_reranker=False)

    if target_path.is_file():
        chunks = pipeline.ingest_file(target_path, version=args.version)
        indexed = retriever.index(chunks)
        logger.info("file_ingestion_complete", file=target_path.name, chunks=len(chunks), indexed=indexed)
    else:
        result = pipeline.ingest_directory(target_path, version=args.version)
        total_indexed = 0
        supported = {".pdf", ".html", ".htm", ".md", ".markdown"}
        for file_path in sorted(target_path.rglob("*")):
            if file_path.suffix.lower() in supported:
                try:
                    chunks = pipeline.ingest_file(file_path, version=args.version)
                    total_indexed += retriever.index(chunks)
                except Exception as e:
                    logger.warning("skipping_failed_file", file=file_path.name, error=str(e))

        logger.info(
            "directory_ingestion_complete",
            processed=result.documents_processed,
            chunks_created=result.chunks_created,
            indexed=total_indexed,
            errors=len(result.errors),
        )


if __name__ == "__main__":
    main()
