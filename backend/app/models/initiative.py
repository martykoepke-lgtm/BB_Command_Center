"""
Initiative model — the living profile of an improvement project.

This is the central entity. Everything else (phases, artifacts, datasets,
analyses, notes, action items) hangs off an initiative.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import ARRAY, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Initiative(Base):
    __tablename__ = "initiatives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    initiative_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("requests.id"), nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    desired_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    out_of_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_case: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification
    methodology: Mapped[str] = mapped_column(String, nullable=False, default="DMAIC")
    initiative_type: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[str] = mapped_column(String, default="medium")
    status: Mapped[str] = mapped_column(String, default="active")

    # Assignment
    lead_analyst_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    sponsor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Dates
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_completion: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_completion: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Current state
    current_phase: Mapped[str] = mapped_column(String, default="define")
    phase_progress: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Impact tracking
    projected_savings: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    actual_savings: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    projected_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_impact: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    request: Mapped["Request | None"] = relationship("Request", back_populates="initiative", foreign_keys=[request_id])
    lead_analyst: Mapped["User | None"] = relationship("User", foreign_keys=[lead_analyst_id], back_populates="led_initiatives")
    sponsor: Mapped["User | None"] = relationship("User", foreign_keys=[sponsor_id], back_populates="sponsored_initiatives")
    team: Mapped["Team | None"] = relationship("Team", foreign_keys=[team_id])
    phases: Mapped[list["Phase"]] = relationship("Phase", back_populates="initiative", cascade="all, delete-orphan", order_by="Phase.phase_order")
    action_items: Mapped[list["ActionItem"]] = relationship("ActionItem", back_populates="initiative", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship("Note", back_populates="initiative", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="initiative", cascade="all, delete-orphan")
    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="initiative", cascade="all, delete-orphan")
    metrics: Mapped[list["Metric"]] = relationship("Metric", back_populates="initiative", cascade="all, delete-orphan")
    conversations: Mapped[list["AIConversation"]] = relationship("AIConversation", back_populates="initiative", cascade="all, delete-orphan")
    stakeholders: Mapped[list["InitiativeStakeholder"]] = relationship("InitiativeStakeholder", back_populates="initiative", cascade="all, delete-orphan")
    external_stakeholders: Mapped[list["ExternalStakeholder"]] = relationship("ExternalStakeholder", back_populates="initiative", cascade="all, delete-orphan")
