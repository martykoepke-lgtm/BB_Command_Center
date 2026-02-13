"""Pydantic schemas for action items, notes, documents, metrics, artifacts, datasets."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Action Items
# ---------------------------------------------------------------------------

class ActionItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    classification: str = "action_item"
    assigned_to: UUID | None = None
    owner_name: str | None = None
    priority: str = "medium"
    due_date: date | None = None
    phase_id: UUID | None = None


class ActionItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    classification: str | None = None
    assigned_to: UUID | None = None
    owner_name: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: date | None = None
    notes: str | None = None


class ActionItemOut(BaseModel):
    id: UUID
    initiative_id: UUID
    phase_id: UUID | None
    title: str
    description: str | None
    classification: str
    assigned_to: UUID | None
    owner_name: str | None
    status: str
    priority: str
    due_date: date | None
    completed_at: datetime | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActionItemList(BaseModel):
    """Paginated list of action items."""
    items: list[ActionItemOut]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1)
    note_type: str = "general"
    phase_id: UUID | None = None


class NoteOut(BaseModel):
    id: UUID
    initiative_id: UUID
    phase_id: UUID | None
    author_id: UUID | None
    note_type: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class DocumentCreate(BaseModel):
    name: str = Field(..., min_length=1)
    document_type: str | None = None
    file_path: str | None = None
    external_url: str | None = None
    phase_id: UUID | None = None


class DocumentOut(BaseModel):
    id: UUID
    initiative_id: UUID
    phase_id: UUID | None
    name: str
    document_type: str | None
    file_path: str | None
    external_url: str | None
    uploaded_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class MetricCreate(BaseModel):
    name: str = Field(..., min_length=1)
    unit: str | None = None
    baseline_value: float | None = None
    baseline_date: date | None = None
    baseline_period: str | None = None
    target_value: float | None = None
    current_value: float | None = None
    notes: str | None = None


class MetricUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    baseline_value: float | None = None
    target_value: float | None = None
    current_value: float | None = None
    current_date: date | None = None
    current_period: str | None = None
    target_met: bool | None = None
    notes: str | None = None


class MetricOut(BaseModel):
    id: UUID
    initiative_id: UUID
    name: str
    unit: str | None
    baseline_value: float | None
    baseline_date: date | None
    target_value: float | None
    current_value: float | None
    current_date: date | None
    target_met: bool | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Phase Artifacts
# ---------------------------------------------------------------------------

class ArtifactCreate(BaseModel):
    artifact_type: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    content: dict


class ArtifactUpdate(BaseModel):
    title: str | None = None
    content: dict | None = None
    status: str | None = None


class ArtifactOut(BaseModel):
    id: UUID
    phase_id: UUID
    initiative_id: UUID
    artifact_type: str
    title: str
    content: dict
    status: str
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Stakeholders
# ---------------------------------------------------------------------------

class StakeholderCreate(BaseModel):
    user_id: UUID
    role: str = Field(..., min_length=1)


class StakeholderOut(BaseModel):
    initiative_id: UUID
    user_id: UUID
    role: str
    added_at: datetime
    user_name: str | None = None
    user_email: str | None = None

    model_config = {"from_attributes": True}


class ExternalStakeholderCreate(BaseModel):
    name: str = Field(..., min_length=1)
    title: str | None = None
    organization: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None


class ExternalStakeholderOut(BaseModel):
    id: UUID
    initiative_id: UUID
    name: str
    title: str | None
    organization: str | None
    email: str | None
    phone: str | None
    role: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

class DatasetOut(BaseModel):
    id: UUID
    initiative_id: UUID
    phase_id: UUID | None
    name: str
    description: str | None
    row_count: int | None
    column_count: int | None
    columns: dict
    summary_stats: dict | None
    uploaded_by: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
