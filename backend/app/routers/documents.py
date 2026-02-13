"""
Documents API — file attachments and external links for initiatives.

Routes:
  GET    /api/initiatives/{id}/documents  — List documents
  POST   /api/initiatives/{id}/documents  — Create document entry
  DELETE /api/documents/{id}              — Delete document
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.supporting import Document
from app.schemas.supporting import DocumentCreate, DocumentOut

router = APIRouter(tags=["Documents"])


@router.get("/initiatives/{initiative_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    initiative_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents attached to an initiative."""
    result = await db.execute(
        select(Document)
        .where(Document.initiative_id == initiative_id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.post("/initiatives/{initiative_id}/documents", response_model=DocumentOut, status_code=201)
async def create_document(
    initiative_id: UUID,
    payload: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a document entry (file reference or external link)."""
    doc = Document(
        initiative_id=initiative_id,
        phase_id=payload.phase_id,
        name=payload.name,
        document_type=payload.document_type,
        file_path=payload.file_path,
        external_url=payload.external_url,
        uploaded_by=current_user.id,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document entry."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.flush()
