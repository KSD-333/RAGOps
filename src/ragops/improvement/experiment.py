"""Experiment tracking — manage RAG configuration experiments."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from ragops.core.logging import get_logger
from ragops.core.types import EvaluationResult

logger = get_logger(__name__)


class Experiment(BaseModel):
    """A RAG configuration experiment."""
    experiment_id: str
    version: str
    description: str = ""
    config: dict = Field(default_factory=dict)
    evaluation_result: EvaluationResult | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending | running | completed | promoted | rejected


class ExperimentTracker:
    """Track and compare RAG experiments.

    Stores experiment configurations and their evaluation results
    for comparison and promotion decisions.
    """

    def __init__(self, storage_dir: str = "./data/experiments"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        version: str,
        description: str = "",
        config: dict | None = None,
    ) -> Experiment:
        """Create a new experiment."""
        experiment = Experiment(
            experiment_id=f"exp_{version}_{int(datetime.now(timezone.utc).timestamp())}",
            version=version,
            description=description,
            config=config or {},
        )

        self._save(experiment)
        logger.info("experiment_created", experiment_id=experiment.experiment_id)
        return experiment

    def record_result(
        self,
        experiment_id: str,
        result: EvaluationResult,
    ) -> Experiment:
        """Record evaluation results for an experiment."""
        experiment = self.get(experiment_id)
        if experiment:
            experiment.evaluation_result = result
            experiment.status = "completed"
            self._save(experiment)
            logger.info("experiment_result_recorded", experiment_id=experiment_id)
        return experiment

    def get(self, experiment_id: str) -> Experiment | None:
        """Get an experiment by ID."""
        path = self._storage_dir / f"{experiment_id}.json"
        if not path.exists():
            return None

        with open(path) as f:
            data = json.loads(f.read())
            return Experiment(**data)

    def list_all(self) -> list[Experiment]:
        """List all experiments."""
        experiments = []
        for path in self._storage_dir.glob("exp_*.json"):
            with open(path) as f:
                data = json.loads(f.read())
                experiments.append(Experiment(**data))

        return sorted(experiments, key=lambda e: e.created_at, reverse=True)

    def _save(self, experiment: Experiment) -> None:
        """Save an experiment to disk."""
        path = self._storage_dir / f"{experiment.experiment_id}.json"
        with open(path, "w") as f:
            f.write(experiment.model_dump_json(indent=2))
