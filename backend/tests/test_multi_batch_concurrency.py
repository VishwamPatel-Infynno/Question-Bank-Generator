import asyncio

import pytest
from app.agents.base import call_llm, get_global_llm_semaphore
from app.core.config import config
from app.db.session import init_db
from app.main import app
from app.repositories import (
    refresh_batch_aggregates,
    save_batch,
    save_jobs_bulk,
    update_job_progress,
)
from app.schemas import GenerationBatch, GenerationJob
from app.services import cancel_all_background_batches, get_global_job_semaphore
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.requires_db


@pytest.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    yield
    await cancel_all_background_batches()


@pytest.mark.asyncio
async def test_global_concurrency_semaphores():
    """Verifies that global job and LLM semaphores are bound to config limits."""
    job_sem = get_global_job_semaphore()
    assert isinstance(job_sem, asyncio.Semaphore)
    # Default is 4
    assert config.GLOBAL_MAX_CONCURRENT_JOBS == 4

    llm_sem = get_global_llm_semaphore()
    assert isinstance(llm_sem, asyncio.Semaphore)
    # Default is 10
    assert config.GLOBAL_MAX_CONCURRENT_LLM_CALLS == 10


@pytest.mark.asyncio
async def test_call_llm_rate_limit_backoff(monkeypatch):
    """Verifies that call_llm intercepts HTTP 429 rate limits and retries with backoff."""
    attempt_count = 0

    class MockUsage:
        prompt_tokens = 120
        completion_tokens = 80
        total_tokens = 200

    class MockChoice:
        class MockMessage:
            content = '{"test": "ok"}'

        message = MockMessage()

    class MockResponse:
        def __init__(self):
            self.choices = [MockChoice()]
            self.usage = MockUsage()

    async def mock_acompletion(**_kwargs):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            # Simulate a 429 Too Many Requests response on first attempt
            raise Exception("HTTP 429 Too Many Requests: Rate limit exceeded")
        return MockResponse()

    monkeypatch.setattr("litellm.acompletion", mock_acompletion)
    monkeypatch.setattr("app.agents.base._resolve_api_key", lambda _m, _k: "test-key")
    monkeypatch.setattr(config, "LLM_BASE_BACKOFF_SECONDS", 0.05)

    content, usage = await call_llm(
        prompt="Test prompt",
        system_prompt="Test system",
    )

    assert attempt_count == 2
    assert content == '{"test": "ok"}'
    assert usage.total_tokens == 200


@pytest.mark.asyncio
async def test_refresh_batch_aggregates_atomic():
    """
    Verifies that refresh_batch_aggregates recalculates batch stats directly
    from the generation_jobs table atomically, eliminating race conditions.
    """
    import uuid

    batch_id = str(uuid.uuid4())
    test_batch = GenerationBatch(
        id=batch_id,
        section="chem_phys",
        subtopic="Thermodynamics",
        difficulty="hard",
        passage_mode="single_passage",
        target_count=50,
        actual_count=0,
        total_jobs=10,
        completed_jobs=0,
        failed_jobs=0,
        status="in_progress",
        created_at="2026-10-26T12:00:00Z",
    )
    await save_batch(test_batch)

    # Create 10 job records
    jobs = []
    for i in range(1, 11):
        status = "completed" if i <= 7 else ("failed" if i == 8 else "pending")
        actual = 5 if i <= 7 else 0
        tokens = 1500 if i <= 7 else 0
        cost = 0.005 if i <= 7 else 0.0
        jobs.append(
            GenerationJob(
                id=str(uuid.uuid4()),
                batch_id=batch_id,
                job_number=i,
                status=status,
                target_count=5,
                actual_count=actual,
                total_tokens=tokens,
                cost_usd=cost,
                created_at="2026-10-26T12:00:00Z",
            )
        )
    await save_jobs_bulk(jobs)

    # Perform atomic aggregation
    refreshed = await refresh_batch_aggregates(batch_id)
    assert refreshed is not None
    assert refreshed.completed_jobs == 7
    assert refreshed.failed_jobs == 1
    assert refreshed.actual_count == 35  # 7 jobs * 5
    assert refreshed.total_tokens == 10500  # 7 * 1500
    assert abs(refreshed.cost_usd - 0.035) < 0.0001
    assert refreshed.status == "in_progress"

    # Now mark the remaining 2 pending jobs as completed
    for j in jobs[8:]:
        await update_job_progress(
            j.id, status="completed", actual_count=5, total_tokens=1500, cost_usd=0.005
        )

    refreshed_complete = await refresh_batch_aggregates(batch_id)
    assert refreshed_complete.completed_jobs == 9
    assert refreshed_complete.failed_jobs == 1
    assert refreshed_complete.actual_count == 45
    assert refreshed_complete.status == "partially_completed"


@pytest.mark.asyncio
async def test_simultaneous_multi_batch_launch_and_metrics(monkeypatch):
    """
    Simulates launching 4 batches simultaneously, verifying that the global pool
    tracks them cleanly without race conditions or resource collisions.
    """

    async def mock_execute(b_id, req, target_jobs=None):
        pass

    monkeypatch.setattr("app.services.batch_runner._execute_batch_workflow", mock_execute)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        batch_ids = []
        sections = ["chem_phys", "cars", "bio_biochem", "psych_soc"]

        # Launch 4 batches simultaneously
        for sec in sections:
            resp = await ac.post(
                "/api/batches/start",
                json={
                    "section": sec,
                    "subtopic": f"{sec} Concurrency Test",
                    "difficulty": "medium",
                    "questions_to_generate": 50,
                    "passage_mode": "single_passage",
                },
            )
            assert resp.status_code == 202
            data = resp.json()
            assert data["success"] is True
            batch_ids.append(data["batch"]["id"])

        assert len(batch_ids) == 4

        # Check list endpoint and concurrency metrics
        list_resp = await ac.get("/api/batches")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert "concurrency_metrics" in list_data
        metrics = list_data["concurrency_metrics"]
        assert metrics["global_max_concurrent_jobs"] == 4
        assert metrics["global_max_concurrent_llm_calls"] == 10
        assert list_data["active_running_batches"] >= 4

        # Verify stop endpoint for one batch
        target_b_id = batch_ids[0]
        stop_resp = await ac.post(f"/api/batches/{target_b_id}/stop")
        assert stop_resp.status_code == 200
        stop_data = stop_resp.json()
        assert stop_data["success"] is True

        # Verify retry endpoint
        retry_resp = await ac.post(f"/api/batches/{target_b_id}/retry")
        assert retry_resp.status_code == 200
        retry_data = retry_resp.json()
        assert retry_data["success"] is True

        # Verify cancel-all endpoint
        cancel_resp = await ac.post("/api/batches/cancel-all")
        assert cancel_resp.status_code == 200
        cancel_data = cancel_resp.json()
        assert cancel_data["success"] is True
        assert cancel_data["stopped_count"] >= 3
