"""Dataset and statistical analysis models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    initiative_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False)
    phase_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("phases.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    columns: Mapped[dict] = mapped_column(JSONB, nullable=False)
    summary_stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    data_preview: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    initiative: Mapped["Initiative"] = relationship("Initiative", back_populates="datasets")
    phase: Mapped["Phase | None"] = relationship("Phase")
    uploader: Mapped["User | None"] = relationship("User", foreign_keys=[uploaded_by])
    analyses: Mapped[list["StatisticalAnalysis"]] = relationship("StatisticalAnalysis", back_populates="dataset", cascade="all, delete-orphan")


class StatisticalAnalysis(Base):
    __tablename__ = "statistical_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    initiative_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    phase_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("phases.id"), nullable=True)

    # Test configuration
    test_type: Mapped[str] = mapped_column(String, nullable=False)
    test_category: Mapped[str] = mapped_column(String, nullable=False)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # AI recommendation context
    ai_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Results
    status: Mapped[str] = mapped_column(String, default="pending")
    results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    charts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_next_steps: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    run_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    initiative: Mapped["Initiative"] = relationship("Initiative")
    dataset: Mapped["Dataset | None"] = relationship("Dataset", back_populates="analyses")
    phase: Mapped["Phase | None"] = relationship("Phase")
    runner: Mapped["User | None"] = relationship("User", foreign_keys=[run_by])
