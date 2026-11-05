"""Concurrent refreshes of one batch must serialize and stay consistent."""

import asyncio
import uuid

import pytest
from app.repositories import (
    get_batch_by_id,
    refresh_batch_aggregates,
    save_batch,
    save_job,
)
from app.schemas import GenerationBatch, GenerationJob

pytestmark = pytest.mark.requires_db


@pytest.mark.asyncio
async def test_concurrent_refreshes_converge_on_job_totals():
    batch_id = str(uuid.uuid4())
    await save_batch(
        GenerationBatch(
            id=batch_id,
            section="chem_phys",
            subtopic="Kinetics",
            difficulty="medium",
            target_count=10,
            total_jobs=2,
            status="in_progress",
        )
    )
    for n in (1, 2):
        await save_job(
            GenerationJob(
                id=str(uuid.uuid4()),
                batch_id=batch_id,
                job_number=n,
                status="completed",
                target_count=5,
                actual_count=5,
                total_tokens=100,
                cost_usd=0.01,
            )
        )

    results = await asyncio.gather(*(refresh_batch_aggregates(batch_id) for _ in range(8)))
    assert all(r is not None and r.completed_jobs == 2 for r in results)

    final = await get_batch_by_id(batch_id)
    assert final.completed_jobs == 2 and final.total_tokens == 200
    assert round(final.cost_usd, 6) == 0.02
