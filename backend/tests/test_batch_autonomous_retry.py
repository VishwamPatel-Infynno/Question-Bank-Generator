import asyncio
import json
import uuid
from unittest.mock import patch

import pytest
from app.db.session import init_db
from app.main import app
from app.repositories import (
    get_jobs_by_batch_id,
    get_questions,
    save_batch,
    save_job,
    update_job_progress,
)
from app.schemas import GenerationBatch, GenerationJob, GenerationRequest, MCATSection
from app.services import retry_incomplete_jobs_for_batch
from app.services.batch_runner import _run_single_job
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.mark.asyncio
async def test_job_trial_count_persistence():
    """Verifies that trial_count is properly stored and updated in PostgreSQL."""
    await init_db()

    batch_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    batch = GenerationBatch(
        id=batch_id,
        section="CPBS",
        target_count=5,
        actual_count=0,
    )
    await save_batch(batch)

    job = GenerationJob(
        id=job_id,
        batch_id=batch_id,
        job_number=1,
        status="pending",
        target_count=5,
        actual_count=0,
        trial_count=1,
    )
    await save_job(job)

    jobs = await get_jobs_by_batch_id(batch_id)
    assert len(jobs) == 1
    assert jobs[0].trial_count == 1

    # Update trial_count to 2
    await update_job_progress(job_id, trial_count=2, status="running")
    jobs = await get_jobs_by_batch_id(batch_id)
    assert jobs[0].trial_count == 2
    assert jobs[0].status == "running"


@pytest.mark.asyncio
async def test_resume_stopped_jobs_under_3_trials():
    """Verifies that stopped/cancelled jobs with trial_count < 3 can be resumed."""
    await init_db()

    batch_id = str(uuid.uuid4())
    job_full_id = str(uuid.uuid4())
    job_short_id = str(uuid.uuid4())
    job_failed_id = str(uuid.uuid4())

    batch = GenerationBatch(
        id=batch_id,
        section="CPBS",
        difficulty="medium",
        target_count=15,
        actual_count=8,
        status="stopped",
    )
    await save_batch(batch)

    # Job 1: full (5/5)
    await save_job(
        GenerationJob(
            id=job_full_id,
            batch_id=batch_id,
            job_number=1,
            status="completed",
            target_count=5,
            actual_count=5,
            trial_count=1,
        )
    )

    # Job 2: shortfall (3/5) on trial 1 (stopped mid-run)
    await save_job(
        GenerationJob(
            id=job_short_id,
            batch_id=batch_id,
            job_number=2,
            status="cancelled",
            target_count=5,
            actual_count=3,
            trial_count=1,
        )
    )

    # Job 3: failed (0/5) on trial 1
    await save_job(
        GenerationJob(
            id=job_failed_id,
            batch_id=batch_id,
            job_number=3,
            status="failed",
            target_count=5,
            actual_count=0,
            trial_count=1,
        )
    )

    b, retried_jobs = await retry_incomplete_jobs_for_batch(batch_id)
    assert b is not None
    assert b.status == "in_progress"

    # Only job_short and job_failed should be reset to pending for re-execution
    retried_pending_ids = {j.id for j in retried_jobs if j.status == "pending"}
    assert job_short_id in retried_pending_ids
    assert job_failed_id in retried_pending_ids
    assert job_full_id not in retried_pending_ids


@pytest.mark.asyncio
async def test_retry_strictly_blocked_after_3_trials():
    """
    Verifies that jobs with trial_count >= 3 cannot be retried,
    and the API returns HTTP 400 Bad Request.
    """
    await init_db()

    batch_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    batch = GenerationBatch(
        id=batch_id,
        section="CPBS",
        difficulty="medium",
        target_count=5,
        actual_count=3,
        status="partially_completed",
    )
    await save_batch(batch)

    # Job that exhausted all 3 trials
    await save_job(
        GenerationJob(
            id=job_id,
            batch_id=batch_id,
            job_number=1,
            status="completed",
            target_count=5,
            actual_count=3,
            trial_count=3,
        )
    )

    # Calling service directly yields empty jobs list
    _b, retried_jobs = await retry_incomplete_jobs_for_batch(batch_id)
    assert len(retried_jobs) == 0

    # Calling API endpoint returns 400 Bad Request
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(f"/api/batches/{batch_id}/retry")
        assert resp.status_code == 400
        data = resp.json()
        assert "maximum 3-trial limit" in data["detail"]


@pytest.mark.asyncio
async def test_run_single_job_autonomous_in_flight_retry():
    """
    Verifies that _run_single_job automatically executes up to 3 trials in-flight
    when an initial trial yields fewer than target_count questions.
    """
    await init_db()

    batch_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    batch = GenerationBatch(
        id=batch_id,
        section="CPBS",
        target_count=5,
        actual_count=0,
    )
    await save_batch(batch)

    job = GenerationJob(
        id=job_id,
        batch_id=batch_id,
        job_number=1,
        status="pending",
        target_count=5,
        actual_count=0,
        trial_count=1,
    )
    await save_job(job)

    call_count = 0

    async def mock_workflow_stream_two_attempts(req):
        nonlocal call_count
        call_count += 1
        yield_count = 3 if call_count == 1 else req.questions_to_generate

        for i in range(yield_count):
            q_id = str(uuid.uuid4())
            q_dict = {
                "id": q_id,
                "batch_id": batch_id,
                "job_id": job_id,
                "section": "chemical_physical",
                "section_label": "Chemical and Physical Foundations",
                "subtopic": "Thermodynamics",
                "difficulty": "medium",
                "question_stem": f"Question {i + 1} from attempt {call_count}",
                "options": [{"id": "A", "text": "Opt A"}, {"id": "B", "text": "Opt B"}],
                "correct_answer_id": "A",
                "explanation": "Rationale",
                "final_score": 92,
                "status": "batch_only",
            }
            yield f"data: {json.dumps({'event_type': 'question_generated', 'data': {'question': q_dict}})}\n\n"
        yield f"data: {json.dumps({'event_type': 'workflow_complete', 'data': {'questions': []}})}\n\n"

    semaphore = asyncio.Semaphore(2)
    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty="medium",
        subtopic="Thermodynamics",
        passage_mode="independent",
        passage_required="No",
        questions_to_generate=5,
    )

    with patch(
        "app.workflow.engine.run_workflow_stream",
        side_effect=mock_workflow_stream_two_attempts,
    ):
        await _run_single_job(batch_id, job, req, semaphore)

    # Verify that run_workflow_stream was called twice autonomously in-flight
    assert call_count == 2

    # Check persisted job status
    jobs = await get_jobs_by_batch_id(batch_id)
    assert len(jobs) == 1
    assert jobs[0].status == "completed"
    assert jobs[0].actual_count == 5
    assert jobs[0].trial_count == 2

    # Check questions saved
    qs = await get_questions(batch_id=batch_id, job_id=job_id)
    assert len(qs) == 5
