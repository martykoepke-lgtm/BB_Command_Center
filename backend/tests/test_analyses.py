"""Statistical analyses router tests — CRUD, execute, rerun."""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.initiative import Initiative
from app.models.analysis import Dataset, StatisticalAnalysis
from app.models.user import User


async def _create_initiative(client: AsyncClient) -> str:
    resp = await client.post("/api/initiatives", json={
        "title": "Analysis test initiative",
        "problem_statement": "Need statistical analysis",
        "desired_outcome": "Data-driven decisions",
    })
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# CRUD Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_analysis(client: AsyncClient):
    """POST /api/initiatives/{id}/analyses creates a statistical analysis."""
    initiative_id = await _create_initiative(client)
    resp = await client.post(f"/api/initiatives/{initiative_id}/analyses", json={
        "test_type": "t_test",
        "test_category": "hypothesis",
        "configuration": {"alpha": 0.05, "alternative": "two_sided"},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["test_type"] == "t_test"
    assert data["test_category"] == "hypothesis"
    assert data["initiative_id"] == initiative_id
    assert data["status"] in ("pending", "completed", "failed")


@pytest.mark.asyncio
async def test_list_analyses(client: AsyncClient):
    """GET /api/initiatives/{id}/analyses lists analyses for an initiative."""
    initiative_id = await _create_initiative(client)
    await client.post(f"/api/initiatives/{initiative_id}/analyses", json={
        "test_type": "chi_square",
        "test_category": "association",
        "configuration": {"alpha": 0.05},
    })
    await client.post(f"/api/initiatives/{initiative_id}/analyses", json={
        "test_type": "t_test",
        "test_category": "hypothesis",
        "configuration": {"alpha": 0.01},
    })

    resp = await client.get(f"/api/initiatives/{initiative_id}/analyses")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_list_analyses_filter_by_category(client: AsyncClient):
    """GET /api/initiatives/{id}/analyses?test_category=hypothesis filters."""
    initiative_id = await _create_initiative(client)
    await client.post(f"/api/initiatives/{initiative_id}/analyses", json={
        "test_type": "t_test",
        "test_category": "hypothesis",
        "configuration": {},
    })
    await client.post(f"/api/initiatives/{initiative_id}/analyses", json={
        "test_type": "control_chart",
        "test_category": "spc",
        "configuration": {},
    })

    resp = await client.get(
        f"/api/initiatives/{initiative_id}/analyses",
        params={"test_category": "hypothesis"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(a["test_category"] == "hypothesis" for a in data)


@pytest.mark.asyncio
async def test_get_analysis(client: AsyncClient):
    """GET /api/analyses/{id} returns a single analysis."""
    initiative_id = await _create_initiative(client)
    create_resp = await client.post(f"/api/initiatives/{initiative_id}/analyses", json={
        "test_type": "anova",
        "test_category": "hypothesis",
        "configuration": {"alpha": 0.05},
    })
    analysis_id = create_resp.json()["id"]

    resp = await client.get(f"/api/analyses/{analysis_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == analysis_id
    assert data["test_type"] == "anova"


@pytest.mark.asyncio
async def test_get_analysis_not_found(client: AsyncClient):
    """GET /api/analyses/{id} returns 404 for missing analysis."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/analyses/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_analysis(client: AsyncClient):
    """DELETE /api/analyses/{id} removes an analysis."""
    initiative_id = await _create_initiative(client)
    create_resp = await client.post(f"/api/initiatives/{initiative_id}/analyses", json={
        "test_type": "t_test",
        "test_category": "hypothesis",
        "configuration": {},
    })
    analysis_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/analyses/{analysis_id}")
    assert resp.status_code == 204

    # Verify deleted
    get_resp = await client.get(f"/api/analyses/{analysis_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_analysis_not_found(client: AsyncClient):
    """DELETE /api/analyses/{id} returns 404 for missing analysis."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.delete(f"/api/analyses/{fake_id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Rerun & Execute Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rerun_analysis(client: AsyncClient):
    """POST /api/analyses/{id}/rerun resets and re-executes."""
    initiative_id = await _create_initiative(client)
    create_resp = await client.post(f"/api/initiatives/{initiative_id}/analyses", json={
        "test_type": "t_test",
        "test_category": "hypothesis",
        "configuration": {"alpha": 0.05},
    })
    analysis_id = create_resp.json()["id"]

    resp = await client.post(f"/api/analyses/{analysis_id}/rerun")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == analysis_id
    assert data["status"] in ("pending", "completed", "failed")


@pytest.mark.asyncio
async def test_rerun_with_new_config(client: AsyncClient):
    """POST /api/analyses/{id}/rerun with updated configuration."""
    initiative_id = await _create_initiative(client)
    create_resp = await client.post(f"/api/initiatives/{initiative_id}/analyses", json={
        "test_type": "t_test",
        "test_category": "hypothesis",
        "configuration": {"alpha": 0.05},
    })
    analysis_id = create_resp.json()["id"]

    resp = await client.post(f"/api/analyses/{analysis_id}/rerun", json={
        "configuration": {"alpha": 0.01, "alternative": "greater"},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["configuration"]["alpha"] == 0.01


@pytest.mark.asyncio
async def test_execute_analysis(client: AsyncClient):
    """POST /api/analyses/{id}/execute (alias for rerun) works."""
    initiative_id = await _create_initiative(client)
    create_resp = await client.post(f"/api/initiatives/{initiative_id}/analyses", json={
        "test_type": "chi_square",
        "test_category": "association",
        "configuration": {"alpha": 0.05},
    })
    analysis_id = create_resp.json()["id"]

    resp = await client.post(f"/api/analyses/{analysis_id}/execute")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == analysis_id
    assert data["status"] in ("pending", "completed", "failed")


@pytest.mark.asyncio
async def test_execute_analysis_not_found(client: AsyncClient):
    """POST /api/analyses/{id}/execute returns 404 for missing analysis."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(f"/api/analyses/{fake_id}/execute")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rerun_analysis_not_found(client: AsyncClient):
    """POST /api/analyses/{id}/rerun returns 404 for missing analysis."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(f"/api/analyses/{fake_id}/rerun")
    assert resp.status_code == 404
