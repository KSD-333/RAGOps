"""System Warm-up Coordinator — asynchronous pre-warming of RAG subsystems.

Warms up:
1. SentenceTransformers Embeddings (warm embed)
2. Cross-Encoder Reranker (model load + dummy rank)
3. ChromaDB collection & search
4. BM25 Sparse Index (if HYBRID_SEARCH=true)
5. Active LLM Provider (Ollama with keep_alive: '30m' or Groq ping)
6. Redis & Relational Database connections

Tracks per-stage timing metrics and overall status ('warming' | 'ready').
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ragops.core.config import get_settings
from ragops.core.logging import get_logger

logger = get_logger(__name__)


class WarmupCoordinator:
    """Manages system warmup state, stage timings, and background orchestration."""

    _instance: WarmupCoordinator | None = None

    def __init__(self) -> None:
        self.status: str = "pending"  # "pending", "warming", "ready", "failed"
        self.stages: dict[str, dict[str, Any]] = {}
        self.total_took_ms: float = 0.0
        self.started_at: float | None = None
        self.completed_at: float | None = None
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> WarmupCoordinator:
        if cls._instance is None:
            cls._instance = WarmupCoordinator()
        return cls._instance

    def get_state(self) -> dict[str, Any]:
        """Return warmup state formatted for health probes and doctor."""
        took = self.total_took_ms
        if self.status == "warming" and self.started_at:
            took = round((time.perf_counter() - self.started_at) * 1000, 2)
        return {
            "status": self.status,
            "took_ms": took,
            "stages": self.stages,
        }

    async def run_warmup(self) -> dict[str, Any]:
        """Execute full asynchronous warmup across all subsystems without blocking startup."""
        settings = get_settings()
        if not getattr(settings, "warmup_on_start", True):
            self.status = "ready"
            self.stages = {"skipped": {"status": "skipped", "took_ms": 0.0}}
            return self.get_state()

        async with self._lock:
            if self.status in ("warming", "ready"):
                return self.get_state()
            self.status = "warming"
            self.started_at = time.perf_counter()
            logger.info("warmup_started")

        def _execute_sync_stages():
            # 1. Embeddings & Reranker
            t0 = time.perf_counter()
            try:
                from ragops.retrieval.embeddings import SentenceTransformerEmbedding
                embedder = SentenceTransformerEmbedding()
                embedder.embed_text("warmup")
                self.stages["embedder"] = {
                    "status": "ready",
                    "model": embedder.model_name,
                    "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
                logger.info("warmup_stage_complete", stage="embedder", took_ms=self.stages["embedder"]["took_ms"])
            except Exception as e:
                self.stages["embedder"] = {
                    "status": "error",
                    "error": str(e),
                    "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
                logger.warning("warmup_stage_failed", stage="embedder", error=str(e))

            t0 = time.perf_counter()
            try:
                from ragops.retrieval.reranker import CrossEncoderReranker
                from ragops.core.types import VectorSearchResult
                reranker = CrossEncoderReranker()
                reranker._load_model()
                dummy_results = [VectorSearchResult(chunk_id="w0", text="warmup test", score=1.0)]
                reranker.rerank("warmup", dummy_results, top_n=1)
                self.stages["reranker"] = {
                    "status": "ready",
                    "model": getattr(reranker, "_model_name", "ms-marco-MiniLM-L-6-v2"),
                    "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
                logger.info("warmup_stage_complete", stage="reranker", took_ms=self.stages["reranker"]["took_ms"])
            except Exception as e:
                self.stages["reranker"] = {
                    "status": "error",
                    "error": str(e),
                    "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
                logger.warning("warmup_stage_failed", stage="reranker", error=str(e))

            # 2. ChromaDB Collection & Search
            t0 = time.perf_counter()
            try:
                from ragops.retrieval.vector_store import ChromaVectorStore
                from ragops.core.types import QueryEmbedding
                store = ChromaVectorStore()
                dummy_emb = [0.0] * 384
                store.search(QueryEmbedding(query="warmup", vector=dummy_emb, model="all-MiniLM-L6-v2"), top_k=1)
                self.stages["chroma"] = {
                    "status": "ready",
                    "count": store.count(),
                    "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
                logger.info("warmup_stage_complete", stage="chroma", took_ms=self.stages["chroma"]["took_ms"])
            except Exception as e:
                self.stages["chroma"] = {
                    "status": "error",
                    "error": str(e),
                    "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
                logger.warning("warmup_stage_failed", stage="chroma", error=str(e))

            # 3. BM25 Index (if hybrid search enabled)
            if getattr(settings.retrieval, "hybrid_search", False):
                t0 = time.perf_counter()
                try:
                    from ragops.api.dependencies import get_retriever
                    retriever = get_retriever()
                    retriever._ensure_bm25_ready()
                    doc_count = len(retriever._bm25_index._documents) if hasattr(retriever, "_bm25_index") else 0
                    self.stages["bm25"] = {
                        "status": "ready",
                        "doc_count": doc_count,
                        "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                    }
                    logger.info("warmup_stage_complete", stage="bm25", took_ms=self.stages["bm25"]["took_ms"])
                except Exception as e:
                    self.stages["bm25"] = {
                        "status": "error",
                        "error": str(e),
                        "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                    }
                    logger.warning("warmup_stage_failed", stage="bm25", error=str(e))

            # 4. Redis and Database Connect
            t0 = time.perf_counter()
            try:
                from ragops.storage.database import get_session
                s = get_session()
                from sqlalchemy import text
                s.execute(text("SELECT 1"))
                s.close()
                self.stages["database"] = {
                    "status": "ready",
                    "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
            except Exception as e:
                self.stages["database"] = {
                    "status": "error",
                    "error": str(e),
                    "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                }

            t0 = time.perf_counter()
            try:
                if settings.redis.enabled:
                    from ragops.storage.redis_cache import RedisSemanticCache
                    r_cache = RedisSemanticCache.get_instance()
                    is_live = r_cache.is_available()
                    self.stages["redis"] = {
                        "status": "ready" if is_live else "offline",
                        "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                    }
            except Exception as e:
                self.stages["redis"] = {
                    "status": "error",
                    "error": str(e),
                    "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                }

            # 5. Active LLM Provider (Ollama with keep_alive: "30m" or Groq ping)
            t0 = time.perf_counter()
            try:
                from ragops.generation.providers.router import get_llm_router
                router = get_llm_router()
                active = router.get_active_provider_name()
                if active == "ollama":
                    # Send tiny warmup generation with keep_alive: "30m"
                    import requests
                    url = f"{router.ollama._base_url}/api/generate"
                    payload = {
                        "model": router.ollama._model,
                        "prompt": "hi",
                        "stream": False,
                        "keep_alive": "30m",
                    }
                    resp = requests.post(url, json=payload, timeout=30.0)
                    self.stages["llm"] = {
                        "status": "ready" if resp.status_code == 200 else "degraded",
                        "provider": "ollama",
                        "model": router.ollama._model,
                        "keep_alive": "30m",
                        "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                    }
                elif active == "groq":
                    # Check groq ping
                    g_check = router.groq.health_check()
                    self.stages["llm"] = {
                        "status": "ready" if g_check["reachable"] else "degraded",
                        "provider": "groq",
                        "model": router.groq._model,
                        "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                    }
                else:
                    self.stages["llm"] = {
                        "status": "degraded",
                        "provider": "none",
                        "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                    }
                logger.info("warmup_stage_complete", stage="llm", took_ms=self.stages["llm"]["took_ms"])
            except Exception as e:
                self.stages["llm"] = {
                    "status": "error",
                    "error": str(e),
                    "took_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
                logger.warning("warmup_stage_failed", stage="llm", error=str(e))

        await asyncio.to_thread(_execute_sync_stages)
        self.completed_at = time.perf_counter()
        self.total_took_ms = round((self.completed_at - (self.started_at or self.completed_at)) * 1000, 2)
        self.status = "ready"
        logger.info("warmup_completed", took_ms=self.total_took_ms, stages=self.stages)
        return self.get_state()
