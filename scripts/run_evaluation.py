#!/usr/bin/env python3
"""Script to execute RAG evaluation against golden datasets with quality gate check."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Ensure src is on sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from ragops.core.logging import setup_logging, get_logger
from ragops.evaluation.runner import EvaluationRunner
from ragops.evaluation.schemas import EvaluationConfig
from ragops.improvement.quality_gate import QualityGate

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run RAGOps evaluation pipeline.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="evaluation/datasets/golden.jsonl",
        help="Path to evaluation dataset (default: evaluation/datasets/golden.jsonl)",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v1",
        help="RAG version to evaluate (default: v1)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation/reports/latest_evaluation.json",
        help="Output report path (default: evaluation/reports/latest_evaluation.json)",
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Disable LLM judge",
    )
    parser.add_argument(
        "--fail-on-gate",
        action="store_true",
        help="Exit with non-zero code if quality gate fails",
    )

    args = parser.parse_args()
    setup_logging("INFO")

    dataset_path = Path(args.dataset)
    if not dataset_path.is_absolute():
        dataset_path = (root_dir / dataset_path).resolve()

    logger.info("running_evaluation", dataset=str(dataset_path), version=args.version)

    config = EvaluationConfig(
        dataset_path=str(dataset_path),
        rag_version=args.version,
        use_llm_judge=not args.no_judge,
    )

    runner = EvaluationRunner(use_llm_judge=not args.no_judge)
    result = runner.run(config)

    # Save output report
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (root_dir / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result.model_dump(), indent=2, default=str), encoding="utf-8")
    logger.info("evaluation_report_saved", path=str(output_path))

    # Evaluate Quality Gate
    gate = QualityGate()
    decision = gate.evaluate(result)

    print("\n" + "=" * 50)
    print("           RAG EVALUATION SUMMARY")
    print("=" * 50)
    print(f"Version:              {result.rag_version}")
    print(f"Retrieval Recall@5:   {result.retrieval_recall:.3f}")
    print(f"Retrieval Precision@5:{result.retrieval_precision:.3f}")
    print(f"MRR:                  {result.mrr:.3f}")
    print(f"Faithfulness:         {result.faithfulness:.3f}")
    print(f"Answer Relevance:     {result.answer_relevance:.3f}")
    print(f"Citation Accuracy:    {result.citation_accuracy:.3f}")
    print(f"P50 Latency:          {result.p50_latency_ms:.0f}ms")
    print(f"P95 Latency:          {result.p95_latency_ms:.0f}ms")
    print(f"Samples Evaluated:    {result.sample_count}")
    print("-" * 50)
    print(f"Quality Gate Status:  {decision.status.value.upper()}")
    print(f"Decision Reasons:     {'; '.join(decision.reasons)}")
    print("=" * 50 + "\n")

    if args.fail_on_gate and decision.status != PromotionStatus.PASS:
        sys.exit(1)



if __name__ == "__main__":
    main()
