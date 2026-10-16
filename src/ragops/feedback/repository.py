"""Feedback repository — persistence layer for user feedback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ragops.core.logging import get_logger
from ragops.core.types import FeedbackRating, FeedbackRecord

logger = get_logger(__name__)


class FeedbackRepository:
    """Store and retrieve user feedback.

    Uses a simple JSON Lines file for storage.
    In production, replace with PostgreSQL via storage module.
    """

    def __init__(self, storage_path: str = "./data/feedback.jsonl"):
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, record: FeedbackRecord) -> str:
        """Save a feedback record. Returns the feedback ID."""
        with open(self._storage_path, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

        logger.info(
            "feedback_saved",
            feedback_id=record.feedback_id,
            trace_id=record.trace_id,
            rating=record.rating.value,
        )
        return record.feedback_id

    def get_all(self) -> list[FeedbackRecord]:
        """Retrieve all feedback records."""
        if not self._storage_path.exists():
            return []

        records: list[FeedbackRecord] = []
        with open(self._storage_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        records.append(FeedbackRecord(**data))
                    except (json.JSONDecodeError, ValueError):
                        continue

        return records

    def get_by_trace(self, trace_id: str) -> list[FeedbackRecord]:
        """Get feedback for a specific trace."""
        return [r for r in self.get_all() if r.trace_id == trace_id]

    def get_stats(self) -> dict[str, Any]:
        """Get feedback statistics."""
        records = self.get_all()
        total = len(records)
        positive = sum(1 for r in records if r.rating == FeedbackRating.POSITIVE)
        negative = total - positive

        return {
            "total": total,
            "positive": positive,
            "negative": negative,
            "positive_rate": positive / total if total > 0 else 0,
        }
