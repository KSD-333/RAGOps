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


@router.get("/feedback/dashboard")
async def get_feedback_dashboard():
    """Get complete feedback triage dashboard with disliked queries log and real-time telemetry."""
    try:
        from ragops.observability.metrics import get_metrics
        from ragops.api.dependencies import get_retriever

        service = get_feedback_service()
        summary = service.get_dashboard_summary()
        metrics = get_metrics()

        total_queries = int(metrics.get_counter("ragops_queries_total"))
        tokens_in = int(metrics.get_counter("ragops_tokens_input_total"))
        tokens_out = int(metrics.get_counter("ragops_tokens_output_total"))
        latency_stats = metrics.get_histogram_stats("ragops_query_latency_ms")

        try:
            retriever = get_retriever()
            docs_count = retriever.document_count
        except Exception:
            docs_count = 0

        return {
            **summary,
            "total_queries": total_queries,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "total_tokens": tokens_in + tokens_out,
            "estimated_cost_usd": round(((tokens_in * 0.05 + tokens_out * 0.08) / 1_000_000), 5),
            "latency_stats": latency_stats,
            "documents_indexed": docs_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")
