from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, case, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import config
from app.db.base import to_datetime
from app.db.session import async_session_factory
from app.models.batch import GenerationBatchModel
from app.models.passage import PassageModel
from app.models.question import QuestionModel
from app.repositories._filters import active_question_clause
from app.repositories.mappers import model_to_schema, schema_to_model
from app.repositories.query_builders import (
    DIFFICULTY_ALIASES,
    SLIM_DEFER,
    build_question_filters,
)
from app.schemas import BatchStatus, Question, enum_value
from app.schemas.question import ACTIVE_QUESTION_STATUSES

logger = logging.getLogger(__name__)

# Giving a question one of these statuses also un-deletes it
_VISIBLE_STATUSES = frozenset({"in_bank", "ai_validated", "batch_only"})

# Backward compatibility aliases
_model_to_schema = model_to_schema
_schema_to_model = schema_to_model
_build_question_filters = build_question_filters
_DIFFICULTY_ALIASES = DIFFICULTY_ALIASES
_SLIM_DEFER = SLIM_DEFER


async def save_question(q: Question) -> Question:
    """Inserts or updates a question in PostgreSQL, auto-syncing passages and batches."""
    now_dt = datetime.now(UTC)
    now_iso = now_dt.isoformat()
    q.updated_at = now_iso

    async with async_session_factory() as session:
        # 1. Auto-sync Passage record atomically if passage_id and stimulus_text exist
        if q.passage_id and q.stimulus_text and q.stimulus_text.strip():
            p_stmt = (
                pg_insert(PassageModel)
                .values(
                    id=q.passage_id,
                    title=f"{q.subtopic or q.section} Passage",
                    text=q.stimulus_text.strip(),
                    word_count=len(q.stimulus_text.split()),
                    section=q.section,
                    subtopic=q.subtopic,
                    image_url=q.image_url,
                    image_svg=q.image_svg,
                    image_description=q.image_description,
                    created_at=to_datetime(q.created_at),
                    updated_at=now_dt,
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "text": q.stimulus_text.strip(),
                        "word_count": len(q.stimulus_text.split()),
                        "updated_at": now_dt,
                    },
                )
            )
            await session.execute(p_stmt)

        # 2. Auto-sync GenerationBatch record atomically if batch_id exists (idempotent, no inflation on edit)
        if q.batch_id:
            b_stmt = (
                pg_insert(GenerationBatchModel)
                .values(
                    id=q.batch_id,
                    section=q.section,
                    subtopic=q.subtopic,
                    difficulty=q.difficulty,
                    passage_mode=q.passage_mode,
                    target_count=1,
                    actual_count=1,
                    total_tokens=q.total_tokens or 0,
                    cost_usd=q.cost_usd or 0.0,
                    status="completed",
                    created_at=to_datetime(q.created_at),
                    updated_at=now_dt,
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )
            await session.execute(b_stmt)

        # 3. Save QuestionModel
        model = _schema_to_model(q)
        await session.merge(model)
        await session.commit()
        return q


async def save_questions_batch(questions: list[Question]) -> list[str]:
    """Inserts or updates an array of questions in PostgreSQL within a single atomic transaction, auto-syncing passages and batches."""
    if not questions:
        return []

    now_dt = datetime.now(UTC)
    now_iso = now_dt.isoformat()
    saved_ids = []

    async with async_session_factory() as session:
        # Pre-group passages and batches to optimize DB roundtrips
        passages_to_upsert: dict[str, PassageModel] = {}
        batches_to_upsert: dict[str, dict[str, Any]] = {}

        for q in questions:
            q.updated_at = now_iso

            # Aggregate passages
            if (
                q.passage_id
                and q.stimulus_text
                and q.stimulus_text.strip()
                and q.passage_id not in passages_to_upsert
            ):
                passages_to_upsert[q.passage_id] = PassageModel(
                    id=q.passage_id,
                    title=f"{q.subtopic or q.section} Passage",
                    text=q.stimulus_text.strip(),
                    word_count=len(q.stimulus_text.split()),
                    section=q.section,
                    subtopic=q.subtopic,
                    image_url=q.image_url,
                    image_svg=q.image_svg,
                    image_description=q.image_description,
                    created_at=to_datetime(q.created_at),
                    updated_at=now_dt,
                )

            # Aggregate batches
            if q.batch_id:
                if q.batch_id not in batches_to_upsert:
                    batches_to_upsert[q.batch_id] = {
                        "section": q.section,
                        "subtopic": q.subtopic,
                        "difficulty": q.difficulty,
                        "passage_mode": q.passage_mode,
                        "count": 0,
                        "tokens": 0,
                        "cost": 0.0,
                        "created_at": to_datetime(q.created_at),
                    }
                b_info = batches_to_upsert[q.batch_id]
                b_info["count"] += 1
                b_info["tokens"] += q.total_tokens or 0
                b_info["cost"] += q.cost_usd or 0.0

        # Upsert passages (one SELECT for every id, not one per passage)
        existing_passages = {}
        if passages_to_upsert:
            rows = await session.execute(
                select(PassageModel).where(PassageModel.id.in_(list(passages_to_upsert)))
            )
            existing_passages = {p.id: p for p in rows.scalars().all()}
        for pid, p_mod in passages_to_upsert.items():
            existing_p = existing_passages.get(pid)
            if not existing_p:
                session.add(p_mod)
            else:
                existing_p.text = p_mod.text
                existing_p.word_count = p_mod.word_count
                if p_mod.image_svg and not existing_p.image_svg:
                    existing_p.image_svg = p_mod.image_svg
                if p_mod.image_url and not existing_p.image_url:
                    existing_p.image_url = p_mod.image_url
                if p_mod.image_description and not existing_p.image_description:
                    existing_p.image_description = p_mod.image_description
                existing_p.updated_at = now_dt

        # Upsert batches (create batch record if it doesn't exist, leave existing batch aggregates intact to avoid double-counting)
        existing_batches = {}
        if batches_to_upsert:
            rows = await session.execute(
                select(GenerationBatchModel).where(
                    GenerationBatchModel.id.in_(list(batches_to_upsert))
                )
            )
            existing_batches = {b.id: b for b in rows.scalars().all()}
        for bid, b_info in batches_to_upsert.items():
            existing_b = existing_batches.get(bid)
            if not existing_b:
                b_model = GenerationBatchModel(
                    id=bid,
                    section=b_info["section"],
                    subtopic=b_info["subtopic"],
                    difficulty=b_info["difficulty"],
                    passage_mode=b_info["passage_mode"],
                    target_count=b_info["count"],
                    actual_count=b_info["count"],
                    total_tokens=b_info["tokens"],
                    cost_usd=b_info["cost"],
                    status="completed",
                    created_at=b_info["created_at"],
                    updated_at=now_dt,
                )
                session.add(b_model)
            else:
                existing_b.updated_at = now_dt

        # Upsert questions. One query finds which ids already exist and loads them into the session,
        # so merge() hits the identity map instead of issuing a SELECT per row; new ids are added
        # directly (merge would otherwise SELECT each of them just to learn they are missing).
        all_ids = [q.id for q in questions]
        existing_rows = await session.execute(
            select(QuestionModel).where(QuestionModel.id.in_(all_ids))
        )
        existing_ids = {m.id for m in existing_rows.scalars().all()}
        for q in questions:
            model = _schema_to_model(q)
            if q.id in existing_ids:
                await session.merge(model)
            else:
                session.add(model)
            saved_ids.append(q.id)

        await session.commit()

    return saved_ids


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
    filters = _build_question_filters(
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
    filters = _build_question_filters(
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
            stmt = stmt.options(*_SLIM_DEFER)
        for cond in filters:
            stmt = stmt.where(cond)

        if sort_by == "score_desc":
            stmt = stmt.order_by(QuestionModel.final_score.desc(), QuestionModel.created_at.desc())
        elif sort_by == "score_asc":
            stmt = stmt.order_by(QuestionModel.final_score.asc(), QuestionModel.created_at.desc())
        elif sort_by == "difficulty":
            diff_order = case(
                (QuestionModel.difficulty.in_(_DIFFICULTY_ALIASES["low"]), 1),
                (QuestionModel.difficulty.in_(_DIFFICULTY_ALIASES["medium"]), 2),
                (QuestionModel.difficulty.in_(_DIFFICULTY_ALIASES["high"]), 3),
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
        return [_model_to_schema(m, slim=slim) for m in models]


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
        return [_model_to_schema(m) for m in result.scalars().all()]


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
        return _model_to_schema(model)


async def delete_question(question_id: str) -> bool:
    """Soft-deletes a question by primary key ID, preserving it for batch progress."""
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        stmt = (
            update(QuestionModel)
            .where(QuestionModel.id == question_id)
            .values(is_deleted=True, deleted_at=now_dt)
        )
        res = await session.execute(stmt)
        await session.commit()
        return bool(res.rowcount and res.rowcount > 0)


async def delete_questions_batch(question_ids: list[str]) -> int:
    """Soft-deletes multiple questions by primary key IDs in a single atomic SQL transaction, preserving them for batch progress."""
    if not question_ids:
        return 0
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        stmt = (
            update(QuestionModel)
            .where(QuestionModel.id.in_(question_ids))
            .values(is_deleted=True, deleted_at=now_dt)
        )
        result = await session.execute(stmt)
        await session.commit()
    return result.rowcount or 0


async def hard_delete_questions_batch(question_ids: list[str]) -> int:
    """Permanently purges questions by primary key IDs from the database (used for duplicate resolution and trimming excess buffer)."""
    if not question_ids:
        return 0
    async with async_session_factory() as session:
        stmt = delete(QuestionModel).where(QuestionModel.id.in_(question_ids))
        result = await session.execute(stmt)
        await session.commit()
    return result.rowcount or 0


async def hard_delete_question(question_id: str) -> bool:
    """Permanently purges a single question by ID from the database."""
    if not question_id:
        return False
    async with async_session_factory() as session:
        stmt = delete(QuestionModel).where(QuestionModel.id == question_id)
        result = await session.execute(stmt)
        await session.commit()
    return bool(result.rowcount and result.rowcount > 0)


async def restore_question(question_id: str) -> Question | None:
    """Restores a soft-deleted question back to active status, and restores its passage if soft-deleted."""
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        stmt = select(QuestionModel).where(QuestionModel.id == question_id)
        res = await session.execute(stmt)
        q = res.scalar_one_or_none()
        if not q:
            return None
        q.is_deleted = False
        q.deleted_at = None
        q.updated_at = now_dt

        # If question has a linked passage that was soft-deleted, restore the passage too
        if q.passage_id:
            p_stmt = (
                update(PassageModel)
                .where(PassageModel.id == q.passage_id)
                .values(is_deleted=False, deleted_at=None)
            )
            await session.execute(p_stmt)

        await session.commit()
        return _model_to_schema(q)


async def update_question_status(question_id: str, status: str) -> bool:
    """Updates the lifecycle status of a single question."""
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        stmt = select(QuestionModel).where(QuestionModel.id == question_id)
        res = await session.execute(stmt)
        q = res.scalar_one_or_none()
        if not q:
            return False
        q.status = status
        if status in _VISIBLE_STATUSES:
            q.is_deleted = False
            q.deleted_at = None
        q.updated_at = now_dt
        await session.commit()
        return True


async def batch_update_question_status(question_ids: list[str], status: str) -> int:
    """Updates the lifecycle status of multiple questions in a single atomic transaction."""
    if not question_ids:
        return 0
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        update_vals: dict[str, Any] = {"status": status, "updated_at": now_dt}
        if status in _VISIBLE_STATUSES:
            update_vals["is_deleted"] = False
            update_vals["deleted_at"] = None

        stmt = update(QuestionModel).where(QuestionModel.id.in_(question_ids)).values(**update_vals)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount or 0


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
            .options(*_SLIM_DEFER)
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
        return [_model_to_schema(m, slim=True) for m in models]


async def override_question_duplicate(question_id: str) -> Question | None:
    """Marks a question's duplicate alert as manually overridden and approved in the database."""
    now_iso = datetime.now(UTC).isoformat()
    now_dt = datetime.now(UTC)
    async with async_session_factory() as session:
        model = await session.get(QuestionModel, question_id)
        if not model or model.is_deleted:
            return None
        model.is_duplicate_override = True
        dup_dict = dict(model.duplicate_info or {})
        dup_dict["is_overridden"] = True
        dup_dict["overridden_at"] = now_iso
        model.duplicate_info = dup_dict
        # A question still held back by a running batch must not leak into the bank early
        if model.status != "batch_only":
            model.status = "in_bank"
        model.updated_at = now_dt
        await session.commit()
        await session.refresh(model)
        return _model_to_schema(model)


@dataclass(frozen=True)
class QuestionHead:
    """The few columns the batch worker needs about a job's questions (no JSONB payloads)."""

    id: str
    status: str
    stimulus_text: str | None
    passage_id: str | None


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
