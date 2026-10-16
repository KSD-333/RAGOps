"""Prompt templates — construct prompts for the LLM.

Owns:
- System prompts
- User prompt construction with context
- Citation formatting

Does NOT know how documents are retrieved.
"""

from __future__ import annotations

from ragops.core.config import get_settings
from ragops.core.types import PromptContext

DEFAULT_SYSTEM_PROMPT = """You are a knowledgeable AI assistant for the RAGOps platform. Your role is to answer questions accurately based ONLY on the provided context documents.

## Instructions:
1. Answer the question using ONLY the information from the provided context
2. If the context doesn't contain enough information to answer fully, clearly state what you can and cannot answer
3. Always cite your sources using [Source: filename] format
4. Be concise but thorough
5. If multiple sources provide relevant information, synthesize them into a coherent answer
6. Never fabricate information not present in the context

## Response Format:
- Start with a direct answer
- Provide supporting details from the context
- End with source citations"""


RAG_USER_PROMPT_TEMPLATE = """## Context Documents:
{context}

## Question:
{query}

## Answer:"""


def build_system_prompt() -> str:
    """Build the system prompt from config or use default."""
    settings = get_settings()
    custom_prompt = settings.yaml_config.get("system_prompt")
    return custom_prompt if custom_prompt else DEFAULT_SYSTEM_PROMPT


def build_user_prompt(prompt_context: PromptContext) -> str:
    """Build the user prompt with context documents and query.

    Formats each context chunk with its source metadata for citation.
    """
    context_parts: list[str] = []

    for i, (text, source) in enumerate(
        zip(prompt_context.context, prompt_context.sources), start=1
    ):
        source_name = source.get("source", f"Document {i}")
        chunk_id = source.get("chunk_id", "")
        section = source.get("section", "")

        header = f"[Document {i} | Source: {source_name}"
        if section:
            header += f" | Section: {section}"
        if chunk_id:
            header += f" | Chunk: {chunk_id}"
        header += "]"

        context_parts.append(f"{header}\n{text}")

    context_text = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant context found."

    return RAG_USER_PROMPT_TEMPLATE.format(
        context=context_text,
        query=prompt_context.query,
    )


def build_evaluation_prompt(question: str, answer: str, context: str) -> str:
    """Build a prompt for LLM-as-a-judge evaluation."""
    return f"""Evaluate the following answer based on the provided context.

## Context:
{context}

## Question:
{question}

## Answer to Evaluate:
{answer}

## Evaluation Criteria:
1. **Faithfulness** (0-1): Is the answer grounded in the context? Does it avoid hallucination?
2. **Relevance** (0-1): Does the answer directly address the question?
3. **Completeness** (0-1): Does the answer cover the key information from the context?

Respond in this exact JSON format:
{{
    "faithfulness": <score>,
    "relevance": <score>,
    "completeness": <score>,
    "reasoning": "<brief explanation>"
}}"""
