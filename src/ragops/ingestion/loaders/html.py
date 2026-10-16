"""HTML document loader using BeautifulSoup + html2text."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

try:
    import html2text
except ImportError:
    html2text = None

from ragops.core.exceptions import DocumentParsingError
from ragops.core.logging import get_logger
from ragops.core.types import DocumentFormat, RawDocument
from ragops.ingestion.loaders import BaseLoader

logger = get_logger(__name__)


class HTMLLoader(BaseLoader):
    """Load and extract text from HTML files."""

    def __init__(self):
        if html2text is not None:
            self._converter = html2text.HTML2Text()
            self._converter.ignore_links = False
            self._converter.ignore_images = True
            self._converter.body_width = 0  # No wrapping
        else:
            self._converter = None

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in (".html", ".htm")


    def load(self, file_path: Path) -> RawDocument:
        """Extract text content from an HTML file."""
        logger.info("loading_html", path=str(file_path))

        if not file_path.exists():
            raise DocumentParsingError(f"File not found: {file_path}")

        try:
            raw_html = file_path.read_text(encoding="utf-8", errors="replace")
            soup = BeautifulSoup(raw_html, "html.parser")

            # Extract title
            title = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Convert to clean text
            if self._converter is not None:
                content = self._converter.handle(str(soup))
            else:
                content = soup.get_text(separator="\n\n", strip=True)


            if not content.strip():
                raise DocumentParsingError(f"No extractable text in HTML: {file_path}")

            return RawDocument(
                source=file_path.name,
                content=content,
                format=DocumentFormat.HTML,
                metadata={
                    "title": title,
                    "file_size_bytes": file_path.stat().st_size,
                },
            )

        except DocumentParsingError:
            raise
        except Exception as e:
            raise DocumentParsingError(
                f"Failed to parse HTML: {file_path}", details={"error": str(e)}
            ) from e
