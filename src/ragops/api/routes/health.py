"""Health check routes — liveness and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter

from ragops.core.config import get_settings
from ragops.observability.metrics import get_metrics

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Liveness probe — is the service running?"""
    return {
        "status": "healthy",
        "service": "ragops",
        "version": "0.1.0",
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe — is the service ready to handle requests?"""
    settings = get_settings()
    return {
        "status": "ready",
        "environment": settings.environment,
        "model": settings.groq.model,
    }


@router.get("/metrics")
async def get_application_metrics():
    """Get application metrics."""
    metrics = get_metrics()
    return metrics.get_all_metrics()
