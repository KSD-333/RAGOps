"""Ollama local LLM provider implementation."""

from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
import time
from typing import Any, Iterator

import requests

from ragops.core.config import get_settings
from ragops.core.exceptions import (
    ModelNotFoundError,
    ProviderUnavailableError,
)
from ragops.core.logging import get_logger
from ragops.core.types import LLMResponse
from ragops.generation.providers.base import LLMProvider

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    """Local LLM provider using Ollama HTTP API with auto-start and health detection."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        auto_pull: bool | None = None,
    ):
        settings = get_settings()
        self._base_url = (base_url or settings.ollama.base_url).rstrip("/")
        self._model = model or settings.ollama.model
        self._timeout = timeout_seconds if timeout_seconds is not None else settings.llm.timeout_seconds
        self._max_retries = max_retries if max_retries is not None else settings.llm.max_retries
        self._auto_pull = auto_pull if auto_pull is not None else settings.ollama.auto_pull
        self._server_process: subprocess.Popen | None = None

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    def is_installed(self) -> bool:
        """Check if the ollama binary is installed on the host system."""
        return shutil.which("ollama") is not None

    def ensure_server_running(self, timeout_sec: float = 10.0) -> bool:
        """If Ollama is installed but not responding, attempt to launch 'ollama serve' in background."""
        if self._ping_server(timeout=2.0):
            return True

        if not self.is_installed():
            logger.info("ollama_binary_not_found_skipping_launch")
            return False

        logger.info("ollama_installed_but_stopped_starting_service")
        try:
            creationflags = 0
            if sys.platform == "win32":
                # DETACHED_PROCESS = 0x00000008, CREATE_NEW_PROCESS_GROUP = 0x00000200
                creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

            self._server_process = subprocess.Popen(
                ["ollama", "serve"],
                shell=False,
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            deadline = time.time() + timeout_sec
            while time.time() < deadline:
                if self._ping_server(timeout=1.5):
                    logger.info("ollama_service_started_successfully")
                    return True
                time.sleep(0.5)

            logger.warning("ollama_startup_timeout_after_wait", timeout_sec=timeout_sec)
            return False
        except Exception as e:
            logger.warning("ollama_auto_start_failed", error=str(e))
            return False

    def _ping_server(self, timeout: float = 2.0) -> bool:
        """Fast check to verify if the Ollama HTTP server is responsive."""
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def list_installed_models(self, timeout: float = 3.0) -> list[str]:
        """Fetch list of models available in the local Ollama instance."""
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("name", "") for m in data.get("models", [])]
            return []
        except Exception as e:
            logger.debug("ollama_list_models_failed", error=str(e))
            return []

    def is_model_installed(self, model: str | None = None) -> bool:
        """Check whether the target model (or tag prefix) is present."""
        target = (model or self._model).lower()
        installed = self.list_installed_models()
        for m in installed:
            m_lower = m.lower()
            if m_lower == target or m_lower.startswith(f"{target}:") or target.startswith(f"{m_lower}:"):
                return True
        return False

    def pull_model_if_needed(self) -> bool:
        """Auto-pull the model if OLLAMA_AUTO_PULL is enabled."""
        if self.is_model_installed():
            return True

        if not self._auto_pull:
            logger.warning(
                "ollama_model_missing_auto_pull_disabled",
                model=self._model,
                fix_hint=f"Run 'ollama pull {self._model}' or set OLLAMA_AUTO_PULL=true",
            )
            return False

        logger.info("pulling_ollama_model", model=self._model)
        try:
            resp = requests.post(
                f"{self._base_url}/api/pull",
                json={"name": self._model, "stream": False},
                timeout=300.0,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("ollama_pull_model_failed", model=self._model, error=str(e))
            return False

    def health_check(self) -> dict[str, Any]:
        """Perform comprehensive health check on Ollama."""
        installed = self.is_installed()
        running = self._ping_server(timeout=2.0)
        models = self.list_installed_models(timeout=2.0) if running else []
        model_ready = any(
            m.lower() == self._model.lower() or m.lower().startswith(f"{self._model.lower()}:")
            for m in models
        )

        msg = "Ollama is ready and operational"
        if not installed:
            msg = "Ollama binary is not installed on system path (download at https://ollama.com)"
        elif not running:
            msg = f"Ollama is installed but not running at {self._base_url} (run 'ollama serve')"
        elif not model_ready:
            msg = f"Ollama is running, but model '{self._model}' is not pulled (run 'ollama pull {self._model}')"

        return {
            "provider": self.name,
            "installed": installed,
            "running": running,
            "model_ready": model_ready,
            "configured_model": self._model,
            "available_models": models,
            "message": msg,
        }

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate response via Ollama /api/chat with retries and exponential backoff."""
        start_time = time.perf_counter()

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 2):
            try:
                resp = requests.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                    timeout=self._timeout,
                )

                if resp.status_code == 404:
                    raise ModelNotFoundError(
                        f"Ollama model '{self._model}' was not found. Please run 'ollama pull {self._model}'.",
                        provider=self.name,
                        status_code=404,
                        fix_hint=f"ollama pull {self._model}",
                    )

                if resp.status_code != 200:
                    raise ProviderUnavailableError(
                        f"Ollama API returned HTTP {resp.status_code}: {resp.text[:200]}",
                        provider=self.name,
                        status_code=resp.status_code,
                    )

                data = resp.json()
                content = data.get("message", {}).get("content", "")
                input_tokens = data.get("prompt_eval_count", 0)
                output_tokens = data.get("eval_count", 0)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                return LLMResponse(
                    text=content,
                    model=self._model,
                    provider=self.name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=elapsed_ms,
                )

            except ModelNotFoundError:
                raise
            except Exception as e:
                last_error = e
                if attempt <= self._max_retries:
                    backoff = (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                    logger.warning(
                        "ollama_request_failed_retrying",
                        attempt=attempt,
                        backoff_sec=round(backoff, 2),
                        error=str(e),
                    )
                    time.sleep(backoff)
                else:
                    break

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        raise ProviderUnavailableError(
            f"Ollama provider failed after {self._max_retries + 1} attempts: {last_error}",
            provider=self.name,
            fix_hint="Ensure 'ollama serve' is running and responsive at http://localhost:11434",
        )

    def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> Iterator[str]:
        """Stream generated tokens via Ollama /api/chat with stream=True."""
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            with requests.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=self._timeout,
                stream=True,
            ) as resp:
                if resp.status_code != 200:
                    raise ProviderUnavailableError(
                        f"Ollama streaming failed with status {resp.status_code}",
                        provider=self.name,
                        status_code=resp.status_code,
                    )
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
        except Exception as e:
            raise ProviderUnavailableError(
                f"Ollama stream interrupted: {e}",
                provider=self.name,
            ) from e
