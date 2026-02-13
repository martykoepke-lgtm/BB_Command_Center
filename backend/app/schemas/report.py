"""Pydantic schemas for report generation."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    """Request to generate a report."""
    report_type: str = Field(
        ...,
        description="Type of report: executive_summary, phase_tollgate, initiative_closeout, portfolio_review, statistical_summary",
    )
    format: str = Field("html", description="Output format: html or pdf")
    include_charts: bool = True
    include_ai_narrative: bool = True
    custom_sections: list[str] | None = None


class ReportOut(BaseModel):
    """Generated report metadata."""
    id: UUID
    initiative_id: UUID | None
    report_type: str
    title: str
    format: str
    status: str
    file_path: str | None
    metadata_json: dict | None = None
    generated_by: UUID | None
    generated_at: datetime | None
    created_at: datetime
    content_html: str | None = None  # Included only when format=html and status=completed

    model_config = {"from_attributes": True}


class ReportListItem(BaseModel):
    """Report summary for list views."""
    id: UUID
    initiative_id: UUID | None
    report_type: str
    title: str
    format: str
    status: str
    generated_at: datetime | None

    model_config = {"from_attributes": True}
