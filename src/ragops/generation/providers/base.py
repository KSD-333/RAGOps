"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterator

from ragops.core.types import LLMResponse


class LLMProvider(ABC):
    """Abstract interface that all LLM providers (Ollama, Groq, etc.) must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier string, e.g. 'ollama' or 'groq'."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model name for this provider."""
        pass

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a complete text response from the model.

        Args:
            system_prompt: System prompt with instructions and guardrails.
            user_prompt: Grounded user prompt with question and context.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum tokens in generated completion.

        Returns:
            LLMResponse containing generated text, token counts, latency, and provider name.
        """
        pass

    @abstractmethod
    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> Iterator[str]:
        """Stream response tokens as they are produced by the model.

        Args:
            system_prompt: System prompt.
            user_prompt: Grounded user prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Yields:
            Token text chunks as produced.
        """
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Check provider connectivity, authentication, and model availability.

        Returns:
            Dictionary containing health diagnostic metrics without sensitive secrets.
        """
        pass

