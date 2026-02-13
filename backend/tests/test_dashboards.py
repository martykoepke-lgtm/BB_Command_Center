"""
Tests for dashboard engine and dashboard API endpoints.

Covers: Portfolio, Team, Initiative, and Pipeline dashboards.
Tests both the DashboardEngine calculations and the API surface.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.initiative import Initiative
from app.models.phase import Phase
from app.models.request import Request
from app.models.supporting import ActionItem, Metric
from app.models.user import User, Team, team_members
from app.services.dashboard_engine import DashboardEngine


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
    """Helper to create an initiative with default values."""
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
) -> Phase:
    """Helper to create a phase."""
    phase = Phase(
        id=uuid.uuid4(),
        initiative_id=initiative_id,
        phase_name=phase_name,
        phase_order=phase_order,
        status=status,
        started_at=started_at,
        completeness_score=0,
    )
    db.add(phase)
    await db.flush()
    return phase


async def _create_action_item(
    db: AsyncSession,
    initiative_id: uuid.UUID,
    *,
    status: str = "not_started",
    priority: str = "medium",
    due_date: date | None = None,
    classification: str = "action_item",
    completed_at: datetime | None = None,
) -> ActionItem:
    """Helper to create an action item."""
    item = ActionItem(
        id=uuid.uuid4(),
        initiative_id=initiative_id,
        title=f"Action {uuid.uuid4().hex[:6]}",
        status=status,
        priority=priority,
        due_date=due_date,
        classification=classification,
        completed_at=completed_at,
    )
    db.add(item)
    await db.flush()
    return item


async def _create_request(
    db: AsyncSession,
    *,
    status: str = "submitted",
    urgency: str = "medium",
) -> Request:
    """Helper to create a request."""
    req = Request(
        id=uuid.uuid4(),
        request_number=f"REQ-{uuid.uuid4().hex[:4].upper()}",
        title=f"Test Request {uuid.uuid4().hex[:6]}",
        requester_name="Test Requester",
        requester_email="requester@test.com",
        problem_statement="Test problem",
        desired_outcome="Test outcome",
        status=status,
        urgency=urgency,
    )
    db.add(req)
    await db.flush()
    return req


# ---------------------------------------------------------------------------
# Dashboard Engine Unit Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_portfolio_metrics_empty(db: AsyncSession):
    """Portfolio dashboard returns zeroes when no initiatives exist."""
    engine = DashboardEngine(db)
    metrics = await engine.get_portfolio_metrics()

    assert metrics.initiative_counts["total"] == 0
    assert metrics.initiative_counts["active"] == 0
    assert metrics.savings["projected_total"] == 0
    assert metrics.savings["actual_total"] == 0
    assert metrics.health_summary["on_track"] == 0
    assert len(metrics.trends) == 12  # always 12 months


@pytest.mark.asyncio
async def test_portfolio_metrics_with_data(db: AsyncSession, test_user: User):
    """Portfolio dashboard correctly counts initiatives by status."""
    await _create_initiative(db, test_user, status="active")
    await _create_initiative(db, test_user, status="active")
    await _create_initiative(db, test_user, status="completed", actual_completion=date.today())
    await _create_initiative(db, test_user, status="blocked")

    engine = DashboardEngine(db)
    metrics = await engine.get_portfolio_metrics()

    assert metrics.initiative_counts["active"] == 2
    assert metrics.initiative_counts["completed"] == 1
    assert metrics.initiative_counts["blocked"] == 1
    assert metrics.initiative_counts["total"] == 4


@pytest.mark.asyncio
async def test_portfolio_savings(db: AsyncSession, test_user: User):
    """Portfolio dashboard sums savings correctly."""
    await _create_initiative(db, test_user, projected_savings=50000, actual_savings=30000)
    await _create_initiative(db, test_user, projected_savings=75000, actual_savings=60000)

    engine = DashboardEngine(db)
    metrics = await engine.get_portfolio_metrics()

    assert metrics.savings["projected_total"] == 125000
    assert metrics.savings["actual_total"] == 90000


@pytest.mark.asyncio
async def test_portfolio_health_scoring_on_track(db: AsyncSession, test_user: User):
    """Active initiative with no issues is classified as on_track."""
    init = await _create_initiative(db, test_user, status="active")
    await _create_phase(
        db, init.id, "define", 1, status="in_progress",
        started_at=datetime.now(timezone.utc) - timedelta(days=5),
    )

    engine = DashboardEngine(db)
    health = await engine._compute_initiative_health(init)
    assert health == "on_track"


@pytest.mark.asyncio
async def test_portfolio_health_scoring_blocked(db: AsyncSession, test_user: User):
    """Initiative with status 'blocked' is classified as blocked."""
    init = await _create_initiative(db, test_user, status="blocked")

    engine = DashboardEngine(db)
    health = await engine._compute_initiative_health(init)
    assert health == "blocked"


@pytest.mark.asyncio
async def test_portfolio_health_scoring_blocker_action(db: AsyncSession, test_user: User):
    """Active initiative with an open blocker action item is classified as blocked."""
    init = await _create_initiative(db, test_user, status="active")
    await _create_action_item(
        db, init.id, classification="blocker", status="not_started",
    )

    engine = DashboardEngine(db)
    health = await engine._compute_initiative_health(init)
    assert health == "blocked"


@pytest.mark.asyncio
async def test_portfolio_health_scoring_at_risk_past_target(db: AsyncSession, test_user: User):
    """Initiative past target completion date is classified as at_risk."""
    init = await _create_initiative(
        db, test_user, status="active",
        target_completion=date.today() - timedelta(days=5),
    )

    engine = DashboardEngine(db)
    health = await engine._compute_initiative_health(init)
    assert health == "at_risk"


@pytest.mark.asyncio
async def test_upcoming_deadlines(db: AsyncSession, test_user: User):
    """Upcoming deadlines returns action items sorted by due date."""
    init = await _create_initiative(db, test_user)

    tomorrow = date.today() + timedelta(days=1)
    next_week = date.today() + timedelta(days=7)
    await _create_action_item(db, init.id, due_date=next_week, status="not_started")
    await _create_action_item(db, init.id, due_date=tomorrow, status="not_started")

    engine = DashboardEngine(db)
    deadlines = await engine._get_upcoming_deadlines(None)

    assert len(deadlines) >= 2
    # First item should be the earliest due date
    assert deadlines[0].due_date <= deadlines[1].due_date


@pytest.mark.asyncio
async def test_initiative_metrics(db: AsyncSession, test_user: User):
    """Initiative dashboard returns phases, metrics, actions, and health."""
    init = await _create_initiative(db, test_user, status="active", projected_savings=100000)
    await _create_phase(
        db, init.id, "define", 1, status="in_progress",
        started_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    await _create_phase(db, init.id, "measure", 2, status="not_started")

    # Add a metric
    metric = Metric(
        id=uuid.uuid4(),
        initiative_id=init.id,
        name="Wait Time",
        unit="minutes",
        baseline_value=45,
        target_value=20,
        current_value=32,
    )
    db.add(metric)
    await db.flush()

    engine = DashboardEngine(db)
    metrics = await engine.get_initiative_metrics(init.id)

    assert metrics.initiative_id == str(init.id)
    assert len(metrics.phases) == 2
    assert len(metrics.metrics) == 1
    assert metrics.metrics[0].name == "Wait Time"
    assert metrics.metrics[0].pct_change is not None  # (32-45)/45*100
    assert metrics.health_score == "on_track"
    assert metrics.days_in_current_phase == 10
    assert metrics.financial_impact["projected_savings"] == 100000


@pytest.mark.asyncio
async def test_pipeline_metrics(db: AsyncSession):
    """Pipeline dashboard correctly counts requests and conversion rate."""
    await _create_request(db, status="submitted")
    await _create_request(db, status="submitted")
    await _create_request(db, status="accepted")
    await _create_request(db, status="converted")

    engine = DashboardEngine(db)
    metrics = await engine.get_pipeline_metrics()

    assert metrics.total_requests == 4
    assert metrics.by_status["submitted"] == 2
    assert metrics.by_status["converted"] == 1
    assert metrics.conversion_rate == 25.0  # 1/4 * 100


@pytest.mark.asyncio
async def test_action_burndown(db: AsyncSession, test_user: User):
    """Action burndown returns weekly snapshots of open vs completed."""
    init = await _create_initiative(db, test_user)

    # Create actions at different times
    await _create_action_item(db, init.id, status="not_started")
    await _create_action_item(
        db, init.id, status="completed",
        completed_at=datetime.now(timezone.utc),
    )

    engine = DashboardEngine(db)
    burndown = await engine._compute_action_burndown(init.id)

    assert len(burndown) >= 1
    # Last point should reflect current state
    last = burndown[-1]
    assert last.open_count + last.completed_count == 2


# ---------------------------------------------------------------------------
# Dashboard API Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_portfolio_endpoint(client, db: AsyncSession, test_user: User):
    """GET /api/dashboards/portfolio returns portfolio metrics."""
    await _create_initiative(db, test_user, status="active")

    resp = await client.get("/api/dashboards/portfolio")
    assert resp.status_code == 200

    data = resp.json()
    assert "initiative_counts" in data
    assert "savings" in data
    assert "trends" in data
    assert "health_summary" in data
    assert "upcoming_deadlines" in data


@pytest.mark.asyncio
async def test_pipeline_endpoint(client, db: AsyncSession):
    """GET /api/dashboards/pipeline returns pipeline metrics."""
    await _create_request(db, status="submitted")

    resp = await client.get("/api/dashboards/pipeline")
    assert resp.status_code == 200

    data = resp.json()
    assert "total_requests" in data
    assert "conversion_rate" in data
    assert "recent_requests" in data


@pytest.mark.asyncio
async def test_initiative_endpoint(client, db: AsyncSession, test_user: User):
    """GET /api/dashboards/initiative/{id} returns initiative metrics."""
    init = await _create_initiative(db, test_user, status="active")
    await _create_phase(
        db, init.id, "define", 1, status="in_progress",
        started_at=datetime.now(timezone.utc),
    )

    resp = await client.get(f"/api/dashboards/initiative/{init.id}")
    assert resp.status_code == 200

    data = resp.json()
    assert data["initiative_id"] == str(init.id)
    assert "phases" in data
    assert "health_score" in data
    assert "days_in_current_phase" in data
