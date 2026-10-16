"""Health check routes — liveness and readiness probes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

from ragops.core.config import get_settings
from ragops.observability.metrics import get_metrics

router = APIRouter(tags=["health"])


@router.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")


@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Return 204 No Content for browser favicon requests."""
    return Response(status_code=204)


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe — is the service running?"""
    return {
        "status": "healthy",
        "service": "ragops",
        "version": "0.1.0",
    }


@router.get("/health/ready")
async def readiness_check() -> dict[str, str]:
    """Readiness probe — is the service ready to handle requests?"""
    settings = get_settings()
    return {
        "status": "ready",
        "environment": settings.environment,
        "model": settings.groq.model,
    }


@router.get("/metrics")
async def get_application_metrics() -> dict[str, Any]:
    """Get application metrics."""
    metrics = get_metrics()
    return metrics.get_all_metrics()
