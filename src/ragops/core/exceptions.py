"""Core exceptions — domain-specific errors for clean error handling."""

from __future__ import annotations


class RAGOpsError(Exception):
    """Base exception for all RAGOps errors."""

    def __init__(self, message: str = "", details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# --- Ingestion Errors ---

class IngestionError(RAGOpsError):
    """Error during document ingestion."""
    pass


class UnsupportedFormatError(IngestionError):
    """Unsupported document format."""
    pass


class DocumentParsingError(IngestionError):
    """Failed to parse a document."""
    pass


# --- Retrieval Errors ---

class RetrievalError(RAGOpsError):
    """Error during retrieval."""
    pass


class EmbeddingError(RetrievalError):
    """Error generating embeddings."""
    pass


class VectorStoreError(RetrievalError):
    """Error interacting with the vector store."""
    pass


# --- Generation Errors ---

class GenerationError(RAGOpsError):
    """Error during LLM generation."""
    pass


class LLMProviderError(GenerationError):
    """Error from the LLM provider (Groq, OpenAI, etc.)."""

    def __init__(self, message: str = "", provider: str = "", status_code: int | None = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(message, {"provider": provider, "status_code": status_code})


class PromptTooLongError(GenerationError):
    """Prompt exceeds the model's context window."""
    pass


# --- Evaluation Errors ---

class EvaluationError(RAGOpsError):
    """Error during evaluation."""
    pass


class DatasetNotFoundError(EvaluationError):
    """Evaluation dataset not found."""
    pass


# --- Quality Gate Errors ---

class QualityGateError(RAGOpsError):
    """Error in quality gate processing."""
    pass


# --- Configuration Errors ---

class ConfigurationError(RAGOpsError):
    """Invalid or missing configuration."""
    pass
