"""Unit tests for QualityGate promotion decisions."""

from __future__ import annotations

import pytest
from ragops.core.types import EvaluationResult, PromotionStatus
from ragops.improvement.quality_gate import QualityGate


def test_quality_gate_passes_when_metrics_exceed_thresholds():
    gate = QualityGate(
        recall_threshold=0.80,
        faithfulness_threshold=0.85,
        relevance_threshold=0.80,
        latency_p95_threshold_ms=3000,
    )
    candidate = EvaluationResult(
        dataset_version="golden_v1",
        rag_version="v2.0",
        retrieval_recall=0.88,
        retrieval_precision=0.85,
        mrr=0.90,
        faithfulness=0.92,
        answer_relevance=0.88,
        citation_accuracy=0.95,
        p50_latency_ms=800,
        p95_latency_ms=1500,
        sample_count=10,
    )

    decision = gate.evaluate(candidate)
    assert decision.status == PromotionStatus.PASS
    assert decision.candidate_version == "v2.0"


def test_quality_gate_fails_when_faithfulness_below_threshold():
    gate = QualityGate(
        recall_threshold=0.80,
        faithfulness_threshold=0.90,
        relevance_threshold=0.80,
        latency_p95_threshold_ms=3000,
    )
    candidate = EvaluationResult(
        dataset_version="golden_v1",
        rag_version="v2.0-bad",
        retrieval_recall=0.88,
        retrieval_precision=0.85,
        mrr=0.90,
        faithfulness=0.72,  # Below 0.90
        answer_relevance=0.88,
        citation_accuracy=0.95,
        p50_latency_ms=800,
        p95_latency_ms=1500,
        sample_count=10,
    )

    decision = gate.evaluate(candidate)
    assert decision.status == PromotionStatus.FAIL
    assert any("Faithfulness" in r or "faithfulness" in r for r in decision.reasons)

