"""Tests for the WebSocket dashboard manager."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ws_manager import DashboardWSManager


def _make_ws() -> MagicMock:
    """Create a mock WebSocket."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def manager() -> DashboardWSManager:
    return DashboardWSManager()


# -------------------------------------------------------------------
# Connection management
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_and_receive_update(manager: DashboardWSManager):
    """Connected client receives broadcast update."""
    ws = _make_ws()
    await manager.connect(ws, "portfolio")

    await manager.broadcast("portfolio", None, {"total_initiatives": 10})

    ws.send_json.assert_called_once()
    payload = ws.send_json.call_args[0][0]
    assert payload["type"] == "dashboard_update"
    assert payload["dashboard_type"] == "portfolio"
    assert payload["data"]["total_initiatives"] == 10


@pytest.mark.asyncio
async def test_disconnect_cleanup(manager: DashboardWSManager):
    """Disconnected client is removed from subscriptions."""
    ws = _make_ws()
    await manager.connect(ws, "portfolio")
    assert manager.connection_count == 1

    manager.disconnect(ws)
    assert manager.connection_count == 0


@pytest.mark.asyncio
async def test_scoped_broadcast(manager: DashboardWSManager):
    """Initiative update only goes to that initiative's subscribers."""
    init_id = uuid.uuid4()
    other_id = uuid.uuid4()

    ws_target = _make_ws()
    ws_other = _make_ws()

    await manager.connect(ws_target, "initiative", init_id)
    await manager.connect(ws_other, "initiative", other_id)

    await manager.broadcast("initiative", init_id, {"phase": "measure"})

    ws_target.send_json.assert_called_once()
    ws_other.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_portfolio_broadcast(manager: DashboardWSManager):
    """Portfolio event goes to all portfolio subscribers."""
    ws1 = _make_ws()
    ws2 = _make_ws()
    ws_init = _make_ws()

    await manager.connect(ws1, "portfolio")
    await manager.connect(ws2, "portfolio")
    await manager.connect(ws_init, "initiative", uuid.uuid4())

    await manager.broadcast("portfolio", None, {"data": "update"})

    assert ws1.send_json.call_count == 1
    assert ws2.send_json.call_count == 1
    ws_init.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_concurrent_connections(manager: DashboardWSManager):
    """Multiple clients receive the same broadcast."""
    clients = [_make_ws() for _ in range(5)]
    for ws in clients:
        await manager.connect(ws, "pipeline")

    await manager.broadcast("pipeline", None, {"status": "ok"})

    for ws in clients:
        ws.send_json.assert_called_once()


@pytest.mark.asyncio
async def test_dead_connection_cleanup(manager: DashboardWSManager):
    """Dead connections are cleaned up during broadcast."""
    ws_alive = _make_ws()
    ws_dead = _make_ws()
    ws_dead.send_json.side_effect = RuntimeError("Connection closed")

    await manager.connect(ws_alive, "portfolio")
    await manager.connect(ws_dead, "portfolio")
    assert manager.connection_count == 2

    await manager.broadcast("portfolio", None, {"data": "test"})

    # Dead connection should be cleaned up
    assert manager.connection_count == 1
    ws_alive.send_json.assert_called_once()


@pytest.mark.asyncio
async def test_unscoped_sub_receives_scoped_broadcast(manager: DashboardWSManager):
    """A subscriber without scope_id receives scoped broadcasts."""
    ws_unscoped = _make_ws()
    init_id = uuid.uuid4()

    await manager.connect(ws_unscoped, "initiative")  # No scope_id

    await manager.broadcast("initiative", init_id, {"phase": "define"})

    # Unscoped subscriber should receive scoped broadcasts
    ws_unscoped.send_json.assert_called_once()
