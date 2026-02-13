"""Phase and artifact models — DMAIC phase tracking and deliverables."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Phase(Base):
    __tablename__ = "phases"
    __table_args__ = (
        UniqueConstraint("initiative_id", "phase_name", name="uq_phase_per_initiative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    initiative_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False)
    phase_name: Mapped[str] = mapped_column(String, nullable=False)
    phase_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="not_started")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gate_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    gate_approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    gate_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    completeness_score: Mapped[float] = mapped_column(Numeric, default=0)

    # Relationships
    initiative: Mapped["Initiative"] = relationship("Initiative", back_populates="phases")
    artifacts: Mapped[list["PhaseArtifact"]] = relationship("PhaseArtifact", back_populates="phase", cascade="all, delete-orphan")
    gate_approver: Mapped["User | None"] = relationship("User", foreign_keys=[gate_approved_by])


class PhaseArtifact(Base):
    __tablename__ = "phase_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("phases.id", ondelete="CASCADE"), nullable=False)
    initiative_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    phase: Mapped["Phase"] = relationship("Phase", back_populates="artifacts")
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
