"""Evaluation runner — runs the evaluation pipeline end-to-end.

Flow: Golden Dataset → RAG Pipeline → Metrics → EvaluationResult

IMPORTANT: Reuses the SAME RAG pipeline used in production.
Do NOT create a separate "fake RAG" for evaluation.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ragops.core.logging import get_logger
from ragops.core.types import (
    EvaluationOutput,
    EvaluationResult,
    EvaluationSample,
    QueryRequest,
)
from ragops.evaluation.datasets import DatasetLoader
from ragops.evaluation.judges import LLMJudge
from ragops.evaluation.metrics import MetricsAggregator
from ragops.evaluation.schemas import EvaluationConfig
from ragops.rag.pipeline import RAGPipeline

logger = get_logger(__name__)


class EvaluationRunner:
    """Run evaluations against the production RAG pipeline.

    Takes a golden dataset, runs each question through the same
    RAG pipeline, and computes comprehensive quality metrics.
    """

    def __init__(
        self,
        rag_pipeline: RAGPipeline | None = None,
        use_llm_judge: bool = True,
    ):
        self._pipeline = rag_pipeline or RAGPipeline()
        self._dataset_loader = DatasetLoader()
        self._metrics = MetricsAggregator()
        self._use_llm_judge = use_llm_judge
        self._judge = LLMJudge() if use_llm_judge else None

    def run(self, config: EvaluationConfig) -> EvaluationResult:
        """Run a full evaluation.

        1. Load golden dataset
        2. Run each question through the RAG pipeline
        3. Optionally use LLM-as-judge for quality scoring
        4. Aggregate metrics
        5. Optionally save report
        """
        logger.info(
            "evaluation_starting",
            dataset=config.dataset_path,
            rag_version=config.rag_version,
        )

        # 1. Load dataset
        samples = self._dataset_loader.load(config.dataset_path)

        # 2. Run pipeline on each sample
        outputs: list[EvaluationOutput] = []
        judge_scores: list[dict[str, float]] = []

        for i, sample in enumerate(samples):
            logger.info("evaluating_sample", index=i + 1, total=len(samples))

            output = self._evaluate_sample(sample, config)
            outputs.append(output)

            # 3. LLM-as-judge (optional)
            if self._judge and config.use_llm_judge:
                context = "\n".join(
                    [f"Chunk: {cid}" for cid in output.retrieved_chunks]
                )
                scores = self._judge.evaluate(
                    question=sample.question,
                    answer=output.actual_answer,
                    context=context or output.actual_answer,
                )
                judge_scores.append(scores)

        # 4. Aggregate metrics
        result = self._metrics.aggregate(
            outputs=outputs,
            dataset_version=Path(config.dataset_path).stem,
            rag_version=config.rag_version,
            judge_scores=judge_scores if judge_scores else None,
        )

        # 5. Save report
        if config.save_report:
            self._save_report(result, outputs, config)

        logger.info(
            "evaluation_complete",
            recall=round(result.retrieval_recall, 3),
            faithfulness=round(result.faithfulness, 3),
            samples=result.sample_count,
        )

        return result

    def _evaluate_sample(
        self, sample: EvaluationSample, config: EvaluationConfig
    ) -> EvaluationOutput:
        """Run a single evaluation sample through the RAG pipeline."""
        request = QueryRequest(
            query=sample.question,
            top_k=config.top_k,
        )

        start_time = time.perf_counter()
        response = self._pipeline.query(request)
        latency_ms = (time.perf_counter() - start_time) * 1000

        retrieved_items = [f"{s.document}:{s.chunk_id}" for s in response.sources]

        return EvaluationOutput(
            question=sample.question,
            expected_answer=sample.expected_answer,
            actual_answer=response.answer,
            expected_chunks=sample.expected_chunks,
            retrieved_chunks=retrieved_items,
            sources=response.sources,
            latency_ms=latency_ms,
            input_tokens=response.metadata.get("input_tokens", 0),
            output_tokens=response.metadata.get("output_tokens", 0),
        )

    def _save_report(
        self,
        result: EvaluationResult,
        outputs: list[EvaluationOutput],
        config: EvaluationConfig,
    ) -> None:
        """Save evaluation report as JSON."""
        report_dir = Path(config.report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)

        report_path = report_dir / f"eval_{config.rag_version}_{int(time.time())}.json"

        report = {
            "summary": result.model_dump(mode="json"),
            "config": config.model_dump(),
            "details": [output.model_dump(mode="json") for output in outputs],
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info("report_saved", path=str(report_path))
