"""Feedback schemas — API-level models for feedback submission."""

from __future__ import annotations

from pydantic import BaseModel

from ragops.core.types import FeedbackRating


class FeedbackRequest(BaseModel):
    """API request to submit feedback on a RAG response."""
    trace_id: str
    rating: FeedbackRating
    comment: str = ""


class FeedbackResponse(BaseModel):
    """API response after feedback submission."""
    feedback_id: str
    status: str = "recorded"
    message: str = "Thank you for your feedback"
