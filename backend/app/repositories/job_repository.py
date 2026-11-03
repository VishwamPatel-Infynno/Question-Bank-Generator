from __future__ import annotations

import logging

from sqlalchemy import select

from app.db.base import to_datetime, to_iso_str
from app.db.session import async_session_factory
from app.models.job import GenerationJobModel
from app.schemas import GenerationJob

logger = logging.getLogger(__name__)


def _job_model_to_schema(m: GenerationJobModel) -> GenerationJob:
    """Converts a SQLAlchemy GenerationJobModel to a Pydantic GenerationJob schema."""
    return GenerationJob(
        id=m.id,
        batch_id=m.batch_id,
        job_number=m.job_number,
        status=m.status or "pending",
        target_count=m.target_count or 5,
        actual_count=m.actual_count or 0,
        trial_count=m.trial_count if m.trial_count is not None else 1,
        passage_id=m.passage_id,
        total_tokens=m.total_tokens or 0,
        prompt_tokens=m.prompt_tokens or 0,
        completion_tokens=m.completion_tokens or 0,
        cost_usd=float(m.cost_usd) if m.cost_usd is not None else 0.0,
        error_message=m.error_message,
        created_at=to_iso_str(m.created_at),
        started_at=to_iso_str(m.started_at) if m.started_at else None,
        completed_at=to_iso_str(m.completed_at) if m.completed_at else None,
    )


def _job_schema_to_model(j: GenerationJob) -> GenerationJobModel:
    """Converts a Pydantic GenerationJob schema to a SQLAlchemy GenerationJobModel."""
    return GenerationJobModel(
        id=j.id,
        batch_id=j.batch_id,
        job_number=j.job_number,
        status=j.status,
        target_count=j.target_count,
        actual_count=j.actual_count,
        trial_count=j.trial_count or 1,
        passage_id=j.passage_id,
        total_tokens=j.total_tokens,
        prompt_tokens=j.prompt_tokens,
        completion_tokens=j.completion_tokens,
        cost_usd=j.cost_usd,
        error_message=j.error_message,
        created_at=to_datetime(j.created_at),
        started_at=to_datetime(j.started_at) if j.started_at else None,
        completed_at=to_datetime(j.completed_at) if j.completed_at else None,
    )


async def save_job(job: GenerationJob) -> GenerationJob:
    """Creates or updates a single generation job record."""
    async with async_session_factory() as session:
        model = _job_schema_to_model(job)
        await session.merge(model)
        await session.commit()
        return job


async def save_jobs_bulk(jobs: list[GenerationJob]) -> list[GenerationJob]:
    """Persists multiple generation job records in a single transaction."""
    if not jobs:
        return []
    async with async_session_factory() as session:
        for j in jobs:
            model = _job_schema_to_model(j)
            await session.merge(model)
        await session.commit()
        return jobs


async def get_jobs_by_batch_id(batch_id: str) -> list[GenerationJob]:
    """Retrieves all jobs for a specific batch, ordered by job_number ascending."""
    async with async_session_factory() as session:
        stmt = (
            select(GenerationJobModel)
            .where(GenerationJobModel.batch_id == batch_id)
            .order_by(GenerationJobModel.job_number.asc())
        )
        result = await session.execute(stmt)
        models = result.scalars().all()
        return [_job_model_to_schema(m) for m in models]


async def get_job_by_id(job_id: str) -> GenerationJob | None:
    """Retrieves a single generation job by ID."""
    async with async_session_factory() as session:
        model = await session.get(GenerationJobModel, job_id)
        if not model:
            return None
        return _job_model_to_schema(model)


async def update_job_progress(
    job_id: str,
    status: str | None = None,
    actual_count: int | None = None,
    trial_count: int | None = None,
    total_tokens: int | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    cost_usd: float | None = None,
    passage_id: str | None = None,
    error_message: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> GenerationJob | None:
    """Updates atomic fields on a job record."""
    async with async_session_factory() as session:
        model = await session.get(GenerationJobModel, job_id)
        if not model:
            return None

        if status is not None:
            model.status = status
        if actual_count is not None:
            model.actual_count = actual_count
        if trial_count is not None:
            model.trial_count = trial_count
        if total_tokens is not None:
            model.total_tokens = total_tokens
        if prompt_tokens is not None:
            model.prompt_tokens = prompt_tokens
        if completion_tokens is not None:
            model.completion_tokens = completion_tokens
        if cost_usd is not None:
            model.cost_usd = cost_usd
        if passage_id is not None:
            model.passage_id = passage_id
        if error_message is not None:
            model.error_message = error_message
        if started_at is not None:
            model.started_at = to_datetime(started_at) if started_at else None
        if completed_at is not None:
            model.completed_at = to_datetime(completed_at) if completed_at else None

        await session.commit()
        await session.refresh(model)
        return _job_model_to_schema(model)
