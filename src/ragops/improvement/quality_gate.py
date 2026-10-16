"""Quality gate — determines whether a new RAG version should be promoted.

Flow:
  Candidate EvaluationResult + Production EvaluationResult + Thresholds
    → QualityGate
    → PromotionDecision (PASS / FAIL)
"""

from __future__ import annotations

from ragops.core.config import get_settings
from ragops.core.logging import get_logger
from ragops.core.types import EvaluationResult, PromotionDecision, PromotionStatus

logger = get_logger(__name__)


class QualityGate:
    """Evaluate whether a candidate RAG version should be promoted to production.

    Compares candidate metrics against:
    1. Absolute thresholds (minimum acceptable quality)
    2. Production baseline (no regression)
    """

    def __init__(
        self,
        recall_threshold: float | None = None,
        faithfulness_threshold: float | None = None,
        relevance_threshold: float | None = None,
        latency_p95_threshold_ms: float | None = None,
    ):
        settings = get_settings()
        eval_config = settings.yaml_config.get("evaluation", {})

        self._recall_threshold = recall_threshold or eval_config.get("retrieval_recall_threshold", 0.85)
        self._faithfulness_threshold = faithfulness_threshold or eval_config.get("faithfulness_threshold", 0.90)
        self._relevance_threshold = relevance_threshold or eval_config.get("relevance_threshold", 0.85)
        self._latency_threshold = latency_p95_threshold_ms or eval_config.get("latency_p95_threshold_ms", 3000)

    def evaluate(
        self,
        candidate: EvaluationResult,
        production: EvaluationResult | None = None,
    ) -> PromotionDecision:
        """Evaluate whether the candidate should be promoted.

        Checks:
        1. Candidate meets absolute thresholds
        2. Candidate doesn't regress vs. production (if available)
        """
        reasons: list[str] = []
        failures: list[str] = []

        # Check absolute thresholds
        if candidate.retrieval_recall >= self._recall_threshold:
            reasons.append(
                f"Retrieval recall {candidate.retrieval_recall:.3f} >= {self._recall_threshold}"
            )
        else:
            failures.append(
                f"Retrieval recall {candidate.retrieval_recall:.3f} < {self._recall_threshold}"
            )

        if candidate.faithfulness >= self._faithfulness_threshold:
            reasons.append(
                f"Faithfulness {candidate.faithfulness:.3f} >= {self._faithfulness_threshold}"
            )
        else:
            failures.append(
                f"Faithfulness {candidate.faithfulness:.3f} < {self._faithfulness_threshold}"
            )

        if candidate.answer_relevance >= self._relevance_threshold:
            reasons.append(
                f"Relevance {candidate.answer_relevance:.3f} >= {self._relevance_threshold}"
            )
        else:
            failures.append(
                f"Relevance {candidate.answer_relevance:.3f} < {self._relevance_threshold}"
            )

        if candidate.p95_latency_ms <= self._latency_threshold:
            reasons.append(
                f"P95 latency {candidate.p95_latency_ms:.0f}ms <= {self._latency_threshold}ms"
            )
        else:
            failures.append(
                f"P95 latency {candidate.p95_latency_ms:.0f}ms > {self._latency_threshold}ms"
            )

        # Check for regression against production
        if production:
            regression_checks = self._check_regression(candidate, production)
            reasons.extend(regression_checks["improvements"])
            failures.extend(regression_checks["regressions"])

        # Decision
        status = PromotionStatus.PASS if not failures else PromotionStatus.FAIL
        all_reasons = (
            [f"[PASS] {r}" for r in reasons] + [f"[FAIL] {f}" for f in failures]
        )


        decision = PromotionDecision(
            status=status,
            candidate_version=candidate.rag_version,
            production_version=production.rag_version if production else "",
            reasons=all_reasons,
            candidate_metrics={
                "retrieval_recall": candidate.retrieval_recall,
                "faithfulness": candidate.faithfulness,
                "answer_relevance": candidate.answer_relevance,
                "p95_latency_ms": candidate.p95_latency_ms,
            },
            production_metrics={
                "retrieval_recall": production.retrieval_recall if production else 0,
                "faithfulness": production.faithfulness if production else 0,
                "answer_relevance": production.answer_relevance if production else 0,
                "p95_latency_ms": production.p95_latency_ms if production else 0,
            } if production else {},
        )

        log_fn = logger.info if status == PromotionStatus.PASS else logger.warning
        log_fn(
            "quality_gate_decision",
            status=status.value,
            candidate=candidate.rag_version,
            reasons_count=len(all_reasons),
        )

        return decision

    def _check_regression(
        self,
        candidate: EvaluationResult,
        production: EvaluationResult,
    ) -> dict[str, list[str]]:
        """Check for regression against production metrics."""
        improvements: list[str] = []
        regressions: list[str] = []

        metrics = [
            ("retrieval_recall", candidate.retrieval_recall, production.retrieval_recall, True),
            ("faithfulness", candidate.faithfulness, production.faithfulness, True),
            ("answer_relevance", candidate.answer_relevance, production.answer_relevance, True),
            ("p95_latency_ms", candidate.p95_latency_ms, production.p95_latency_ms, False),
        ]

        for name, candidate_val, prod_val, higher_is_better in metrics:
            if higher_is_better:
                if candidate_val >= prod_val:
                    improvements.append(f"{name} improved: {prod_val:.3f} → {candidate_val:.3f}")
                else:
                    diff = prod_val - candidate_val
                    if diff > 0.05:  # > 5% regression
                        regressions.append(
                            f"{name} regressed significantly: {prod_val:.3f} → {candidate_val:.3f}"
                        )
            else:
                if candidate_val <= prod_val:
                    improvements.append(f"{name} improved: {prod_val:.0f} → {candidate_val:.0f}")
                else:
                    diff_pct = (candidate_val - prod_val) / prod_val * 100 if prod_val > 0 else 0
                    if diff_pct > 20:  # > 20% latency increase
                        regressions.append(
                            f"{name} regressed: {prod_val:.0f} → {candidate_val:.0f} (+{diff_pct:.0f}%)"
                        )

        return {"improvements": improvements, "regressions": regressions}
