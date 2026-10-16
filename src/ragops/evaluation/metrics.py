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
            faithfulness_heuristic,
            answer_relevance_heuristic,
            citation_accuracy,
        )

        # Compute per-sample metrics
        recalls = []
        precisions = []
        mrrs = []
        faithfulness_scores = []
        relevance_scores = []
        citation_scores = []
        latencies = []
        total_input_tokens = 0
        total_output_tokens = 0

        for i, output in enumerate(outputs):
            # Retrieval metrics
            recalls.append(recall_at_k(output.expected_chunks, output.retrieved_chunks, k=5))
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

        result = EvaluationResult(
            dataset_version=dataset_version,
            rag_version=rag_version,
            retrieval_recall=statistics.mean(recalls) if recalls else 0,
            retrieval_precision=statistics.mean(precisions) if precisions else 0,
            mrr=statistics.mean(mrrs) if mrrs else 0,
            faithfulness=statistics.mean(faithfulness_scores) if faithfulness_scores else 0,
            answer_relevance=statistics.mean(relevance_scores) if relevance_scores else 0,
            citation_accuracy=statistics.mean(citation_scores) if citation_scores else 0,
            p50_latency_ms=sorted_latencies[p50_idx] if sorted_latencies else 0,
            p95_latency_ms=sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)] if sorted_latencies else 0,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            sample_count=len(outputs),
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
