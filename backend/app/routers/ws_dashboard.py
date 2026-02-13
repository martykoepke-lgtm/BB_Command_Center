"""
WebSocket endpoint for real-time dashboard updates.

Nexus Phase 5: Clients subscribe to dashboard types and receive
live metric pushes when workflow events trigger recalculation.

Endpoints:
  WS /api/ws/dashboard?type=portfolio          — portfolio-wide updates
  WS /api/ws/dashboard?type=initiative&id=X    — single initiative updates
  WS /api/ws/dashboard?type=pipeline           — pipeline updates
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.ws_manager import get_ws_manager

router = APIRouter(tags=["WebSocket Dashboard"])

VALID_DASHBOARD_TYPES = {"portfolio", "initiative", "pipeline", "team"}


@router.websocket("/ws/dashboard")
async def dashboard_websocket(
    ws: WebSocket,
    type: str = Query("portfolio"),
    id: str | None = Query(None),
):
    """
    WebSocket endpoint for real-time dashboard updates.

    Query params:
        type: Dashboard type (portfolio, initiative, pipeline, team)
        id: Scope ID (required for initiative and team types)

    Server pushes:
        {"type": "dashboard_update", "dashboard_type": "...", "scope_id": "...", "data": {...}}
    """
    if type not in VALID_DASHBOARD_TYPES:
        await ws.close(code=4000, reason=f"Invalid dashboard type: {type}")
        return

    scope_id: UUID | None = None
    if id:
        try:
            scope_id = UUID(id)
        except ValueError:
            await ws.close(code=4001, reason=f"Invalid scope ID: {id}")
            return

    manager = get_ws_manager()
    await manager.connect(ws, type, scope_id)

    try:
        # Keep connection alive — client can send pings or close
        while True:
            # Wait for any client message (ping/keepalive)
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
