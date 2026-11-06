"""Standalone /generate runs must always finalize their job and batch rows."""

import pytest
from app.repositories import get_batch_by_id, get_job_by_id
from app.schemas import GenerationRequest
from app.workflow import engine as engine_mod
from app.workflow import run_workflow_stream
from app.workflow.sse import iter_sse_events
from factories import make_request

pytestmark = pytest.mark.requires_db


def _req(n: int = 1) -> GenerationRequest:
    return make_request(questions_to_generate=n)


async def test_all_rejected_run_marks_job_failed_not_running(monkeypatch):
    async def always_reject(*_a, **_k):
        return False

    monkeypatch.setattr(engine_mod, "_run_question_review_loop", always_reject)

    job_id = batch_id = None
    last = {}
    async for evt in iter_sse_events(run_workflow_stream(_req())):
        job_id = job_id or (evt.get("data") or {}).get("job_id")
        batch_id = batch_id or (evt.get("data") or {}).get("batch_id")
        last = evt

    assert job_id
    job = await get_job_by_id(job_id)
    assert job.status == "failed"
    # Rejected attempts still cost real tokens; they must be reported and persisted
    assert last["event_type"] == "workflow_rejected"
    assert last["data"]["cumulative_usage"]["total_tokens"] > 0
    assert job.total_tokens == last["data"]["cumulative_usage"]["total_tokens"]


async def test_closing_on_workflow_complete_keeps_job_completed():
    job_id = batch_id = None
    stream = run_workflow_stream(_req())
    async for evt in iter_sse_events(stream):
        data = evt.get("data") or {}
        job_id = job_id or data.get("job_id")
        batch_id = batch_id or data.get("batch_id")
        if evt["event_type"] == "workflow_complete":
            break  # consumer stops reading on the terminal event
    await stream.aclose()

    job = await get_job_by_id(job_id)
    assert job.status == "completed", job.status
    assert job.total_tokens > 0
    assert (await get_batch_by_id(batch_id)).status == "completed"


async def test_standalone_run_leaves_no_in_flight_drafts_behind():
    from app.workflow import dedup_inflight

    async for _ in run_workflow_stream(_req(3)):
        pass
    assert dedup_inflight._IN_FLIGHT_BATCH_STEMS == {}
