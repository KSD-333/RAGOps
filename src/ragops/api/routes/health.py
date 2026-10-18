"""Health check routes — liveness and readiness probes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, RedirectResponse

from ragops.core.config import get_settings
from ragops.observability.metrics import get_metrics

router = APIRouter(tags=["health"])

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def get_react_dist_index() -> Path | None:
    """Find the modern React app index.html across production packaging and dev environments."""
    candidates = [
        Path(__file__).resolve().parent.parent / "static_react" / "index.html",
        Path.cwd() / "react" / "dist" / "index.html",
        Path.cwd() / "src" / "ragops" / "api" / "static_react" / "index.html",
        Path("/app/react/dist/index.html"),
        Path("/opt/render/project/src/react/dist/index.html"),
        Path(__file__).resolve().parents[4] / "react" / "dist" / "index.html",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


@router.get("/", include_in_schema=False)
async def root() -> Response:
    """Serve the interactive modern React UI, fallback to static UI or API docs."""
    react_index = get_react_dist_index()
    if react_index:
        return FileResponse(react_index)
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
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
