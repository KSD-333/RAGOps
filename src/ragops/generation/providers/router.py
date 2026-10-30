"""LLM provider router with circuit breaker, intelligent fallback, and degraded mode."""

from __future__ import annotations

import time
from typing import Any, Iterator

from ragops.core.config import get_settings
from ragops.core.exceptions import (
    CircuitBreakerOpenError,
)
from ragops.core.logging import get_logger
from ragops.core.types import LLMResponse
from ragops.generation.providers.base import LLMProvider
from ragops.generation.providers.groq_provider import GroqProvider
from ragops.generation.providers.ollama_provider import OllamaProvider

logger = get_logger(__name__)


class CircuitBreaker:
    """Simple time-based circuit breaker to avoid hammering failing providers."""

    def __init__(self, failure_threshold: int = 3, reset_timeout_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout_seconds
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self) -> None:
        """Reset failure counter on successful request."""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        """Increment failure counter and transition to OPEN if threshold reached."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def is_available(self) -> bool:
        """Check if requests can be routed to this provider."""
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        # HALF_OPEN: allow a probe request
        return True


class LLMRouter:
    """Intelligent router managing local Ollama and cloud Groq providers.

    Features:
    - Auto detection (Ollama first, Groq fallback)
    - Per-provider circuit breaking (3 failures -> 60s cooldown)
    - Single-turn request fallback recording (provider_used, fallback_used, provider_error)
    - Graceful degraded mode when no providers are functional
    """

    def __init__(
        self,
        mode: str | None = None,
        ollama_provider: OllamaProvider | None = None,
        groq_provider: GroqProvider | None = None,
    ):
        settings = get_settings()
        self._mode = (mode or settings.llm.provider).lower()
        self.ollama = ollama_provider or OllamaProvider()
        self.groq = groq_provider or GroqProvider()

        self._breakers = {
            "ollama": CircuitBreaker(failure_threshold=3, reset_timeout_seconds=60.0),
            "groq": CircuitBreaker(failure_threshold=3, reset_timeout_seconds=60.0),
        }

        self.last_provider_used: str = "none"
        self.last_fallback_used: bool = False
        self.last_provider_error: str | None = None
        self._active_provider_cache: str | None = None
        self._last_detected_time: float = 0.0

    @property
    def model_name(self) -> str:
        active = self.get_active_provider_name()
        if active == "ollama":
            return self.ollama.model_name
        if active == "groq":
            return self.groq.model_name
        return "degraded-no-llm"

    def get_provider(self, name: str) -> LLMProvider:
        """Get provider instance by name."""
        if name == "ollama":
            return self.ollama
        if name == "groq":
            return self.groq
        raise ValueError(f"Unknown provider name: {name}")

    def detect_active_provider(self, auto_start_ollama: bool = False) -> str:
        """Detect best available provider based on configured mode and live health checks."""
        if self._mode == "ollama":
            if auto_start_ollama:
                self.ollama.ensure_server_running()
            return "ollama"

        if self._mode == "groq":
            return "groq"

        # 'auto' mode: prefer Ollama if running or startable, else fallback to Groq
        if auto_start_ollama and self.ollama.is_installed():
            self.ollama.ensure_server_running(timeout_sec=5.0)

        # 1. Check Ollama server and model
        if self._breakers["ollama"].is_available():
            if self.ollama._ping_server(timeout=1.5):
                if self.ollama.is_model_installed():
                    return "ollama"
                # If model not installed but auto-pull enabled
                if self.ollama.pull_model_if_needed():
                    return "ollama"

        # 2. Check Groq
        if self._breakers["groq"].is_available() and self.groq.is_key_present():
            return "groq"

        # If Ollama is installed and running (even without target model), still prefer ollama over complete failure
        if self.ollama._ping_server(timeout=1.0):
            return "ollama"

        # If neither is ready: report degraded
        return "degraded"

    def get_active_provider_name(self) -> str:
        """Return currently cached active provider name (refreshed every 30 seconds)."""
        now = time.time()
        if self._active_provider_cache is None or (now - self._last_detected_time > 30.0):
            self._active_provider_cache = self.detect_active_provider(auto_start_ollama=False)
            self._last_detected_time = now
        return self._active_provider_cache

    def diagnose(self, force_refresh: bool = False) -> dict[str, Any]:
        """Produce full health diagnosis for /health/ready and CLI doctor command with 30s cache."""
        now = time.time()
        if not force_refresh and hasattr(self, "_cached_diagnose") and hasattr(self, "_cached_diagnose_time"):
            if now - self._cached_diagnose_time < 30.0:
                return self._cached_diagnose

        ollama_health = self.ollama.health_check()
        groq_health = self.groq.health_check()

        if self._mode == "ollama":
            active = "ollama"
        elif self._mode == "groq":
            active = "groq"
        else:
            if ollama_health.get("model_ready"):
                active = "ollama"
            elif groq_health.get("reachable"):
                active = "groq"
            elif ollama_health.get("running"):
                active = "ollama"
            else:
                active = "degraded"

        is_degraded = active == "degraded" or (not ollama_health["model_ready"] and not groq_health["reachable"])

        result = {
            "mode": self._mode,
            "active_provider": active,
            "degraded": is_degraded,
            "ollama": ollama_health,
            "groq": groq_health,
            "circuits": {
                "ollama": self._breakers["ollama"].state,
                "groq": self._breakers["groq"].state,
            },
        }
        self._cached_diagnose = result
        self._cached_diagnose_time = now
        return result

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate response with automated multi-provider fallback and degraded protection."""
        self.last_fallback_used = False
        self.last_provider_error = None

        # Determine target provider order based on mode
        if self._mode == "ollama":
            chain = ["ollama"]
        elif self._mode == "groq":
            chain = ["groq"]
        else:  # "auto"
            active = self.get_active_provider_name()
            if active == "ollama":
                chain = ["ollama", "groq"]
            elif active == "groq":
                chain = ["groq", "ollama"]
            else:
                chain = ["ollama", "groq"]

        primary_provider = chain[0]
        secondary_provider = chain[1] if len(chain) > 1 else None

        # Attempt Primary Provider
        try:
            if not self._breakers[primary_provider].is_available():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN for {primary_provider} due to recent errors.",
                    provider=primary_provider,
                )

            provider_obj = self.get_provider(primary_provider)
            response = provider_obj.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature if temperature is not None else 0.1,
                max_tokens=max_tokens or 2048,
            )
            self._breakers[primary_provider].record_success()
            self.last_provider_used = primary_provider
            self._active_provider_cache = primary_provider
            return response

        except Exception as primary_err:
            self._breakers[primary_provider].record_failure()
            self.last_provider_error = str(primary_err)
            logger.warning(
                "primary_llm_provider_failed",
                primary=primary_provider,
                error=str(primary_err),
                will_fallback=bool(secondary_provider),
            )

            # If no fallback provider configured, handle degraded mode or bubble up
            if not secondary_provider:
                return self._handle_degraded_response(primary_err)

            # Attempt Fallback Provider once
            try:
                if not self._breakers[secondary_provider].is_available():
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is OPEN for fallback provider {secondary_provider}.",
                        provider=secondary_provider,
                    )

                logger.info("attempting_llm_fallback", fallback_provider=secondary_provider)
                fallback_obj = self.get_provider(secondary_provider)
                response = fallback_obj.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature if temperature is not None else 0.1,
                    max_tokens=max_tokens or 2048,
                )
                self._breakers[secondary_provider].record_success()
                self.last_provider_used = secondary_provider
                self.last_fallback_used = True
                self._active_provider_cache = secondary_provider
                return response

            except Exception as secondary_err:
                self._breakers[secondary_provider].record_failure()
                logger.error(
                    "all_llm_providers_failed",
                    primary_error=str(primary_err),
                    secondary_error=str(secondary_err),
                )
                return self._handle_degraded_response(secondary_err)

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Stream response tokens from active provider."""
        active = self.get_active_provider_name()
        if active == "degraded":
            yield "[Degraded Mode: No active LLM provider available]"
            return

        provider = self.get_provider(active if active in ("ollama", "groq") else "groq")
        yield from provider.stream(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature if temperature is not None else 0.1,
            max_tokens=max_tokens or 2048,
        )

    def _handle_degraded_response(self, error: Exception) -> LLMResponse:
        """Construct clear degraded mode response when all LLM providers are offline."""
        self.last_provider_used = "degraded"
        degraded_text = (
            "⚠️ **[Degraded Mode]** Live LLM response synthesis is temporarily unavailable because neither "
            "local Ollama nor cloud Groq could be reached.\n\n"
            "**Document retrieval and semantic caching are still fully functional.**\n\n"
            "**How to enable generation:**\n"
            "- **Local (Recommended):** Install Ollama from [ollama.com](https://ollama.com) and run `ollama run llama3.2:3b`\n"
            "- **Cloud:** Set a valid `GROQ_API_KEY` in your `.env` file\n"
            "- Run `ragops doctor` in your terminal to diagnose provider status."
        )
        return LLMResponse(
            text=degraded_text,
            model="degraded-mode",
            provider="degraded",
            input_tokens=0,
            output_tokens=len(degraded_text.split()),
            latency_ms=1.0,
        )


_router_instance: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    """Get or initialize singleton LLMRouter instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance
