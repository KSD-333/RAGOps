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
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ragops.api.middleware import RequestLoggingMiddleware
from ragops.api.routes import health, query, feedback, auth, admin, company
from ragops.core.config import get_settings
from ragops.core.logging import setup_logging, get_logger
from ragops.storage.database import init_db

logger = get_logger(__name__)


async def _async_warmup():
    """Background warmup for embedding and reranker models so server port binds immediately."""
    try:
        import asyncio
        from ragops.api.dependencies import get_retriever
        from ragops.core.types import VectorSearchResult

        def _warm():
            retriever = get_retriever()
            retriever._embeddings.embed_text("warmup")
            if hasattr(retriever._reranker, "_load_model"):
                retriever._reranker._load_model()
                dummy = [VectorSearchResult(chunk_id="w", text="warmup", score=1.0)]
                retriever._reranker.rerank("warmup", dummy, top_n=1)

        await asyncio.to_thread(_warm)
        logger.info("retrieval_models_warmed_up")
    except Exception as e:
        logger.warning("models_warmup_failed", error=str(e))


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

    # Initialize database tables and seed default dummy users (admin, test1, test2)
    try:
        init_db()
    except Exception as db_err:
        logger.warning("database_init_failed", error=str(db_err))

    # Launch model warmup in background task so Uvicorn opens listening port in <1 second
    asyncio.create_task(_async_warmup())

    yield
    logger.info("ragops_shutting_down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    tags_metadata = [
        {
            "name": "query",
            "description": (
                "**Core RAG Inference Subsystem**. Encapsulates end-to-end question answering: "
                "query embedding via SentenceTransformers (`all-MiniLM-L6-v2`), vector similarity "
                "search in ChromaDB, cross-encoder neural reranking (`ms-marco-MiniLM-L-6-v2`), "
                "and citation-grounded LLM inference via Groq LPUs (`llama-3.1-70b-versatile`)."
            ),
        },
        {
            "name": "feedback",
            "description": (
                "**Continuous Improvement & Evaluation Loop**. Records real-world user feedback "
                "(thumbs up/down) to persistent JSONL audit trails, aggregates live telemetry, "
                "and exposes metrics for hallucination triage and token spend tracking."
            ),
        },
        {
            "name": "health",
            "description": (
                "**Orchestration & Liveness Probes**. Cloud-native endpoints for Kubernetes and container "
                "runners: liveness (`/health`), readiness with warmed model verification (`/health/ready`), "
                "and Prometheus telemetry (`/metrics`)."
            ),
        },
    ]

    app = FastAPI(
        title="RAGOps — Production Enterprise RAG Platform",
        description=(
            "### Enterprise AI Retrieval-Augmented Generation & Operations Engine\n\n"
            "RAGOps is an end-to-end production RAG platform engineered with:\n"
            "- **Hybrid Neural Retrieval**: SentenceTransformers (`all-MiniLM-L6-v2`) 384d dense embeddings.\n"
            "- **Precision Reranking**: Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) candidate filtering.\n"
            "- **Vector Store**: ChromaDB persistent HNSW indexing.\n"
            "- **Ultra-Low-Latency Inference**: Groq LPUs running LLaMA 3.1 70B with strict citation provenance and zero-hallucination abstention.\n"
            "- **Observability & Triage**: Latency tracking, token spend computation, and user feedback triage.\n\n"
            "Use this interactive OpenAPI specification to test endpoints, view request/response schemas, and integrate client applications."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=tags_metadata,
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
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(query.router, prefix="/api/v1")
    app.include_router(feedback.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(company.router, prefix="/api/v1")

    # --- Static Assets (Preserved Original Web UI) ---
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # --- Modern React UI Assets ---
    def get_react_assets_dir() -> Path | None:
        candidates = [
            Path.cwd() / "react" / "dist" / "assets",
            Path(__file__).resolve().parent / "static_react" / "assets",
            Path.cwd() / "src" / "ragops" / "api" / "static_react" / "assets",
            Path("/app/react/dist/assets"),
            Path("/opt/render/project/src/react/dist/assets"),
            Path(__file__).resolve().parents[3] / "react" / "dist" / "assets",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    react_assets = get_react_assets_dir()
    if react_assets:
        app.mount("/assets", StaticFiles(directory=react_assets), name="react_assets")

    return app


# Application instance for uvicorn
app = create_app()
