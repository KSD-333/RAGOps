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

DEFAULT_SYSTEM_PROMPT = """You are the official enterprise AI policy and compliance assistant for Carraro India Limited (CIL), part of the multinational Carraro Group.

## Organization & Repository Identity:
- Company: Carraro India Limited (CIL) / Carraro Group
- Industry Context: Carraro is an international engineering manufacturer specializing in transmission systems, axles, and driveline solutions for agricultural machinery (tractors) and construction equipment.
- Indexed Repository Scope: This knowledge base contains 33 internal corporate governance policies, codes of conduct, statutory compliance guidelines, and board procedures (such as POSH Prevention of Sexual Harassment Policy, Whistleblowing Vigil Mechanism, Code of Ethics, Materiality Policy, Board Diversity, CSR, and Insider Trading Regulations).

## Operational Guidelines:
1. Always answer questions accurately based on the provided context documents.
2. When asked about the company name, corporate background, products, or industry:
   - Identify the company as Carraro India Limited (CIL) / Carraro Group.
   - Clarify constructively that this RAG portal specifically indexes corporate compliance, ethics, statutory, and governance policies rather than commercial product brochures, technical catalogs, or founding archives.
   - Highlight the relevant compliance documents available (e.g., Code of Ethics, Whistleblower mechanism, Board governance).
3. For policy inquiries (e.g. POSH procedures, reporting channels, compliance officers), provide clear, step-by-step answers directly from the documents.
4. When conversation history is provided, resolve follow-up questions, pronouns ("it", "the committee", "who"), and continuity naturally.
5. Always cite your sources using [Source: filename] format.
6. Be polite, authoritative, professional, and helpful. Avoid harsh or robotic rejections."""


RAG_USER_PROMPT_TEMPLATE = """{history_block}## Context Documents:
{context}

## Current Question:
{query}

## Answer:"""


def build_system_prompt() -> str:
    """Build the system prompt from config or use default."""
    settings = get_settings()
    custom_prompt = settings.yaml_config.get("system_prompt")
    return custom_prompt if custom_prompt else DEFAULT_SYSTEM_PROMPT


def build_user_prompt(prompt_context: PromptContext) -> str:
    """Build the user prompt with context documents, conversation history, and query.

    Formats each context chunk with its source metadata for citation,
    and prepends recent conversational turns for multi-turn coherence.
    """
    # 1. Format Conversation History if present
    history_block = ""
    if prompt_context.chat_history:
        history_lines = ["## Conversation History (Recent Turns):"]
        for turn in prompt_context.chat_history[-3:]:
            q = turn.get("query", "").strip()
            a = turn.get("answer", "").strip()
            if q:
                history_lines.append(f"User: {q}")
            if a:
                # Truncate lengthy past answers to preserve prompt budget
                short_a = a[:350].strip()
                if len(a) > 350:
                    short_a += "..."
                history_lines.append(f"Assistant: {short_a}")
        history_block = "\n".join(history_lines) + "\n\n"

    # 2. Format Context Chunks
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

        # Clean replacement characters from text
        clean_text = text.replace("\ufffd", "'").replace(" \ufffd ", " ' ")
        context_parts.append(f"{header}\n{clean_text}")

    context_text = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant context found."

    return RAG_USER_PROMPT_TEMPLATE.format(
        history_block=history_block,
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
