"""Markdown document loader."""

from __future__ import annotations

import re
from pathlib import Path

from ragops.core.exceptions import DocumentParsingError
from ragops.core.logging import get_logger
from ragops.core.types import DocumentFormat, RawDocument
from ragops.ingestion.loaders import BaseLoader

logger = get_logger(__name__)


class MarkdownLoader(BaseLoader):
    """Load and extract text from Markdown files."""

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in (".md", ".markdown", ".txt")

    def load(self, file_path: Path) -> RawDocument:
        """Extract text content from a Markdown file.

        Preserves the markdown structure but extracts heading hierarchy
        into metadata for section-aware chunking.
        """
        logger.info("loading_markdown", path=str(file_path))

        if not file_path.exists():
            raise DocumentParsingError(f"File not found: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")

            if not content.strip():
                raise DocumentParsingError(f"Empty markdown file: {file_path}")

            # Extract heading structure for metadata
            headings = []
            for match in re.finditer(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE):
                headings.append({
                    "level": len(match.group(1)),
                    "text": match.group(2).strip(),
                })

            return RawDocument(
                source=file_path.name,
                content=content,
                format=DocumentFormat.MARKDOWN,
                metadata={
                    "headings": headings,
                    "heading_count": len(headings),
                    "file_size_bytes": file_path.stat().st_size,
                },
            )

        except DocumentParsingError:
            raise
        except Exception as e:
            raise DocumentParsingError(
                f"Failed to load Markdown: {file_path}", details={"error": str(e)}
            ) from e
