"""Event system — structured domain events for observability."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from ragops.core.logging import get_logger

logger = get_logger(__name__)


class EventBus:
    """Simple event bus for domain events.

    Allows modules to emit events without tight coupling.
    Observability, feedback, and metrics can subscribe to events.
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Emit an event to all subscribers."""
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }

        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("event_handler_failed", event_type=event_type, error=str(e))

        logger.debug("event_emitted", type=event_type, handlers=len(handlers))


# Global event bus
_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Get the global event bus."""
    return _event_bus
