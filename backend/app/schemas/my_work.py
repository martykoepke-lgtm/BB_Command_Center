"""Pydantic schemas for the My Work aggregate endpoint."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class MyInitiativeSummary(BaseModel):
    """Compact initiative for My Work view."""
    id: UUID
    initiative_number: str
    title: str
    methodology: str
    initiative_type: str | None
    priority: str
    status: str
    current_phase: str
    start_date: date | None
    target_completion: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MyActionItem(BaseModel):
    """Action item with parent initiative context."""
    id: UUID
    initiative_id: UUID
    initiative_number: str | None = None
    initiative_title: str | None = None
    title: str
    description: str | None
    status: str
    priority: str
    due_date: date | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MyWorkStats(BaseModel):
    """Quick-glance stats for the personal workspace."""
    active_initiatives: int = 0
    open_actions: int = 0
    overdue_actions: int = 0
    due_this_week: int = 0


class MyWorkResponse(BaseModel):
    """Aggregate response for GET /my-work."""
    stats: MyWorkStats
    initiatives: list[MyInitiativeSummary]
    actions: list[MyActionItem]
