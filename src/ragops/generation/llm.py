"""LLM client — interface + Groq implementation.

Flow: Prompt → LLMClient → LLMResponse

The LLM client handles:
- API communication
- Retry logic
- Token counting
- Latency tracking

It does NOT know how documents are retrieved or how prompts are built.
"""

from __future__ import annotations

import time
from typing import Protocol

from groq import Groq

from ragops.core.config import get_settings
from ragops.core.exceptions import LLMProviderError
from ragops.core.logging import get_logger
from ragops.core.types import LLMResponse

logger = get_logger(__name__)


class LLMClient(Protocol):
    """Interface for LLM clients — swap providers without changing the pipeline."""

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        ...

    @property
    def model_name(self) -> str:
        """Current model name."""
        ...


class GroqClient:
    """LLM client using the Groq API.

    Supports Llama, Mixtral, and other models hosted on Groq.
    Provides fast inference with detailed usage tracking.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        settings = get_settings()
        self._api_key = api_key or settings.groq.api_key
        self._model = model or settings.groq.model
        self._default_temperature = settings.groq.temperature
        self._default_max_tokens = settings.groq.max_tokens

        if not self._api_key:
            raise LLMProviderError(
                "GROQ_API_KEY not set. Please add it to your .env file.",
                provider="groq",
            )

        self._client = Groq(api_key=self._api_key)
        logger.info("groq_client_initialized", model=self._model)

    @property
    def model_name(self) -> str:
        return self._model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a response using the Groq API.

        Returns LLMResponse with text, token usage, and latency metadata.
        """
        start_time = time.perf_counter()

        effective_temp = temperature if temperature is not None else self._default_temperature
        effective_max_tokens = max_tokens or self._default_max_tokens

        logger.debug(
            "generating",
            model=self._model,
            temperature=effective_temp,
            max_tokens=effective_max_tokens,
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=effective_temp,
                max_tokens=effective_max_tokens,
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            text = response.choices[0].message.content or ""
            usage = response.usage

            llm_response = LLMResponse(
                text=text,
                model=self._model,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                latency_ms=elapsed_ms,
            )

            logger.info(
                "generation_complete",
                model=self._model,
                input_tokens=llm_response.input_tokens,
                output_tokens=llm_response.output_tokens,
                latency_ms=round(elapsed_ms, 2),
            )

            return llm_response

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "generation_failed",
                model=self._model,
                error=str(e),
                latency_ms=round(elapsed_ms, 2),
            )
            raise LLMProviderError(
                f"Groq API error: {e}",
                provider="groq",
            ) from e


class MockLLMClient:
    """Mock LLM client for testing, CI environments, and offline runs."""

    def __init__(self, model: str = "mock-groq-llama-3"):
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Simulate LLM response generation based on prompt context."""
        logger.debug("mock_generating", model=self._model)

        # Detect judge evaluation prompts requesting JSON scoring
        if "json" in system_prompt.lower() or "faithfulness" in user_prompt.lower():
            import json
            payload = json.dumps({
                "faithfulness": 0.94,
                "relevance": 0.92,
                "completeness": 0.90,
                "reasoning": "The response accurately covers all core elements with full context grounding.",
            })
            return LLMResponse(
                text=payload,
                model=self._model,
                input_tokens=max(1, len(user_prompt.split())),
                output_tokens=30,
                latency_ms=15.0,
            )

        # Detect location, facility, or plant queries from prompt context
        combined = f"{system_prompt} {user_prompt}".lower()
        if any(k in combined for k in ["location", "plant", "headquarter", "facility"]):
            answer = (
                "Based on verified corporate documentation, the company maintains corporate headquarters "
                "and operational facilities including manufacturing plants and regional locations."
            )
            return LLMResponse(
                text=answer,
                model=self._model,
                input_tokens=max(1, len(user_prompt.split())),
                output_tokens=32,
                latency_ms=25.0,
            )

        answer = (
            "Based on the provided documentation, the requested procedure is fully supported. "
            "Refer to the cited architecture sections for configuration parameters and best practices."
        )
        return LLMResponse(
            text=answer,
            model=self._model,
            input_tokens=max(1, len(user_prompt.split())),
            output_tokens=32,
            latency_ms=25.0,
        )


