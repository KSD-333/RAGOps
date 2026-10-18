"""Generation schemas — request/response models for the generation module."""

from __future__ import annotations

from pydantic import BaseModel


class GenerationRequest(BaseModel):
    """Request for LLM generation."""
    system_prompt: str
    user_prompt: str
    temperature: float = 0.1
    max_tokens: int = 2048
    model: str | None = None


class GenerationConfig(BaseModel):
    """Configuration for generation behavior."""
    include_citations: bool = True
    max_context_length: int = 4000
    response_format: str = "text"  # text | json
