"""Pydantic schemas for user and team management."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserUpdate(BaseModel):
    """Fields an admin or user can update on a profile."""
    full_name: str | None = None
    title: str | None = None
    role: str | None = None
    avatar_url: str | None = None
    skills: list[str] | None = None
    capacity_hours: float | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    """User returned from API."""
    id: UUID
    email: str
    full_name: str
    title: str | None
    role: str
    avatar_url: str | None
    skills: list
    capacity_hours: float
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserWorkload(BaseModel):
    """User with workload allocation summary."""
    id: UUID
    full_name: str
    role: str
    capacity_hours: float
    allocated_hours: float  # total hours allocated this week
    utilization_pct: float  # allocated / capacity * 100
    active_initiatives: int

    model_config = {"from_attributes": True}


class UserList(BaseModel):
    """Paginated list of users."""
    items: list[UserOut]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

class TeamCreate(BaseModel):
    """Payload to create a new team."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    department: str | None = None
    organization: str | None = None
    manager_id: UUID | None = None


class TeamUpdate(BaseModel):
    """Partial update for a team."""
    name: str | None = None
    description: str | None = None
    department: str | None = None
    organization: str | None = None
    manager_id: UUID | None = None


class TeamMemberOut(BaseModel):
    """Team member info."""
    user_id: UUID
    full_name: str
    email: str
    role: str
    role_in_team: str

    model_config = {"from_attributes": True}


class TeamOut(BaseModel):
    """Team returned from API."""
    id: UUID
    name: str
    description: str | None
    department: str | None
    organization: str | None
    manager_id: UUID | None
    created_at: datetime
    member_count: int = 0

    model_config = {"from_attributes": True}


class TeamList(BaseModel):
    """Paginated list of teams."""
    items: list[TeamOut]
    total: int
    page: int
    page_size: int
