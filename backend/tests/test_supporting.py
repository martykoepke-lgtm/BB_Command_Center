"""Tests for notes, documents, metrics, and artifacts routers."""

import pytest
from httpx import AsyncClient


async def _create_initiative_with_phase(client: AsyncClient) -> tuple[str, str, str]:
    """Create an initiative and return (initiative_id, first_phase_id, first_phase_name)."""
    resp = await client.post("/api/initiatives", json={
        "title": "Supporting entity test initiative",
        "problem_statement": "Need to test notes, docs, metrics, artifacts",
        "desired_outcome": "All supporting entities work correctly",
    })
    data = resp.json()
    return data["id"], data["phases"][0]["id"], data["phases"][0]["phase_name"]


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_note(client: AsyncClient):
    initiative_id, _, _ = await _create_initiative_with_phase(client)
    resp = await client.post(f"/api/initiatives/{initiative_id}/notes", json={
        "content": "This is an important observation from the gemba walk.",
        "note_type": "observation",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "This is an important observation from the gemba walk."
    assert data["note_type"] == "observation"


@pytest.mark.asyncio
async def test_list_notes(client: AsyncClient):
    initiative_id, _, _ = await _create_initiative_with_phase(client)
    await client.post(f"/api/initiatives/{initiative_id}/notes", json={
        "content": "Note one for listing test",
    })
    await client.post(f"/api/initiatives/{initiative_id}/notes", json={
        "content": "Note two for listing test",
    })

    resp = await client.get(f"/api/initiatives/{initiative_id}/notes")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_list_notes_filter_type(client: AsyncClient):
    initiative_id, _, _ = await _create_initiative_with_phase(client)
    await client.post(f"/api/initiatives/{initiative_id}/notes", json={
        "content": "Decision note content",
        "note_type": "decision",
    })
    await client.post(f"/api/initiatives/{initiative_id}/notes", json={
        "content": "General note content",
        "note_type": "general",
    })

    resp = await client.get(
        f"/api/initiatives/{initiative_id}/notes",
        params={"note_type": "decision"},
    )
    assert resp.status_code == 200
    for note in resp.json():
        assert note["note_type"] == "decision"


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_document(client: AsyncClient):
    initiative_id, _, _ = await _create_initiative_with_phase(client)
    resp = await client.post(f"/api/initiatives/{initiative_id}/documents", json={
        "name": "Project Charter v1",
        "document_type": "charter",
        "external_url": "https://docs.example.com/charter",
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "Project Charter v1"


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient):
    initiative_id, _, _ = await _create_initiative_with_phase(client)
    await client.post(f"/api/initiatives/{initiative_id}/documents", json={
        "name": "Document one for listing",
    })

    resp = await client.get(f"/api/initiatives/{initiative_id}/documents")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_metric(client: AsyncClient):
    initiative_id, _, _ = await _create_initiative_with_phase(client)
    resp = await client.post(f"/api/initiatives/{initiative_id}/metrics", json={
        "name": "Average Cycle Time",
        "unit": "hours",
        "baseline_value": 72.0,
        "target_value": 48.0,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Average Cycle Time"
    assert data["baseline_value"] == 72.0
    assert data["target_value"] == 48.0


@pytest.mark.asyncio
async def test_update_metric(client: AsyncClient):
    initiative_id, _, _ = await _create_initiative_with_phase(client)
    create_resp = await client.post(f"/api/initiatives/{initiative_id}/metrics", json={
        "name": "Defect Rate",
        "unit": "%",
        "baseline_value": 5.0,
        "target_value": 2.0,
    })
    metric_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/metrics/{metric_id}", json={
        "current_value": 3.5,
        "target_met": False,
    })
    assert resp.status_code == 200
    assert resp.json()["current_value"] == 3.5
    assert resp.json()["target_met"] is False


@pytest.mark.asyncio
async def test_list_metrics(client: AsyncClient):
    initiative_id, _, _ = await _create_initiative_with_phase(client)
    await client.post(f"/api/initiatives/{initiative_id}/metrics", json={
        "name": "Throughput metric test",
        "unit": "units/hr",
    })

    resp = await client.get(f"/api/initiatives/{initiative_id}/metrics")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_artifact(client: AsyncClient):
    initiative_id, _, phase_name = await _create_initiative_with_phase(client)
    resp = await client.post(
        f"/api/initiatives/{initiative_id}/phases/{phase_name}/artifacts",
        json={
            "artifact_type": "project_charter",
            "title": "Project Charter",
            "content": {
                "problem": "Lab cycle time too long",
                "goal": "Reduce to 48 hours",
                "scope": "Lab department",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["artifact_type"] == "project_charter"
    assert data["status"] == "draft"
    assert "problem" in data["content"]


@pytest.mark.asyncio
async def test_list_artifacts(client: AsyncClient):
    initiative_id, _, phase_name = await _create_initiative_with_phase(client)
    await client.post(
        f"/api/initiatives/{initiative_id}/phases/{phase_name}/artifacts",
        json={
            "artifact_type": "sipoc",
            "title": "SIPOC Diagram",
            "content": {"suppliers": [], "inputs": [], "process": [], "outputs": [], "customers": []},
        },
    )

    resp = await client.get(f"/api/initiatives/{initiative_id}/phases/{phase_name}/artifacts")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_artifact(client: AsyncClient):
    initiative_id, _, phase_name = await _create_initiative_with_phase(client)
    create_resp = await client.post(
        f"/api/initiatives/{initiative_id}/phases/{phase_name}/artifacts",
        json={
            "artifact_type": "voc",
            "title": "Voice of Customer",
            "content": {"feedback": []},
        },
    )
    artifact_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/artifacts/{artifact_id}", json={
        "status": "approved",
        "content": {"feedback": ["Need faster turnaround"]},
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert len(resp.json()["content"]["feedback"]) == 1
