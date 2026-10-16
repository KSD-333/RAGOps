"""Unit tests for generation evaluation metrics."""

from __future__ import annotations

import pytest
from ragops.evaluation.generation import (
    answer_relevance_heuristic,
    citation_accuracy,
    faithfulness_heuristic,
)


def test_answer_relevance_heuristic():
    question = "What is the capital of France?"
    good_answer = "The capital of France is Paris."
    bad_answer = "Quantum computing uses qubits."

    score_good = answer_relevance_heuristic(question, good_answer)
    score_bad = answer_relevance_heuristic(question, bad_answer)

    assert score_good > score_bad
    assert score_good > 0.5
    assert answer_relevance_heuristic("", "") == 0.0


def test_citation_accuracy():
    cited = ["arch.md", "sec.md"]
    retrieved = ["arch.md", "sec.md", "ops.md"]
    assert citation_accuracy(cited, retrieved) == 1.0

    cited_hallucinated = ["arch.md", "ghost.md"]
    assert citation_accuracy(cited_hallucinated, retrieved) == 0.5
    assert citation_accuracy([], retrieved) == 1.0


def test_faithfulness_heuristic():
    context = ["PostgreSQL with pgvector provides similarity search."]
    faithful_answer = "PostgreSQL provides similarity search."
    unfaithful_answer = "Mongo database supports clustering algorithms."

    faithful_score = faithfulness_heuristic(faithful_answer, context)
    unfaithful_score = faithfulness_heuristic(unfaithful_answer, context)

    assert faithful_score > unfaithful_score
