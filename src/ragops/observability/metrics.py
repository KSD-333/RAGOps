"""Application metrics — counters, gauges, histograms for monitoring.

Tracks:
- Requests/sec, error rate
- Retrieval metrics (chunks retrieved, empty retrieval rate)
- LLM metrics (tokens, latency, cost)
- Quality metrics (from evaluation)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ragops.core.logging import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Collect and report application metrics.

    In production, this would export to Prometheus/Grafana.
    For now, provides an in-memory metrics store.
    """

    def __init__(self):
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: float = 1.0, labels: dict | None = None) -> None:
        """Increment a counter."""
        key = self._make_key(name, labels)
        self._counters[key] += value

    def set_gauge(self, name: str, value: float, labels: dict | None = None) -> None:
        """Set a gauge value."""
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def observe(self, name: str, value: float, labels: dict | None = None) -> None:
        """Record an observation (for histograms)."""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)

    def get_counter(self, name: str, labels: dict | None = None) -> float:
        """Get a counter value."""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, labels: dict | None = None) -> float:
        """Get a gauge value."""
        key = self._make_key(name, labels)
        return self._gauges.get(key, 0.0)

    def get_histogram_stats(self, name: str, labels: dict | None = None) -> dict[str, float]:
        """Get histogram statistics."""
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])

        if not values:
            return {"count": 0, "min": 0, "max": 0, "mean": 0, "p50": 0, "p95": 0, "p99": 0}

        sorted_values = sorted(values)
        n = len(sorted_values)

        return {
            "count": n,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "mean": sum(sorted_values) / n,
            "p50": sorted_values[n // 2],
            "p95": sorted_values[int(n * 0.95)],
            "p99": sorted_values[int(n * 0.99)],
        }

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics as a dictionary."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                key: self.get_histogram_stats(key) for key in self._histograms
            },
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()

    def _make_key(self, name: str, labels: dict | None = None) -> str:
        """Create a metric key with optional labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


# Global metrics instance
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    return _metrics
