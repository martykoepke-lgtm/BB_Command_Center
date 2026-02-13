"""Action items router tests — CRUD, auto-complete timestamp."""

import pytest
from httpx import AsyncClient


async def _create_initiative(client: AsyncClient) -> str:
    resp = await client.post("/api/initiatives", json={
        "title": "Action test initiative here",
        "problem_statement": "Need actions to track work items",
        "desired_outcome": "All actions tracked and completed",
    })
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_action_item(client: AsyncClient):
    initiative_id = await _create_initiative(client)
    resp = await client.post(f"/api/initiatives/{initiative_id}/actions", json={
        "title": "Collect baseline data",
        "description": "Gather 30 days of cycle time data",
        "priority": "high",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Collect baseline data"
    assert data["status"] == "not_started"
    assert data["priority"] == "high"
    assert data["initiative_id"] == initiative_id


@pytest.mark.asyncio
async def test_list_initiative_actions(client: AsyncClient):
    initiative_id = await _create_initiative(client)
    await client.post(f"/api/initiatives/{initiative_id}/actions", json={
        "title": "Action one for listing",
    })
    await client.post(f"/api/initiatives/{initiative_id}/actions", json={
        "title": "Action two for listing",
    })

    resp = await client.get(f"/api/initiatives/{initiative_id}/actions")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_list_all_actions(client: AsyncClient):
    initiative_id = await _create_initiative(client)
    await client.post(f"/api/initiatives/{initiative_id}/actions", json={
        "title": "Global action item test",
    })

    resp = await client.get("/api/actions")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_update_action_item(client: AsyncClient):
    initiative_id = await _create_initiative(client)
    create_resp = await client.post(f"/api/initiatives/{initiative_id}/actions", json={
        "title": "Action to update here",
    })
    action_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/actions/{action_id}", json={
        "priority": "critical",
        "notes": "Escalated by manager",
    })
    assert resp.status_code == 200
    assert resp.json()["priority"] == "critical"
    assert resp.json()["notes"] == "Escalated by manager"


@pytest.mark.asyncio
async def test_completing_action_sets_timestamp(client: AsyncClient):
    initiative_id = await _create_initiative(client)
    create_resp = await client.post(f"/api/initiatives/{initiative_id}/actions", json={
        "title": "Action to complete here",
    })
    action_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/actions/{action_id}", json={
        "status": "completed",
    })
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is not None


@pytest.mark.asyncio
async def test_get_single_action(client: AsyncClient):
    initiative_id = await _create_initiative(client)
    create_resp = await client.post(f"/api/initiatives/{initiative_id}/actions", json={
        "title": "Action to get by ID",
        "priority": "critical",
    })
    action_id = create_resp.json()["id"]

    resp = await client.get(f"/api/actions/{action_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == action_id
    assert data["title"] == "Action to get by ID"
    assert data["priority"] == "critical"


@pytest.mark.asyncio
async def test_get_single_action_not_found(client: AsyncClient):
    resp = await client.get("/api/actions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_action_global(client: AsyncClient):
    """POST /api/actions with initiative_id in the body."""
    initiative_id = await _create_initiative(client)
    resp = await client.post("/api/actions", json={
        "initiative_id": initiative_id,
        "title": "Global create action",
        "priority": "high",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Global create action"
    assert data["initiative_id"] == initiative_id


@pytest.mark.asyncio
async def test_delete_action_item(client: AsyncClient):
    initiative_id = await _create_initiative(client)
    create_resp = await client.post(f"/api/initiatives/{initiative_id}/actions", json={
        "title": "Action to delete here",
    })
    action_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/actions/{action_id}")
    assert resp.status_code == 204

    # Verify deleted
    get_resp = await client.get(f"/api/actions/{action_id}")
    assert get_resp.status_code == 404
