"""User management router tests — list, get, update, workload."""

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_list_users_requires_admin_or_manager(client: AsyncClient):
    """Analyst role should be forbidden from listing all users."""
    resp = await client.get("/api/users")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_users_as_admin(admin_client: AsyncClient):
    resp = await admin_client.get("/api/users")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient, test_user: User):
    resp = await client.get(f"/api/users/{test_user.id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == test_user.email


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/users/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_own_profile(client: AsyncClient, test_user: User):
    resp = await client.patch(f"/api/users/{test_user.id}", json={
        "full_name": "Updated Name",
        "title": "Senior Analyst",
    })
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"
    assert resp.json()["title"] == "Senior Analyst"


@pytest.mark.asyncio
async def test_analyst_cannot_change_own_role(client: AsyncClient, test_user: User):
    """Non-admins cannot promote themselves."""
    resp = await client.patch(f"/api/users/{test_user.id}", json={
        "role": "admin",
    })
    assert resp.status_code == 200
    # Role change should be silently ignored for non-admins
    assert resp.json()["role"] == "analyst"


@pytest.mark.asyncio
async def test_analyst_cannot_update_other_user(client: AsyncClient, admin_user: User):
    """Analyst cannot update another user's profile."""
    resp = await client.patch(f"/api/users/{admin_user.id}", json={
        "full_name": "Hacked Name",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_user_workload(client: AsyncClient, test_user: User):
    resp = await client.get(f"/api/users/{test_user.id}/workload")
    assert resp.status_code == 200
    data = resp.json()
    assert data["capacity_hours"] == 40.0
    assert data["allocated_hours"] == 0.0
    assert data["utilization_pct"] == 0.0
    assert data["active_initiatives"] == 0
