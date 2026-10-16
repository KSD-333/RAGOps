"""PDF document loader using pypdf."""

from __future__ import annotations

from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

from ragops.core.exceptions import DocumentParsingError
from ragops.core.logging import get_logger
from ragops.core.types import DocumentFormat, RawDocument
from ragops.ingestion.loaders import BaseLoader

logger = get_logger(__name__)


class PDFLoader(BaseLoader):
    """Load and extract text from PDF files."""

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def load(self, file_path: Path) -> RawDocument:
        """Extract text content from a PDF file.

        Extracts text page-by-page and includes page numbers in metadata.
        """
        logger.info("loading_pdf", path=str(file_path))

        if not file_path.exists():
            raise DocumentParsingError(f"File not found: {file_path}")

        if PdfReader is None:
            raise DocumentParsingError(
                "PDF parsing requires 'pypdf' or 'PyPDF2'. Please run 'pip install pypdf'."
            )


        try:
            reader = PdfReader(str(file_path))
            pages: list[str] = []
            page_metadata: list[dict] = []

            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)
                    page_metadata.append({"page_number": i + 1})

            content = "\n\n".join(pages)

            if not content.strip():
                raise DocumentParsingError(f"No extractable text in PDF: {file_path}")

            return RawDocument(
                source=file_path.name,
                content=content,
                format=DocumentFormat.PDF,
                metadata={
                    "total_pages": len(reader.pages),
                    "pages_with_text": len(pages),
                    "file_size_bytes": file_path.stat().st_size,
                    "page_details": page_metadata,
                },
            )

        except DocumentParsingError:
            raise
        except Exception as e:
            raise DocumentParsingError(
                f"Failed to parse PDF: {file_path}", details={"error": str(e)}
            ) from e
