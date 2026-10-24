"""High-Performance Redis Semantic Cache for RAGOps.

Supports Redis and Memurai on Windows (127.0.0.1:6379).
Provides:
1. Exact match caching (<1-2ms latency).
2. Semantic similarity vector matching (threshold configurable, default 0.90-0.95).
3. Automatic indexing by corporate identity, scope, and query intent.
4. Hit counters, TTL expiration, and telemetry integration.
5. Non-blocking graceful fallback if Redis server is unreachable.
"""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from typing import Any

from ragops.core.config import get_settings
from ragops.core.logging import get_logger

logger = get_logger(__name__)

# Cache safety rule: abstention detector
from ragops.rag.query_intelligence import is_abstention_text


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a)
    norm_b = sum(b * b for b in vec_b)
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def ensure_redis_running(redis_url: str | None = None, timeout_secs: float = 3.0) -> bool:
    """Ensure that Redis / Memurai is active and accepting connections.

    If Redis is already running and responds to ping, returns True immediately (<1ms).
    If Redis is not running, attempts to automatically launch it:
    1. On Windows:
       a. Attempts to start the 'Memurai' Windows Service (`sc.exe start Memurai` / `net start Memurai`).
       b. If service start fails or is not accessible, checks for `C:\\Program Files\\Memurai\\memurai.exe`
          (or `memurai.exe` / `redis-server.exe` in PATH) and launches it as a detached background daemon.
    2. On Linux/Unix:
       a. Attempts `systemctl start redis` or `service redis-server start`.
       b. Or launches `redis-server --daemonize yes`.
    3. Polls connection for up to `timeout_secs` until PING succeeds.
    """
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    url = redis_url or get_settings().redis.url

    # 1. Quick check: is Redis already running?
    try:
        import redis
        test_client = redis.Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5)
        if test_client.ping():
            return True
    except Exception:
        pass

    logger.info("redis_offline_attempting_auto_start", url=url)

    # 2. Attempt automatic startup based on OS platform
    started_trigger = False

    if sys.platform == "win32":
        # Strategy A: Windows Service 'Memurai'
        try:
            res = subprocess.run(
                ["sc.exe", "start", "Memurai"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = (res.stdout or "").lower()
            if res.returncode == 0 or "already running" in out:
                started_trigger = True
        except Exception:
            pass

        if not started_trigger:
            try:
                res2 = subprocess.run(
                    ["net", "start", "Memurai"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res2.returncode == 0 or "already started" in (res2.stdout or "").lower():
                    started_trigger = True
            except Exception:
                pass

        # Strategy B: Direct process launch (memurai.exe or redis-server.exe)
        if not started_trigger:
            possible_paths = [
                Path("C:/Program Files/Memurai/memurai.exe"),
                Path("C:/Program Files (x86)/Memurai/memurai.exe"),
            ]
            which_memurai = shutil.which("memurai") or shutil.which("memurai.exe")
            if which_memurai:
                possible_paths.insert(0, Path(which_memurai))
            which_redis = shutil.which("redis-server") or shutil.which("redis-server.exe")
            if which_redis:
                possible_paths.append(Path(which_redis))

            for exe in possible_paths:
                if exe.exists() and exe.is_file():
                    conf_path = exe.parent / "memurai.conf"
                    cmd = [str(exe)]
                    if conf_path.exists():
                        cmd.append(str(conf_path))
                    try:
                        # Windows detached process flags: DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
                        DETACHED = 0x00000008 | 0x00000200 | 0x08000000
                        subprocess.Popen(
                            cmd,
                            creationflags=DETACHED,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            close_fds=True,
                        )
                        started_trigger = True
                        logger.info("spawned_memurai_background_process", path=str(exe))
                        break
                    except Exception as spawn_err:
                        logger.warning("failed_spawning_memurai_process", path=str(exe), error=str(spawn_err))

    else:
        # Linux / Unix / macOS / Docker
        if shutil.which("systemctl"):
            try:
                subprocess.run(["systemctl", "start", "redis"], capture_output=True, timeout=5)
                started_trigger = True
            except Exception:
                pass
        elif shutil.which("service"):
            try:
                subprocess.run(["service", "redis-server", "start"], capture_output=True, timeout=5)
                started_trigger = True
            except Exception:
                pass

        if not started_trigger and shutil.which("redis-server"):
            try:
                subprocess.Popen(["redis-server", "--daemonize", "yes"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                started_trigger = True
            except Exception:
                pass

    # 3. Poll connection until timeout expires
    deadline = time.time() + timeout_secs
    while time.time() < deadline:
        try:
            import redis
            poll_client = redis.Redis.from_url(url, socket_timeout=0.6, socket_connect_timeout=0.6)
            if poll_client.ping():
                logger.info("redis_server_auto_started_successfully", url=url)
                return True
        except Exception:
            time.sleep(0.3)

    logger.warning("redis_auto_start_timed_out_fallback_active", url=url)
    return False


class RedisSemanticCache:
    """Production Redis Semantic & Exact Cache with Memurai support."""

    _instance: RedisSemanticCache | None = None

    @classmethod
    def get_instance(cls) -> RedisSemanticCache:
        """Get or create singleton RedisSemanticCache instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, redis_url: str | None = None, enabled: bool | None = None):
        settings = get_settings()
        self._redis_url = redis_url or settings.redis.url
        self._enabled = enabled if enabled is not None else settings.redis.enabled
        self._default_ttl = settings.redis.ttl_seconds
        self._similarity_threshold = settings.redis.similarity_threshold

        self._client = None
        self._is_connected: bool = False
        self._last_connect_attempt: float = 0.0
        self._reconnect_cooldown_secs: float = 5.0  # Avoid hammer reconnects if Redis down

        if self._enabled:
            self._connect()

    def _connect(self) -> bool:
        """Attempt connection to Redis / Memurai with auto-start fallback."""
        now = time.time()
        if now - self._last_connect_attempt < self._reconnect_cooldown_secs:
            return self._is_connected

        self._last_connect_attempt = now
        try:
            import redis
            self._client = redis.Redis.from_url(
                self._redis_url,
                socket_timeout=1.5,
                socket_connect_timeout=1.5,
                decode_responses=True,
            )
            # Test with ping
            if self._client.ping():
                self._is_connected = True
                logger.info("redis_cache_connected", url=self._redis_url)
                return True
        except Exception:
            # If initial connect fails, attempt auto-starting Memurai / Redis service!
            try:
                if ensure_redis_running(self._redis_url):
                    import redis
                    self._client = redis.Redis.from_url(
                        self._redis_url,
                        socket_timeout=1.5,
                        socket_connect_timeout=1.5,
                        decode_responses=True,
                    )
                    if self._client.ping():
                        self._is_connected = True
                        logger.info("redis_cache_connected_after_auto_start", url=self._redis_url)
                        return True
            except Exception as auto_err:
                logger.warning("redis_connect_auto_start_failed", error=str(auto_err))

            self._is_connected = False
            self._client = None
            logger.warning("redis_cache_connection_failed", url=self._redis_url)
        return False

    def is_available(self) -> bool:
        """Check whether Redis is currently available and healthy."""
        if not self._enabled:
            return False
        if not self._is_connected or self._client is None:
            return self._connect()
        try:
            return bool(self._client.ping())
        except Exception:
            self._is_connected = False
            return False

    # -------------------------------------------------------------------------
    # Exact Match Caching (<1-2ms)
    # -------------------------------------------------------------------------

    def get_exact(self, company: str, cache_key: str) -> dict[str, Any] | None:
        """Retrieve exact match cache entry by cache key."""
        if not self.is_available() or not self._client:
            return None

        exact_key = f"ragops:cache:exact:{company}:{cache_key}"
        try:
            val = self._client.get(exact_key)
            if not val:
                return None

            data = json.loads(val)
            answer = data.get("answer", "")
            # Safety gate: never return abstention from cache
            if is_abstention_text(answer):
                self._client.delete(exact_key)
                return None

            # Increment hit metrics in background
            try:
                pipe = self._client.pipeline(transaction=False)
                pipe.incr(f"ragops:cache:hits:{cache_key}")
                pipe.hincrby("ragops:cache:global_stats", "exact_hits", 1)
                pipe.hincrby("ragops:cache:global_stats", "total_hits", 1)
                pipe.execute()
                data["hit_count"] = data.get("hit_count", 1) + 1
            except Exception:
                pass

            return data
        except Exception as e:
            logger.warning("redis_get_exact_failed", key=exact_key, error=str(e))
            return None

    def set_exact(
        self,
        company: str,
        cache_key: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Save exact match cache entry with TTL."""
        if not self.is_available() or not self._client:
            return False

        exact_key = f"ragops:cache:exact:{company}:{cache_key}"
        ttl_val = ttl if ttl is not None else self._default_ttl
        try:
            self._client.set(exact_key, json.dumps(data), ex=ttl_val)
            return True
        except Exception as e:
            logger.warning("redis_set_exact_failed", key=exact_key, error=str(e))
            return False

    # -------------------------------------------------------------------------
    # Semantic Similarity Matching (90% - 95% relevance)
    # -------------------------------------------------------------------------

    def search_semantic(
        self,
        company: str,
        scope: str,
        intent: str,
        query_vector: list[float],
        threshold: float | None = None,
    ) -> tuple[dict[str, Any] | None, float]:
        """Search cached questions for scope/intent with cosine similarity >= threshold.

        Threshold defaults to 0.92 (in user's requested 90%-95% range).
        Returns: (matching_data_dict, similarity_score) or (None, highest_sim_observed).
        """
        if not self.is_available() or not self._client or not query_vector:
            return None, 0.0

        min_threshold = threshold if threshold is not None else self._similarity_threshold
        index_key = f"ragops:cache:index:{company}:{scope}:{intent}"

        try:
            candidate_keys = self._client.smembers(index_key)
            if not candidate_keys:
                return None, 0.0

            # Batch retrieve all candidates in single pipelined roundtrip
            pipe = self._client.pipeline(transaction=False)
            keys_list = list(candidate_keys)
            for ck in keys_list:
                pipe.get(f"ragops:cache:semantic:{ck}")
            results = pipe.execute()

            best_entry: dict[str, Any] | None = None
            highest_sim = 0.0
            best_cache_key: str | None = None

            for ck, raw in zip(keys_list, results):
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                    cand_vector = entry.get("embedding")
                    if not cand_vector:
                        continue

                    # Guard against abstention in cache
                    if is_abstention_text(entry.get("answer", "")):
                        self.delete_entry(ck, company=company, scope=scope, intent=intent)
                        continue

                    sim = cosine_similarity(query_vector, cand_vector)
                    if sim > highest_sim:
                        highest_sim = sim
                        if sim >= min_threshold:
                            best_entry = entry
                            best_cache_key = ck
                except Exception:
                    continue

            if best_entry and best_cache_key:
                # Increment hit counters
                try:
                    p = self._client.pipeline(transaction=False)
                    p.incr(f"ragops:cache:hits:{best_cache_key}")
                    p.hincrby("ragops:cache:global_stats", "semantic_hits", 1)
                    p.hincrby("ragops:cache:global_stats", "total_hits", 1)
                    p.execute()
                except Exception:
                    pass

                best_entry["hit_count"] = best_entry.get("hit_count", 1) + 1
                best_entry["similarity"] = round(highest_sim, 4)
                return best_entry, highest_sim

            return None, highest_sim

        except Exception as e:
            logger.warning("redis_search_semantic_failed", error=str(e))
            return None, 0.0

    # -------------------------------------------------------------------------
    # Store in Cache (Exact + Semantic Index)
    # -------------------------------------------------------------------------

    def store_cache(
        self,
        company: str,
        cache_key: str,
        scope: str,
        intent: str,
        target_entity: str,
        query: str,
        query_vector: list[float] | None,
        response_dict: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Store verified Q&A in Redis with exact key and semantic vector indexing."""
        if not self.is_available() or not self._client:
            return False

        # Guard: NEVER cache abstentions or refusals
        if is_abstention_text(response_dict.get("answer", "")):
            return False

        ttl_val = ttl if ttl is not None else self._default_ttl
        exact_key = f"ragops:cache:exact:{company}:{cache_key}"
        semantic_key = f"ragops:cache:semantic:{cache_key}"
        index_key = f"ragops:cache:index:{company}:{scope}:{intent}"
        all_keys_set = "ragops:cache:all_keys"

        payload = {
            "cache_key": cache_key,
            "company": company,
            "original_query": query,
            "scope": scope,
            "intent": intent,
            "target_entity": target_entity,
            "answer": response_dict.get("answer", ""),
            "sources": response_dict.get("sources", []),
            "citations": response_dict.get("citations", []),
            "chunks_sent": response_dict.get("chunks_sent", []),
            "model": response_dict.get("model", "groq"),
            "hit_count": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            pipe = self._client.pipeline(transaction=False)
            # 1. Exact match record
            pipe.set(exact_key, json.dumps(payload), ex=ttl_val)

            # 2. Semantic index record (with embedding vector)
            if query_vector:
                semantic_payload = dict(payload)
                semantic_payload["embedding"] = query_vector
                pipe.set(semantic_key, json.dumps(semantic_payload), ex=ttl_val)
                # Add to scope/intent index
                pipe.sadd(index_key, cache_key)
                pipe.expire(index_key, ttl_val)

            # 3. Add to set of all keys for enumeration / purge
            pipe.sadd(all_keys_set, cache_key)
            pipe.hincrby("ragops:cache:global_stats", "total_stored", 1)
            pipe.execute()

            logger.info("stored_in_redis_cache", cache_key=cache_key, company=company, intent=intent)
            return True
        except Exception as e:
            logger.warning("redis_store_cache_failed", cache_key=cache_key, error=str(e))
            return False

    # -------------------------------------------------------------------------
    # Management & Metrics
    # -------------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get Redis cache status, entries count, and hit metrics."""
        connected = self.is_available()
        stats: dict[str, Any] = {
            "redis_enabled": self._enabled,
            "redis_connected": connected,
            "redis_url": self._redis_url,
            "similarity_threshold": self._similarity_threshold,
            "similarity_threshold_range": "0.90 - 0.95 (direct cache hit)",
            "total_cached_entries": 0,
            "total_hits": 0,
            "exact_hits": 0,
            "semantic_hits": 0,
            "used_memory_human": "0B",
            "uptime_seconds": 0,
        }

        if not connected or not self._client:
            return stats

        try:
            info = self._client.info()
            stats["used_memory_human"] = info.get("used_memory_human", "0B")
            stats["uptime_seconds"] = info.get("uptime_in_seconds", 0)

            # Total cached entries
            all_keys = self._client.smembers("ragops:cache:all_keys")
            stats["total_cached_entries"] = len(all_keys)

            # Global hits
            g_stats = self._client.hgetall("ragops:cache:global_stats") or {}
            stats["total_hits"] = int(g_stats.get("total_hits", 0))
            stats["exact_hits"] = int(g_stats.get("exact_hits", 0))
            stats["semantic_hits"] = int(g_stats.get("semantic_hits", 0))
        except Exception as e:
            logger.warning("redis_get_stats_failed", error=str(e))

        return stats

    def list_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        """List active entries stored in Redis."""
        if not self.is_available() or not self._client:
            return []

        try:
            all_keys = list(self._client.smembers("ragops:cache:all_keys"))[:limit]
            if not all_keys:
                return []

            pipe = self._client.pipeline(transaction=False)
            for k in all_keys:
                pipe.get(f"ragops:cache:semantic:{k}")
            raw_entries = pipe.execute()

            entries = []
            for k, raw in zip(all_keys, raw_entries):
                if not raw:
                    continue
                try:
                    e = json.loads(raw)
                    hits = self._client.get(f"ragops:cache:hits:{k}") or e.get("hit_count", 1)
                    entries.append({
                        "cache_key": k,
                        "original_query": e.get("original_query", ""),
                        "company": e.get("company", ""),
                        "scope": e.get("scope", ""),
                        "intent": e.get("intent", ""),
                        "target_entity": e.get("target_entity", ""),
                        "hit_count": int(hits),
                        "created_at": e.get("created_at", ""),
                        "answer_preview": e.get("answer", "")[:120] + "...",
                    })
                except Exception:
                    continue
            entries.sort(key=lambda x: x["hit_count"], reverse=True)
            return entries
        except Exception as e:
            logger.warning("redis_list_entries_failed", error=str(e))
            return []

    def clear_cache(self) -> int:
        """Purge all RAGOps cache keys from Redis."""
        if not self.is_available() or not self._client:
            return 0

        try:
            # Find all ragops:cache:* keys
            cursor = "0"
            all_keys: list[str] = []
            while True:
                cursor, keys = self._client.scan(cursor=cursor, match="ragops:cache:*", count=100)
                all_keys.extend(keys)
                if cursor == 0 or cursor == "0":
                    break

            if all_keys:
                # Delete in chunks
                chunk_size = 500
                deleted = 0
                for i in range(0, len(all_keys), chunk_size):
                    deleted += self._client.delete(*all_keys[i : i + chunk_size])
                logger.info("redis_cache_cleared", count=deleted)
                return deleted
            return 0
        except Exception as e:
            logger.warning("redis_clear_cache_failed", error=str(e))
            return 0

    def delete_entry(
        self,
        cache_key: str,
        company: str | None = None,
        scope: str | None = None,
        intent: str | None = None,
    ) -> bool:
        """Delete an individual entry and clean up associated indices."""
        if not self.is_available() or not self._client:
            return False

        try:
            pipe = self._client.pipeline(transaction=False)
            pipe.delete(f"ragops:cache:semantic:{cache_key}")
            pipe.delete(f"ragops:cache:hits:{cache_key}")
            pipe.srem("ragops:cache:all_keys", cache_key)
            if company:
                pipe.delete(f"ragops:cache:exact:{company}:{cache_key}")
                if scope and intent:
                    pipe.srem(f"ragops:cache:index:{company}:{scope}:{intent}", cache_key)
            pipe.execute()
            return True
        except Exception as e:
            logger.warning("redis_delete_entry_failed", key=cache_key, error=str(e))
            return False
