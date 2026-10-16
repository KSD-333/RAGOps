"""Generation evaluation metrics — faithfulness, answer relevance, citation accuracy."""

from __future__ import annotations

from ragops.core.logging import get_logger

logger = get_logger(__name__)


def answer_relevance_heuristic(question: str, answer: str) -> float:
    """Simple answer relevance score based on question term coverage.

    For production, use LLM-as-judge (see judges.py).
    """
    if not answer or not question:
        return 0.0

    question_terms = set(question.lower().split())
    answer_terms = set(answer.lower().split())

    # What fraction of question terms appear in the answer?
    if not question_terms:
        return 0.0

    overlap = len(question_terms & answer_terms)
    coverage = overlap / len(question_terms)
    return min(coverage, 1.0)


def citation_accuracy(
    cited_sources: list[str],
    retrieved_sources: list[str],
) -> float:
    """Check if cited sources match actually retrieved sources.

    Citation accuracy = |cited ∩ retrieved| / |cited|
    """
    if not cited_sources:
        return 1.0  # No citations = nothing wrong

    correct = sum(
        1
        for cited in cited_sources
        if any(cited == ret or cited in ret or ret in cited for ret in retrieved_sources)
    )
    return correct / len(cited_sources)


def faithfulness_heuristic(answer: str, context_texts: list[str]) -> float:
    """Simple faithfulness heuristic — how much of the answer is grounded in context.

    Measures token-level overlap between answer and context.
    For production, use LLM-as-judge (see judges.py).
    """
    if not answer or not context_texts:
        return 0.0

    # Combine all context
    context_combined = " ".join(context_texts).lower()
    context_tokens = set(context_combined.split())

    answer_tokens = set(answer.lower().split())
    if not answer_tokens:
        return 0.0

    # What fraction of answer tokens appear in context?
    # Filter out common words for a more meaningful score
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "to", "of", "and", "in", "for", "on", "with", "at", "by", "it", "this", "that"}
    meaningful_answer_tokens = answer_tokens - stopwords
    meaningful_context_tokens = context_tokens - stopwords

    if not meaningful_answer_tokens:
        return 1.0

    grounded = len(meaningful_answer_tokens & meaningful_context_tokens)
    return grounded / len(meaningful_answer_tokens)
