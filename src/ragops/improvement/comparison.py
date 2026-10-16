"""Comparison — compare candidate vs production evaluation results."""

from __future__ import annotations

from ragops.core.logging import get_logger
from ragops.core.types import EvaluationResult

logger = get_logger(__name__)


class VersionComparison:
    """Compare two RAG versions side-by-side."""

    def compare(
        self,
        candidate: EvaluationResult,
        production: EvaluationResult,
    ) -> dict:
        """Generate a comparison report between two versions."""
        metrics = {
            "retrieval_recall": {
                "candidate": candidate.retrieval_recall,
                "production": production.retrieval_recall,
                "delta": candidate.retrieval_recall - production.retrieval_recall,
                "improved": candidate.retrieval_recall >= production.retrieval_recall,
            },
            "faithfulness": {
                "candidate": candidate.faithfulness,
                "production": production.faithfulness,
                "delta": candidate.faithfulness - production.faithfulness,
                "improved": candidate.faithfulness >= production.faithfulness,
            },
            "answer_relevance": {
                "candidate": candidate.answer_relevance,
                "production": production.answer_relevance,
                "delta": candidate.answer_relevance - production.answer_relevance,
                "improved": candidate.answer_relevance >= production.answer_relevance,
            },
            "p95_latency_ms": {
                "candidate": candidate.p95_latency_ms,
                "production": production.p95_latency_ms,
                "delta": candidate.p95_latency_ms - production.p95_latency_ms,
                "improved": candidate.p95_latency_ms <= production.p95_latency_ms,
            },
            "citation_accuracy": {
                "candidate": candidate.citation_accuracy,
                "production": production.citation_accuracy,
                "delta": candidate.citation_accuracy - production.citation_accuracy,
                "improved": candidate.citation_accuracy >= production.citation_accuracy,
            },
        }

        overall_improved = sum(1 for m in metrics.values() if m["improved"])
        total_metrics = len(metrics)

        return {
            "candidate_version": candidate.rag_version,
            "production_version": production.rag_version,
            "metrics": metrics,
            "overall_improved": overall_improved,
            "total_metrics": total_metrics,
            "recommendation": "promote" if overall_improved >= 3 else "reject",
        }
