"""Team management router tests — CRUD, member add/remove."""

import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_create_team(admin_client: AsyncClient):
    resp = await admin_client.post("/api/teams", json={
        "name": "Quality Team",
        "description": "Performance excellence analysts",
        "department": "Operations",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Quality Team"
    assert data["member_count"] == 0


@pytest.mark.asyncio
async def test_create_team_analyst_forbidden(client: AsyncClient):
    """Analysts cannot create teams."""
    resp = await client.post("/api/teams", json={
        "name": "Unauthorized Team",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_teams(admin_client: AsyncClient):
    await admin_client.post("/api/teams", json={"name": "Team Alpha"})
    resp = await admin_client.get("/api/teams")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_team_by_id(admin_client: AsyncClient):
    create_resp = await admin_client.post("/api/teams", json={"name": "Lookup Team"})
    team_id = create_resp.json()["id"]

    resp = await admin_client.get(f"/api/teams/{team_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Lookup Team"


@pytest.mark.asyncio
async def test_update_team(admin_client: AsyncClient):
    create_resp = await admin_client.post("/api/teams", json={"name": "Old Name"})
    team_id = create_resp.json()["id"]

    resp = await admin_client.patch(f"/api/teams/{team_id}", json={
        "name": "New Name",
        "department": "Quality",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    assert resp.json()["department"] == "Quality"


@pytest.mark.asyncio
async def test_delete_team(admin_client: AsyncClient):
    """DELETE /api/teams/{id} removes a team."""
    create_resp = await admin_client.post("/api/teams", json={"name": "Team to Delete"})
    team_id = create_resp.json()["id"]

    resp = await admin_client.delete(f"/api/teams/{team_id}")
    assert resp.status_code == 204

    # Verify deleted
    get_resp = await admin_client.get(f"/api/teams/{team_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_team_not_found(admin_client: AsyncClient):
    """DELETE /api/teams/{id} returns 404 for missing team."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await admin_client.delete(f"/api/teams/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_member_to_team(admin_client: AsyncClient, test_user: User):
    create_resp = await admin_client.post("/api/teams", json={"name": "Member Test Team"})
    team_id = create_resp.json()["id"]

    resp = await admin_client.post(
        f"/api/teams/{team_id}/members",
        json={"user_id": str(test_user.id), "role_in_team": "analyst"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "added"


@pytest.mark.asyncio
async def test_add_duplicate_member_fails(admin_client: AsyncClient, test_user: User):
    create_resp = await admin_client.post("/api/teams", json={"name": "Dup Member Team"})
    team_id = create_resp.json()["id"]

    await admin_client.post(
        f"/api/teams/{team_id}/members",
        json={"user_id": str(test_user.id)},
    )
    resp = await admin_client.post(
        f"/api/teams/{team_id}/members",
        json={"user_id": str(test_user.id)},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_team_members(admin_client: AsyncClient, test_user: User):
    create_resp = await admin_client.post("/api/teams", json={"name": "Members List Team"})
    team_id = create_resp.json()["id"]

    await admin_client.post(
        f"/api/teams/{team_id}/members",
        json={"user_id": str(test_user.id)},
    )

    resp = await admin_client.get(f"/api/teams/{team_id}/members")
    assert resp.status_code == 200
    members = resp.json()
    assert len(members) == 1
    assert members[0]["full_name"] == test_user.full_name


@pytest.mark.asyncio
async def test_remove_team_member(admin_client: AsyncClient, test_user: User):
    create_resp = await admin_client.post("/api/teams", json={"name": "Remove Member Team"})
    team_id = create_resp.json()["id"]

    await admin_client.post(
        f"/api/teams/{team_id}/members",
        json={"user_id": str(test_user.id)},
    )

    resp = await admin_client.delete(f"/api/teams/{team_id}/members/{test_user.id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_remove_nonexistent_member(admin_client: AsyncClient):
    create_resp = await admin_client.post("/api/teams", json={"name": "Empty Team"})
    team_id = create_resp.json()["id"]
    fake_user = "00000000-0000-0000-0000-000000000000"

    resp = await admin_client.delete(f"/api/teams/{team_id}/members/{fake_user}")
    assert resp.status_code == 404
