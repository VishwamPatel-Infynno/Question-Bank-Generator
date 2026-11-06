"""
batch_runner.py - Background batch orchestration for multi-job MCAT question generation.

Manages the lifecycle of background asyncio tasks that run multiple GenerationJobs
within a GenerationBatch. Governs job scheduling, retry logic, deficit refill,
deduplication resolution, and clean cancellation across modular helper services.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.config import config
from app.core.errors import sanitize_error_text
from app.repositories import (
    batch_update_question_status,
    get_batch_by_id,
    get_jobs_by_batch_id,
    get_questions,
    hard_delete_questions_batch,
    refresh_batch_aggregates,
    save_batch,
    save_jobs_bulk,
    update_job_progress,
)
from app.schemas import (
    EXECUTABLE_JOB_STATES,
    LIVE_STATES,
    RETRYABLE_JOB_STATES,
    BatchStatus,
    GenerationBatch,
    GenerationJob,
    GenerationRequest,
    JobStatus,
    is_question_active,
)
from app.services.batch_concurrency import (
    cancel_background_batch,
    get_global_job_semaphore,
    get_stored_batch_request,
    register_batch_task,
    store_batch_request,
    unregister_batch_task,
)
from app.services.batch_resolution import (
    compute_jobs_with_deficits,
    find_cluster_duplicates,
    identify_batch_buffer_excess,
    partition_questions_by_job,
)
from app.services.batch_worker import (
    MAX_JOB_TRIALS,
    MAX_REFILL_CYCLES,
    QUESTIONS_PER_JOB,
    _run_single_job,
    _run_single_job_refill,
)

logger = logging.getLogger(__name__)

__all__ = [
    "QUESTIONS_PER_JOB",
    "_execute_batch_workflow",
    "_execute_in_set_refill",
    "_run_single_job",
    "_run_single_job_refill",
    "auto_resolve_batch_and_refill",
    "launch_background_batch",
    "refill_batch_deficit",
    "retry_incomplete_jobs_for_batch",
]


async def _execute_in_set_refill(
    batch_id: str,
    req: GenerationRequest,
    jobs_to_refill: list[tuple[GenerationJob, int]],
    current_cycle: int = 2,
    max_cycles: int = MAX_REFILL_CYCLES,
) -> None:
    """Coordinates execution of in-set replenishment without creating new jobs."""
    tasks: list[asyncio.Task[Any]] = []
    try:
        semaphore = get_global_job_semaphore()
        tasks = [
            asyncio.create_task(_run_single_job_refill(batch_id, job, job_deficit, req, semaphore))
            for job, job_deficit in jobs_to_refill
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        await refresh_batch_aggregates(batch_id, allow_complete=False)

        # Autonomous duplicate resolution and refill on next cycle if needed
        refill_result = await auto_resolve_batch_and_refill(
            batch_id, current_cycle=current_cycle, max_cycles=max_cycles
        )
        if not refill_result.get("refill_launched"):
            await refresh_batch_aggregates(batch_id, allow_complete=True)
    except asyncio.CancelledError:
        logger.info("In-set refill for batch %s was cancelled.", batch_id)
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await refresh_batch_aggregates(batch_id)
        raise
    except Exception as e:
        logger.error("Error during in-set refill for batch %s: %s", batch_id, e, exc_info=True)
        b = await get_batch_by_id(batch_id)
        if b:
            b.status = BatchStatus.FAILED
            b.error_message = sanitize_error_text(e)
            await save_batch(b)
    finally:
        unregister_batch_task(batch_id, asyncio.current_task())


async def _fail_stuck_jobs(batch_id: str, job_ids: list[str]) -> None:
    """Marks jobs that a finished runner left pending/running as failed so they never hang."""
    wanted = set(job_ids)
    now_iso = datetime.now(UTC).isoformat()
    for job in await get_jobs_by_batch_id(batch_id):
        if job.id in wanted and job.status in LIVE_STATES:
            logger.warning("Job %s ended without a terminal status; marking it failed.", job.id)
            await update_job_progress(
                job.id,
                status=JobStatus.FAILED,
                error_message=job.error_message or "Job ended unexpectedly.",
                completed_at=now_iso,
            )


async def _execute_batch_workflow(
    batch_id: str,
    req: GenerationRequest,
    target_jobs: list[GenerationJob] | None = None,
    current_cycle: int = 1,
    max_cycles: int = MAX_REFILL_CYCLES,
) -> None:
    """Coordinates the execution of jobs within a batch using the global worker semaphore."""
    tasks: list[asyncio.Task[Any]] = []
    try:
        jobs = target_jobs or await get_jobs_by_batch_id(batch_id)
        if not jobs:
            logger.error("No jobs found for batch %s", batch_id)
            failed = await get_batch_by_id(batch_id)
            if failed and failed.status in LIVE_STATES:
                failed.status = BatchStatus.FAILED
                failed.error_message = "Batch has no jobs to run."
                await save_batch(failed)
            return

        # An explicit target list (retry/resume) was already filtered by the caller against fresh
        # database state, so trust it: its in-memory statuses are stale by now. Otherwise pick the
        # jobs that still need work.
        executable_jobs = (
            list(target_jobs)
            if target_jobs
            else [j for j in jobs if j.status in EXECUTABLE_JOB_STATES]
        )
        if not executable_jobs:
            logger.info("Batch %s has no pending jobs to execute.", batch_id)
            await refresh_batch_aggregates(batch_id)
            return

        # Acquire slots from the shared global worker pool
        semaphore = get_global_job_semaphore()
        tasks = [
            asyncio.create_task(_run_single_job(batch_id, job, req, semaphore))
            for job in executable_jobs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for job, res in zip(executable_jobs, results, strict=True):
            if isinstance(res, BaseException):
                logger.error("Job %s of batch %s crashed: %r", job.id, batch_id, res, exc_info=res)
        await _fail_stuck_jobs(batch_id, [j.id for j in executable_jobs])

        # Finalize batch state atomically without premature completion
        updated_batch = await refresh_batch_aggregates(batch_id, allow_complete=False)
        if updated_batch:
            logger.info(
                "Batch %s finished execution. Status: %s (%s/%s jobs, %s/%s questions).",
                batch_id,
                updated_batch.status,
                updated_batch.completed_jobs,
                updated_batch.total_jobs,
                updated_batch.actual_count,
                updated_batch.target_count,
            )

        # Autonomous duplicate resolution and refill
        refill_result = await auto_resolve_batch_and_refill(
            batch_id, current_cycle=current_cycle, max_cycles=max_cycles
        )
        if not refill_result.get("refill_launched"):
            # Batch has fully concluded all processing, deduplication, and refilling
            await refresh_batch_aggregates(batch_id, allow_complete=True)

    except asyncio.CancelledError:
        logger.info("Batch %s execution was cancelled; terminating all sub-tasks...", batch_id)
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await refresh_batch_aggregates(batch_id)
        raise
    except Exception as e:
        logger.error("Fatal error in batch %s execution: %s", batch_id, e, exc_info=True)
        b = await get_batch_by_id(batch_id)
        if b:
            b.status = BatchStatus.FAILED
            b.error_message = sanitize_error_text(e)
            await save_batch(b)
    finally:
        unregister_batch_task(batch_id, asyncio.current_task())


async def auto_resolve_batch_and_refill(
    batch_id: str,
    current_cycle: int = 1,
    max_cycles: int = MAX_REFILL_CYCLES,
    threshold: float | None = None,
) -> dict[str, Any]:
    """
    Evaluates active questions in a batch for duplicate clusters, permanently deletes
    redundant duplicates in favor of the highest-scoring question in each cluster,
    and automatically triggers in-set replenishment within affected sets if a deficit exists,
    capped at max_cycles (up to 3 cycles). Also trims excess questions within sets to exact target.
    """
    threshold = config.DUPLICATE_HARD_THRESHOLD if threshold is None else threshold
    b = await get_batch_by_id(batch_id)
    if not b:
        return {"resolved": False, "reason": "Batch not found"}

    linked_questions = await get_questions(batch_id=batch_id)
    active_questions = [q for q in linked_questions if is_question_active(q.status)]

    clusters, duplicate_ids_to_purge = find_cluster_duplicates(
        active_questions, threshold=threshold
    )

    if duplicate_ids_to_purge:
        await hard_delete_questions_batch(duplicate_ids_to_purge)
        logger.info(
            "Auto-resolved %s duplicate cluster(s) in batch %s; permanently deleted %s duplicate question(s).",
            len(clusters),
            batch_id,
            len(duplicate_ids_to_purge),
        )

    # Enforce exact target count per existing job (trim excess questions within each set)
    existing_jobs = await get_jobs_by_batch_id(batch_id)
    existing_jobs.sort(key=lambda j: j.job_number)
    all_refreshed_qs = await get_questions(batch_id=batch_id)
    active_refreshed_qs = [q for q in all_refreshed_qs if is_question_active(q.status)]

    qs_by_job = partition_questions_by_job(active_refreshed_qs)

    for job in existing_jobs:
        job_qs = qs_by_job.get(job.id, [])
        if len(job_qs) > job.target_count:
            job_qs.sort(key=lambda q: q.final_score or 0, reverse=True)
            excess_to_delete = [q.id for q in job_qs[job.target_count :]]
            if excess_to_delete:
                await hard_delete_questions_batch(excess_to_delete)
                logger.info(
                    "Trimmed Set #%s (Job %s) to target count %s: permanently deleted %s excess question(s).",
                    job.job_number,
                    job.id,
                    job.target_count,
                    len(excess_to_delete),
                )
            await update_job_progress(job.id, actual_count=job.target_count)

    await refresh_batch_aggregates(batch_id, allow_complete=False)
    refreshed_b = await get_batch_by_id(batch_id)
    refreshed_questions = await get_questions(batch_id=batch_id)
    valid_active = [q for q in refreshed_questions if is_question_active(q.status)]
    remaining_active = len(valid_active)
    target = refreshed_b.target_count if refreshed_b else 50
    deficit = max(0, target - remaining_active)

    refill_launched = False
    if deficit > 0 and current_cycle < max_cycles:
        buffer = 1 if deficit < QUESTIONS_PER_JOB else 2
        refill_target = min(target, deficit + buffer)
        logger.info(
            "Auto-refill triggered for batch %s: deficit=%s, refill_target=%s (buffer=%s), cycle=%s/%s",
            batch_id,
            deficit,
            refill_target,
            buffer,
            current_cycle + 1,
            max_cycles,
        )
        _, refill_jobs = await refill_batch_deficit(
            batch_id, refill_target, cycle=current_cycle + 1, max_cycles=max_cycles
        )
        # No job to refill means nothing was launched; the caller must then finalize the batch.
        refill_launched = bool(refill_jobs)
    elif remaining_active > target:
        excess_buffer_ids = identify_batch_buffer_excess(valid_active, target)
        if excess_buffer_ids:
            await batch_update_question_status(excess_buffer_ids, status="discarded")
            logger.info(
                "Capped batch %s to exact target %s: archived %s excess buffer question(s).",
                batch_id,
                target,
                len(excess_buffer_ids),
            )
        await refresh_batch_aggregates(batch_id, allow_complete=False)
        remaining_active = target
        deficit = 0

    return {
        "resolved": True,
        "clusters_count": len(clusters),
        "archived_duplicates_count": len(duplicate_ids_to_purge),
        "remaining_active": remaining_active,
        "deficit": deficit,
        "refill_launched": refill_launched,
        "current_cycle": current_cycle,
    }


def _resolve_effective_request(
    batch: GenerationBatch, req: GenerationRequest | None = None
) -> GenerationRequest:
    """Request used to (re)launch a batch: explicit, then cached, then stored payload, then a default.

    The stored payload never contains the client's ``api_key`` (it is scrubbed), so a relaunch
    without an in-memory request falls back to the server-configured credentials.
    """
    effective = req or get_stored_batch_request(batch.id)
    if not effective and batch.request_payload:
        try:
            effective = GenerationRequest(**batch.request_payload)
        except Exception as err:
            logger.warning("Could not deserialize stored batch request_payload: %s", err)
    if not effective:
        effective = GenerationRequest(
            section=batch.section or "chem_phys",
            difficulty=batch.difficulty or "medium",
            subtopic=batch.subtopic,
            passage_mode=batch.passage_mode,
            questions_to_generate=5,
        )
    return effective


async def retry_incomplete_jobs_for_batch(
    batch_id: str,
    req: GenerationRequest | None = None,
) -> tuple[GenerationBatch | None, list[GenerationJob]]:
    """Re-launches failed or cancelled jobs for a batch into the global worker pool."""
    b = await get_batch_by_id(batch_id)
    if not b:
        return None, []

    # Stop any currently active task for this batch first
    await cancel_background_batch(batch_id)

    jobs = await get_jobs_by_batch_id(batch_id)
    # Strictly enforce the trial ceiling: only jobs with trial_count < MAX_JOB_TRIALS are eligible for retry/resume
    retryable_jobs = [
        j
        for j in jobs
        if (j.trial_count or 1) < MAX_JOB_TRIALS
        and (
            j.status in RETRYABLE_JOB_STATES
            or (j.actual_count < (j.target_count or QUESTIONS_PER_JOB))
        )
    ]
    if not retryable_jobs:
        return b, []

    # Reset retryable jobs to pending while preserving their current trial count
    for j in retryable_jobs:
        await update_job_progress(
            j.id,
            status=JobStatus.PENDING,
            clear=("error_message", "started_at", "completed_at"),
        )

    b.status = BatchStatus.IN_PROGRESS
    b.error_message = None
    await save_batch(b)

    effective_req = _resolve_effective_request(b, req)

    task = asyncio.create_task(_execute_batch_workflow(batch_id, effective_req, retryable_jobs))
    register_batch_task(batch_id, task)

    refreshed_batch = await get_batch_by_id(batch_id)
    all_jobs = await get_jobs_by_batch_id(batch_id)
    return refreshed_batch, all_jobs


async def refill_batch_deficit(
    batch_id: str,
    deficit: int,
    cycle: int = 2,
    max_cycles: int = MAX_REFILL_CYCLES,
) -> tuple[GenerationBatch | None, list[GenerationJob]]:
    """
    Replenishes questions in-place for existing jobs that have deficits,
    preserving exact job/set counts without creating extra sets.
    """
    b = await get_batch_by_id(batch_id)
    if not b or deficit <= 0:
        return b, []

    existing_jobs = await get_jobs_by_batch_id(batch_id)
    if not existing_jobs:
        return b, []

    existing_jobs.sort(key=lambda j: j.job_number)
    linked_questions = await get_questions(batch_id=batch_id)
    active_questions = [q for q in linked_questions if is_question_active(q.status)]

    qs_by_job = partition_questions_by_job(active_questions)
    jobs_to_refill = compute_jobs_with_deficits(existing_jobs, qs_by_job, total_deficit=deficit)

    if not jobs_to_refill:
        logger.info("No existing jobs in batch %s have deficits to refill.", batch_id)
        return b, []

    b.status = BatchStatus.IN_PROGRESS
    b.error_message = None
    await save_batch(b)

    effective_req = _resolve_effective_request(b)

    task = asyncio.create_task(
        _execute_in_set_refill(
            batch_id,
            effective_req,
            jobs_to_refill,
            current_cycle=cycle,
            max_cycles=max_cycles,
        )
    )
    register_batch_task(batch_id, task)

    refreshed_batch = await get_batch_by_id(batch_id)
    return refreshed_batch, [j for j, _ in jobs_to_refill]


async def launch_background_batch(
    req: GenerationRequest,
    batch_id: str | None = None,
) -> tuple[GenerationBatch, list[GenerationJob]]:
    """
    Initializes a batch with constituent jobs in PostgreSQL and launches
    the background runner task governed by the global worker pool.
    5 questions = 1 job; 50 questions = 10 jobs.
    """
    b_id = batch_id or str(uuid.uuid4())
    now_iso = datetime.now(UTC).isoformat()

    sec_val = req.section.value if hasattr(req.section, "value") else str(req.section)
    diff_val = req.difficulty.value if hasattr(req.difficulty, "value") else str(req.difficulty)

    target_count = req.questions_to_generate or 50
    total_jobs = max(1, (target_count + (QUESTIONS_PER_JOB - 1)) // QUESTIONS_PER_JOB)

    # Cache request for potential 1-click retries
    store_batch_request(b_id, req)

    # 1. Create GenerationBatch record
    batch = GenerationBatch(
        id=b_id,
        section=sec_val,
        subtopic=req.subtopic or f"{sec_val} Comprehensive Set",
        difficulty=diff_val,
        passage_mode=req.passage_mode or "single_passage",
        target_count=target_count,
        actual_count=0,
        total_jobs=total_jobs,
        completed_jobs=0,
        failed_jobs=0,
        status=BatchStatus.IN_PROGRESS,
        # Never persist credentials; retries fall back to the server-configured key.
        request_payload=req.model_dump(exclude={"api_key"}),
        created_at=now_iso,
    )
    await save_batch(batch)

    # 2. Create GenerationJob stubs
    jobs: list[GenerationJob] = []
    for num in range(1, total_jobs + 1):
        job_target = min(
            QUESTIONS_PER_JOB,
            target_count - (num - 1) * QUESTIONS_PER_JOB,
        )
        j = GenerationJob(
            id=str(uuid.uuid4()),
            batch_id=b_id,
            job_number=num,
            status=JobStatus.PENDING,
            target_count=job_target,
            actual_count=0,
            created_at=now_iso,
        )
        jobs.append(j)

    await save_jobs_bulk(jobs)

    # 3. Spawn background asyncio task governed by global worker pool
    task = asyncio.create_task(_execute_batch_workflow(b_id, req))
    register_batch_task(b_id, task)

    return batch, jobs
