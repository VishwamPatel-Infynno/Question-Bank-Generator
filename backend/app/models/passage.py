from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.question import QuestionModel


class PassageModel(Base):
    __tablename__ = "passages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    subtopic: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_svg: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Bidirectional relationships
    questions: Mapped[list[QuestionModel]] = relationship(
        "QuestionModel",
        back_populates="passage",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
