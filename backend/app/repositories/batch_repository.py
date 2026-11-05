from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import config
from app.db.base import to_datetime, to_iso_str
from app.db.session import async_session_factory
from app.models.batch import GenerationBatchModel
from app.models.job import GenerationJobModel
from app.models.question import QuestionModel
from app.repositories._filters import active_question_clause
from app.schemas import (
    COMPLETED_STATES,
    LIVE_STATES,
    BatchStatus,
    GenerationBatch,
    JobStatus,
)

logger = logging.getLogger(__name__)


_SECRET_REQUEST_FIELDS = ("api_key",)


def _scrub_request_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Drops credentials from a stored/returned request payload (never persist or echo keys)."""
    if not payload:
        return payload
    return {k: v for k, v in payload.items() if k not in _SECRET_REQUEST_FIELDS}


def _batch_model_to_schema(
    m: GenerationBatchModel, include_payload: bool = True
) -> GenerationBatch:
    """Converts a SQLAlchemy GenerationBatchModel to a Pydantic GenerationBatch schema."""
    return GenerationBatch(
        id=m.id,
        section=m.section,
        subtopic=m.subtopic,
        difficulty=m.difficulty,
        passage_mode=m.passage_mode,
        target_count=m.target_count or 0,
        actual_count=m.actual_count or 0,
        total_jobs=m.total_jobs or 10,
        completed_jobs=m.completed_jobs or 0,
        failed_jobs=m.failed_jobs or 0,
        error_message=m.error_message,
        total_tokens=m.total_tokens or 0,
        cost_usd=float(m.cost_usd) if m.cost_usd is not None else 0.0,
        status=m.status or "completed",
        request_payload=(
            _scrub_request_payload(getattr(m, "request_payload", None)) if include_payload else None
        ),
        created_at=to_iso_str(m.created_at),
        updated_at=to_iso_str(m.updated_at) if m.updated_at else None,
    )


def _batch_schema_to_model(b: GenerationBatch) -> GenerationBatchModel:
    """Converts a Pydantic GenerationBatch schema to a SQLAlchemy GenerationBatchModel."""
    return GenerationBatchModel(
        id=b.id,
        section=b.section,
        subtopic=b.subtopic,
        difficulty=b.difficulty,
        passage_mode=b.passage_mode,
        target_count=b.target_count,
        actual_count=b.actual_count,
        total_jobs=b.total_jobs,
        completed_jobs=b.completed_jobs,
        failed_jobs=b.failed_jobs,
        error_message=b.error_message,
        total_tokens=b.total_tokens,
        cost_usd=b.cost_usd,
        status=b.status,
        request_payload=_scrub_request_payload(b.request_payload),
        created_at=to_datetime(b.created_at),
        updated_at=to_datetime(b.updated_at) if b.updated_at else datetime.now(UTC),
    )


async def get_batches(
    section: str | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[GenerationBatch]:
    """Retrieves generation batch logs with optional section and status filtering."""
    async with async_session_factory() as session:
        stmt = select(GenerationBatchModel)
        if section:
            stmt = stmt.where(GenerationBatchModel.section == section)
        if status:
            stmt = stmt.where(GenerationBatchModel.status == status)

        stmt = stmt.order_by(GenerationBatchModel.created_at.desc())
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        result = await session.execute(stmt)
        models = result.scalars().all()
        # List rows omit request_payload: it can be large and only the single-batch view needs it.
        return [_batch_model_to_schema(m, include_payload=False) for m in models]


async def batch_exists(batch_id: str) -> bool:
    """Cheap existence check (no row hydration, no JSONB payload)."""
    async with async_session_factory() as session:
        found = await session.execute(
            select(GenerationBatchModel.id).where(GenerationBatchModel.id == batch_id)
        )
        return found.first() is not None


async def get_batch_by_id(batch_id: str) -> GenerationBatch | None:
    """Retrieves a single generation batch by primary key ID."""
    async with async_session_factory() as session:
        model = await session.get(GenerationBatchModel, batch_id)
        if not model:
            return None
        return _batch_model_to_schema(model)


async def save_batch(batch: GenerationBatch) -> GenerationBatch:
    """Creates or updates a generation batch record."""
    batch.updated_at = datetime.now(UTC).isoformat()
    async with async_session_factory() as session:
        model = _batch_schema_to_model(batch)
        await session.merge(model)
        await session.commit()
        return batch


async def _execute_promote_batch_questions(
    session: AsyncSession, batch_id: str, timestamp: datetime | None = None
) -> int:
    """Updates qualifying batch_only questions (score > threshold) to ai_validated within an active session."""
    ts = timestamp or datetime.now(UTC)
    promote_stmt = (
        update(QuestionModel)
        .where(
            QuestionModel.batch_id == batch_id,
            QuestionModel.status == "batch_only",
            active_question_clause(),
            QuestionModel.final_score > config.PASSING_SCORE_THRESHOLD,
        )
        .values(status="ai_validated", updated_at=ts)
    )
    res = await session.execute(promote_stmt)
    return res.rowcount or 0


async def delete_batch(batch_id: str) -> bool:
    """Deletes a batch and cascades delete to related jobs."""
    async with async_session_factory() as session:
        model = await session.get(GenerationBatchModel, batch_id)
        if not model:
            return False
        await session.delete(model)
        await session.commit()
        return True


async def refresh_batch_aggregates(
    batch_id: str, allow_complete: bool = False
) -> GenerationBatch | None:
    """
    Recalculates completed_jobs, failed_jobs, actual_count, total_tokens, and cost_usd
    directly from the generation_jobs table in a single atomic database operation.
    Guarantees zero lost updates from concurrent jobs.
    When allow_complete is False, in-progress batches are preserved in 'in_progress'
    so that deduplication and refills do not cause premature completion.
    """
    async with async_session_factory() as session:
        # Row lock: concurrent jobs refresh the same batch; without it two refreshes compute from
        # different snapshots and the last commit can move counts or status backwards. This is
        # FOR NO KEY UPDATE (key_share=True): it serializes writers of the batch row but does not
        # conflict with the FOR KEY SHARE lock that every question INSERT takes through its foreign
        # key, which a plain FOR UPDATE does (that caused deadlocks with concurrent saves).
        batch_model = await session.get(
            GenerationBatchModel, batch_id, with_for_update={"key_share": True}
        )
        if not batch_model:
            return None

        stmt = select(
            func.count()
            .filter(GenerationJobModel.status.in_(COMPLETED_STATES))
            .label("completed_jobs"),
            func.count().filter(GenerationJobModel.status.in_(LIVE_STATES)).label("active_jobs"),
            func.count().filter(GenerationJobModel.status == JobStatus.FAILED).label("failed_jobs"),
            func.coalesce(func.sum(GenerationJobModel.actual_count), 0).label("actual_count"),
            func.coalesce(func.sum(GenerationJobModel.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(GenerationJobModel.cost_usd), 0.0).label("cost_usd"),
        ).where(GenerationJobModel.batch_id == batch_id)

        res = await session.execute(stmt)
        row = res.one()

        completed_jobs = int(row.completed_jobs or 0)
        failed_jobs = int(row.failed_jobs or 0)
        active_jobs = int(row.active_jobs or 0)
        job_sum_actual = int(row.actual_count or 0)
        total_tokens = int(row.total_tokens or 0)
        cost_usd = round(float(row.cost_usd or 0.0), 6)

        # Count real active questions in the batch (excluding soft-deleted, discarded, failed, rejected)
        q_count_stmt = select(func.count(QuestionModel.id)).where(
            QuestionModel.batch_id == batch_id,
            active_question_clause(),
            QuestionModel.status.notin_(
                ("discarded", "rejected_below_threshold", "error", "failed")
            ),
        )
        q_count_res = await session.execute(q_count_stmt)
        active_q_count = int(q_count_res.scalar() or 0)
        actual_count = active_q_count if active_q_count > 0 else job_sum_actual

        batch_model.completed_jobs = completed_jobs
        batch_model.failed_jobs = failed_jobs
        batch_model.actual_count = actual_count
        batch_model.total_tokens = total_tokens
        batch_model.cost_usd = cost_usd
        batch_model.updated_at = datetime.now(UTC)

        total_jobs = batch_model.total_jobs or 10
        target_count = batch_model.target_count or 50

        # Preserve terminal or user-stopped status unless transitioning upon completion. A
        # partially_completed batch with no live jobs is terminal (e.g. just stopped by the user).
        keep_terminal = batch_model.status in (BatchStatus.CANCELLED, BatchStatus.STOPPED) or (
            batch_model.status == BatchStatus.PARTIALLY_COMPLETED and active_jobs == 0
        )
        if not keep_terminal:
            if completed_jobs + failed_jobs >= total_jobs and failed_jobs > 0:
                batch_model.status = (
                    BatchStatus.PARTIALLY_COMPLETED if completed_jobs > 0 else BatchStatus.FAILED
                )
            elif actual_count >= target_count and actual_count > 0:
                batch_model.status = (
                    BatchStatus.COMPLETED if allow_complete else BatchStatus.IN_PROGRESS
                )
            elif completed_jobs >= total_jobs:
                if allow_complete:
                    batch_model.status = (
                        BatchStatus.COMPLETED
                        if actual_count >= target_count
                        else BatchStatus.PARTIALLY_COMPLETED
                    )
                else:
                    batch_model.status = "in_progress"
            elif batch_model.status != BatchStatus.COMPLETED:
                batch_model.status = BatchStatus.IN_PROGRESS

            # Final resolution: a caller that says the batch is done (allow_complete) while no job
            # is pending or running must leave a terminal status. Without this a batch whose jobs
            # ended cancelled/stopped (client disconnect, stop then resume) stayed "in_progress"
            # forever with nothing running it.
            if allow_complete and active_jobs == 0 and batch_model.status in LIVE_STATES:
                if actual_count >= target_count and actual_count > 0:
                    batch_model.status = BatchStatus.COMPLETED
                elif actual_count > 0 or completed_jobs > 0:
                    batch_model.status = BatchStatus.PARTIALLY_COMPLETED
                elif failed_jobs > 0:
                    batch_model.status = BatchStatus.FAILED
                else:
                    batch_model.status = BatchStatus.CANCELLED

        # If batch is completed or partially completed, promote qualifying active questions (>90 score) to 'ai_validated'
        if batch_model.status in COMPLETED_STATES:
            await _execute_promote_batch_questions(session, batch_id)

        await session.commit()
        await session.refresh(batch_model)
        return _batch_model_to_schema(batch_model)


async def promote_completed_batch_questions(batch_id: str) -> int:
    """
    Promotes all active questions with final_score > 90 belonging to a completed batch
    from 'batch_only' to 'ai_validated' (Ready for Review).
    """
    async with async_session_factory() as session:
        promoted = await _execute_promote_batch_questions(session, batch_id)
        await session.commit()
        if promoted > 0:
            logger.info(
                "Promoted %s questions in completed batch %s to 'ai_validated'.", promoted, batch_id
            )
        return promoted


async def scrub_stored_request_secrets() -> int:
    """One-time cleanup: removes API keys that earlier versions persisted in request payloads."""
    async with async_session_factory() as session:
        res = await session.execute(
            update(GenerationBatchModel)
            .where(func.jsonb_exists(GenerationBatchModel.request_payload, "api_key"))
            .values(request_payload=GenerationBatchModel.request_payload.op("-")("api_key"))
        )
        await session.commit()
        return res.rowcount or 0


async def reconcile_interrupted_batches() -> int:
    """Safely transitions orphan in_progress batches to 'stopped' on backend startup.

    When the backend restarts or experiences an unexpected process termination,
    background worker tasks cease running. This sweep updates any orphan in_progress
    batches to 'stopped', preserves all fulfilled questions, and promotes questions
    that passed the quality threshold so users can inspect them or resume the batch.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(GenerationBatchModel).where(
                GenerationBatchModel.status == BatchStatus.IN_PROGRESS
            )
        )
        orphans = list(result.scalars().all())
        if not orphans:
            return 0

        now = datetime.now(UTC)
        for b in orphans:
            b.status = BatchStatus.STOPPED
            b.updated_at = now
            b.error_message = "Server restarted while batch was generating. Progress preserved."
            await _execute_promote_batch_questions(session, b.id, timestamp=now)

        # Jobs of orphaned batches would otherwise show "running" forever. 'stopped' keeps them
        # retryable: the retry flow re-launches any job below its target count.
        await session.execute(
            update(GenerationJobModel)
            .where(
                GenerationJobModel.batch_id.in_([b.id for b in orphans]),
                GenerationJobModel.status.in_(LIVE_STATES),
            )
            .values(status=JobStatus.STOPPED, completed_at=now)
        )

        await session.commit()
        logger.info(
            "Startup batch reconciliation: safely marked %s orphan batch(es) as 'stopped'.",
            len(orphans),
        )
        return len(orphans)
