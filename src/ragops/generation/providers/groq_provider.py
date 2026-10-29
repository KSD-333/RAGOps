"""Groq cloud LLM provider implementation with model validation and secret masking."""

from __future__ import annotations

import random
import time
from typing import Any, Iterator

import requests
from groq import Groq

from ragops.core.config import get_settings
from ragops.core.exceptions import (
    ModelNotFoundError,
    ProviderUnavailableError,
)
from ragops.core.logging import get_logger
from ragops.core.types import LLMResponse
from ragops.generation.providers.base import LLMProvider

logger = get_logger(__name__)


def mask_secret(secret: str) -> str:
    """Safely mask secret credentials for logging and diagnostics."""
    if not secret:
        return "<not-set>"
    clean = secret.strip()
    if len(clean) <= 8:
        return "***"
    return f"{clean[:4]}...{clean[-4:]}"


class GroqProvider(LLMProvider):
    """Cloud LLM provider using the Groq API with robust error handling and secret masking."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ):
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.groq.api_key
        self._model = model or settings.groq.model
        self._timeout = timeout_seconds if timeout_seconds is not None else settings.llm.timeout_seconds
        self._max_retries = max_retries if max_retries is not None else settings.llm.max_retries
        self._default_temperature = settings.groq.temperature
        self._default_max_tokens = settings.groq.max_tokens
        self._client: Groq | None = None

        if self._api_key:
            try:
                self._client = Groq(api_key=self._api_key, timeout=self._timeout)
            except Exception as e:
                logger.warning("groq_sdk_init_failed", error=str(e))

    @property
    def name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model

    def is_key_present(self) -> bool:
        """Check if an API key is configured."""
        return bool(self._api_key and self._api_key.strip() and self._api_key != "your_groq_api_key_here")

    def health_check(self) -> dict[str, Any]:
        """Validate Groq credentials and model availability via /openai/v1/models."""
        if not self.is_key_present():
            return {
                "provider": self.name,
                "key_present": False,
                "reachable": False,
                "masked_key": "<none>",
                "model": self._model,
                "model_in_list": False,
                "message": "GROQ_API_KEY is missing or unconfigured in .env",
                "fix_hint": "Add your Groq API key to .env (sign up at https://console.groq.com)",
            }

        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            resp = requests.get(url, headers=headers, timeout=5.0)

            if resp.status_code == 401:
                return {
                    "provider": self.name,
                    "key_present": True,
                    "reachable": False,
                    "masked_key": mask_secret(self._api_key),
                    "model": self._model,
                    "model_in_list": False,
                    "message": "Groq API key is invalid or revoked (HTTP 401 Unauthorized)",
                    "fix_hint": "Verify and replace your GROQ_API_KEY in .env",
                }

            if resp.status_code == 429:
                return {
                    "provider": self.name,
                    "key_present": True,
                    "reachable": False,
                    "masked_key": mask_secret(self._api_key),
                    "model": self._model,
                    "model_in_list": False,
                    "message": "Groq API rate limit or credit quota exceeded (HTTP 429 Too Many Requests)",
                    "fix_hint": "Wait for rate limits to reset or verify billing at console.groq.com",
                }

            if resp.status_code == 200:
                data = resp.json()
                model_ids = [m.get("id", "") for m in data.get("data", [])]
                model_in_list = self._model in model_ids

                msg = f"Groq API is reachable and authenticated. Active model: {self._model}"
                if not model_in_list:
                    msg = (
                        f"Groq API is connected, but configured model '{self._model}' is not in available models list. "
                        f"Models might have been deprecated. Top models: {', '.join(model_ids[:5])}"
                    )

                return {
                    "provider": self.name,
                    "key_present": True,
                    "reachable": True,
                    "masked_key": mask_secret(self._api_key),
                    "model": self._model,
                    "model_in_list": model_in_list,
                    "available_models_count": len(model_ids),
                    "message": msg,
                }

            return {
                "provider": self.name,
                "key_present": True,
                "reachable": False,
                "masked_key": mask_secret(self._api_key),
                "model": self._model,
                "model_in_list": False,
                "message": f"Groq API returned HTTP {resp.status_code}: {resp.text[:120]}",
            }

        except requests.exceptions.Timeout:
            return {
                "provider": self.name,
                "key_present": True,
                "reachable": False,
                "masked_key": mask_secret(self._api_key),
                "model": self._model,
                "model_in_list": False,
                "message": "Groq API connection timed out (>5s)",
                "fix_hint": "Check network connectivity or outbound internet access",
            }
        except Exception as e:
            return {
                "provider": self.name,
                "key_present": True,
                "reachable": False,
                "masked_key": mask_secret(self._api_key),
                "model": self._model,
                "model_in_list": False,
                "message": f"Groq connection error: {str(e)}",
                "fix_hint": "Check network routing or proxy settings",
            }

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate response via Groq with retries and exponential backoff."""
        if not self.is_key_present():
            raise ProviderUnavailableError(
                "GROQ_API_KEY is not configured.",
                provider=self.name,
                fix_hint="Add GROQ_API_KEY to your .env file",
            )

        start_time = time.perf_counter()
        effective_temp = temperature if temperature is not None else self._default_temperature
        effective_max_tokens = max_tokens or self._default_max_tokens

        client = self._client or Groq(api_key=self._api_key, timeout=self._timeout)

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 2):
            try:
                response = client.chat.completions.create(
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

                return LLMResponse(
                    text=text,
                    model=self._model,
                    provider=self.name,
                    input_tokens=usage.prompt_tokens if usage else 0,
                    output_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=elapsed_ms,
                )

            except Exception as e:
                last_error = e
                err_str = str(e).lower()

                # Don't retry on authentication failure
                if "401" in err_str or "unauthorized" in err_str:
                    raise ProviderUnavailableError(
                        f"Groq API authentication failed (invalid key): {e}",
                        provider=self.name,
                        status_code=401,
                        fix_hint="Verify GROQ_API_KEY in .env",
                    ) from e

                # Don't retry if model is explicitly not found
                if "404" in err_str or "model_not_found" in err_str:
                    raise ModelNotFoundError(
                        f"Groq model '{self._model}' was not found: {e}",
                        provider=self.name,
                        status_code=404,
                        fix_hint="Set GROQ_MODEL in .env to a valid model such as 'llama-3.1-8b-instant'",
                    ) from e

                if attempt <= self._max_retries:
                    backoff = (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                    logger.warning(
                        "groq_request_failed_retrying",
                        attempt=attempt,
                        backoff_sec=round(backoff, 2),
                        error=str(e),
                    )
                    time.sleep(backoff)
                else:
                    break

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        raise ProviderUnavailableError(
            f"Groq API request failed after {self._max_retries + 1} attempts: {last_error}",
            provider=self.name,
            fix_hint="Verify Groq status at https://status.groq.com and check network connection",
        )

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Stream response tokens from Groq API."""
        if not self.is_key_present():
            raise ProviderUnavailableError(
                "GROQ_API_KEY is not configured.",
                provider=self.name,
            )

        effective_temp = temperature if temperature is not None else self._default_temperature
        effective_max_tokens = max_tokens or self._default_max_tokens
        client = self._client or Groq(api_key=self._api_key, timeout=self._timeout)

        try:
            stream_resp = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=effective_temp,
                max_tokens=effective_max_tokens,
                stream=True,
            )
            for chunk in stream_resp:
                delta = chunk.choices[0].delta.content if chunk.choices else ""
                if delta:
                    yield delta
        except Exception as e:
            raise ProviderUnavailableError(
                f"Groq stream error: {e}",
                provider=self.name,
            ) from e

