"""Unit tests for DocumentCleaner."""

from __future__ import annotations

import pytest
from ragops.core.types import DocumentFormat, RawDocument
from ragops.ingestion.cleaners import DocumentCleaner


def test_cleaner_normalizes_whitespace():
    cleaner = DocumentCleaner()
    raw = RawDocument(
        source="test.md",
        format=DocumentFormat.MARKDOWN,
        content="This   has   too    many   spaces.\n\n\n\n\nAnd excessive blank lines.",
    )
    cleaned = cleaner.clean(raw)
    assert "This has too many spaces." in cleaned.content
    assert "\n\n\n\n" not in cleaned.content


def test_cleaner_removes_control_characters():
    cleaner = DocumentCleaner()
    raw = RawDocument(
        source="test.md",
        format=DocumentFormat.MARKDOWN,
        content="Valid text\x00with control\x08characters\x1b.",
    )
    cleaned = cleaner.clean(raw)
    assert "\x00" not in cleaned.content
    assert "\x08" not in cleaned.content
    assert "Valid textwith controlcharacters." in cleaned.content


def test_cleaner_preserves_metadata():
    cleaner = DocumentCleaner()
    meta = {"doc_id": "123", "author": "Alice"}
    raw = RawDocument(
        source="test.md",
        format=DocumentFormat.MARKDOWN,
        content="Simple content",
        metadata=meta,
    )
    cleaned = cleaner.clean(raw)
    assert cleaned.source == "test.md"
    assert cleaned.metadata["doc_id"] == "123"
    assert cleaned.metadata["author"] == "Alice"

