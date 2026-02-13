"""Pydantic schemas for statistical analyses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AnalysisCreate(BaseModel):
    """Payload to create and run a statistical analysis."""
    dataset_id: UUID | None = None
    phase_id: UUID | None = None
    test_type: str = Field(..., description="e.g., t_test_2sample, chi_square, anova, normality, cpk")
    test_category: str = Field(..., description="e.g., hypothesis, descriptive, spc, regression, correlation")
    configuration: dict = Field(..., description="Test-specific params: columns, alpha, hypothesis, etc.")
    ai_recommended: bool = False
    ai_reasoning: str | None = None


class AnalysisRerun(BaseModel):
    """Optional updated configuration for a rerun."""
    configuration: dict | None = None


class AnalysisOut(BaseModel):
    """Analysis returned from API."""
    id: UUID
    initiative_id: UUID
    dataset_id: UUID | None
    phase_id: UUID | None
    test_type: str
    test_category: str
    configuration: dict
    ai_recommended: bool
    ai_reasoning: str | None
    status: str
    results: dict | None
    charts: dict | None
    ai_interpretation: str | None
    ai_next_steps: str | None
    validation: dict | None = None
    run_by: UUID | None
    run_at: datetime | None
    duration_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
