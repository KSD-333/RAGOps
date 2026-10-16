"""API middleware — request logging, error handling, CORS."""

from __future__ import annotations

import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ragops.core.logging import get_logger
from ragops.observability.metrics import get_metrics

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests with timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        # Add request ID to headers
        logger.info(
            "request_received",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "request_completed",
                request_id=request_id,
                status=response.status_code,
                latency_ms=round(elapsed_ms, 2),
            )

            # Record metrics
            metrics = get_metrics()
            metrics.increment("http_requests_total", labels={"status": str(response.status_code)})
            metrics.observe("http_request_duration_ms", elapsed_ms)

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-Ms"] = str(round(elapsed_ms, 2))

            return response

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "request_failed",
                request_id=request_id,
                error=str(e),
                latency_ms=round(elapsed_ms, 2),
            )

            metrics = get_metrics()
            metrics.increment("http_requests_total", labels={"status": "500"})
            metrics.increment("http_request_errors_total")

            raise
