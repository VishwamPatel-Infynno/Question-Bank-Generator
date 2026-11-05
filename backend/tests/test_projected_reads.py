"""Lightweight repository reads used by the batch worker."""

import uuid

import pytest
from app.repositories import (
    batch_exists,
    get_active_job_question_heads,
    save_batch,
    save_job,
    save_question,
)
from app.schemas import GenerationBatch, GenerationJob
from factories import make_question

pytestmark = pytest.mark.requires_db


def _question(batch_id, job_id, status, stimulus="Passage text"):
    return make_question(
        batch_id=batch_id,
        job_id=job_id,
        run_id=job_id,
        status=status,
        stimulus_text=stimulus,
        options=[{"id": "A", "text": "opt A"}, {"id": "B", "text": "opt B"}],
    )


@pytest.mark.asyncio
async def test_heads_return_only_active_questions_with_the_columns_the_worker_needs():
    batch_id, job_id = str(uuid.uuid4()), str(uuid.uuid4())
    await save_batch(
        GenerationBatch(
            id=batch_id, section="chem_phys", subtopic="K", difficulty="medium", target_count=5
        )
    )
    await save_job(
        GenerationJob(id=job_id, batch_id=batch_id, job_number=1, status="running", target_count=5)
    )
    kept = _question(batch_id, job_id, "batch_only", stimulus="First passage")
    await save_question(kept)
    await save_question(_question(batch_id, job_id, "discarded"))
    await save_question(_question(batch_id, job_id, "below_threshold"))

    heads = await get_active_job_question_heads(batch_id, job_id)
    assert [h.id for h in heads] == [kept.id]
    assert heads[0].stimulus_text == "First passage" and heads[0].status == "batch_only"


@pytest.mark.asyncio
async def test_batch_exists_is_a_cheap_boolean_check():
    batch_id = str(uuid.uuid4())
    assert await batch_exists(batch_id) is False
    await save_batch(
        GenerationBatch(
            id=batch_id, section="chem_phys", subtopic="K", difficulty="medium", target_count=5
        )
    )
    assert await batch_exists(batch_id) is True


@pytest.mark.asyncio
async def test_slim_reads_do_not_touch_the_deferred_json_blobs():
    from app.repositories import get_questions

    batch_id, job_id = str(uuid.uuid4()), str(uuid.uuid4())
    await save_batch(
        GenerationBatch(
            id=batch_id, section="chem_phys", subtopic="K", difficulty="medium", target_count=5
        )
    )
    await save_job(
        GenerationJob(id=job_id, batch_id=batch_id, job_number=1, status="running", target_count=5)
    )
    q = _question(batch_id, job_id, "batch_only")
    q.stage_outcomes = {"drafting": {"x": 1}}
    await save_question(q)

    slim = await get_questions(batch_id=batch_id, slim=True)
    full = await get_questions(batch_id=batch_id)
    assert slim[0].stage_outcomes == {} and slim[0].iterations_history == []
    assert full[0].stage_outcomes == {"drafting": {"x": 1}}


@pytest.mark.asyncio
async def test_save_questions_batch_select_count_does_not_grow_with_the_batch():
    from app.db.session import engine
    from app.repositories import get_question_by_id, save_questions_batch
    from sqlalchemy import event

    batch_id, job_id = str(uuid.uuid4()), str(uuid.uuid4())
    await save_batch(
        GenerationBatch(
            id=batch_id, section="chem_phys", subtopic="K", difficulty="medium", target_count=5
        )
    )
    await save_job(
        GenerationJob(id=job_id, batch_id=batch_id, job_number=1, status="running", target_count=5)
    )

    async def selects_for(questions) -> int:
        seen: list[str] = []

        def count(conn, cursor, statement, params, context, executemany):
            if statement.lstrip().upper().startswith("SELECT") and "FROM questions" in statement:
                seen.append(statement)

        event.listen(engine.sync_engine, "before_cursor_execute", count)
        try:
            await save_questions_batch(questions)
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", count)
        return len(seen)

    small = await selects_for([_question(batch_id, job_id, "batch_only")])
    existing = _question(batch_id, job_id, "batch_only")
    await save_question(existing)
    existing.explanation = "Updated explanation"
    fresh = [_question(batch_id, job_id, "batch_only") for _ in range(9)]
    large = await selects_for([existing, *fresh])

    assert large == small, f"SELECTs grew with batch size: {small} -> {large}"
    assert (await get_question_by_id(existing.id)).explanation == "Updated explanation"
    for q in fresh:
        assert await get_question_by_id(q.id) is not None
