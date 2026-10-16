"""Evaluation datasets — loading and managing golden datasets.

Golden datasets contain question-answer pairs with expected context
for measuring RAG quality.
"""

from __future__ import annotations

import json
from pathlib import Path

from ragops.core.exceptions import DatasetNotFoundError
from ragops.core.logging import get_logger
from ragops.core.types import EvaluationSample

logger = get_logger(__name__)


class DatasetLoader:
    """Load evaluation datasets from JSONL files."""

    def load(self, path: str | Path) -> list[EvaluationSample]:
        """Load an evaluation dataset from a JSONL file.

        Each line should be a JSON object with:
        - question: str
        - expected_answer: str (optional)
        - expected_chunks: list[str] (optional)
        """
        path = Path(path)
        if not path.exists():
            raise DatasetNotFoundError(f"Dataset not found: {path}")

        samples: list[EvaluationSample] = []

        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    sample = EvaluationSample(
                        question=data["question"],
                        expected_answer=data.get("expected_answer", ""),
                        expected_chunks=data.get("expected_chunks", []),
                        metadata=data.get("metadata", {}),
                    )
                    samples.append(sample)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(
                        "skipping_invalid_sample",
                        line=line_num,
                        error=str(e),
                    )

        logger.info("dataset_loaded", path=str(path), samples=len(samples))
        return samples

    def save(self, samples: list[EvaluationSample], path: str | Path) -> None:
        """Save evaluation samples to a JSONL file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            for sample in samples:
                f.write(sample.model_dump_json() + "\n")

        logger.info("dataset_saved", path=str(path), samples=len(samples))
