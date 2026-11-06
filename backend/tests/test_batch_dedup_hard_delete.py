import uuid

import pytest
from app.main import app
from app.repositories import (
    get_questions,
    hard_delete_questions_batch,
    refresh_batch_aggregates,
    save_batch,
    save_job,
    save_question,
)
from app.schemas import GenerationBatch, GenerationJob, OptionChoice, Question
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


async def test_hard_delete_purges_duplicate_questions():
    """Verifies that hard_delete_questions_batch permanently removes records from PostgreSQL."""

    batch_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    q_id_keep = str(uuid.uuid4())
    q_id_dup = str(uuid.uuid4())

    batch = GenerationBatch(
        id=batch_id,
        section="CPBS",
        target_count=5,
        actual_count=2,
    )
    await save_batch(batch)

    job = GenerationJob(
        id=job_id,
        batch_id=batch_id,
        job_number=1,
        status="completed",
        target_count=5,
        actual_count=2,
    )
    await save_job(job)

    opts = [OptionChoice(id="A", text="Opt A"), OptionChoice(id="B", text="Opt B")]
    q1 = Question(
        id=q_id_keep,
        batch_id=batch_id,
        job_id=job_id,
        section="chemical_physical",
        section_label="Chemical and Physical Foundations of Biological Systems",
        subtopic="Thermodynamics",
        difficulty="medium",
        question_stem="Unique question about thermodynamics?",
        options=opts,
        correct_answer_id="A",
        explanation="Rationale",
        final_score=95,
        status="ai_validated",
    )
    q2 = Question(
        id=q_id_dup,
        batch_id=batch_id,
        job_id=job_id,
        section="chemical_physical",
        section_label="Chemical and Physical Foundations of Biological Systems",
        subtopic="Thermodynamics",
        difficulty="medium",
        question_stem="Duplicate question about thermodynamics?",
        options=opts,
        correct_answer_id="A",
        explanation="Rationale",
        final_score=91,
        status="discarded",
    )
    await save_question(q1)
    await save_question(q2)

    # Both exist initially
    initial_qs = await get_questions(batch_id=batch_id, include_deleted=True)
    assert any(q.id == q_id_keep for q in initial_qs)
    assert any(q.id == q_id_dup for q in initial_qs)

    # Perform hard delete of duplicate
    deleted_count = await hard_delete_questions_batch([q_id_dup])
    assert deleted_count == 1

    # Duplicate is permanently gone, keep question remains
    post_qs = await get_questions(batch_id=batch_id, include_deleted=True)
    assert any(q.id == q_id_keep for q in post_qs)
    assert not any(q.id == q_id_dup for q in post_qs)

    # Verify GET /api/batches/{batch_id} returns only 1 question for job, zero duplicates
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/batches/{batch_id}")
        assert res.status_code == 200
        data = res.json()
        assert len(data["questions"]) == 1
        assert data["questions"][0]["id"] == q_id_keep
        assert len(data["jobs"][0]["questions"]) == 1
        assert data["jobs"][0]["questions"][0]["id"] == q_id_keep


async def test_refresh_batch_aggregates_completion_guard():
    """Verifies that refresh_batch_aggregates keeps in_progress status when allow_complete=False."""

    batch_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    batch = GenerationBatch(
        id=batch_id,
        section="CPBS",
        target_count=5,
        actual_count=0,
        status="in_progress",
    )
    await save_batch(batch)

    job = GenerationJob(
        id=job_id,
        batch_id=batch_id,
        job_number=1,
        status="completed",
        target_count=5,
        actual_count=5,
    )
    await save_job(job)

    # When allow_complete=False, status must stay in_progress despite actual_count >= target_count
    b_in_prog = await refresh_batch_aggregates(batch_id, allow_complete=False)
    assert b_in_prog is not None
    assert b_in_prog.status == "in_progress"

    # When allow_complete=True, status transitions to completed
    b_completed = await refresh_batch_aggregates(batch_id, allow_complete=True)
    assert b_completed is not None
    assert b_completed.status == "completed"
