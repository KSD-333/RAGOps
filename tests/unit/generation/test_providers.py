"""Unit tests for LLM providers, circuit breaker, and router."""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch
import pytest

# Ensure SQLite is used during unit tests to avoid postgres connection timeout
os.environ["DATABASE_URL"] = "sqlite:///data/ragops.db"

from ragops.core.exceptions import (
    CircuitBreakerOpenError,
    ModelNotFoundError,
    ProviderUnavailableError,
)
from ragops.core.types import LLMResponse
from ragops.generation.providers.base import LLMProvider
from ragops.generation.providers.groq_provider import GroqProvider, mask_secret
from ragops.generation.providers.ollama_provider import OllamaProvider
from ragops.generation.providers.router import CircuitBreaker, LLMRouter


def test_mask_secret():
    assert mask_secret("") == "<not-set>"
    assert mask_secret(None) == "<not-set>"
    assert mask_secret("short") == "***"
    assert mask_secret("gsk_1234567890abcdef") == "gsk_...cdef"


def test_circuit_breaker_transitions():
    cb = CircuitBreaker(failure_threshold=3, reset_timeout_seconds=0.1)
    assert cb.state == "CLOSED"
    assert cb.is_available() is True

    # 2 failures do not trip
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "CLOSED"
    assert cb.is_available() is True

    # 3rd failure trips
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.is_available() is False

    # After cooldown, allow request should transition to HALF_OPEN
    time.sleep(0.12)
    assert cb.is_available() is True
    assert cb.state == "HALF_OPEN"

    # Success resets to CLOSED
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.failure_count == 0


def test_ollama_provider_health_check_not_installed():
    with patch("shutil.which", return_value=None), patch("requests.get", side_effect=Exception("Connection refused")):
        provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.2:3b")
        status = provider.health_check()
        assert status["installed"] is False
        assert status["running"] is False
        assert status["model_ready"] is False


def test_ollama_provider_health_check_running_model_ready():
    with patch("shutil.which", return_value="/usr/bin/ollama"):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "models": [{"name": "llama3.2:3b"}, {"name": "mistral:latest"}]
            }
            mock_get.return_value = mock_resp

            provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.2:3b")
            status = provider.health_check()
            assert status["installed"] is True
            assert status["running"] is True
            assert status["model_ready"] is True


def test_ollama_provider_health_check_model_missing():
    with patch("shutil.which", return_value="/usr/bin/ollama"):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"models": [{"name": "mistral:latest"}]}
            mock_get.return_value = mock_resp

            provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.2:3b")
            status = provider.health_check()
            assert status["installed"] is True
            assert status["running"] is True
            assert status["model_ready"] is False


def test_groq_provider_health_check_no_key():
    provider = GroqProvider(api_key="", model="llama-3.3-70b-versatile")
    status = provider.health_check()
    assert status["key_present"] is False
    assert status["reachable"] is False


def test_groq_provider_health_check_auth_error():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Invalid API Key"
        mock_get.return_value = mock_resp

        provider = GroqProvider(api_key="bad_key_12345678", model="llama-3.3-70b-versatile")
        status = provider.health_check()
        assert status["key_present"] is True
        assert status["reachable"] is False
        assert "401" in status["message"] or "Invalid" in status["message"]


def test_groq_provider_health_check_success():
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"id": "llama-3.3-70b-versatile"}, {"id": "mixtral-8x7b-32768"}]
        }
        mock_get.return_value = mock_resp

        provider = GroqProvider(api_key="gsk_valid_12345678", model="llama-3.3-70b-versatile")
        status = provider.health_check()
        assert status["key_present"] is True
        assert status["reachable"] is True
        assert status["model_in_list"] is True
        assert status["available_models_count"] == 2


def test_router_auto_mode_ollama_success():
    mock_ollama = MagicMock(spec=OllamaProvider)
    mock_ollama.name = "ollama"
    mock_ollama.model_name = "llama3.2:3b"
    mock_ollama.is_installed.return_value = True
    mock_ollama._ping_server.return_value = True
    mock_ollama.is_model_installed.return_value = True
    mock_ollama.generate.return_value = LLMResponse(
        text="Hello from Ollama",
        model="llama3.2:3b",
        provider="ollama",
        input_tokens=10,
        output_tokens=5,
        latency_ms=100.0,
    )

    mock_groq = MagicMock(spec=GroqProvider)
    mock_groq.name = "groq"
    mock_groq.model_name = "llama-3.3-70b-versatile"
    mock_groq.is_key_present.return_value = True

    router = LLMRouter(mode="auto", ollama_provider=mock_ollama, groq_provider=mock_groq)
    resp = router.generate("System", "User prompt")

    assert resp.provider == "ollama"
    assert resp.text == "Hello from Ollama"
    assert router.last_provider_used == "ollama"
    assert router.last_fallback_used is False


def test_router_auto_mode_ollama_fails_groq_fallback():
    mock_ollama = MagicMock(spec=OllamaProvider)
    mock_ollama.name = "ollama"
    mock_ollama.model_name = "llama3.2:3b"
    mock_ollama.is_installed.return_value = True
    mock_ollama._ping_server.return_value = True
    mock_ollama.is_model_installed.return_value = True
    mock_ollama.generate.side_effect = ProviderUnavailableError("Ollama crashed")

    mock_groq = MagicMock(spec=GroqProvider)
    mock_groq.name = "groq"
    mock_groq.model_name = "llama-3.3-70b-versatile"
    mock_groq.is_key_present.return_value = True
    mock_groq.generate.return_value = LLMResponse(
        text="Hello from Groq fallback",
        model="llama-3.3-70b-versatile",
        provider="groq",
        input_tokens=10,
        output_tokens=6,
        latency_ms=120.0,
    )

    router = LLMRouter(mode="auto", ollama_provider=mock_ollama, groq_provider=mock_groq)
    resp = router.generate("System", "User prompt")

    assert resp.provider == "groq"
    assert resp.text == "Hello from Groq fallback"
    assert router.last_provider_used == "groq"
    assert router.last_fallback_used is True
    assert "Ollama crashed" in router.last_provider_error


def test_router_degraded_mode_when_both_fail():
    mock_ollama = MagicMock(spec=OllamaProvider)
    mock_ollama.name = "ollama"
    mock_ollama.model_name = "llama3.2:3b"
    mock_ollama.is_installed.return_value = False
    mock_ollama._ping_server.return_value = False
    mock_ollama.is_model_installed.return_value = False
    mock_ollama.generate.side_effect = ProviderUnavailableError("No ollama")

    mock_groq = MagicMock(spec=GroqProvider)
    mock_groq.name = "groq"
    mock_groq.model_name = "llama-3.3-70b-versatile"
    mock_groq.is_key_present.return_value = False
    mock_groq.generate.side_effect = ProviderUnavailableError("No groq key")

    router = LLMRouter(mode="auto", ollama_provider=mock_ollama, groq_provider=mock_groq)
    resp = router.generate("System", "User prompt")

    assert resp.provider == "degraded"
    assert "[Degraded Mode]" in resp.text
    assert "ragops doctor" in resp.text
    assert "Ollama" in resp.text
    assert "GROQ_API_KEY" in resp.text
