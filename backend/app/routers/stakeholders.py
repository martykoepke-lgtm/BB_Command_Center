"""
Stakeholders API — manage internal and external stakeholders on initiatives.

Routes:
  GET    /api/initiatives/{id}/stakeholders           — List internal stakeholders
  POST   /api/initiatives/{id}/stakeholders           — Add internal stakeholder
  DELETE /api/initiatives/{id}/stakeholders/{user_id}  — Remove internal stakeholder
  GET    /api/initiatives/{id}/external-stakeholders           — List external stakeholders
  POST   /api/initiatives/{id}/external-stakeholders           — Add external stakeholder
  DELETE /api/external-stakeholders/{id}                       — Remove external stakeholder
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.supporting import InitiativeStakeholder, ExternalStakeholder
from app.schemas.supporting import (
    StakeholderCreate,
    StakeholderOut,
    ExternalStakeholderCreate,
    ExternalStakeholderOut,
)

router = APIRouter(tags=["Stakeholders"])


# ---- Internal Stakeholders ----

@router.get("/initiatives/{initiative_id}/stakeholders", response_model=list[StakeholderOut])
async def list_stakeholders(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all internal stakeholders for an initiative."""
    result = await db.execute(
        select(InitiativeStakeholder, User.full_name, User.email)
        .join(User, InitiativeStakeholder.user_id == User.id)
        .where(InitiativeStakeholder.initiative_id == initiative_id)
        .order_by(InitiativeStakeholder.added_at)
    )
    rows = result.all()
    return [
        StakeholderOut(
            initiative_id=sh.initiative_id,
            user_id=sh.user_id,
            role=sh.role,
            added_at=sh.added_at,
            user_name=name,
            user_email=email,
        )
        for sh, name, email in rows
    ]


@router.post("/initiatives/{initiative_id}/stakeholders", response_model=StakeholderOut, status_code=201)
async def add_stakeholder(
    initiative_id: UUID,
    payload: StakeholderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an internal stakeholder to an initiative."""
    # Check if already exists
    existing = await db.execute(
        select(InitiativeStakeholder).where(
            InitiativeStakeholder.initiative_id == initiative_id,
            InitiativeStakeholder.user_id == payload.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User is already a stakeholder")

    sh = InitiativeStakeholder(
        initiative_id=initiative_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    db.add(sh)
    await db.flush()
    await db.refresh(sh)

    # Get user info for response
    user = await db.get(User, payload.user_id)
    return StakeholderOut(
        initiative_id=sh.initiative_id,
        user_id=sh.user_id,
        role=sh.role,
        added_at=sh.added_at,
        user_name=user.full_name if user else None,
        user_email=user.email if user else None,
    )


@router.delete("/initiatives/{initiative_id}/stakeholders/{user_id}", status_code=204)
async def remove_stakeholder(
    initiative_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an internal stakeholder from an initiative."""
    result = await db.execute(
        select(InitiativeStakeholder).where(
            InitiativeStakeholder.initiative_id == initiative_id,
            InitiativeStakeholder.user_id == user_id,
        )
    )
    sh = result.scalar_one_or_none()
    if sh is None:
        raise HTTPException(status_code=404, detail="Stakeholder not found")
    await db.delete(sh)
    await db.flush()


# ---- External Stakeholders ----

@router.get("/initiatives/{initiative_id}/external-stakeholders", response_model=list[ExternalStakeholderOut])
async def list_external_stakeholders(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all external stakeholders for an initiative."""
    result = await db.execute(
        select(ExternalStakeholder)
        .where(ExternalStakeholder.initiative_id == initiative_id)
        .order_by(ExternalStakeholder.created_at)
    )
    return result.scalars().all()


@router.post("/initiatives/{initiative_id}/external-stakeholders", response_model=ExternalStakeholderOut, status_code=201)
async def add_external_stakeholder(
    initiative_id: UUID,
    payload: ExternalStakeholderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add an external stakeholder to an initiative."""
    sh = ExternalStakeholder(
        initiative_id=initiative_id,
        name=payload.name,
        title=payload.title,
        organization=payload.organization,
        email=payload.email,
        phone=payload.phone,
        role=payload.role,
    )
    db.add(sh)
    await db.flush()
    await db.refresh(sh)
    return sh


@router.delete("/external-stakeholders/{stakeholder_id}", status_code=204)
async def remove_external_stakeholder(
    stakeholder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an external stakeholder."""
    result = await db.execute(
        select(ExternalStakeholder).where(ExternalStakeholder.id == stakeholder_id)
    )
    sh = result.scalar_one_or_none()
    if sh is None:
        raise HTTPException(status_code=404, detail="External stakeholder not found")
    await db.delete(sh)
    await db.flush()
