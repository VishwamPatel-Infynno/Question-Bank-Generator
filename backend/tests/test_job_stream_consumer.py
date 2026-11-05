"""The shared stream reader and request builder behind job runs and refills."""

import json
import uuid

import pytest
from app.schemas import GenerationJob, GenerationRequest
from app.services import batch_worker as bw


def _evt(event_type, **data):
    return f"data: {json.dumps({'event_type': event_type, 'data': data})}\n\n"


async def _stream(*chunks):
    for chunk in chunks:
        yield chunk


def _raw_question():
    return {"id": str(uuid.uuid4())}


@pytest.fixture
def persist(monkeypatch):
    """Replaces persistence with a recorder; `abort_on` makes the n-th call report a vanished batch."""
    state = {"calls": [], "abort_on": None, "progress": []}

    async def fake_persist(batch_id, job_id, passage_id, raw_q, job_questions):
        state["calls"].append((batch_id, job_id, passage_id, raw_q))
        if state["abort_on"] == len(state["calls"]):
            return None, True
        q = type("Q", (), {"id": raw_q["id"]})()
        job_questions.append(q)
        return q, False

    async def fake_progress(job_id, **fields):
        state["progress"].append(fields)

    monkeypatch.setattr(bw, "_persist_job_question", fake_persist)
    monkeypatch.setattr(bw, "update_job_progress", fake_progress)
    return state


def _usage_totals():
    return bw._JobUsage(GenerationJob(batch_id="b", job_number=1))


async def _consume(stream, usage, existing=2, new=None):
    new = [] if new is None else new
    aborted = await bw._consume_job_stream(
        stream,
        batch_id="b",
        job_id="j",
        passage_id="p",
        existing_count=existing,
        new_questions=new,
        usage_totals=usage,
    )
    return aborted, new


async def test_generated_questions_are_persisted_and_progress_counts_existing_ones(persist):
    usage = _usage_totals()
    aborted, new = await _consume(
        _stream(
            "noise without data prefix",
            "data: {not json}\n\n",
            _evt("question_generated", question=_raw_question()),
            _evt("question_generated", question=_raw_question()),
        ),
        usage,
        existing=2,
    )
    assert aborted is False and len(new) == 2
    assert [p["actual_count"] for p in persist["progress"]] == [3, 4]
    assert all(call[:3] == ("b", "j", "p") for call in persist["calls"])


async def test_workflow_complete_persists_remaining_and_counts_usage(persist):
    usage = _usage_totals()
    _, new = await _consume(
        _stream(
            _evt(
                "workflow_complete",
                questions=[_raw_question()],
                cumulative_usage={"total_tokens": 9, "total_cost_usd": 0.5},
            )
        ),
        usage,
    )
    assert len(new) == 1
    assert usage.tokens == 9 and usage.cost == 0.5


async def test_a_vanished_batch_stops_the_reader(persist):
    persist["abort_on"] = 1
    usage = _usage_totals()
    aborted, new = await _consume(
        _stream(
            _evt("question_generated", question=_raw_question()),
            _evt("question_generated", question=_raw_question()),
        ),
        usage,
    )
    assert aborted is True and new == []
    assert len(persist["calls"]) == 1


async def test_rejected_run_counts_its_spend_without_failing(persist):
    usage = _usage_totals()
    aborted, _ = await _consume(
        _stream(_evt("workflow_rejected", cumulative_usage={"total_tokens": 7})), usage
    )
    assert aborted is False and usage.tokens == 7


async def test_error_event_raises_after_counting_spend(persist):
    usage = _usage_totals()
    with pytest.raises(RuntimeError, match="provider down"):
        await _consume(
            _stream(
                _evt("workflow_error", error="provider down", cumulative_usage={"total_tokens": 5})
            ),
            usage,
        )
    assert usage.tokens == 5


async def test_error_event_without_usage_still_raises(persist):
    with pytest.raises(RuntimeError, match="Unknown workflow error"):
        await _consume(_stream(_evt("workflow_error")), _usage_totals())


def test_attempt_request_carries_batch_job_and_passage_settings(monkeypatch):
    monkeypatch.setattr(bw.config, "BATCH_PASSING_SCORE_THRESHOLD", 85)
    job = GenerationJob(id="job-1", batch_id="batch-1", job_number=1)
    base = GenerationRequest(section="chem_phys", subtopic="Kinetics")
    req = bw._build_attempt_request(
        base,
        job=job,
        batch_id="batch-1",
        is_passage_mode=True,
        passage_id="p-1",
        thematic_angle="angle",
        questions_to_generate=3,
        shared_stimulus="Shared passage",
    )
    assert (req.run_id, req.batch_id, req.job_id) == ("job-1", "batch-1", "job-1")
    assert req.passing_threshold == 85 and req.questions_to_generate == 3
    assert (req.passage_mode, req.passage_required, req.passage_id) == (
        "single_passage",
        "Yes",
        "p-1",
    )
    assert req.thematic_angle == "angle" and req.shared_stimulus == "Shared passage"
    independent = bw._build_attempt_request(
        base,
        job=job,
        batch_id="batch-1",
        is_passage_mode=False,
        passage_id=None,
        thematic_angle="a",
        questions_to_generate=1,
        shared_stimulus=None,
    )
    assert (independent.passage_mode, independent.passage_required) == ("independent", "No")
    assert base.batch_id is None  # the base request is copied, never mutated
