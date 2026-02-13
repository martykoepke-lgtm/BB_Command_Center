"""
Metrics API — KPI tracking for initiatives.

Routes:
  GET    /api/initiatives/{id}/metrics  — List metrics
  POST   /api/initiatives/{id}/metrics  — Create metric
  PATCH  /api/metrics/{id}              — Update metric
  DELETE /api/metrics/{id}              — Delete metric
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.supporting import Metric
from app.schemas.supporting import MetricCreate, MetricOut, MetricUpdate

router = APIRouter(tags=["Metrics"])


@router.get("/initiatives/{initiative_id}/metrics", response_model=list[MetricOut])
async def list_metrics(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all metrics for an initiative."""
    result = await db.execute(
        select(Metric)
        .where(Metric.initiative_id == initiative_id)
        .order_by(Metric.created_at.desc())
    )
    return result.scalars().all()


@router.post("/initiatives/{initiative_id}/metrics", response_model=MetricOut, status_code=201)
async def create_metric(
    initiative_id: UUID,
    payload: MetricCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new KPI metric for an initiative."""
    metric = Metric(
        initiative_id=initiative_id,
        name=payload.name,
        unit=payload.unit,
        baseline_value=payload.baseline_value,
        baseline_date=payload.baseline_date,
        baseline_period=payload.baseline_period,
        target_value=payload.target_value,
        current_value=payload.current_value,
        notes=payload.notes,
    )
    db.add(metric)
    await db.flush()
    await db.refresh(metric)
    return metric


@router.patch("/metrics/{metric_id}", response_model=MetricOut)
async def update_metric(
    metric_id: UUID,
    payload: MetricUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a metric (e.g., set current value, mark target met)."""
    result = await db.execute(select(Metric).where(Metric.id == metric_id))
    metric = result.scalar_one_or_none()
    if metric is None:
        raise HTTPException(status_code=404, detail="Metric not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(metric, field, value)

    metric.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(metric)
    return metric


@router.delete("/metrics/{metric_id}", status_code=204)
async def delete_metric(
    metric_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a metric."""
    result = await db.execute(select(Metric).where(Metric.id == metric_id))
    metric = result.scalar_one_or_none()
    if metric is None:
        raise HTTPException(status_code=404, detail="Metric not found")
    await db.delete(metric)
    await db.flush()
