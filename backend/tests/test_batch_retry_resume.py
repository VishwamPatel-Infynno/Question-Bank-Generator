"""Retry/resume must run the jobs it selected, and stuck jobs must never hang."""

from unittest.mock import AsyncMock

from app.schemas import GenerationJob, GenerationRequest
from app.services import batch_runner


def _job(status: str, actual: int = 2) -> GenerationJob:
    return GenerationJob(
        id=f"job-{status}",
        batch_id="b1",
        job_number=1,
        status=status,
        target_count=5,
        actual_count=actual,
    )


async def test_explicit_target_jobs_run_even_when_their_in_memory_status_is_stale(monkeypatch):
    ran: list[str] = []

    async def fake_run(batch_id, job, req, sem):
        ran.append(job.id)

    monkeypatch.setattr(batch_runner, "_run_single_job", fake_run)
    monkeypatch.setattr(batch_runner, "_fail_stuck_jobs", AsyncMock())
    monkeypatch.setattr(batch_runner, "refresh_batch_aggregates", AsyncMock(return_value=None))
    monkeypatch.setattr(
        batch_runner,
        "auto_resolve_batch_and_refill",
        AsyncMock(return_value={"refill_launched": True}),
    )

    # 'completed' with 2/5 questions is what a short job looks like; retry chose it on purpose
    short = _job("completed")
    req = GenerationRequest(section="CP", subtopic="Kinetics", difficulty="Medium")
    await batch_runner._execute_batch_workflow("b1", req, target_jobs=[short])
    assert ran == ["job-completed"]


async def test_stopped_jobs_are_executable_on_a_normal_run(monkeypatch):
    ran: list[str] = []

    async def fake_run(batch_id, job, req, sem):
        ran.append(job.id)

    monkeypatch.setattr(batch_runner, "_run_single_job", fake_run)
    monkeypatch.setattr(batch_runner, "_fail_stuck_jobs", AsyncMock())
    monkeypatch.setattr(
        batch_runner,
        "get_jobs_by_batch_id",
        AsyncMock(return_value=[_job("stopped"), _job("completed", actual=5)]),
    )
    monkeypatch.setattr(batch_runner, "refresh_batch_aggregates", AsyncMock(return_value=None))
    monkeypatch.setattr(
        batch_runner,
        "auto_resolve_batch_and_refill",
        AsyncMock(return_value={"refill_launched": True}),
    )
    req = GenerationRequest(section="CP", subtopic="Kinetics", difficulty="Medium")
    await batch_runner._execute_batch_workflow("b1", req)
    assert ran == ["job-stopped"]


async def test_jobs_left_running_by_a_finished_runner_are_failed(monkeypatch):
    updates: list[tuple] = []

    async def fake_update(job_id, **kwargs):
        updates.append((job_id, kwargs["status"]))

    monkeypatch.setattr(
        batch_runner,
        "get_jobs_by_batch_id",
        AsyncMock(return_value=[_job("running"), _job("completed")]),
    )
    monkeypatch.setattr(batch_runner, "update_job_progress", fake_update)
    await batch_runner._fail_stuck_jobs("b1", ["job-running", "job-completed"])
    assert updates == [("job-running", "failed")]
