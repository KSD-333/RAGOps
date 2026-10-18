"""Feedback service — business logic for user feedback."""

from __future__ import annotations

from ragops.core.logging import get_logger
from ragops.core.types import FeedbackRating, FeedbackRecord
from ragops.feedback.repository import FeedbackRepository
from ragops.feedback.schemas import FeedbackRequest, FeedbackResponse

logger = get_logger(__name__)


class FeedbackService:
    """Process and store user feedback on RAG responses.

    Flow: User Feedback → FeedbackService → FeedbackRepository → Storage
    """

    def __init__(self, repository: FeedbackRepository | None = None):
        self._repository = repository or FeedbackRepository()

    def submit(self, request: FeedbackRequest) -> FeedbackResponse:
        """Submit user feedback for a RAG response."""
        record = FeedbackRecord(
            trace_id=request.trace_id,
            query=request.query,
            rating=request.rating,
            comment=request.comment,
        )

        feedback_id = self._repository.save(record)

        logger.info(
            "feedback_submitted",
            feedback_id=feedback_id,
            trace_id=request.trace_id,
            rating=request.rating.value,
        )

        return FeedbackResponse(
            feedback_id=feedback_id,
            status="recorded",
        )

    def get_stats(self) -> dict:
        """Get feedback statistics."""
        return self._repository.get_stats()

    def get_negative_feedback(self) -> list[FeedbackRecord]:
        """Get all negative feedback for improvement analysis."""
        all_records = self._repository.get_all()
        return [r for r in all_records if r.rating == FeedbackRating.NEGATIVE]

    def get_dashboard_summary(self) -> dict:
        """Get feedback summary including recent disliked queries for RAGOps triage."""
        all_records = self._repository.get_all()
        stats = self._repository.get_stats()
        disliked = [
            {
                "feedback_id": r.feedback_id,
                "trace_id": r.trace_id,
                "query": r.query or "(Query text unrecorded)",
                "comment": r.comment or "Marked as inaccurate by user",
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(r.created_at, "strftime") else str(r.created_at),
            }
            for r in reversed(all_records)
            if r.rating == FeedbackRating.NEGATIVE
        ]
        return {
            **stats,
            "disliked_queries": disliked[:20],
        }
