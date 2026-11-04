import uuid

import pytest
from app.db.session import init_db
from app.repositories import (
    get_batch_by_id,
    get_question_by_id,
    get_question_status_counts,
    get_questions,
    promote_completed_batch_questions,
    save_batch,
    save_job,
    save_question,
)
from app.schemas import GenerationBatch, GenerationJob, OptionChoice, Question

pytestmark = pytest.mark.requires_db


@pytest.fixture(autouse=True)
async def ensure_db():
    await init_db()


@pytest.mark.asyncio
async def test_withhold_questions_until_batch_completed():
    batch_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    q_id = str(uuid.uuid4())

    # 1. Create an in-progress batch and job
    batch = GenerationBatch(
        id=batch_id,
        section="chem_phys",
        subtopic="Thermodynamics",
        difficulty="medium",
        passage_mode="single_passage",
        target_count=5,
        actual_count=1,
        total_jobs=1,
        completed_jobs=0,
        failed_jobs=0,
        status="in_progress",
    )
    await save_batch(batch)

    job = GenerationJob(
        id=job_id,
        batch_id=batch_id,
        job_number=1,
        status="running",
        target_count=5,
        actual_count=1,
    )
    await save_job(job)

    # 2. Add a question with score 95 generated while batch is running (status = batch_only)
    opts = [
        OptionChoice(id="A", text="Option A"),
        OptionChoice(id="B", text="Option B"),
        OptionChoice(id="C", text="Option C"),
        OptionChoice(id="D", text="Option D"),
    ]
    q = Question(
        id=q_id,
        section="chem_phys",
        section_label="Chemical and Physical Foundations",
        subtopic="Thermodynamics",
        difficulty="medium",
        batch_id=batch_id,
        job_id=job_id,
        question_stem="What is the standard enthalpy of reaction?",
        options=opts,
        correct_answer_id="A",
        explanation="Option A is correct.",
        final_score=95,
        status="batch_only",
    )
    await save_question(q)

    # 3. Verify that while the batch is in_progress, this question does NOT appear in ai_validated (Ready for Review)
    validated_qs = await get_questions(status="ai_validated")
    assert not any(item.id == q_id for item in validated_qs)

    # 4. Verify that question status counts do not count it under ai_validated
    counts_before = await get_question_status_counts()
    # It must be counted under batch_only, NOT ai_validated
    assert counts_before.get("batch_only", 0) >= 1

    # 5. Mark the batch as completed and promote
    batch_obj = await get_batch_by_id(batch_id)
    assert batch_obj is not None
    batch_obj.completed_jobs = 1
    batch_obj.actual_count = 5
    batch_obj.status = "completed"
    await save_batch(batch_obj)

    promoted_count = await promote_completed_batch_questions(batch_id)
    assert promoted_count == 1

    # 6. Verify that question is now promoted to ai_validated and visible in Ready for Review
    updated_q = await get_question_by_id(q_id)
    assert updated_q is not None
    assert updated_q.status == "ai_validated"

    validated_qs_after = await get_questions(status="ai_validated")
    assert any(item.id == q_id for item in validated_qs_after)

    counts_after = await get_question_status_counts()
    assert counts_after.get("ai_validated", 0) >= 1


@pytest.mark.asyncio
async def test_cancelled_batch_does_not_promote_questions():
    batch_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    q_id = str(uuid.uuid4())

    batch = GenerationBatch(
        id=batch_id,
        section="bio_biochem",
        subtopic="Enzyme Kinetics",
        difficulty="hard",
        target_count=50,
        actual_count=10,
        total_jobs=10,
        completed_jobs=2,
        failed_jobs=0,
        status="cancelled",
    )
    await save_batch(batch)

    job = GenerationJob(
        id=job_id,
        batch_id=batch_id,
        job_number=1,
        status="cancelled",
        target_count=5,
        actual_count=5,
    )
    await save_job(job)

    opts = [
        OptionChoice(id="A", text="Option A"),
        OptionChoice(id="B", text="Option B"),
        OptionChoice(id="C", text="Option C"),
        OptionChoice(id="D", text="Option D"),
    ]
    q = Question(
        id=q_id,
        section="bio_biochem",
        section_label="Biological and Biochemical Foundations",
        subtopic="Enzyme Kinetics",
        difficulty="hard",
        batch_id=batch_id,
        job_id=job_id,
        question_stem="Which inhibitor alters Km without changing Vmax?",
        options=opts,
        correct_answer_id="B",
        explanation="Competitive inhibition.",
        final_score=96,
        status="batch_only",
    )
    await save_question(q)

    # Cancelled batches must NOT have questions promoted
    validated_qs = await get_questions(status="ai_validated")
    assert not any(item.id == q_id for item in validated_qs)

    q_in_db = await get_question_by_id(q_id)
    assert q_in_db.status == "batch_only"
