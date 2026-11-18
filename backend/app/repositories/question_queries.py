"""
question_queries.py - Query and aggregation operations for MCAT Questions.

Encapsulates all read-only database operations including filtered searches,
paginated listings, metrics aggregations, status counts, and reference question lookups.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, case, func, or_, select

from app.core.config import config
from app.db.session import async_session_factory
from app.models.batch import GenerationBatchModel
from app.models.question import QuestionModel
from app.repositories._filters import active_question_clause
from app.repositories.mappers import model_to_schema
from app.repositories.query_builders import (
    DIFFICULTY_ALIASES,
    SLIM_DEFER,
    build_question_filters,
)
from app.schemas import BatchStatus, Question, enum_value
from app.schemas.question import ACTIVE_QUESTION_STATUSES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuestionHead:
    """The few columns the batch worker needs about a job's questions (no JSONB payloads)."""

    id: str
    status: str
    stimulus_text: str | None
    passage_id: str | None


async def get_repository_metrics(status: str | None = None) -> dict[str, Any]:
    """Computes repository-wide metrics via native SQL aggregation with zero Python memory overhead."""
    async with async_session_factory() as session:
        stmt = select(
            func.count(QuestionModel.id).label("total_count"),
            func.coalesce(func.sum(QuestionModel.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(QuestionModel.cost_usd), 0.0).label("total_cost_usd"),
        ).where(active_question_clause())
        if status and status != "all":
            stmt = stmt.where(QuestionModel.status == status)
        res = await session.execute(stmt)
        row = res.one()
        return {
            "total_count": int(row.total_count),
            "total_tokens": int(row.total_tokens),
            "total_cost_usd": round(float(row.total_cost_usd), 5),
        }


async def count_questions(
    section: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    combination_id: str | None = None,
    run_id: str | None = None,
    batch_id: str | None = None,
    job_id: str | None = None,
    passage_id: str | None = None,
    status: str | None = None,
    include_deleted: bool = False,
) -> int:
    """Returns the total number of questions matching specific filter criteria."""
    filters = build_question_filters(
        section=section,
        difficulty=difficulty,
        search=search,
        combination_id=combination_id,
        run_id=run_id,
        batch_id=batch_id,
        job_id=job_id,
        passage_id=passage_id,
        status=status,
        include_deleted=include_deleted,
    )
    async with async_session_factory() as session:
        stmt = select(func.count(QuestionModel.id))
        for cond in filters:
            stmt = stmt.where(cond)
        res = await session.execute(stmt)
        return int(res.scalar() or 0)


async def get_questions(
    section: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    combination_id: str | None = None,
    run_id: str | None = None,
    batch_id: str | None = None,
    job_id: str | None = None,
    passage_id: str | None = None,
    status: str | None = None,
    sort_by: str | None = "newest",
    limit: int | None = None,
    offset: int | None = 0,
    slim: bool = False,
    include_deleted: bool = False,
) -> list[Question]:
    """Retrieves questions from PostgreSQL with optional filtering, hybrid full-text search, pagination, and slim payload projection."""
    filters = build_question_filters(
        section=section,
        difficulty=difficulty,
        search=search,
        combination_id=combination_id,
        run_id=run_id,
        batch_id=batch_id,
        job_id=job_id,
        passage_id=passage_id,
        status=status,
        include_deleted=include_deleted,
    )
    async with async_session_factory() as session:
        stmt = select(QuestionModel)
        if slim:
            # The slim schema omits these blobs anyway (about 70% of a row's bytes): do not read them
            stmt = stmt.options(*SLIM_DEFER)
        for cond in filters:
            stmt = stmt.where(cond)

        if sort_by == "score_desc":
            stmt = stmt.order_by(QuestionModel.final_score.desc(), QuestionModel.created_at.desc())
        elif sort_by == "score_asc":
            stmt = stmt.order_by(QuestionModel.final_score.asc(), QuestionModel.created_at.desc())
        elif sort_by == "difficulty":
            diff_order = case(
                (QuestionModel.difficulty.in_(DIFFICULTY_ALIASES["low"]), 1),
                (QuestionModel.difficulty.in_(DIFFICULTY_ALIASES["medium"]), 2),
                (QuestionModel.difficulty.in_(DIFFICULTY_ALIASES["high"]), 3),
                else_=4,
            )
            stmt = stmt.order_by(diff_order, QuestionModel.created_at.desc())
        else:
            stmt = stmt.order_by(QuestionModel.created_at.desc())

        if offset and offset > 0:
            stmt = stmt.offset(offset)
        if limit and limit > 0:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        models = result.scalars().all()
        return [model_to_schema(m, slim=slim) for m in models]


async def get_active_batch_questions(batch_id: str) -> list[Question]:
    """A batch's questions that still count (the same set every refill and deficit path uses)."""
    async with async_session_factory() as session:
        stmt = (
            select(QuestionModel)
            .where(
                QuestionModel.batch_id == batch_id,
                active_question_clause(),
                QuestionModel.status.in_(ACTIVE_QUESTION_STATUSES),
            )
            .order_by(QuestionModel.created_at.desc())
        )
        result = await session.execute(stmt)
        return [model_to_schema(m) for m in result.scalars().all()]


async def get_question_by_id(question_id: str, include_deleted: bool = False) -> Question | None:
    """Retrieves a single question by primary key ID."""
    async with async_session_factory() as session:
        stmt = select(QuestionModel).where(QuestionModel.id == question_id)
        if not include_deleted:
            stmt = stmt.where(active_question_clause())
        res = await session.execute(stmt)
        model = res.scalar_one_or_none()
        if not model:
            return None
        return model_to_schema(model)


async def get_question_status_counts() -> dict[str, int]:
    """Returns counts of questions grouped by lifecycle status."""
    async with async_session_factory() as session:
        in_progress_batches = select(GenerationBatchModel.id).where(
            GenerationBatchModel.status == BatchStatus.IN_PROGRESS
        )
        ai_validated_gate = and_(
            QuestionModel.final_score > config.PASSING_SCORE_THRESHOLD,
            or_(
                QuestionModel.batch_id.is_(None),
                QuestionModel.batch_id.notin_(in_progress_batches),
            ),
        )
        stmt = (
            select(QuestionModel.status, func.count(QuestionModel.id))
            .where(
                active_question_clause(),
                or_(
                    QuestionModel.status != "ai_validated",
                    and_(
                        QuestionModel.status == "ai_validated",
                        ai_validated_gate,
                    ),
                ),
            )
            .group_by(QuestionModel.status)
        )
        res = await session.execute(stmt)
        counts = {row[0] or "in_bank": row[1] for row in res.all()}

        del_stmt = select(func.count(QuestionModel.id)).where(QuestionModel.is_deleted.is_(True))
        deleted_count = (await session.execute(del_stmt)).scalar() or 0

        return {
            "ai_validated": counts.get("ai_validated", 0),
            "in_bank": counts.get("in_bank", 0),
            "discarded": counts.get("discarded", 0),
            "below_threshold": counts.get("below_threshold", 0),
            "batch_only": counts.get("batch_only", 0),
            "deleted": deleted_count,
            "total": sum(counts.values()),
        }


async def get_subtopic_reference_questions(
    section: str,
    subtopic: str | None = None,
    limit: int = 50,
) -> list[Question]:
    """
    Retrieves recent questions from the question bank matching the section and subtopic
    to serve as the collision reference pool for deduplication.
    """
    async with async_session_factory() as session:
        # Dedup only reads stems/options: skip the large JSONB audit blobs of every reference row
        stmt = (
            select(QuestionModel)
            .options(*SLIM_DEFER)
            .where(
                active_question_clause(),
                QuestionModel.status.in_(["in_bank", "ai_validated", "approved"]),
            )
        )
        if section:
            sec_val = enum_value(section)
            stmt = stmt.where(
                or_(
                    QuestionModel.section == sec_val,
                    QuestionModel.section_label.ilike(f"%{sec_val}%"),
                )
            )
        if subtopic and subtopic.strip():
            sub_val = subtopic.strip()
            stmt = stmt.where(
                or_(
                    QuestionModel.subtopic == sub_val,
                    QuestionModel.subtopic.ilike(f"%{sub_val}%"),
                )
            )

        stmt = stmt.order_by(QuestionModel.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        models = result.scalars().all()
        return [model_to_schema(m, slim=True) for m in models]


async def get_active_job_question_heads(batch_id: str, job_id: str) -> list[QuestionHead]:
    """Active (not deleted, not discarded) questions of a job, projected to a few columns.

    The worker only counts them and reads the first one's stimulus/passage, so loading full rows
    (about 11 KB of JSONB each) on every trial was wasted I/O.
    """
    async with async_session_factory() as session:
        stmt = (
            select(
                QuestionModel.id,
                QuestionModel.status,
                QuestionModel.stimulus_text,
                QuestionModel.passage_id,
            )
            .where(
                QuestionModel.batch_id == batch_id,
                QuestionModel.job_id == job_id,
                active_question_clause(),
                QuestionModel.status.in_(sorted(ACTIVE_QUESTION_STATUSES)),
            )
            .order_by(QuestionModel.created_at.asc())
        )
        rows = (await session.execute(stmt)).all()
        return [QuestionHead(r.id, r.status, r.stimulus_text, r.passage_id) for r in rows]
