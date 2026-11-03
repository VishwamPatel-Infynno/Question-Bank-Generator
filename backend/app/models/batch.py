from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.job import GenerationJobModel
    from app.models.question import QuestionModel


class GenerationBatchModel(Base):
    __tablename__ = "generation_batches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'running', 'completed', 'partially_completed', 'failed', 'cancelled', 'stopped')",
            name="ck_generation_batches_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    section: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    subtopic: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    passage_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    actual_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True, default="completed")
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    total_jobs: Mapped[int | None] = mapped_column(Integer, nullable=True, default=10)
    completed_jobs: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    failed_jobs: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    jobs: Mapped[list[GenerationJobModel]] = relationship(
        "GenerationJobModel", back_populates="batch", cascade="all, delete-orphan", lazy="selectin"
    )
    questions: Mapped[list[QuestionModel]] = relationship(
        "QuestionModel", back_populates="batch", lazy="selectin"
    )
