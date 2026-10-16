"""Unit tests for ResponseBuilder."""

from __future__ import annotations

import pytest
from ragops.core.types import LLMResponse
from ragops.generation.response import ResponseBuilder


def test_response_builder_constructs_sources_and_metadata(sample_retrieved_context):
    builder = ResponseBuilder()
    llm_resp = LLMResponse(
        text="RAGOps uses Sentence Transformers for dense retrieval.",
        model="llama-3.1-70b-versatile",
        input_tokens=150,
        output_tokens=30,
        latency_ms=120.5,
    )

    rag_response = builder.build(
        llm_response=llm_resp,
        retrieved_context=sample_retrieved_context,
        trace_id="test_trace_123",
    )

    assert rag_response.answer == llm_resp.text
    assert rag_response.trace_id == "test_trace_123"
    assert len(rag_response.sources) == len(sample_retrieved_context.chunks)
    assert rag_response.sources[0].document == "architecture_guide.md"
    assert rag_response.metadata["model"] == "llama-3.1-70b-versatile"
    assert rag_response.metadata["input_tokens"] == 150
    assert rag_response.metadata["output_tokens"] == 30
