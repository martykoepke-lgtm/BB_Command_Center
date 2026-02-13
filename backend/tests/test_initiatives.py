"""Initiative router tests — CRUD, phase management, auto-advance."""

import pytest
from httpx import AsyncClient


VALID_INITIATIVE = {
    "title": "Reduce cycle time in lab processing",
    "problem_statement": "Lab results take 72 hours on average",
    "desired_outcome": "Reduce to under 48 hours for 90% of tests",
    "methodology": "DMAIC",
    "priority": "high",
}


@pytest.mark.asyncio
async def test_create_initiative_dmaic(client: AsyncClient):
    resp = await client.post("/api/initiatives", json=VALID_INITIATIVE)
    assert resp.status_code == 201
    data = resp.json()
    assert data["initiative_number"].startswith("INI-")
    assert data["methodology"] == "DMAIC"
    assert data["status"] == "active"
    assert data["current_phase"] == "define"
    assert len(data["phases"]) == 5
    phase_names = [p["phase_name"] for p in data["phases"]]
    assert phase_names == ["define", "measure", "analyze", "improve", "control"]
    # First phase should be in_progress
    assert data["phases"][0]["status"] == "in_progress"
    assert data["phases"][1]["status"] == "not_started"


@pytest.mark.asyncio
async def test_create_initiative_a3(client: AsyncClient):
    resp = await client.post("/api/initiatives", json={
        **VALID_INITIATIVE,
        "title": "A3 problem solving initiative",
        "methodology": "A3",
    })
    assert resp.status_code == 201
    assert len(resp.json()["phases"]) == 7


@pytest.mark.asyncio
async def test_create_initiative_pdsa(client: AsyncClient):
    resp = await client.post("/api/initiatives", json={
        **VALID_INITIATIVE,
        "title": "PDSA rapid improvement cycle",
        "methodology": "PDSA",
    })
    assert resp.status_code == 201
    assert len(resp.json()["phases"]) == 4


@pytest.mark.asyncio
async def test_create_initiative_kaizen(client: AsyncClient):
    resp = await client.post("/api/initiatives", json={
        **VALID_INITIATIVE,
        "title": "Kaizen event for scheduling",
        "methodology": "Kaizen",
    })
    assert resp.status_code == 201
    assert len(resp.json()["phases"]) == 3


@pytest.mark.asyncio
async def test_list_initiatives(client: AsyncClient):
    await client.post("/api/initiatives", json=VALID_INITIATIVE)
    resp = await client.get("/api/initiatives")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_list_initiatives_filter_status(client: AsyncClient):
    resp = await client.get("/api/initiatives", params={"status": "active"})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "active"


@pytest.mark.asyncio
async def test_get_initiative_by_id(client: AsyncClient):
    create_resp = await client.post("/api/initiatives", json=VALID_INITIATIVE)
    initiative_id = create_resp.json()["id"]

    resp = await client.get(f"/api/initiatives/{initiative_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == initiative_id


@pytest.mark.asyncio
async def test_get_initiative_not_found(client: AsyncClient):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/initiatives/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_initiative(client: AsyncClient):
    create_resp = await client.post("/api/initiatives", json=VALID_INITIATIVE)
    initiative_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/initiatives/{initiative_id}", json={
        "priority": "critical",
        "scope": "Lab department only",
    })
    assert resp.status_code == 200
    assert resp.json()["priority"] == "critical"
    assert resp.json()["scope"] == "Lab department only"


@pytest.mark.asyncio
async def test_list_phases(client: AsyncClient):
    create_resp = await client.post("/api/initiatives", json=VALID_INITIATIVE)
    initiative_id = create_resp.json()["id"]

    resp = await client.get(f"/api/initiatives/{initiative_id}/phases")
    assert resp.status_code == 200
    phases = resp.json()
    assert len(phases) == 5
    assert phases[0]["phase_name"] == "define"


@pytest.mark.asyncio
async def test_phase_auto_advance(client: AsyncClient):
    """Complete define phase → measure should auto-start, initiative current_phase updates."""
    create_resp = await client.post("/api/initiatives", json=VALID_INITIATIVE)
    initiative_id = create_resp.json()["id"]

    # Complete the define phase
    resp = await client.patch(
        f"/api/initiatives/{initiative_id}/phases/define",
        params={"status": "completed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # Check initiative moved to measure
    init_resp = await client.get(f"/api/initiatives/{initiative_id}")
    assert init_resp.json()["current_phase"] == "measure"

    # Measure phase should be in_progress
    phases_resp = await client.get(f"/api/initiatives/{initiative_id}/phases")
    phases = {p["phase_name"]: p for p in phases_resp.json()}
    assert phases["measure"]["status"] == "in_progress"


@pytest.mark.asyncio
async def test_completing_all_phases_completes_initiative(client: AsyncClient):
    """Walk through all 5 DMAIC phases → initiative should become completed."""
    create_resp = await client.post("/api/initiatives", json=VALID_INITIATIVE)
    initiative_id = create_resp.json()["id"]

    for phase in ["define", "measure", "analyze", "improve", "control"]:
        resp = await client.patch(
            f"/api/initiatives/{initiative_id}/phases/{phase}",
            params={"status": "completed"},
        )
        assert resp.status_code == 200

    init_resp = await client.get(f"/api/initiatives/{initiative_id}")
    data = init_resp.json()
    assert data["status"] == "completed"
    assert data["current_phase"] == "complete"


@pytest.mark.asyncio
async def test_update_phase_gate_approval(client: AsyncClient):
    create_resp = await client.post("/api/initiatives", json=VALID_INITIATIVE)
    initiative_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/initiatives/{initiative_id}/phases/define",
        params={"gate_approved": True, "gate_notes": "Approved by sponsor"},
    )
    assert resp.status_code == 200
    assert resp.json()["gate_approved"] is True


@pytest.mark.asyncio
async def test_update_nonexistent_phase(client: AsyncClient):
    create_resp = await client.post("/api/initiatives", json=VALID_INITIATIVE)
    initiative_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/initiatives/{initiative_id}/phases/nonexistent",
        params={"status": "completed"},
    )
    assert resp.status_code == 404
