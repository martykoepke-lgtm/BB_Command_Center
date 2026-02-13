"""Request intake router tests — CRUD, convert to initiative."""

import pytest
from httpx import AsyncClient


VALID_REQUEST = {
    "title": "Reduce patient wait times",
    "description": "Average wait times exceed 30 minutes",
    "requester_name": "Jane Doe",
    "requester_email": "jane@hospital.org",
    "requester_dept": "Operations",
    "problem_statement": "Patients wait too long in the lobby",
    "desired_outcome": "Average wait under 15 minutes",
    "business_impact": "Patient satisfaction scores dropping",
    "urgency": "high",
}


@pytest.mark.asyncio
async def test_create_request(client: AsyncClient):
    resp = await client.post("/api/requests", json=VALID_REQUEST)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == VALID_REQUEST["title"]
    assert data["request_number"].startswith("REQ-")
    assert data["status"] == "submitted"
    assert data["urgency"] == "high"


@pytest.mark.asyncio
async def test_create_request_minimal(client: AsyncClient):
    resp = await client.post("/api/requests", json={
        "title": "Simple request title here",
        "requester_name": "John",
    })
    assert resp.status_code == 201
    assert resp.json()["urgency"] == "medium"  # default


@pytest.mark.asyncio
async def test_create_request_validation_error(client: AsyncClient):
    resp = await client.post("/api/requests", json={
        "title": "Hi",  # too short (min_length=5)
        "requester_name": "John",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_requests(client: AsyncClient):
    # Create two requests
    await client.post("/api/requests", json={
        "title": "First request title",
        "requester_name": "Alice",
    })
    await client.post("/api/requests", json={
        "title": "Second request title",
        "requester_name": "Bob",
    })

    resp = await client.get("/api/requests")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_list_requests_filter_status(client: AsyncClient):
    resp = await client.get("/api/requests", params={"status": "submitted"})
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "submitted"


@pytest.mark.asyncio
async def test_get_request_by_id(client: AsyncClient):
    create_resp = await client.post("/api/requests", json={
        "title": "Specific request lookup",
        "requester_name": "Carol",
    })
    request_id = create_resp.json()["id"]

    resp = await client.get(f"/api/requests/{request_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == request_id


@pytest.mark.asyncio
async def test_get_request_not_found(client: AsyncClient):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/requests/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_request(client: AsyncClient):
    create_resp = await client.post("/api/requests", json={
        "title": "Request to be updated",
        "requester_name": "Dave",
    })
    request_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/requests/{request_id}", json={
        "status": "under_review",
        "review_notes": "Looks promising",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "under_review"
    assert data["review_notes"] == "Looks promising"
    assert data["reviewed_at"] is not None


@pytest.mark.asyncio
async def test_convert_request_to_initiative(client: AsyncClient):
    # Create and accept a request
    create_resp = await client.post("/api/requests", json={
        "title": "Convert me to initiative",
        "requester_name": "Eve",
        "problem_statement": "Too many defects",
        "desired_outcome": "Zero defects",
    })
    request_id = create_resp.json()["id"]

    await client.patch(f"/api/requests/{request_id}", json={
        "status": "accepted",
    })

    # Convert
    resp = await client.post(f"/api/requests/{request_id}/convert")
    assert resp.status_code == 201
    data = resp.json()
    assert data["initiative_number"].startswith("INI-")
    assert len(data["phases"]) == 5  # DMAIC phases
    assert data["phases"][0]["phase_name"] == "define"


@pytest.mark.asyncio
async def test_convert_non_accepted_request_fails(client: AsyncClient):
    create_resp = await client.post("/api/requests", json={
        "title": "Not accepted request here",
        "requester_name": "Frank",
    })
    request_id = create_resp.json()["id"]

    resp = await client.post(f"/api/requests/{request_id}/convert")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_convert_already_converted_fails(client: AsyncClient):
    create_resp = await client.post("/api/requests", json={
        "title": "Already converted request",
        "requester_name": "Grace",
        "problem_statement": "Something broken",
        "desired_outcome": "Fix it",
    })
    request_id = create_resp.json()["id"]

    await client.patch(f"/api/requests/{request_id}", json={"status": "accepted"})
    await client.post(f"/api/requests/{request_id}/convert")

    # Second convert should fail
    resp = await client.post(f"/api/requests/{request_id}/convert")
    assert resp.status_code == 400
