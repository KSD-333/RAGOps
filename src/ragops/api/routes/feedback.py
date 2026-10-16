"""Feedback routes — user feedback submission and retrieval."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ragops.api.dependencies import get_feedback_service
from ragops.feedback.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback on a RAG response.

    Users can rate responses as positive/negative with optional comments.
    This feeds into the continuous improvement pipeline.
    """
    try:
        service = get_feedback_service()
        response = service.submit(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")


@router.get("/feedback/stats")
async def get_feedback_stats():
    """Get feedback statistics — positive/negative rate breakdown."""
    try:
        service = get_feedback_service()
        return service.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
