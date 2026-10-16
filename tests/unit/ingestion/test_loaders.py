"""Unit tests for document loaders."""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from ragops.core.exceptions import DocumentParsingError
from ragops.core.types import DocumentFormat
from ragops.ingestion.loaders.html import HTMLLoader
from ragops.ingestion.loaders.markdown import MarkdownLoader


def test_markdown_loader_extracts_headings_and_content():
    loader = MarkdownLoader()
    assert loader.supports(Path("doc.md"))
    assert loader.supports(Path("doc.markdown"))
    assert not loader.supports(Path("doc.pdf"))

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Main Heading\n\nSome paragraph text here.\n\n## Subheading\n\nMore details.")
        f_path = Path(f.name)

    try:
        raw_doc = loader.load(f_path)
        assert raw_doc.format == DocumentFormat.MARKDOWN
        assert "Main Heading" in raw_doc.content
        assert raw_doc.metadata["heading_count"] == 2
        assert raw_doc.metadata["headings"][0]["text"] == "Main Heading"
        assert raw_doc.metadata["headings"][1]["level"] == 2
    finally:
        f_path.unlink()


def test_markdown_loader_handles_empty_file():
    loader = MarkdownLoader()
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("   \n\n")
        f_path = Path(f.name)

    try:
        with pytest.raises(DocumentParsingError):
            loader.load(f_path)
    finally:
        f_path.unlink()


def test_html_loader_extracts_clean_text():
    loader = HTMLLoader()
    assert loader.supports(Path("index.html"))

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write("<html><head><title>Test Page</title></head><body><h1>Header</h1><p>Body text.</p></body></html>")
        f_path = Path(f.name)

    try:
        raw_doc = loader.load(f_path)
        assert raw_doc.format == DocumentFormat.HTML
        assert "Body text." in raw_doc.content
        assert raw_doc.metadata.get("title") == "Test Page"
    finally:
        f_path.unlink()
