"""Tests for full-stack enterprise optimizations: session injection, slim batch queries, and connection protection."""

import uuid

import pytest
from app.db.session import async_session_factory
from app.repositories import (
    count_batches,
    count_passages,
    count_questions,
    delete_passage,
    get_batch_by_id,
    get_batches,
    get_jobs_by_batch_id,
    get_passage_by_id,
    get_passages,
    get_questions,
    get_repository_metrics,
    restore_passage,
    save_batch,
    save_job,
    save_passage,
    save_question,
)
from app.schemas import (
    BatchStatus,
    GenerationBatch,
    GenerationJob,
    OptionChoice,
    Passage,
    Question,
)

pytestmark = pytest.mark.requires_db


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_session_injection_reusability():
    """Verify that question and batch query functions accept an injected session and work seamlessly."""
    uid = uuid.uuid4().hex[:8]
    sec = f"bio_biochem_{uid}"

    # Create test batch, job, and question
    batch = GenerationBatch(
        id=f"batch-sess-{uid}",
        section=sec,
        subtopic="Metabolism",
        difficulty="medium",
        passage_mode="independent",
        target_count=5,
        actual_count=1,
        total_jobs=1,
        completed_jobs=1,
        status=BatchStatus.COMPLETED,
    )
    await save_batch(batch)

    job = GenerationJob(
        id=f"job-sess-{uid}",
        batch_id=batch.id,
        job_number=1,
        status="completed",
        target_count=5,
        actual_count=1,
    )
    await save_job(job)

    question = Question(
        id=f"q-sess-{uid}",
        batch_id=batch.id,
        job_id=job.id,
        section=sec,
        section_label="Biological and Biochemical Foundations of Living Systems",
        subtopic="Metabolism",
        difficulty="medium",
        question_stem="Which enzyme catalyzes the committed step of glycolysis?",
        options=[
            OptionChoice(id="A", text="Hexokinase"),
            OptionChoice(id="B", text="Phosphofructokinase-1"),
            OptionChoice(id="C", text="Pyruvate kinase"),
            OptionChoice(id="D", text="Aldolase"),
        ],
        correct_answer_id="B",
        explanation="PFK-1 catalyzes the committed step.",
        final_score=92,
        status="in_bank",
        stage_outcomes={"stage_1": "draft_data", "details": "some long diagnostic payload"},
        iterations_history=[{"iteration": 1, "audit": "passed"}],
    )
    await save_question(question)

    # Now verify that multiple queries execute over ONE shared session seamlessly
    async with async_session_factory() as session:
        # Pipelined execution over single connection
        qs = await get_questions(batch_id=batch.id, session=session)
        cnt = await count_questions(batch_id=batch.id, session=session)
        metrics = await get_repository_metrics(status="in_bank", session=session)
        b_fetched = await get_batch_by_id(batch.id, session=session)
        b_list = await get_batches(section=sec, session=session)
        b_count = await count_batches(section=sec, session=session)
        jobs = await get_jobs_by_batch_id(batch.id, session=session)

    assert len(qs) == 1
    assert qs[0].id == question.id
    assert cnt == 1
    assert metrics["total_count"] >= 1
    assert b_fetched is not None
    assert b_fetched.id == batch.id
    assert len(b_list) == 1
    assert b_count == 1
    assert len(jobs) == 1
    assert jobs[0].id == job.id


async def test_batch_detail_slim_projection_endpoint(client):
    """Verify that /api/batches/{id} defaults to slim=True and omits heavy JSONB blobs."""
    uid = uuid.uuid4().hex[:8]
    sec = f"cars_{uid}"

    batch = GenerationBatch(
        id=f"batch-slim-{uid}",
        section=sec,
        subtopic="Humanities",
        difficulty="medium",
        passage_mode="independent",
        target_count=5,
        status=BatchStatus.COMPLETED,
    )
    await save_batch(batch)

    job = GenerationJob(
        id=f"job-slim-{uid}",
        batch_id=batch.id,
        job_number=1,
        status="completed",
        target_count=5,
        actual_count=1,
    )
    await save_job(job)

    question = Question(
        id=f"q-slim-{uid}",
        batch_id=batch.id,
        job_id=job.id,
        section=sec,
        section_label="Critical Analysis and Reasoning Skills",
        subtopic="Humanities",
        difficulty="medium",
        question_stem="The author's primary argument focuses on which theme?",
        options=[
            OptionChoice(id="A", text="Epistemology"),
            OptionChoice(id="B", text="Aesthetics"),
            OptionChoice(id="C", text="Metaphysics"),
            OptionChoice(id="D", text="Ethics"),
        ],
        correct_answer_id="A",
        explanation="The passage analyzes epistemology.",
        final_score=95,
        status="in_bank",
        stage_outcomes={"heavy_audit_trace": "X" * 5000},
        iterations_history=[{"cycle": 1, "audit_trace": "Y" * 2000}],
    )
    await save_question(question)

    # 1. Default request should be slim (slim=True)
    res_default = await client.get(f"/api/batches/{batch.id}")
    assert res_default.status_code == 200
    data_default = res_default.json()
    assert data_default["batch"]["id"] == batch.id
    assert len(data_default["questions"]) == 1
    q_default = data_default["questions"][0]
    # Heavy diagnostic fields should be empty/omitted in slim mode
    assert not q_default.get("stage_outcomes")
    assert not q_default.get("iterations_history")
    # Core fields needed by batch cards are fully present
    assert q_default["id"] == question.id
    assert q_default["final_score"] == 95
    assert len(q_default["options"]) == 4

    # 2. Explicit slim=false should preserve diagnostic history
    res_full = await client.get(f"/api/batches/{batch.id}?slim=false")
    assert res_full.status_code == 200
    data_full = res_full.json()
    q_full = data_full["questions"][0]
    assert q_full.get("stage_outcomes") is not None
    assert "heavy_audit_trace" in q_full["stage_outcomes"]


async def test_passage_session_injection_and_mutations():
    """Verify that passage repository functions and question mutations accept an injected AsyncSession."""
    uid = uuid.uuid4().hex[:8]
    sec = f"cars_passage_{uid}"

    passage = Passage(
        id=f"passage-{uid}",
        section=sec,
        title="Philosophy of Science Passage",
        subtopic="Epistemology",
        text="Scientific realism asserts that the universe described by science is real.",
        word_count=10,
    )

    async with async_session_factory() as session:
        # 1. Save passage with injected session
        saved = await save_passage(passage, session=session)
        assert saved.id == passage.id

        # 2. Query passage by ID with injected session
        fetched = await get_passage_by_id(passage.id, session=session)
        assert fetched is not None
        assert fetched.title == passage.title

        # 3. List and count passages with injected session
        passages = await get_passages(section=sec, session=session)
        assert len(passages) >= 1
        assert passages[0].id == passage.id

        count = await count_passages(section=sec, session=session)
        assert count >= 1

        # 4. Save question linked to passage with injected session
        q = Question(
            id=f"q-pass-{uid}",
            passage_id=passage.id,
            section=sec,
            section_label="Critical Analysis and Reasoning Skills",
            subtopic="Epistemology",
            difficulty="medium",
            stimulus_text=passage.text,
            question_stem="What does scientific realism claim?",
            options=[
                OptionChoice(id="A", text="Science describes real world entities"),
                OptionChoice(id="B", text="Science is mere instrumental convention"),
                OptionChoice(id="C", text="Science cannot know truth"),
                OptionChoice(id="D", text="Science is subjective"),
            ],
            correct_answer_id="A",
            explanation="Scientific realism claims the entities described by theories are real.",
            final_score=90,
            status="in_bank",
        )
        saved_q = await save_question(q, session=session)
        assert saved_q.id == q.id

        # 5. Soft-delete passage with injected session
        del_success, _ = await delete_passage(passage.id, session=session)
        assert del_success is True

        # 6. Restore passage with injected session
        restored = await restore_passage(passage.id, session=session)
        assert restored is True
