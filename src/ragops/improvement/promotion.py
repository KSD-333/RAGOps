"""Promotion — manage version promotion lifecycle."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ragops.core.logging import get_logger
from ragops.core.types import PromotionDecision, PromotionStatus

logger = get_logger(__name__)


class PromotionManager:
    """Manage the promotion of RAG versions to production.

    Tracks which version is currently in production and
    maintains a history of promotion decisions.
    """

    def __init__(self, registry_path: str = "./data/version_registry.json"):
        self._registry_path = Path(registry_path)
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._registry = self._load_registry()

    def get_production_version(self) -> str:
        """Get the currently deployed production version."""
        return self._registry.get("production_version", "v1")

    def promote(self, decision: PromotionDecision) -> bool:
        """Promote a candidate version to production.

        Returns True if promotion was successful.
        """
        if decision.status != PromotionStatus.PASS:
            logger.warning("promotion_rejected", version=decision.candidate_version)
            return False

        old_version = self.get_production_version()

        self._registry["production_version"] = decision.candidate_version
        self._registry["previous_version"] = old_version
        self._registry["promoted_at"] = datetime.now(timezone.utc).isoformat()
        self._registry.setdefault("history", []).append({
            "version": decision.candidate_version,
            "from_version": old_version,
            "reasons": decision.reasons,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        })

        self._save_registry()

        logger.info(
            "version_promoted",
            old_version=old_version,
            new_version=decision.candidate_version,
        )
        return True

    def rollback(self) -> str:
        """Rollback to the previous version."""
        previous = self._registry.get("previous_version")
        if not previous:
            logger.warning("no_previous_version_for_rollback")
            return self.get_production_version()

        current = self.get_production_version()
        self._registry["production_version"] = previous
        self._registry["previous_version"] = current
        self._save_registry()

        logger.info("version_rolled_back", from_version=current, to_version=previous)
        return previous

    def _load_registry(self) -> dict:
        if self._registry_path.exists():
            with open(self._registry_path) as f:
                return json.loads(f.read())
        return {"production_version": "v1", "history": []}

    def _save_registry(self) -> None:
        with open(self._registry_path, "w") as f:
            json.dump(self._registry, f, indent=2, default=str)
