"""Unit tests for prompt generation templates."""

from __future__ import annotations

import pytest
from ragops.core.types import PromptContext
from ragops.generation.prompts import (
    DEFAULT_SYSTEM_PROMPT,
    build_evaluation_prompt,
    build_system_prompt,
    build_user_prompt,
)


def test_build_system_prompt_returns_valid_string():
    prompt = build_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 20
    assert "context" in prompt.lower()


def test_build_user_prompt_formats_sources_and_query():
    ctx = PromptContext(
        query="How does auth work?",
        context=["Auth uses OAuth 2.0 with JWT tokens."],
        sources=[{"source": "auth_spec.md", "chunk_id": "c1", "section": "Security"}],
    )
    user_prompt = build_user_prompt(ctx)
    assert "How does auth work?" in user_prompt
    assert "Auth uses OAuth 2.0 with JWT tokens." in user_prompt
    assert "auth_spec.md" in user_prompt


def test_build_evaluation_prompt_contains_criteria():
    eval_prompt = build_evaluation_prompt(
        question="What is the port?",
        answer="The port is 8000.",
        context="API runs on port 8000.",
    )
    assert "faithfulness" in eval_prompt
    assert "relevance" in eval_prompt
    assert "What is the port?" in eval_prompt
    assert "The port is 8000." in eval_prompt
