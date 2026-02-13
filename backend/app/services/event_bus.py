"""
Lightweight async event bus for workflow automation.

Nexus Phase 5: Connects subsystems via publish/subscribe events.
Handlers run as fire-and-forget background tasks so publishers
never block on handler execution.

Event flow:
  Router → publish(event_type, payload) → handlers run in background
  Handler → invoke AI agent, send email, broadcast WS update, etc.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

DATASET_UPLOADED = "dataset.uploaded"
ANALYSIS_COMPLETED = "analysis.completed"
PHASE_ADVANCED = "phase.advanced"
INITIATIVE_COMPLETED = "initiative.completed"
ACTION_ASSIGNED = "action.assigned"
ACTION_BLOCKER = "action.blocker_flagged"


# Handler type: async callable that takes a payload dict
EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------

class EventBus:
    """
    In-process async event bus.

    Handlers are registered via subscribe() and invoked as background
    asyncio tasks when publish() is called. Each handler runs independently;
    a failing handler does not block other handlers or the publisher.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._background_tasks: set[asyncio.Task] = set()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        self._handlers.setdefault(event_type, []).append(handler)
        logger.debug("EventBus: subscribed %s to %s", handler.__name__, event_type)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """
        Publish an event. All registered handlers run as background tasks.

        This method returns immediately — handlers execute asynchronously.
        """
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug("EventBus: no handlers for %s", event_type)
            return

        logger.info("EventBus: publishing %s (%d handlers)", event_type, len(handlers))

        for handler in handlers:
            task = asyncio.create_task(self._run_handler(handler, event_type, payload))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def _run_handler(
        self,
        handler: EventHandler,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Execute a single handler with error isolation."""
        try:
            await handler(payload)
        except Exception:
            logger.exception(
                "EventBus: handler %s failed for event %s",
                handler.__name__,
                event_type,
            )

    async def drain(self) -> None:
        """Wait for all background tasks to complete. Useful in tests."""
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

    @property
    def handler_count(self) -> int:
        return sum(len(h) for h in self._handlers.values())


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_event_bus: EventBus | None = None


def init_event_bus() -> EventBus:
    """Create and store the global event bus singleton."""
    global _event_bus
    _event_bus = EventBus()
    return _event_bus


def get_event_bus() -> EventBus:
    """FastAPI dependency: returns the global event bus."""
    if _event_bus is None:
        raise RuntimeError("EventBus not initialized — app not started")
    return _event_bus
