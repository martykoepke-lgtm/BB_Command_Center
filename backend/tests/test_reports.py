"""
Tests for report generation service and report API endpoints.

Covers: executive_summary, phase_tollgate, initiative_closeout,
portfolio_review, statistical_summary report types, plus CRUD operations.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.initiative import Initiative
from app.models.phase import Phase, PhaseArtifact
from app.models.analysis import StatisticalAnalysis
from app.models.supporting import ActionItem, Metric, Report
from app.models.user import User
from app.services.report_generator import (
    generate_report,
    build_executive_summary,
    build_phase_tollgate,
    build_initiative_closeout,
    build_portfolio_review,
    build_statistical_summary,
    REPORT_TITLES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_initiative(
    db: AsyncSession,
    user: User,
    *,
    status: str = "active",
    methodology: str = "DMAIC",
    priority: str = "medium",
    current_phase: str = "define",
    projected_savings: float | None = None,
    actual_savings: float | None = None,
    target_completion: date | None = None,
    actual_completion: date | None = None,
) -> Initiative:
    init = Initiative(
        id=uuid.uuid4(),
        initiative_number=f"INI-{uuid.uuid4().hex[:4].upper()}",
        title=f"Test Initiative {uuid.uuid4().hex[:6]}",
        problem_statement="Test problem statement for this initiative.",
        desired_outcome="Test desired outcome for this initiative.",
        methodology=methodology,
        priority=priority,
        status=status,
        current_phase=current_phase,
        lead_analyst_id=user.id,
        start_date=date.today() - timedelta(days=30),
        target_completion=target_completion or date.today() + timedelta(days=60),
        actual_completion=actual_completion,
        projected_savings=projected_savings,
        actual_savings=actual_savings,
        phase_progress={},
    )
    db.add(init)
    await db.flush()
    return init


async def _create_phase(
    db: AsyncSession,
    initiative_id: uuid.UUID,
    phase_name: str,
    phase_order: int,
    status: str = "not_started",
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> Phase:
    phase = Phase(
        id=uuid.uuid4(),
        initiative_id=initiative_id,
        phase_name=phase_name,
        phase_order=phase_order,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        completeness_score=0,
    )
    db.add(phase)
    await db.flush()
    return phase


async def _create_action_item(
    db: AsyncSession,
    initiative_id: uuid.UUID,
    *,
    phase_id: uuid.UUID | None = None,
    status: str = "not_started",
    priority: str = "medium",
    due_date: date | None = None,
) -> ActionItem:
    item = ActionItem(
        id=uuid.uuid4(),
        initiative_id=initiative_id,
        phase_id=phase_id,
        title=f"Action {uuid.uuid4().hex[:6]}",
        status=status,
        priority=priority,
        due_date=due_date,
    )
    db.add(item)
    await db.flush()
    return item


async def _create_metric(
    db: AsyncSession,
    initiative_id: uuid.UUID,
    *,
    name: str = "Wait Time",
    unit: str = "minutes",
    baseline_value: float = 45,
    target_value: float = 20,
    current_value: float = 32,
    target_met: bool | None = None,
) -> Metric:
    metric = Metric(
        id=uuid.uuid4(),
        initiative_id=initiative_id,
        name=name,
        unit=unit,
        baseline_value=baseline_value,
        target_value=target_value,
        current_value=current_value,
        target_met=target_met,
    )
    db.add(metric)
    await db.flush()
    return metric


async def _create_analysis(
    db: AsyncSession,
    initiative_id: uuid.UUID,
    *,
    test_type: str = "t_test",
    test_category: str = "hypothesis",
    status: str = "completed",
    results: dict | None = None,
) -> StatisticalAnalysis:
    analysis = StatisticalAnalysis(
        id=uuid.uuid4(),
        initiative_id=initiative_id,
        dataset_id=uuid.uuid4(),
        test_type=test_type,
        test_category=test_category,
        status=status,
        configuration={"alpha": 0.05},
        results=results or {"p_value": 0.03, "statistic": 2.15},
    )
    db.add(analysis)
    await db.flush()
    return analysis


# ---------------------------------------------------------------------------
# Report Generator Unit Tests (AI disabled to avoid external calls)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_executive_summary(db: AsyncSession, test_user: User):
    """Executive summary report contains initiative info and metrics."""
    init = await _create_initiative(
        db, test_user, status="active", projected_savings=100000,
    )
    await _create_phase(db, init.id, "define", 1, status="in_progress")
    await _create_metric(db, init.id)
    await _create_action_item(db, init.id, status="completed")
    await _create_action_item(db, init.id, status="not_started")

    html = await build_executive_summary(init.id, db, include_ai=False)

    assert "Executive Summary" in html
    assert init.initiative_number in html
    assert init.title in html
    assert "Wait Time" in html
    assert "Phase Progress" in html
    assert "Action Items" in html


@pytest.mark.asyncio
async def test_generate_phase_tollgate(db: AsyncSession, test_user: User):
    """Phase tollgate report contains phase info and artifacts."""
    init = await _create_initiative(db, test_user, status="active")
    phase = await _create_phase(
        db, init.id, "define", 1, status="in_progress",
        started_at=datetime.now(timezone.utc) - timedelta(days=10),
    )

    # Create an artifact
    artifact = PhaseArtifact(
        id=uuid.uuid4(),
        phase_id=phase.id,
        title="Project Charter",
        artifact_type="document",
        status="completed",
    )
    db.add(artifact)
    await db.flush()

    # Create phase-level action items
    await _create_action_item(
        db, init.id, phase_id=phase.id, status="completed",
    )

    html = await build_phase_tollgate(init.id, "define", db, include_ai=False)

    assert "Tollgate Review" in html
    assert "Define" in html
    assert init.initiative_number in html
    assert "Project Charter" in html
    assert "Deliverables" in html


@pytest.mark.asyncio
async def test_generate_initiative_closeout(db: AsyncSession, test_user: User):
    """Closeout report contains timeline and results."""
    init = await _create_initiative(
        db, test_user,
        status="completed",
        projected_savings=80000,
        actual_savings=75000,
        actual_completion=date.today(),
    )
    await _create_phase(
        db, init.id, "define", 1, status="completed",
        started_at=datetime.now(timezone.utc) - timedelta(days=30),
        completed_at=datetime.now(timezone.utc) - timedelta(days=20),
    )
    await _create_phase(
        db, init.id, "measure", 2, status="completed",
        started_at=datetime.now(timezone.utc) - timedelta(days=20),
        completed_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    await _create_metric(
        db, init.id, current_value=18, target_met=True,
    )
    await _create_analysis(db, init.id)

    html = await build_initiative_closeout(init.id, db, include_ai=False)

    assert "Closeout" in html
    assert init.initiative_number in html
    assert "Phase Timeline" in html
    assert "Results" in html
    assert "$80,000" in html or "80,000" in html
    assert "t_test" in html


@pytest.mark.asyncio
async def test_generate_portfolio_review(db: AsyncSession, test_user: User):
    """Portfolio review report shows cross-initiative summary."""
    await _create_initiative(db, test_user, status="active", projected_savings=50000)
    await _create_initiative(db, test_user, status="active", projected_savings=30000)
    await _create_initiative(db, test_user, status="completed", actual_completion=date.today())

    html = await build_portfolio_review(db, include_ai=False)

    assert "Portfolio Review" in html
    assert "Active" in html
    assert "Status Distribution" in html
    assert "Methodology Breakdown" in html


@pytest.mark.asyncio
async def test_generate_statistical_summary(db: AsyncSession, test_user: User):
    """Statistical summary report lists analyses and interpretations."""
    init = await _create_initiative(db, test_user, status="active")

    analysis = await _create_analysis(
        db, init.id,
        test_type="chi_square",
        test_category="association",
        results={"p_value": 0.001, "statistic": 12.5},
    )
    # Add AI interpretation to the analysis
    analysis.ai_interpretation = "There is a significant association between the variables."
    analysis.ai_next_steps = "Consider segmenting by department for deeper analysis."
    await db.flush()

    html = await build_statistical_summary(init.id, db, include_ai=False, include_charts=False)

    assert "Statistical Analysis Summary" in html
    assert "chi_square" in html
    assert "significant association" in html
    assert "segmenting by department" in html


@pytest.mark.asyncio
async def test_generate_report_dispatcher(db: AsyncSession, test_user: User):
    """generate_report() correctly dispatches to the right builder."""
    init = await _create_initiative(db, test_user, status="active")
    await _create_phase(db, init.id, "define", 1, status="in_progress")

    html = await generate_report(
        "executive_summary", init.id, None, db,
        include_ai=False, include_charts=False,
    )
    assert "Executive Summary" in html
    assert init.title in html


@pytest.mark.asyncio
async def test_generate_report_unknown_type(db: AsyncSession):
    """generate_report() raises ValueError for unknown report type."""
    with pytest.raises(ValueError, match="Unknown report type"):
        await generate_report("nonexistent_type", uuid.uuid4(), None, db)


@pytest.mark.asyncio
async def test_generate_report_phase_tollgate_requires_phase(db: AsyncSession, test_user: User):
    """phase_tollgate requires both initiative_id and phase_name."""
    init = await _create_initiative(db, test_user)

    with pytest.raises(ValueError, match="phase_tollgate requires"):
        await generate_report("phase_tollgate", init.id, None, db)


@pytest.mark.asyncio
async def test_report_titles_mapping():
    """REPORT_TITLES contains all expected report types."""
    expected = {"executive_summary", "phase_tollgate", "initiative_closeout", "portfolio_review", "statistical_summary"}
    assert set(REPORT_TITLES.keys()) == expected


# ---------------------------------------------------------------------------
# Report API Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_initiative_report_endpoint(client, db: AsyncSession, test_user: User):
    """POST /api/initiatives/{id}/reports creates a report."""
    init = await _create_initiative(db, test_user, status="active")
    await _create_phase(db, init.id, "define", 1, status="in_progress")

    resp = await client.post(
        f"/api/initiatives/{init.id}/reports",
        json={
            "report_type": "executive_summary",
            "format": "html",
            "include_ai_narrative": False,
            "include_charts": False,
        },
    )
    assert resp.status_code == 201

    data = resp.json()
    assert data["report_type"] == "executive_summary"
    assert data["status"] == "completed"
    assert data["initiative_id"] == str(init.id)
    assert data["content_html"] is not None
    assert "Executive Summary" in data["content_html"]


@pytest.mark.asyncio
async def test_create_portfolio_report_endpoint(admin_client, db: AsyncSession, admin_user: User):
    """POST /api/reports/portfolio requires admin/manager and creates a report."""
    resp = await admin_client.post(
        "/api/reports/portfolio",
        json={
            "report_type": "portfolio_review",
            "format": "html",
            "include_ai_narrative": False,
            "include_charts": False,
        },
    )
    assert resp.status_code == 201

    data = resp.json()
    assert data["report_type"] == "portfolio_review"
    assert data["status"] == "completed"
    assert data["initiative_id"] is None


@pytest.mark.asyncio
async def test_portfolio_report_requires_correct_type(admin_client):
    """POST /api/reports/portfolio rejects non-portfolio_review types."""
    resp = await admin_client.post(
        "/api/reports/portfolio",
        json={
            "report_type": "executive_summary",
            "format": "html",
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_initiative_reports(client, db: AsyncSession, test_user: User):
    """GET /api/initiatives/{id}/reports lists reports for an initiative."""
    init = await _create_initiative(db, test_user)

    # Create a report record
    report = Report(
        initiative_id=init.id,
        report_type="executive_summary",
        title="Executive Summary",
        format="html",
        status="completed",
        generated_by=test_user.id,
        generated_at=datetime.now(timezone.utc),
        content_html="<html>Test</html>",
    )
    db.add(report)
    await db.flush()

    resp = await client.get(f"/api/initiatives/{init.id}/reports")
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) >= 1
    assert data[0]["report_type"] == "executive_summary"


@pytest.mark.asyncio
async def test_get_report_by_id(client, db: AsyncSession, test_user: User):
    """GET /api/reports/{id} returns a single report with HTML content."""
    init = await _create_initiative(db, test_user)

    report = Report(
        initiative_id=init.id,
        report_type="executive_summary",
        title="Executive Summary",
        format="html",
        status="completed",
        generated_by=test_user.id,
        generated_at=datetime.now(timezone.utc),
        content_html="<html><body>Report Content</body></html>",
    )
    db.add(report)
    await db.flush()

    resp = await client.get(f"/api/reports/{report.id}")
    assert resp.status_code == 200

    data = resp.json()
    assert data["id"] == str(report.id)
    assert "Report Content" in data["content_html"]


@pytest.mark.asyncio
async def test_get_report_not_found(client):
    """GET /api/reports/{id} returns 404 for missing report."""
    resp = await client.get(f"/api/reports/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_report(client, db: AsyncSession, test_user: User):
    """DELETE /api/reports/{id} removes a report."""
    init = await _create_initiative(db, test_user)

    report = Report(
        initiative_id=init.id,
        report_type="executive_summary",
        title="Executive Summary",
        format="html",
        status="completed",
        generated_by=test_user.id,
        content_html="<html>Test</html>",
    )
    db.add(report)
    await db.flush()

    resp = await client.delete(f"/api/reports/{report.id}")
    assert resp.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/api/reports/{report.id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_report_not_found(client):
    """DELETE /api/reports/{id} returns 404 for missing report."""
    resp = await client.delete(f"/api/reports/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_all_reports_admin(admin_client, db: AsyncSession, admin_user: User):
    """GET /api/reports lists all reports (admin only)."""
    # Create a couple of reports
    report1 = Report(
        report_type="portfolio_review",
        title="Portfolio Review",
        format="html",
        status="completed",
        generated_by=admin_user.id,
        generated_at=datetime.now(timezone.utc),
    )
    report2 = Report(
        report_type="executive_summary",
        title="Executive Summary",
        format="html",
        status="completed",
        generated_by=admin_user.id,
        generated_at=datetime.now(timezone.utc),
    )
    db.add_all([report1, report2])
    await db.flush()

    resp = await admin_client.get("/api/reports")
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_list_all_reports_with_filter(admin_client, db: AsyncSession, admin_user: User):
    """GET /api/reports?report_type=portfolio_review filters by type."""
    report = Report(
        report_type="portfolio_review",
        title="Portfolio Review",
        format="html",
        status="completed",
        generated_by=admin_user.id,
    )
    db.add(report)
    await db.flush()

    resp = await admin_client.get("/api/reports?report_type=portfolio_review")
    assert resp.status_code == 200

    data = resp.json()
    assert all(r["report_type"] == "portfolio_review" for r in data)


@pytest.mark.asyncio
async def test_report_crud_full_lifecycle(client, db: AsyncSession, test_user: User):
    """Full lifecycle: generate → list → get → delete."""
    init = await _create_initiative(db, test_user, status="active")
    await _create_phase(db, init.id, "define", 1, status="in_progress")

    # Generate
    create_resp = await client.post(
        f"/api/initiatives/{init.id}/reports",
        json={
            "report_type": "executive_summary",
            "format": "html",
            "include_ai_narrative": False,
            "include_charts": False,
        },
    )
    assert create_resp.status_code == 201
    report_id = create_resp.json()["id"]

    # List for initiative
    list_resp = await client.get(f"/api/initiatives/{init.id}/reports")
    assert list_resp.status_code == 200
    assert any(r["id"] == report_id for r in list_resp.json())

    # Get single
    get_resp = await client.get(f"/api/reports/{report_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["content_html"] is not None

    # Delete
    del_resp = await client.delete(f"/api/reports/{report_id}")
    assert del_resp.status_code == 204

    # Verify deleted
    verify_resp = await client.get(f"/api/reports/{report_id}")
    assert verify_resp.status_code == 404


# ---------------------------------------------------------------------------
# Unified Generate Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unified_generate_with_initiative(client, db: AsyncSession, test_user: User):
    """POST /api/reports/generate with initiative_id creates an initiative report."""
    init = await _create_initiative(db, test_user, status="active")
    await _create_phase(db, init.id, "define", 1, status="in_progress")

    resp = await client.post("/api/reports/generate", json={
        "report_type": "executive_summary",
        "format": "html",
        "include_ai_narrative": False,
        "include_charts": False,
        "initiative_id": str(init.id),
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["report_type"] == "executive_summary"
    assert data["status"] == "completed"
    assert data["initiative_id"] == str(init.id)


@pytest.mark.asyncio
async def test_unified_generate_portfolio(client, db: AsyncSession, test_user: User):
    """POST /api/reports/generate without initiative_id creates a portfolio report."""
    resp = await client.post("/api/reports/generate", json={
        "report_type": "portfolio_review",
        "format": "html",
        "include_ai_narrative": False,
        "include_charts": False,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["report_type"] == "portfolio_review"
    assert data["initiative_id"] is None
