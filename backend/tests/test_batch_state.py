"""Batch correctness: terminal resolution, stop/refill guards, cost accounting."""

import asyncio
import uuid
from types import SimpleNamespace

import pytest
from app.agents import base
from app.repositories import (
    get_batch_by_id,
    refresh_batch_aggregates,
    save_batch,
    save_job,
    update_job_progress,
)
from app.schemas import GenerationBatch, GenerationJob
from app.services import batch_concurrency
from app.services.batch_worker import _JobUsage
from factories import make_question

requires_db = pytest.mark.requires_db


async def _batch_with_job(job_status, job_actual=0, batch_status="in_progress", target=5):
    batch_id, job_id = str(uuid.uuid4()), str(uuid.uuid4())
    await save_batch(
        GenerationBatch(
            id=batch_id,
            section="chem_phys",
            subtopic="K",
            difficulty="medium",
            target_count=target,
            total_jobs=1,
            status=batch_status,
        )
    )
    await save_job(
        GenerationJob(
            id=job_id,
            batch_id=batch_id,
            job_number=1,
            status=job_status,
            target_count=target,
            actual_count=job_actual,
        )
    )
    return batch_id, job_id


@requires_db
@pytest.mark.parametrize(
    ("job_status", "actual", "expected"),
    [
        ("cancelled", 0, "cancelled"),
        ("cancelled", 2, "partially_completed"),
        ("failed", 0, "failed"),
    ],
)
async def test_idle_batch_is_resolved_to_a_terminal_status(job_status, actual, expected):
    batch_id, _ = await _batch_with_job(job_status, actual)
    batch = await refresh_batch_aggregates(batch_id, allow_complete=True)
    assert batch.status == expected


@requires_db
async def test_batch_with_a_running_job_is_never_finalized():
    batch_id, _ = await _batch_with_job("running", 1)
    batch = await refresh_batch_aggregates(batch_id, allow_complete=True)
    assert batch.status == "in_progress"


@requires_db
async def test_without_allow_complete_the_status_is_left_alone():
    batch_id, _ = await _batch_with_job("cancelled", 0)
    batch = await refresh_batch_aggregates(batch_id, allow_complete=False)
    assert batch.status == "in_progress"


@requires_db
async def test_stopping_a_finished_batch_does_not_rewrite_it():
    batch_id, _ = await _batch_with_job("completed", 5, batch_status="completed")
    assert await batch_concurrency.stop_background_batch(batch_id) is False
    assert (await get_batch_by_id(batch_id)).status == "completed"


@requires_db
async def test_stopping_an_unknown_batch_is_a_noop():
    assert await batch_concurrency.stop_background_batch(str(uuid.uuid4())) is False


@requires_db
async def test_stopping_a_stale_in_progress_batch_still_works():
    batch_id, job_id = await _batch_with_job("running", 0)
    assert await batch_concurrency.stop_background_batch(batch_id) is True
    assert (await get_batch_by_id(batch_id)).status == "cancelled"
    await update_job_progress(job_id, status="cancelled")


@requires_db
async def test_refill_is_refused_while_the_batch_is_running(client, monkeypatch):
    batch_id, _ = await _batch_with_job("running", 0)
    pending = asyncio.get_running_loop().create_future()
    monkeypatch.setitem(batch_concurrency._active_batch_tasks, batch_id, pending)
    res = await client.post(f"/api/batches/{batch_id}/refill")
    assert res.status_code == 409


def test_job_usage_accumulates_all_trials_and_starts_from_stored_totals():
    job = GenerationJob(batch_id="b", job_number=1, total_tokens=100, cost_usd=0.5)
    usage = _JobUsage(job)
    usage.add({"total_tokens": 10, "total_prompt_tokens": 6, "total_completion_tokens": 4})
    usage.add({"total_cost_usd": 0.25})
    usage.add(None)
    assert usage.fields() == {
        "total_tokens": 110,
        "prompt_tokens": 6,
        "completion_tokens": 4,
        "cost_usd": 0.75,
    }


async def test_truncated_retry_usage_is_billed_in_the_final_result(monkeypatch):
    def resp(content, finish):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)
            ],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

    calls = []

    async def fake_completion(**kwargs):
        calls.append(1)
        return resp("cut", "length") if len(calls) == 1 else resp('{"ok": 1}', "stop")

    monkeypatch.setattr(base.litellm, "acompletion", fake_completion)
    _, usage = await base.call_llm(
        "hi", "sys", model="deepinfra/some-model", api_key="k", max_tokens=1000
    )
    assert usage.calls == 2
    assert usage.total_tokens == 30
    assert usage.prompt_tokens == 20


async def test_db_init_retries_until_the_database_is_available(monkeypatch):
    import app.main as main_mod

    attempts = []

    async def fake_init():
        attempts.append(1)
        return len(attempts) >= 3

    ran = []

    async def fake_maintenance():
        ran.append(True)

    monkeypatch.setattr(main_mod, "init_db", fake_init)
    monkeypatch.setattr(main_mod, "_post_init_maintenance", fake_maintenance)
    await main_mod._retry_db_init(first_delay=0.01, max_delay=0.02)
    assert len(attempts) == 3
    assert ran == [True]


def _passage_question(passage_id, status="in_bank"):
    return make_question(passage_id=passage_id, status=status)


@requires_db
async def test_restoring_a_passage_restores_only_questions_deleted_with_it():
    from app.repositories import (
        delete_passage,
        delete_question,
        get_question_by_id,
        restore_passage,
        save_passage,
        save_question,
    )
    from app.schemas import Passage

    passage = await save_passage(Passage(text="A passage about enzymes " * 5, section="CPBS"))
    together = await save_question(_passage_question(passage.id))
    earlier = await save_question(_passage_question(passage.id))
    assert await delete_question(earlier.id)  # deleted on its own, before the passage
    await delete_passage(passage.id)
    assert await restore_passage(passage.id)
    assert await get_question_by_id(together.id) is not None
    assert await get_question_by_id(earlier.id) is None


@requires_db
async def test_duplicate_override_keeps_batch_only_questions_out_of_the_bank():
    from app.repositories import override_question_duplicate, save_question

    held = await save_question(_passage_question(None, status="batch_only"))
    free = await save_question(_passage_question(None, status="ai_validated"))
    assert (await override_question_duplicate(held.id)).status == "batch_only"
    assert (await override_question_duplicate(free.id)).status == "in_bank"


@requires_db
async def test_deleting_an_unknown_question_is_a_404(client):
    res = await client.delete(f"/api/questions/{uuid.uuid4()}")
    assert res.status_code == 404
