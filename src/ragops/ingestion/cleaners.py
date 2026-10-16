"""Document cleaners — normalize and clean extracted text.

Flow: RawDocument → Cleaner → CleanDocument

Handles whitespace, malformed text, encoding issues, repeated headers, etc.
"""

from __future__ import annotations

import re
import unicodedata

from ragops.core.logging import get_logger
from ragops.core.types import CleanDocument, RawDocument

logger = get_logger(__name__)


class DocumentCleaner:
    """Clean raw document text for chunking.

    Applies a chain of cleaning operations:
    1. Unicode normalization
    2. Control character removal
    3. Whitespace normalization
    4. Repeated line/header deduplication
    5. Artifact removal (page numbers, watermarks)
    """

    def clean(self, doc: RawDocument) -> CleanDocument:
        """Clean a raw document and return a CleanDocument."""
        logger.debug("cleaning_document", source=doc.source)

        text = doc.content

        # Normalize unicode
        text = unicodedata.normalize("NFKC", text)

        # Remove control characters (keep newlines, tabs)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        # Normalize whitespace within lines
        text = re.sub(r"[^\S\n]+", " ", text)

        # Remove excessive blank lines (more than 2 consecutive)
        text = re.sub(r"\n{4,}", "\n\n\n", text)

        # Remove repeated headers/footers (common in PDFs)
        text = self._remove_repeated_lines(text)

        # Remove common PDF artifacts
        text = self._remove_artifacts(text)

        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Final strip
        text = text.strip()

        return CleanDocument(
            source=doc.source,
            content=text,
            metadata={**doc.metadata, "original_length": len(doc.content), "cleaned_length": len(text)},
        )

    def _remove_repeated_lines(self, text: str) -> str:
        """Remove lines that appear more than 3 times (likely headers/footers)."""
        lines = text.split("\n")
        line_counts: dict[str, int] = {}
        for line in lines:
            stripped = line.strip()
            if stripped:
                line_counts[stripped] = line_counts.get(stripped, 0) + 1

        # Remove lines that appear > 3 times (threshold for header/footer detection)
        repeated = {line for line, count in line_counts.items() if count > 3 and len(line) < 100}

        if repeated:
            logger.debug("removing_repeated_lines", count=len(repeated))
            lines = [line for line in lines if line.strip() not in repeated]

        return "\n".join(lines)

    def _remove_artifacts(self, text: str) -> str:
        """Remove common document artifacts like page numbers."""
        # Remove standalone page numbers
        text = re.sub(r"^\s*(?:Page\s+)?\d+\s*$", "", text, flags=re.MULTILINE)

        # Remove common watermarks
        text = re.sub(r"(?i)^\s*(confidential|draft|internal use only)\s*$", "", text, flags=re.MULTILINE)

        return text
