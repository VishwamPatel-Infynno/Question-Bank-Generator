from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.batch import GenerationBatchModel
    from app.models.question import QuestionModel


class GenerationJobModel(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'running', 'completed', 'failed', 'cancelled', 'stopped')",
            name="ck_generation_jobs_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    batch_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("generation_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )  # pending, running, completed, failed, cancelled
    target_count: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    actual_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trial_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    passage_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Bidirectional relationships
    batch: Mapped[GenerationBatchModel] = relationship(
        "GenerationBatchModel", back_populates="jobs"
    )
    questions: Mapped[list[QuestionModel]] = relationship(
        "QuestionModel", back_populates="job", lazy="selectin"
    )
