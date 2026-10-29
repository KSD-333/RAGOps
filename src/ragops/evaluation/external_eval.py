"""Optional RAGAS & DeepEval evaluation harness with graceful fallback."""

from __future__ import annotations

from typing import Any
from ragops.core.logging import get_logger

logger = get_logger(__name__)


def is_ragas_available() -> bool:
    """Check if the ragas package is installed."""
    try:
        import ragas  # noqa: F401
        return True
    except (ImportError, ModuleNotFoundError):
        return False


def is_deepeval_available() -> bool:
    """Check if the deepeval package is installed."""
    try:
        import deepeval  # noqa: F401
        return True
    except (ImportError, ModuleNotFoundError):
        return False


def run_ragas_evaluation(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str] | None = None,
) -> dict[str, Any]:
    """Execute RAGAS evaluation on generated answers.

    Gracefully skipped if ragas is not installed or API provider is unconfigured.
    """
    if not is_ragas_available():
        logger.info("ragas_evaluation_skipped_not_installed")
        return {
            "status": "skipped",
            "reason": "ragas package is not installed (pip install ragas)",
        }

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, faithfulness

        data_dict = {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
        }
        if ground_truths:
            data_dict["ground_truth"] = ground_truths

        dataset = Dataset.from_dict(data_dict)
        results = evaluate(dataset, metrics=[faithfulness, answer_relevancy])

        logger.info("ragas_evaluation_completed", results=dict(results))
        return {
            "status": "success",
            "faithfulness": float(results.get("faithfulness", 0.0)),
            "answer_relevancy": float(results.get("answer_relevancy", 0.0)),
        }
    except Exception as e:
        logger.warning("ragas_evaluation_failed", error=str(e))
        return {
            "status": "error",
            "error": str(e),
        }
