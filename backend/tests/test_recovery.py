"""Startup recovery: orphaned running jobs must not stay 'running' forever."""

import uuid

import pytest
from app.repositories import (
    get_batch_by_id,
    get_job_by_id,
    reconcile_interrupted_batches,
    save_batch,
    save_job,
    update_job_progress,
)
from app.schemas import GenerationBatch, GenerationJob

pytestmark = pytest.mark.requires_db


async def _make_batch_with_job(job_status: str, error: str | None = None):
    batch_id, job_id = str(uuid.uuid4()), str(uuid.uuid4())
    await save_batch(
        GenerationBatch(
            id=batch_id,
            section="chem_phys",
            subtopic="Kinetics",
            difficulty="medium",
            target_count=5,
            status="in_progress",
        )
    )
    await save_job(
        GenerationJob(
            id=job_id,
            batch_id=batch_id,
            job_number=1,
            status=job_status,
            target_count=5,
            error_message=error,
        )
    )
    return batch_id, job_id


@pytest.mark.asyncio
async def test_reconcile_stops_orphaned_batches_and_their_running_jobs():
    batch_id, running_id = await _make_batch_with_job("running")
    _, done_id = await _make_batch_with_job("completed")

    await reconcile_interrupted_batches()

    assert (await get_batch_by_id(batch_id)).status == "stopped"
    assert (await get_job_by_id(running_id)).status == "stopped"
    # A job that already finished keeps its terminal status
    assert (await get_job_by_id(done_id)).status == "completed"


@pytest.mark.asyncio
async def test_update_job_progress_can_clear_fields_explicitly():
    _, job_id = await _make_batch_with_job("failed", error="boom")

    await update_job_progress(job_id, status="pending")  # None means unchanged
    assert (await get_job_by_id(job_id)).error_message == "boom"

    await update_job_progress(job_id, clear=("error_message",))
    assert (await get_job_by_id(job_id)).error_message is None
