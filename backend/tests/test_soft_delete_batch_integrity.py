import uuid

import pytest
from app.main import app
from app.repositories import (
    delete_passage,
    delete_question,
    get_passages,
    get_questions,
    save_batch,
    save_job,
    save_passage,
    save_question,
)
from app.schemas import (
    GenerationBatch,
    GenerationJob,
    OptionChoice,
    Passage,
    Question,
)
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


async def test_soft_delete_passage_and_batch_integrity():

    batch_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    passage_id = str(uuid.uuid4())
    q_id = str(uuid.uuid4())

    # 1. Create Batch & Job
    batch = GenerationBatch(
        id=batch_id,
        section="biological_biochemical",
        subtopic="Enzyme Kinetics",
        difficulty="medium",
        target_count=5,
        actual_count=1,
    )
    await save_batch(batch)

    job = GenerationJob(
        id=job_id,
        batch_id=batch_id,
        job_number=1,
        status="completed",
        target_count=5,
        actual_count=1,
        passage_id=passage_id,
    )
    await save_job(job)

    # 2. Create Passage
    passage = Passage(
        id=passage_id,
        title="Enzyme Kinetics Passage",
        text="This is an experimental passage examining Michaelis-Menten kinetics.",
        section="biological_biochemical",
        subtopic="Enzyme Kinetics",
    )
    await save_passage(passage)

    # 3. Create Question linked to batch, job, and passage
    opts = [
        OptionChoice(id="A", text="Option A"),
        OptionChoice(id="B", text="Option B"),
        OptionChoice(id="C", text="Option C"),
        OptionChoice(id="D", text="Option D"),
    ]
    question = Question(
        id=q_id,
        batch_id=batch_id,
        job_id=job_id,
        passage_id=passage_id,
        section="biological_biochemical",
        section_label="Biological and Biochemical Foundations of Living Systems",
        subtopic="Enzyme Kinetics",
        difficulty="medium",
        stimulus_text=passage.text,
        question_stem="What is the Km of the reaction?",
        options=opts,
        correct_answer_id="B",
        explanation="Km is the substrate concentration at half-Vmax.",
        final_score=94,
        status="in_bank",
    )
    await save_question(question)

    # Verify initially present
    active_passages = await get_passages(search="Enzyme Kinetics Passage")
    assert any(p.id == passage_id for p in active_passages)
    active_questions = await get_questions(section="biological_biochemical", status="in_bank")
    assert any(q.id == q_id for q in active_questions)

    # 4. Soft-delete the passage
    deleted, count = await delete_passage(passage_id)
    assert deleted is True
    assert count >= 1

    # Passage should NOT appear in get_passages (Passage Bank)
    post_delete_passages = await get_passages(search="Enzyme Kinetics Passage")
    assert not any(p.id == passage_id for p in post_delete_passages)

    # Question should NOT appear in active Question Bank queries
    post_delete_questions = await get_questions(section="biological_biochemical", status="in_bank")
    assert not any(q.id == q_id for q in post_delete_questions)

    # CRITICAL TEST: Batch Progress endpoint GET /batches/{batch_id} must have question and stimulus INTACT!
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/batches/{batch_id}")
        assert res.status_code == 200
        batch_data = res.json()
        assert len(batch_data["questions"]) == 1
        q_in_batch = batch_data["questions"][0]
        assert q_in_batch["id"] == q_id
        assert q_in_batch["is_deleted"] is True
        assert (
            q_in_batch["stimulus_text"]
            == "This is an experimental passage examining Michaelis-Menten kinetics."
        )
        assert len(batch_data["jobs"]) == 1
        job_questions = batch_data["jobs"][0]["questions"]
        assert len(job_questions) == 1
        assert job_questions[0]["id"] == q_id


async def test_soft_delete_question_and_restore():

    batch_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    q_id = str(uuid.uuid4())

    batch = GenerationBatch(
        id=batch_id,
        section="chemical_physical",
        subtopic="Thermodynamics",
        target_count=5,
        actual_count=1,
    )
    await save_batch(batch)

    job = GenerationJob(
        id=job_id,
        batch_id=batch_id,
        job_number=1,
        status="completed",
        target_count=5,
        actual_count=1,
    )
    await save_job(job)

    opts = [
        OptionChoice(id="A", text="Endothermic"),
        OptionChoice(id="B", text="Exothermic"),
        OptionChoice(id="C", text="Isothermal"),
        OptionChoice(id="D", text="Isochoric"),
    ]
    question = Question(
        id=q_id,
        batch_id=batch_id,
        job_id=job_id,
        section="chemical_physical",
        section_label="Chemical and Physical Foundations of Biological Systems",
        subtopic="Thermodynamics",
        difficulty="hard",
        question_stem="Which process releases heat to the surroundings?",
        options=opts,
        correct_answer_id="B",
        explanation="Exothermic processes release heat (negative delta H).",
        final_score=92,
        status="in_bank",
    )
    await save_question(question)

    # 1. Soft-delete question via delete_question
    del_res = await delete_question(q_id)
    assert del_res is True

    # Active query should NOT return the deleted question
    active_qs = await get_questions(section="chemical_physical", status="in_bank")
    assert not any(q.id == q_id for q in active_qs)

    # But Batch Detail MUST retain the question
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/batches/{batch_id}")
        assert res.status_code == 200
        batch_data = res.json()
        assert len(batch_data["questions"]) == 1
        assert batch_data["questions"][0]["is_deleted"] is True

        # 2. Restore question via REST API
        restore_res = await ac.post(f"/api/questions/{q_id}/restore")
        assert restore_res.status_code == 200
        assert restore_res.json()["success"] is True

    # Question should now be active again in Question Bank
    reactivated_qs = await get_questions(section="chemical_physical", status="in_bank")
    assert any(q.id == q_id for q in reactivated_qs)
