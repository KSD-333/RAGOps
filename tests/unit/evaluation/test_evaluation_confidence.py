"""Tests for Wilson score confidence intervals and external evaluation harness."""

import os
os.environ["DATABASE_URL"] = "sqlite:///data/ragops.db"

from unittest.mock import patch
import pytest

from ragops.evaluation.confidence import wilson_score_interval, is_grounded_abstention
from ragops.evaluation.external_eval import run_ragas_evaluation, is_ragas_available, is_deepeval_available
from ragops.evaluation.metrics import MetricsAggregator
from ragops.core.types import EvaluationOutput


def test_wilson_score_interval_valid():
    # 95 out of 100
    ci = wilson_score_interval(95, 100, confidence=0.95)
    assert ci["sample_size"] == 100
    assert ci["successes"] == 95
    assert ci["proportion"] == 0.95
    assert 0.88 <= ci["ci_lower"] <= 0.92
    assert 0.97 <= ci["ci_upper"] <= 0.99
    assert ci["ci_lower"] < ci["ci_upper"]


def test_wilson_score_interval_perfect_score():
    # 15 out of 15 (100% abstention on golden set)
    ci = wilson_score_interval(15, 15, confidence=0.95)
    assert ci["proportion"] == 1.0
    # Center is pulled inward, lower bound is ~0.796
    assert 0.78 <= ci["ci_lower"] <= 0.82
    assert ci["ci_upper"] == 1.0


def test_wilson_score_interval_zero_hits():
    # 0 out of 20
    ci = wilson_score_interval(0, 20, confidence=0.95)
    assert ci["proportion"] == 0.0
    assert ci["ci_lower"] == 0.0
    assert 0.15 <= ci["ci_upper"] <= 0.20


def test_wilson_score_interval_zero_sample():
    # 0 out of 0
    ci = wilson_score_interval(0, 0)
    assert ci["sample_size"] == 0
    assert ci["proportion"] == 0.0
    assert ci["ci_lower"] == 0.0
    assert ci["ci_upper"] == 0.0


def test_is_grounded_abstention():
    # True positives
    assert is_grounded_abstention("I do not have sufficient information in the knowledge base to answer.")
    assert is_grounded_abstention("Based on the provided documents, I cannot answer this.")
    assert is_grounded_abstention("The retrieved documents do not contain information regarding this question.")
    assert is_grounded_abstention("Not enough context provided.")

    # False (actual answers)
    assert not is_grounded_abstention("RAGOps uses Sentence Transformers with 384 dimensions.")
    assert not is_grounded_abstention("All API requests must use TLS 1.3.")


def test_metrics_aggregator_computes_wilson_ci():
    aggregator = MetricsAggregator()
    outputs = [
        # In-domain hit
        EvaluationOutput(
            question="What is the default embedding?",
            expected_answer="all-MiniLM-L6-v2",
            actual_answer="all-MiniLM-L6-v2 with 384 dimensions",
            expected_chunks=["arch.md"],
            retrieved_chunks=["arch.md:0"],
            sources=[],
            latency_ms=10.0,
            input_tokens=10,
            output_tokens=10,
        ),
        # In-domain miss
        EvaluationOutput(
            question="What is the vector db?",
            expected_answer="ChromaDB",
            actual_answer="Unknown",
            expected_chunks=["arch.md"],
            retrieved_chunks=["other.md:0"],
            sources=[],
            latency_ms=10.0,
            input_tokens=10,
            output_tokens=10,
        ),
        # Abstention query (expected_chunks is empty)
        EvaluationOutput(
            question="What is the capital of Australia?",
            expected_answer="Unknown",
            actual_answer="I do not have sufficient information to answer this question.",
            expected_chunks=[],
            retrieved_chunks=[],
            sources=[],
            latency_ms=10.0,
            input_tokens=10,
            output_tokens=10,
        ),
    ]

    result = aggregator.aggregate(outputs, dataset_version="test", rag_version="v1")
    assert result.sample_count == 3
    assert result.recall_sample_size == 2
    assert result.recall_wilson_ci_95["sample_size"] == 2
    assert result.recall_wilson_ci_95["successes"] == 1
    assert result.recall_wilson_ci_95["proportion"] == 0.5

    assert result.abstention_sample_size == 1
    assert result.abstention_accuracy == 1.0
    assert result.abstention_wilson_ci_95["sample_size"] == 1
    assert result.abstention_wilson_ci_95["proportion"] == 1.0


def test_ragas_evaluation_skipped_gracefully():
    with patch("ragops.evaluation.external_eval.is_ragas_available", return_value=False):
        res = run_ragas_evaluation(
            questions=["Q1"],
            answers=["A1"],
            contexts=[["C1"]],
        )
        assert res["status"] == "skipped"
        assert "not installed" in res["reason"]
