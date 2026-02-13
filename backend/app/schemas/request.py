"""Pydantic schemas for improvement request intake."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RequestCreate(BaseModel):
    """Payload to submit a new improvement request."""
    title: str = Field(..., min_length=5, max_length=200)
    description: str | None = None
    requester_name: str = Field(..., min_length=1)
    requester_email: str | None = None
    requester_dept: str | None = None
    problem_statement: str | None = None
    desired_outcome: str | None = None
    business_impact: str | None = None
    urgency: str = "medium"


class RequestUpdate(BaseModel):
    """Fields that can be updated on a request (e.g., during review)."""
    status: str | None = None
    review_notes: str | None = None
    complexity_score: float | None = None
    recommended_methodology: str | None = None
    urgency: str | None = None


class RequestOut(BaseModel):
    """Request returned from API."""
    id: UUID
    request_number: str
    title: str
    description: str | None
    requester_name: str
    requester_email: str | None
    requester_dept: str | None
    problem_statement: str | None
    desired_outcome: str | None
    business_impact: str | None
    urgency: str
    complexity_score: float | None
    recommended_methodology: str | None
    status: str
    reviewed_by: UUID | None
    review_notes: str | None
    submitted_at: datetime
    reviewed_at: datetime | None
    converted_initiative_id: UUID | None

    model_config = {"from_attributes": True}


class RequestList(BaseModel):
    """Paginated list of requests."""
    items: list[RequestOut]
    total: int
    page: int
    page_size: int
