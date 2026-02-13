"""Pydantic schemas for initiatives — the living project profile."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, Field

# Allowed work-item classifications
WorkItemType = Literal["initiative", "consultation", "work_assignment"]


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------

class InitiativeCreate(BaseModel):
    """Payload to create a new initiative (often from an accepted request)."""
    title: str = Field(..., min_length=5, max_length=200)
    problem_statement: str = Field(..., min_length=10)
    desired_outcome: str = Field(..., min_length=10)
    scope: str | None = None
    out_of_scope: str | None = None
    business_case: str | None = None
    methodology: str = "DMAIC"
    initiative_type: WorkItemType = "initiative"
    priority: str = "medium"
    lead_analyst_id: UUID | None = None
    team_id: UUID | None = None
    sponsor_id: UUID | None = None
    start_date: date | None = None
    target_completion: date | None = None
    projected_savings: float | None = None
    projected_impact: str | None = None
    tags: list[str] = Field(default_factory=list)
    request_id: UUID | None = None  # link back to originating request


class InitiativeUpdate(BaseModel):
    """Partial update for an initiative."""
    title: str | None = None
    problem_statement: str | None = None
    desired_outcome: str | None = None
    scope: str | None = None
    out_of_scope: str | None = None
    business_case: str | None = None
    methodology: str | None = None
    initiative_type: str | None = None
    priority: str | None = None
    status: str | None = None
    current_phase: str | None = None
    lead_analyst_id: UUID | None = None
    team_id: UUID | None = None
    sponsor_id: UUID | None = None
    start_date: date | None = None
    target_completion: date | None = None
    actual_completion: date | None = None
    projected_savings: float | None = None
    actual_savings: float | None = None
    projected_impact: str | None = None
    actual_impact: str | None = None
    tags: list[str] | None = None


# ---------------------------------------------------------------------------
# Read responses
# ---------------------------------------------------------------------------

class PhaseOut(BaseModel):
    """Phase summary within an initiative response."""
    id: UUID
    initiative_id: UUID
    phase_name: str
    phase_order: int
    status: str
    gate_approved: bool
    completeness_score: float
    started_at: datetime | None
    completed_at: datetime | None
    ai_summary: str | None

    model_config = {"from_attributes": True}


class InitiativeOut(BaseModel):
    """Full initiative profile returned from API."""
    id: UUID
    initiative_number: str
    request_id: UUID | None
    title: str
    problem_statement: str
    desired_outcome: str
    scope: str | None
    out_of_scope: str | None
    business_case: str | None
    methodology: str
    initiative_type: str | None
    priority: str
    status: str
    lead_analyst_id: UUID | None
    team_id: UUID | None
    sponsor_id: UUID | None
    start_date: date | None
    target_completion: date | None
    actual_completion: date | None
    current_phase: str
    phase_progress: dict
    projected_savings: float | None
    actual_savings: float | None
    projected_impact: str | None
    actual_impact: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    # Nested
    phases: list[PhaseOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class InitiativeSummary(BaseModel):
    """Compact initiative for list/dashboard views."""
    id: UUID
    initiative_number: str
    title: str
    methodology: str
    initiative_type: str | None
    priority: str
    status: str
    current_phase: str
    lead_analyst_id: UUID | None
    start_date: date | None
    target_completion: date | None
    projected_savings: float | None
    tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class InitiativeList(BaseModel):
    """Paginated list of initiatives."""
    items: list[InitiativeSummary]
    total: int
    page: int
    page_size: int
