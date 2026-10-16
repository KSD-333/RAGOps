"""FastAPI application — the main API entry point.

The API layer should remain THIN — it handles:
- Request validation
- Routing
- Serialization
- Error handling

It does NOT directly call vector DB or LLM.
All business logic goes through the RAG pipeline.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ragops.api.middleware import RequestLoggingMiddleware
from ragops.api.routes import health, query, feedback
from ragops.core.config import get_settings
from ragops.core.logging import setup_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown."""
    settings = get_settings()
    setup_logging(settings.observability.log_level)
    logger.info(
        "ragops_starting",
        environment=settings.environment,
        model=settings.groq.model,
    )
    yield
    logger.info("ragops_shutting_down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="RAGOps — Production RAG Platform",
        description=(
            "Production-grade RAG platform with evaluation, observability, "
            "feedback loops, and quality gates."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins if hasattr(settings.api, 'cors_origins') else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    # --- Routes ---
    app.include_router(health.router, prefix="")
    app.include_router(query.router, prefix="/api/v1")
    app.include_router(feedback.router, prefix="/api/v1")

    return app


# Application instance for uvicorn
app = create_app()
