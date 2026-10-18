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

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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

    # Warm up embedding and reranker models at startup so first request has 0 cold start
    try:
        from ragops.api.dependencies import get_retriever
        from ragops.core.types import VectorSearchResult
        retriever = get_retriever()
        retriever._embeddings.embed_text("warmup")
        if hasattr(retriever._reranker, "_load_model"):
            retriever._reranker._load_model()
            dummy = [VectorSearchResult(chunk_id="w", text="warmup", score=1.0)]
            retriever._reranker.rerank("warmup", dummy, top_n=1)
        logger.info("retrieval_models_warmed_up")
    except Exception as e:
        logger.warning("models_warmup_failed", error=str(e))

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

    # --- Static Assets (Web UI) ---
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app


# Application instance for uvicorn
app = create_app()
