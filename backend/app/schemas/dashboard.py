"""Pydantic schemas for dashboard endpoints — typed response models."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class TrendPoint(BaseModel):
    """Single data point in a time-series trend."""
    month: str  # YYYY-MM
    count: int = 0
    projected_savings: float = 0
    actual_savings: float = 0


class DeadlineItem(BaseModel):
    """An upcoming action item deadline."""
    action_item_id: str
    title: str
    due_date: date
    priority: str
    status: str
    initiative_id: str | None = None
    initiative_number: str | None = None
    initiative_title: str | None = None
    owner_name: str | None = None


class MemberMetrics(BaseModel):
    """Workload metrics for a single team member."""
    user_id: str
    full_name: str
    capacity_hours: float
    allocated_hours: float
    utilization_pct: float
    active_initiative_count: int
    initiatives: list[dict] = Field(default_factory=list)


class InitiativeSummaryItem(BaseModel):
    """Compact initiative record for dashboard lists."""
    id: str
    initiative_number: str
    title: str
    status: str
    current_phase: str
    priority: str
    methodology: str | None = None
    lead_analyst_id: str | None = None
    health_score: str | None = None  # on_track, at_risk, blocked


class BurndownPoint(BaseModel):
    """A point in an action-item burndown chart."""
    date: str  # YYYY-MM-DD
    open_count: int
    completed_count: int


# ---------------------------------------------------------------------------
# Portfolio Dashboard
# ---------------------------------------------------------------------------

class PortfolioMetrics(BaseModel):
    """Full portfolio-level dashboard response."""
    initiative_counts: dict = Field(
        default_factory=dict,
        description="Counts by lifecycle: active, on_hold, blocked, completed, cancelled, total",
    )
    action_counts: dict = Field(
        default_factory=dict,
        description="Action items: open, overdue, due_this_week, completed_this_week",
    )
    savings: dict = Field(
        default_factory=dict,
        description="Financial: projected_total, actual_total, this_quarter_actual",
    )
    utilization: dict = Field(
        default_factory=dict,
        description="Team avg utilization: team_avg_pct, overloaded_count, available_count",
    )
    phase_distribution: dict = Field(
        default_factory=dict,
        description="Active initiatives per phase: define, measure, analyze, ...",
    )
    status_distribution: dict = Field(
        default_factory=dict,
        description="Initiatives per status: active, completed, blocked, ...",
    )
    priority_distribution: dict = Field(
        default_factory=dict,
        description="Initiatives per priority: critical, high, medium, low",
    )
    methodology_distribution: dict = Field(
        default_factory=dict,
        description="Initiatives per methodology: DMAIC, Kaizen, A3, ...",
    )
    trends: list[TrendPoint] = Field(
        default_factory=list,
        description="Monthly trend data for last 12 months",
    )
    health_summary: dict = Field(
        default_factory=dict,
        description="Health classification: on_track, at_risk, blocked counts",
    )
    upcoming_deadlines: list[DeadlineItem] = Field(
        default_factory=list,
        description="Next 10 action items by due date",
    )


# ---------------------------------------------------------------------------
# Team Dashboard
# ---------------------------------------------------------------------------

class TeamMetrics(BaseModel):
    """Team-level dashboard response."""
    team_id: str
    team_name: str
    member_count: int = 0
    average_utilization: float = 0
    members: list[MemberMetrics] = Field(default_factory=list)
    initiatives: list[InitiativeSummaryItem] = Field(default_factory=list)
    action_compliance: dict = Field(
        default_factory=dict,
        description="on_time_pct, overdue_count, total_completed",
    )
    overloaded: list[str] = Field(default_factory=list, description="User IDs with >90% utilization")
    available: list[str] = Field(default_factory=list, description="User IDs with <60% utilization")


# ---------------------------------------------------------------------------
# Initiative Dashboard
# ---------------------------------------------------------------------------

class PhaseDetail(BaseModel):
    """Phase information for initiative dashboard."""
    phase_name: str
    phase_order: int
    status: str
    gate_approved: bool
    completeness_score: float
    started_at: datetime | None = None
    completed_at: datetime | None = None


class MetricDetail(BaseModel):
    """KPI metric for initiative dashboard."""
    name: str
    unit: str | None = None
    baseline_value: float | None = None
    target_value: float | None = None
    current_value: float | None = None
    target_met: bool | None = None
    pct_change: float | None = None  # computed: (current - baseline) / baseline * 100


class AnalysisSummary(BaseModel):
    """Statistical analysis entry for initiative dashboard."""
    id: str
    test_type: str
    test_category: str
    status: str
    created_at: datetime | None = None


class InitiativeMetrics(BaseModel):
    """Single initiative deep-dive dashboard response."""
    initiative_id: str
    initiative_number: str
    title: str
    methodology: str
    status: str
    current_phase: str
    phases: list[PhaseDetail] = Field(default_factory=list)
    metrics: list[MetricDetail] = Field(default_factory=list)
    action_summary: dict = Field(
        default_factory=dict,
        description="Action items by status: not_started, in_progress, completed, deferred",
    )
    action_burndown: list[BurndownPoint] = Field(default_factory=list)
    analyses: list[AnalysisSummary] = Field(default_factory=list)
    health_score: str = "on_track"  # on_track, at_risk, blocked
    days_in_current_phase: int = 0
    financial_impact: dict = Field(
        default_factory=dict,
        description="projected_savings, actual_savings",
    )


# ---------------------------------------------------------------------------
# Pipeline Dashboard
# ---------------------------------------------------------------------------

class RecentRequest(BaseModel):
    """Request summary for pipeline dashboard."""
    id: str
    request_number: str
    title: str
    status: str
    urgency: str | None = None
    submitted_at: datetime | None = None


class PipelineMetrics(BaseModel):
    """Request pipeline / intake funnel dashboard response."""
    total_requests: int = 0
    by_status: dict = Field(default_factory=dict)
    by_urgency: dict = Field(default_factory=dict)
    conversion_rate: float = 0
    avg_review_days: float | None = None
    recent_requests: list[RecentRequest] = Field(default_factory=list)
