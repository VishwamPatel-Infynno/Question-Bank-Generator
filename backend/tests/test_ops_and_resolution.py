"""Request ids, body limits, error sanitising, liveness, batch resolution helpers."""

import uuid

import pytest
from app.core.config import config
from app.core.errors import sanitize_error_text
from app.schemas import GenerationJob
from app.services.batch_resolution import (
    compute_jobs_with_deficits,
    identify_batch_buffer_excess,
    partition_questions_by_job,
)
from factories import make_question


def _q(job_id, score, qid=None):
    return make_question(
        id=qid or str(uuid.uuid4()), job_id=job_id, final_score=score, subtopic="K"
    )


@pytest.mark.asyncio
async def test_liveness_never_touches_the_database(client, monkeypatch):
    import app.api.v1.health as health

    async def boom():
        raise AssertionError("liveness must not query the database")

    monkeypatch.setattr(health, "check_db_health", boom)
    res = await client.get("/api/health/live")
    assert res.status_code == 200
    assert res.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_request_id_is_generated_and_echoed(client):
    generated = (await client.get("/api/health/live")).headers["x-request-id"]
    assert len(generated) == 16
    echoed = await client.get("/api/health/live", headers={"x-request-id": "trace-abc.123"})
    assert echoed.headers["x-request-id"] == "trace-abc.123"
    unsafe = await client.get("/api/health/live", headers={"x-request-id": "bad id\twith space"})
    assert unsafe.headers["x-request-id"] != "bad id\twith space"


@pytest.mark.asyncio
async def test_oversized_bodies_are_rejected_before_any_work(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_REQUEST_BODY_MB", 1)
    res = await client.post("/api/questions/check-duplicate", content=b"x" * (1024 * 1024 + 1))
    assert res.status_code == 413
    assert res.json()["code"] == "payload_too_large"
    assert "x-request-id" in res.headers


@pytest.mark.asyncio
async def test_body_limit_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_REQUEST_BODY_MB", 0)
    res = await client.post("/api/questions/check-duplicate", content=b"x" * 2048)
    assert res.status_code == 422  # reached validation, not the size guard


@pytest.mark.asyncio
async def test_bulk_id_lists_are_bounded(client):
    res = await client.post("/api/questions/delete-batch", json={"ids": ["x"] * 1001})
    assert res.status_code == 422


def test_error_text_is_stripped_of_secrets_urls_and_length():
    raw = (
        "Call failed: https://api.example.com/v1/x?api_key=SECRET123&user=7 "
        "Authorization: Bearer abcdef123456789 key sk-abcdefghijklmnop api_key=hunter2\n"
        + "x"
        * 500
    )
    clean = sanitize_error_text(raw)
    assert "SECRET123" not in clean and "abcdef123456789" not in clean
    assert "sk-abcdefghijklmnop" not in clean and "hunter2" not in clean
    assert "https://api.example.com/v1/x" in clean and "?" not in clean
    assert "\n" not in clean and len(clean) <= 300


def test_buffer_excess_returns_the_lowest_scores_only():
    qs = [_q("j", s, qid=f"q{s}") for s in (99, 95, 91, 88)]
    assert identify_batch_buffer_excess(qs, 4) == []
    assert identify_batch_buffer_excess(qs, 2) == ["q91", "q88"]


def test_jobs_with_deficits_and_fallback_allocation():
    done = GenerationJob(id="a", batch_id="b", job_number=1, target_count=2, status="completed")
    short = GenerationJob(id="b", batch_id="b", job_number=2, target_count=3, status="running")
    by_job = {"a": [_q("a", 95), _q("a", 95)], "b": [_q("b", 95)]}
    assert [(j.id, d) for j, d in compute_jobs_with_deficits([short, done], by_job)] == [("b", 2)]
    full = {"a": by_job["a"], "b": [_q("b", 95)] * 3}
    assert compute_jobs_with_deficits([done, short], full) == []
    # nothing short but a deficit remains: the first unfinished job absorbs it
    fallback = compute_jobs_with_deficits([done, short], full, total_deficit=5)
    assert [(j.id, d) for j, d in fallback] == [("b", 3)]


def test_questions_are_grouped_by_job_then_run():
    a, b = _q("j1", 95), _q(None, 95)
    b.run_id = "r1"
    groups = partition_questions_by_job([a, b, _q(None, 95)])
    assert set(groups) == {"j1", "r1"}
