"""Tests for the async event bus."""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from app.services.event_bus import EventBus


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


# -------------------------------------------------------------------
# Core publish / subscribe
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscribe_and_publish(bus: EventBus):
    """Handler receives the published payload."""
    received = []

    async def handler(payload: dict):
        received.append(payload)

    bus.subscribe("test.event", handler)
    await bus.publish("test.event", {"key": "value"})
    await bus.drain()

    assert len(received) == 1
    assert received[0] == {"key": "value"}


@pytest.mark.asyncio
async def test_multiple_handlers(bus: EventBus):
    """All handlers fire for the same event type."""
    calls = {"a": 0, "b": 0}

    async def handler_a(payload):
        calls["a"] += 1

    async def handler_b(payload):
        calls["b"] += 1

    bus.subscribe("multi", handler_a)
    bus.subscribe("multi", handler_b)
    await bus.publish("multi", {})
    await bus.drain()

    assert calls == {"a": 1, "b": 1}


@pytest.mark.asyncio
async def test_handler_exception_isolated(bus: EventBus):
    """A failing handler does not prevent other handlers from running."""
    success_called = False

    async def bad_handler(payload):
        raise ValueError("boom")

    async def good_handler(payload):
        nonlocal success_called
        success_called = True

    bus.subscribe("err", bad_handler)
    bus.subscribe("err", good_handler)
    await bus.publish("err", {})
    await bus.drain()

    assert success_called


@pytest.mark.asyncio
async def test_no_subscribers(bus: EventBus):
    """Publishing with no subscribers does not error."""
    await bus.publish("nobody.listens", {"data": 1})
    # Should not raise


@pytest.mark.asyncio
async def test_publish_returns_quickly(bus: EventBus):
    """Handlers run in the background; publish returns immediately."""
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_handler(payload):
        started.set()
        await release.wait()

    bus.subscribe("slow", slow_handler)
    await bus.publish("slow", {})

    # Publish returned — handler should be running but not finished
    await asyncio.wait_for(started.wait(), timeout=2.0)

    # Clean up
    release.set()
    await bus.drain()


@pytest.mark.asyncio
async def test_different_events_isolated(bus: EventBus):
    """Handlers only fire for their subscribed event type."""
    calls = {"a": 0, "b": 0}

    async def handler_a(p):
        calls["a"] += 1

    async def handler_b(p):
        calls["b"] += 1

    bus.subscribe("event_a", handler_a)
    bus.subscribe("event_b", handler_b)

    await bus.publish("event_a", {})
    await bus.drain()

    assert calls == {"a": 1, "b": 0}


@pytest.mark.asyncio
async def test_handler_count(bus: EventBus):
    """handler_count property reports total registered handlers."""
    async def h(p): ...

    assert bus.handler_count == 0
    bus.subscribe("x", h)
    bus.subscribe("y", h)
    bus.subscribe("x", h)
    assert bus.handler_count == 3


@pytest.mark.asyncio
async def test_drain_with_no_tasks(bus: EventBus):
    """drain() works even when no tasks are pending."""
    await bus.drain()  # Should not raise
