"""
WebSocket connection manager for real-time dashboard updates.

Nexus Phase 5: Manages WebSocket subscriptions by dashboard type
(portfolio, initiative, pipeline) and broadcasts metric updates
when workflow events trigger recalculation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """A single WebSocket subscription to a dashboard view."""
    ws: WebSocket
    dashboard_type: str  # "portfolio", "initiative", "pipeline"
    scope_id: UUID | None = None  # initiative_id for scoped subscriptions


class DashboardWSManager:
    """
    Manages WebSocket connections subscribed to dashboard updates.

    Usage:
        manager = DashboardWSManager()

        # On client connect
        await manager.connect(ws, "portfolio")

        # On workflow event
        await manager.broadcast("portfolio", None, {"initiative_counts": {...}})

        # On client disconnect
        manager.disconnect(ws)
    """

    def __init__(self) -> None:
        self._subscriptions: list[Subscription] = []

    async def connect(
        self,
        ws: WebSocket,
        dashboard_type: str,
        scope_id: UUID | None = None,
    ) -> None:
        """Accept a WebSocket connection and register its subscription."""
        await ws.accept()
        sub = Subscription(ws=ws, dashboard_type=dashboard_type, scope_id=scope_id)
        self._subscriptions.append(sub)
        logger.info(
            "Dashboard WS connected: type=%s scope=%s (total: %d)",
            dashboard_type, scope_id, len(self._subscriptions),
        )

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket from all subscriptions."""
        before = len(self._subscriptions)
        self._subscriptions = [s for s in self._subscriptions if s.ws is not ws]
        removed = before - len(self._subscriptions)
        if removed:
            logger.info("Dashboard WS disconnected (%d subs remaining)", len(self._subscriptions))

    async def broadcast(
        self,
        dashboard_type: str,
        scope_id: UUID | None,
        data: dict,
    ) -> None:
        """
        Send data to all matching subscriptions.

        Matching rules:
        - dashboard_type must match exactly
        - If scope_id is provided, only subscribers with that scope_id (or no scope) receive it
        - If scope_id is None, all subscribers of that dashboard_type receive it
        """
        dead: list[Subscription] = []

        for sub in self._subscriptions:
            if sub.dashboard_type != dashboard_type:
                continue

            # Scope filtering: if broadcast has a scope, only send to matching or unscoped subs
            if scope_id is not None and sub.scope_id is not None and sub.scope_id != scope_id:
                continue

            try:
                await sub.ws.send_json({
                    "type": "dashboard_update",
                    "dashboard_type": dashboard_type,
                    "scope_id": str(scope_id) if scope_id else None,
                    "data": data,
                })
            except Exception:
                dead.append(sub)

        # Clean up dead connections
        if dead:
            self._subscriptions = [s for s in self._subscriptions if s not in dead]
            logger.info("Cleaned up %d dead dashboard WS connections", len(dead))

    @property
    def connection_count(self) -> int:
        return len(self._subscriptions)


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_ws_manager: DashboardWSManager | None = None


def init_ws_manager() -> DashboardWSManager:
    """Create and store the global WS manager singleton."""
    global _ws_manager
    _ws_manager = DashboardWSManager()
    return _ws_manager


def get_ws_manager() -> DashboardWSManager:
    """FastAPI dependency: returns the global WS manager."""
    if _ws_manager is None:
        raise RuntimeError("DashboardWSManager not initialized — app not started")
    return _ws_manager
