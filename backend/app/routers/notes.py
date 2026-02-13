"""
Notes API — initiative-scoped notes (decisions, blockers, meeting notes, etc.)

Routes:
  GET    /api/initiatives/{id}/notes  — List notes
  POST   /api/initiatives/{id}/notes  — Create note
  DELETE /api/notes/{id}              — Delete note
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.supporting import Note
from app.schemas.supporting import NoteCreate, NoteOut

router = APIRouter(tags=["Notes"])


@router.get("/initiatives/{initiative_id}/notes", response_model=list[NoteOut])
async def list_notes(
    initiative_id: UUID,
    note_type: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notes for an initiative, optionally filtered by type."""
    query = select(Note).where(Note.initiative_id == initiative_id)
    if note_type:
        query = query.where(Note.note_type == note_type)
    query = query.order_by(Note.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/initiatives/{initiative_id}/notes", response_model=NoteOut, status_code=201)
async def create_note(
    initiative_id: UUID,
    payload: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a note on an initiative."""
    note = Note(
        initiative_id=initiative_id,
        phase_id=payload.phase_id,
        author_id=current_user.id,
        note_type=payload.note_type,
        content=payload.content,
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)
    return note


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a note."""
    result = await db.execute(select(Note).where(Note.id == note_id))
    note = result.scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    await db.delete(note)
    await db.flush()
