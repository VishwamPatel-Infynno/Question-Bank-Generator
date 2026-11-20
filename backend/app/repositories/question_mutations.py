"""
question_mutations.py - Write, update, deletion, and lifecycle mutations for MCAT Questions.

Encapsulates atomic state modifications including question saves with passage/batch
synchronization, soft and permanent deletions, status transitions, and duplicate overrides.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.db.base import to_datetime
from app.db.session import scoped_session
from app.models.batch import GenerationBatchModel
from app.models.passage import PassageModel
from app.models.question import QuestionModel
from app.repositories.mappers import model_to_schema, schema_to_model
from app.schemas import Question

logger = logging.getLogger(__name__)


class BatchNotFoundError(LookupError):
    """A question references a batch that does not exist (never created, or deleted meanwhile)."""

    def __init__(self, batch_id: str):
        super().__init__(f"Batch not found: {batch_id}")
        self.batch_id = batch_id


# Giving a question one of these statuses also un-deletes it
_VISIBLE_STATUSES = frozenset({"in_bank", "ai_validated", "batch_only"})


async def save_question(q: Question, session: AsyncSession | None = None) -> Question:
    """Inserts or updates a question in PostgreSQL, auto-syncing passages, batches, and vector embeddings."""
    now_dt = datetime.now(UTC)
    now_iso = now_dt.isoformat()
    q.updated_at = now_iso

    # Populate pgvector embedding if missing
    if q.embedding is None and config.ENABLE_PGVECTOR_RAG:
        try:
            from app.services.embeddings import embed_question

            q.embedding = await embed_question(q)
        except Exception as exc:
            logger.debug("Automatic question embedding generation skipped: %s", exc)

    async with scoped_session(session) as session:
        # 1. Auto-sync Passage record atomically if passage_id and stimulus_text exist
        if q.passage_id and q.stimulus_text and q.stimulus_text.strip():
            words = q.stimulus_text.split()
            p_stmt = (
                pg_insert(PassageModel)
                .values(
                    id=q.passage_id,
                    title=f"{q.subtopic or q.section} Passage",
                    text=q.stimulus_text.strip(),
                    word_count=len(words),
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
                        "word_count": len(words),
                        "updated_at": now_dt,
                    },
                )
            )
            await session.execute(p_stmt)

        # 2. Batch sync. A generation job's question (job_id set) needs a real batch: fabricating a
        # "completed" one would resurrect a batch the user deleted while a worker was still saving.
        # Manual approvals (no job) keep auto-creating the batch record, idempotently.
        if q.batch_id and q.job_id:
            found = await session.execute(
                select(GenerationBatchModel.id).where(GenerationBatchModel.id == q.batch_id)
            )
            if found.first() is None:
                raise BatchNotFoundError(q.batch_id)
        elif q.batch_id:
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
        model = schema_to_model(q)
        await session.merge(model)
        await session.commit()
        return q


async def save_questions_batch(
    questions: list[Question], session: AsyncSession | None = None
) -> list[str]:
    """Inserts or updates an array of questions in PostgreSQL within a single atomic transaction, auto-syncing passages and batches."""
    if not questions:
        return []

    now_dt = datetime.now(UTC)
    now_iso = now_dt.isoformat()
    saved_ids = []

    # Batch populate pgvector embeddings if missing
    if config.ENABLE_PGVECTOR_RAG:
        try:
            from app.services.embeddings import build_question_embedding_text, embed_texts

            missing_indices = [i for i, q in enumerate(questions) if q.embedding is None]
            if missing_indices:
                texts_to_embed = [
                    build_question_embedding_text(questions[i]) for i in missing_indices
                ]
                computed_vectors = await embed_texts(texts_to_embed)
                for orig_idx, vec in zip(missing_indices, computed_vectors, strict=False):
                    questions[orig_idx].embedding = vec
        except Exception as exc:
            logger.debug("Batch question embedding generation skipped: %s", exc)

    async with scoped_session(session) as session:
        # Pre-group passages and batches to optimize DB roundtrips
        passages_to_upsert: dict[str, PassageModel] = {}
        batches_to_upsert: dict[str, dict[str, Any]] = {}
        job_batch_ids: set[str] = {q.batch_id for q in questions if q.batch_id and q.job_id}

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
                if bid in job_batch_ids:
                    # Worker/job saves never fabricate a batch (see save_question)
                    raise BatchNotFoundError(bid)
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
            model = schema_to_model(q)
            if q.id in existing_ids:
                await session.merge(model)
            else:
                session.add(model)
            saved_ids.append(q.id)

        await session.commit()

    return saved_ids


async def delete_question(question_id: str, session: AsyncSession | None = None) -> bool:
    """Soft-deletes a question by primary key ID, preserving it for batch progress."""
    now_dt = datetime.now(UTC)
    async with scoped_session(session) as session:
        stmt = (
            update(QuestionModel)
            .where(QuestionModel.id == question_id)
            .values(is_deleted=True, deleted_at=now_dt)
        )
        res = await session.execute(stmt)
        await session.commit()
        return bool(res.rowcount and res.rowcount > 0)


async def delete_questions_batch(
    question_ids: list[str], session: AsyncSession | None = None
) -> int:
    """Soft-deletes multiple questions by primary key IDs in a single atomic SQL transaction, preserving them for batch progress."""
    if not question_ids:
        return 0
    now_dt = datetime.now(UTC)
    async with scoped_session(session) as session:
        stmt = (
            update(QuestionModel)
            .where(QuestionModel.id.in_(question_ids))
            .values(is_deleted=True, deleted_at=now_dt)
        )
        result = await session.execute(stmt)
        await session.commit()
    return result.rowcount or 0


async def hard_delete_questions_batch(
    question_ids: list[str], session: AsyncSession | None = None
) -> int:
    """Permanently purges questions by primary key IDs from the database (used for duplicate resolution and trimming excess buffer)."""
    if not question_ids:
        return 0
    async with scoped_session(session) as session:
        stmt = delete(QuestionModel).where(QuestionModel.id.in_(question_ids))
        result = await session.execute(stmt)
        await session.commit()
    return result.rowcount or 0


async def hard_delete_question(question_id: str, session: AsyncSession | None = None) -> bool:
    """Permanently purges a single question by ID from the database."""
    if not question_id:
        return False
    async with scoped_session(session) as session:
        stmt = delete(QuestionModel).where(QuestionModel.id == question_id)
        result = await session.execute(stmt)
        await session.commit()
    return bool(result.rowcount and result.rowcount > 0)


async def restore_question(
    question_id: str, session: AsyncSession | None = None
) -> Question | None:
    """Restores a soft-deleted question back to active status, and restores its passage if soft-deleted."""
    now_dt = datetime.now(UTC)
    async with scoped_session(session) as session:
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
        return model_to_schema(q)


async def update_question_status(
    question_id: str, status: str, session: AsyncSession | None = None
) -> bool:
    """Updates the lifecycle status of a single question."""
    now_dt = datetime.now(UTC)
    async with scoped_session(session) as session:
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


async def batch_update_question_status(
    question_ids: list[str], status: str, session: AsyncSession | None = None
) -> int:
    """Updates the lifecycle status of multiple questions in a single atomic transaction."""
    if not question_ids:
        return 0
    now_dt = datetime.now(UTC)
    async with scoped_session(session) as session:
        update_vals: dict[str, Any] = {"status": status, "updated_at": now_dt}
        if status in _VISIBLE_STATUSES:
            update_vals["is_deleted"] = False
            update_vals["deleted_at"] = None

        stmt = update(QuestionModel).where(QuestionModel.id.in_(question_ids)).values(**update_vals)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount or 0


async def override_question_duplicate(
    question_id: str, session: AsyncSession | None = None
) -> Question | None:
    """Marks a question's duplicate alert as manually overridden and approved in the database."""
    now_dt = datetime.now(UTC)
    now_iso = now_dt.isoformat()
    async with scoped_session(session) as session:
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
        return model_to_schema(model)
