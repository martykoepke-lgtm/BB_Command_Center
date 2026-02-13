"""
Dashboard API — aggregated views for leadership and team dashboards.

Routes:
  GET  /api/dashboards/portfolio        — Portfolio summary (all initiatives)
  GET  /api/dashboards/team/{id}        — Team utilization & initiative status
  GET  /api/dashboards/initiative/{id}  — Single initiative deep-dive stats
  GET  /api/dashboards/pipeline         — Request pipeline (intake funnel)

Delegates all aggregation logic to app.services.dashboard_engine.DashboardEngine.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import (
    InitiativeMetrics,
    PipelineMetrics,
    PortfolioMetrics,
    TeamMetrics,
)
from app.services.dashboard_engine import DashboardEngine


router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


@router.get("/portfolio", response_model=PortfolioMetrics)
async def portfolio_dashboard(
    team_id: UUID | None = Query(None, description="Filter by team"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Portfolio-level dashboard — roll-up of all initiatives.

    Returns initiative counts, distributions, savings, utilization,
    health scoring, 12-month trends, and upcoming deadlines.
    Optionally filtered by team_id.
    """
    engine = DashboardEngine(db)
    return await engine.get_portfolio_metrics(team_id=team_id)


@router.get("/team/{team_id}", response_model=TeamMetrics)
async def team_dashboard(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Team dashboard — utilization, member breakdown, initiative status,
    and action item compliance for a specific team.
    """
    engine = DashboardEngine(db)
    return await engine.get_team_metrics(team_id)


@router.get("/initiative/{initiative_id}", response_model=InitiativeMetrics)
async def initiative_dashboard(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Single initiative deep-dive dashboard.

    Returns phase timeline, KPI metrics with percent change,
    action item summary and burndown, statistical analyses,
    health score, days in current phase, and financial impact.
    """
    engine = DashboardEngine(db)
    return await engine.get_initiative_metrics(initiative_id)


@router.get("/pipeline", response_model=PipelineMetrics)
async def pipeline_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request pipeline / intake funnel dashboard.

    Shows how requests flow: submitted → under_review → accepted/declined → converted.
    Includes conversion rate, average review time, and recent requests.
    """
    engine = DashboardEngine(db)
    return await engine.get_pipeline_metrics()
