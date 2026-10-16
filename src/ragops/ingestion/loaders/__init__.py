"""Document loaders — extract raw content from different file formats.

Each loader is responsible ONLY for extraction. It does NOT clean or chunk.

Flow: File → Loader → RawDocument
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ragops.core.exceptions import DocumentParsingError, UnsupportedFormatError
from ragops.core.logging import get_logger
from ragops.core.types import DocumentFormat, RawDocument

logger = get_logger(__name__)


class BaseLoader(ABC):
    """Interface for document loaders."""

    @abstractmethod
    def load(self, file_path: Path) -> RawDocument:
        """Load and extract text from a file."""
        ...

    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """Check if this loader supports the given file format."""
        ...
