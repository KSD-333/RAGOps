"""Metrics aggregator — combines retrieval and generation metrics."""

from __future__ import annotations

import statistics

from ragops.core.logging import get_logger
from ragops.core.types import EvaluationOutput, EvaluationResult

logger = get_logger(__name__)


class MetricsAggregator:
    """Aggregate evaluation outputs into a single EvaluationResult."""

    def aggregate(
        self,
        outputs: list[EvaluationOutput],
        dataset_version: str,
        rag_version: str,
        judge_scores: list[dict[str, float]] | None = None,
    ) -> EvaluationResult:
        """Aggregate individual evaluation outputs into summary metrics."""
        if not outputs:
            return EvaluationResult(
                dataset_version=dataset_version,
                rag_version=rag_version,
            )

        from ragops.evaluation.retrieval import recall_at_k, precision_at_k, mrr
        from ragops.evaluation.generation import (
            answer_relevance_heuristic,
            citation_accuracy,
        )
        from ragops.evaluation.confidence import (
            is_grounded_abstention,
            wilson_score_interval,
        )

        # Compute per-sample metrics
        recalls = []
        in_domain_recalls = []
        recall_hits = 0
        abstention_successes = 0
        abstention_total = 0

        precisions = []
        mrrs = []
        faithfulness_scores = []
        relevance_scores = []
        citation_scores = []
        latencies = []
        total_input_tokens = 0
        total_output_tokens = 0

        for i, output in enumerate(outputs):
            is_abstention_test = (not output.expected_chunks)

            if is_abstention_test:
                abstention_total += 1
                if is_grounded_abstention(output.actual_answer):
                    abstention_successes += 1
            else:
                r_k = recall_at_k(output.expected_chunks, output.retrieved_chunks, k=5)
                recalls.append(r_k)
                in_domain_recalls.append(r_k)
                if r_k > 0.0:
                    recall_hits += 1

            # Precision & MRR
            precisions.append(precision_at_k(output.expected_chunks, output.retrieved_chunks, k=5))
            mrrs.append(mrr(output.expected_chunks, output.retrieved_chunks))

            # Generation metrics (heuristic or LLM-judge)
            if judge_scores and i < len(judge_scores):
                faithfulness_scores.append(judge_scores[i].get("faithfulness", 0))
                relevance_scores.append(judge_scores[i].get("relevance", 0))
            else:
                # Fallback to heuristic scoring
                # For faithfulness, we need context — use retrieved_chunks as proxy
                faithfulness_scores.append(0.5)  # Placeholder without context
                relevance_scores.append(
                    answer_relevance_heuristic(output.question, output.actual_answer)
                )

            # Citation metrics
            cited = [s.document for s in output.sources]
            retrieved = output.retrieved_chunks
            citation_scores.append(citation_accuracy(cited, retrieved) if cited else 1.0)

            # System metrics
            latencies.append(output.latency_ms)
            total_input_tokens += output.input_tokens
            total_output_tokens += output.output_tokens

        # Aggregate
        sorted_latencies = sorted(latencies)
        p50_idx = len(sorted_latencies) // 2
        p95_idx = int(len(sorted_latencies) * 0.95)

        # Compute 95% Wilson Confidence Intervals
        recall_ci = wilson_score_interval(recall_hits, len(in_domain_recalls))
        abstention_ci = wilson_score_interval(abstention_successes, abstention_total)

        result = EvaluationResult(
            dataset_version=dataset_version,
            rag_version=rag_version,
            retrieval_recall=statistics.mean(recalls) if recalls else 0.0,
            retrieval_precision=statistics.mean(precisions) if precisions else 0.0,
            mrr=statistics.mean(mrrs) if mrrs else 0.0,
            faithfulness=statistics.mean(faithfulness_scores) if faithfulness_scores else 0.0,
            answer_relevance=statistics.mean(relevance_scores) if relevance_scores else 0.0,
            citation_accuracy=statistics.mean(citation_scores) if citation_scores else 0.0,
            p50_latency_ms=sorted_latencies[p50_idx] if sorted_latencies else 0.0,
            p95_latency_ms=sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)] if sorted_latencies else 0.0,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            sample_count=len(outputs),
            recall_sample_size=len(in_domain_recalls),
            recall_wilson_ci_95=recall_ci,
            abstention_accuracy=abstention_ci["proportion"],
            abstention_sample_size=abstention_total,
            abstention_wilson_ci_95=abstention_ci,
        )

        logger.info(
            "metrics_aggregated",
            recall=round(result.retrieval_recall, 3),
            faithfulness=round(result.faithfulness, 3),
            relevance=round(result.answer_relevance, 3),
            p95_latency=round(result.p95_latency_ms, 1),
            samples=result.sample_count,
        )

        return result
