from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.batch import GenerationBatchModel
    from app.models.job import GenerationJobModel
    from app.models.passage import PassageModel


class QuestionModel(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "length(trim(section)) > 0",
            name="ck_questions_section",
        ),
        CheckConstraint(
            "status IN ('in_bank', 'ai_validated', 'batch_only', 'below_threshold', 'discarded', 'approved', 'rejected_below_threshold', 'error', 'failed')",
            name="ck_questions_status",
        ),
        CheckConstraint(
            "final_score >= 0 AND final_score <= 100",
            name="ck_questions_final_score",
        ),
        Index("ix_questions_status_created", "status", "created_at"),
        Index("ix_questions_section_created", "section", "created_at"),
        Index("ix_questions_batch_job", "batch_id", "job_id"),
        Index("ix_questions_section_subtopic", "section", "subtopic"),
        Index("ix_questions_is_duplicate_override", "is_duplicate_override"),
        Index("ix_questions_section_difficulty", "section", "difficulty"),
        Index("ix_questions_status_final_score", "status", "final_score"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    section: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    section_label: Mapped[str] = mapped_column(String(128), nullable=False)
    subtopic: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    stimulus_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_stem: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    correct_answer_id: Mapped[str] = mapped_column(String(32), nullable=False)
    correct_answer_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_svg: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_score: Mapped[int] = mapped_column(Integer, nullable=False)
    review_rubric: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    iteration_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    iterations_history: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    batch_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("generation_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("generation_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="in_bank", index=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Token usage & cost tracking
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0)
    token_usage_details: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    # Manager Combination Matrix attributes
    combination_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    content_domain: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    question_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    interaction_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    primary_trap: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    passage_required: Mapped[str | None] = mapped_column(String(16), nullable=True)
    passage_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    passage_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("passages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    passage_questions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visual_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # MCAT-specific scoring & AAMC Skill attributes
    mcat_scaled_score: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    aamc_skill: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # Granular Dependent Taxonomy Hierarchy
    subject: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    unit: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    topic: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    subskill: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    likely_mistake_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Deduplication & Collision Metadata
    duplicate_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_duplicate_override: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Multi-Stage Raw Outcome JSON
    stage_outcomes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Bidirectional relationships
    passage: Mapped[PassageModel | None] = relationship("PassageModel", back_populates="questions")
    batch: Mapped[GenerationBatchModel | None] = relationship(
        "GenerationBatchModel", back_populates="questions"
    )
    job: Mapped[GenerationJobModel | None] = relationship(
        "GenerationJobModel", back_populates="questions"
    )
