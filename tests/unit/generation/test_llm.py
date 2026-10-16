"""Unit tests for LLM clients."""

from __future__ import annotations

import pytest
from ragops.generation.llm import MockLLMClient


def test_mock_llm_client_generates_response():
    client = MockLLMClient(model="custom-mock-llama")
    assert client.model_name == "custom-mock-llama"

    resp = client.generate(
        system_prompt="You are a helper.",
        user_prompt="Explain RAGOps architecture in two sentences.",
    )

    assert resp.model == "custom-mock-llama"
    assert len(resp.text) > 10
    assert resp.input_tokens > 0
    assert resp.output_tokens > 0
    assert resp.latency_ms > 0
