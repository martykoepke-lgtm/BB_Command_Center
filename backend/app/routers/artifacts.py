"""
Phase artifacts API — deliverables within DMAIC phases.

Routes:
  GET    /api/initiatives/{id}/phases/{phase}/artifacts — List artifacts for phase (by name)
  POST   /api/initiatives/{id}/phases/{phase}/artifacts — Create artifact (by name)
  GET    /api/phases/{phase_id}/artifacts               — List artifacts for phase (by ID)
  POST   /api/phases/{phase_id}/artifacts               — Create artifact (by ID)
  GET    /api/artifacts/{id}    — Get single artifact
  PATCH  /api/artifacts/{id}    — Update artifact
  DELETE /api/artifacts/{id}    — Delete artifact
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
from app.models.phase import Phase, PhaseArtifact
from app.schemas.supporting import ArtifactCreate, ArtifactOut, ArtifactUpdate

router = APIRouter(tags=["Artifacts"])


@router.get(
    "/initiatives/{initiative_id}/phases/{phase_name}/artifacts",
    response_model=list[ArtifactOut],
)
async def list_phase_artifacts(
    initiative_id: UUID,
    phase_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all artifacts for a specific phase of an initiative."""
    # Find the phase
    phase_result = await db.execute(
        select(Phase).where(
            Phase.initiative_id == initiative_id,
            Phase.phase_name == phase_name,
        )
    )
    phase = phase_result.scalar_one_or_none()
    if phase is None:
        raise HTTPException(status_code=404, detail=f"Phase '{phase_name}' not found")

    result = await db.execute(
        select(PhaseArtifact)
        .where(PhaseArtifact.phase_id == phase.id)
        .order_by(PhaseArtifact.created_at.desc())
    )
    return result.scalars().all()


@router.post(
    "/initiatives/{initiative_id}/phases/{phase_name}/artifacts",
    response_model=ArtifactOut,
    status_code=201,
)
async def create_artifact(
    initiative_id: UUID,
    phase_name: str,
    payload: ArtifactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new artifact in a phase."""
    phase_result = await db.execute(
        select(Phase).where(
            Phase.initiative_id == initiative_id,
            Phase.phase_name == phase_name,
        )
    )
    phase = phase_result.scalar_one_or_none()
    if phase is None:
        raise HTTPException(status_code=404, detail=f"Phase '{phase_name}' not found")

    artifact = PhaseArtifact(
        phase_id=phase.id,
        initiative_id=initiative_id,
        artifact_type=payload.artifact_type,
        title=payload.title,
        content=payload.content,
        created_by=current_user.id,
    )
    db.add(artifact)
    await db.flush()
    await db.refresh(artifact)
    return artifact


@router.get("/phases/{phase_id}/artifacts", response_model=list[ArtifactOut])
async def list_artifacts_by_phase_id(
    phase_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all artifacts for a phase by phase UUID."""
    phase_result = await db.execute(select(Phase).where(Phase.id == phase_id))
    phase = phase_result.scalar_one_or_none()
    if phase is None:
        raise HTTPException(status_code=404, detail="Phase not found")

    result = await db.execute(
        select(PhaseArtifact)
        .where(PhaseArtifact.phase_id == phase_id)
        .order_by(PhaseArtifact.created_at.desc())
    )
    return result.scalars().all()


@router.post("/phases/{phase_id}/artifacts", response_model=ArtifactOut, status_code=201)
async def create_artifact_by_phase_id(
    phase_id: UUID,
    payload: ArtifactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create an artifact in a phase by phase UUID."""
    phase_result = await db.execute(select(Phase).where(Phase.id == phase_id))
    phase = phase_result.scalar_one_or_none()
    if phase is None:
        raise HTTPException(status_code=404, detail="Phase not found")

    artifact = PhaseArtifact(
        phase_id=phase_id,
        initiative_id=phase.initiative_id,
        artifact_type=payload.artifact_type,
        title=payload.title,
        content=payload.content,
        created_by=current_user.id,
    )
    db.add(artifact)
    await db.flush()
    await db.refresh(artifact)
    return artifact


@router.get("/artifacts/{artifact_id}", response_model=ArtifactOut)
async def get_artifact(
    artifact_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single artifact by ID."""
    result = await db.execute(select(PhaseArtifact).where(PhaseArtifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.patch("/artifacts/{artifact_id}", response_model=ArtifactOut)
async def update_artifact(
    artifact_id: UUID,
    payload: ArtifactUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an artifact's content or status."""
    result = await db.execute(select(PhaseArtifact).where(PhaseArtifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(artifact, field, value)

    artifact.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(artifact)
    return artifact


@router.delete("/artifacts/{artifact_id}", status_code=204)
async def delete_artifact(
    artifact_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an artifact."""
    result = await db.execute(select(PhaseArtifact).where(PhaseArtifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    await db.delete(artifact)
    await db.flush()
