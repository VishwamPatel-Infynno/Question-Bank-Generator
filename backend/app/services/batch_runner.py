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

from app.repositories.batch_repository import (
    get_batch_by_id,
    promote_completed_batch_questions,
    refresh_batch_aggregates,
    save_batch,
)
from app.repositories.job_repository import (
    get_jobs_by_batch_id,
    save_jobs_bulk,
    update_job_progress,
)
from app.repositories.question_repository import (
    batch_update_question_status,
    get_questions,
    hard_delete_questions_batch,
)
from app.schemas import (
    GenerationBatch,
    GenerationJob,
    GenerationRequest,
    is_question_active,
)
from app.services.batch_concurrency import (
    _active_batch_tasks,
    _batch_requests,
    cancel_all_background_batches,
    cancel_background_batch,
    get_active_batch_metrics,
    get_global_job_semaphore,
    get_stored_batch_request,
    register_batch_task,
    stop_background_batch,
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
    BATCH_THEMATIC_ANGLES,
    QUESTIONS_PER_JOB,
    _persist_job_question,
    _run_single_job,
    _run_single_job_refill,
)

logger = logging.getLogger(__name__)

__all__ = [
    "QUESTIONS_PER_JOB",
    "BATCH_THEMATIC_ANGLES",
    "_active_batch_tasks",
    "_batch_requests",
    "get_global_job_semaphore",
    "get_active_batch_metrics",
    "stop_background_batch",
    "cancel_background_batch",
    "cancel_all_background_batches",
    "register_batch_task",
    "unregister_batch_task",
    "store_batch_request",
    "get_stored_batch_request",
    "_persist_job_question",
    "_run_single_job",
    "_run_single_job_refill",
    "_execute_in_set_refill",
    "_execute_batch_workflow",
    "auto_resolve_batch_and_refill",
    "refill_batch_deficit",
    "retry_incomplete_jobs_for_batch",
    "launch_background_batch",
]


async def _execute_in_set_refill(
    batch_id: str,
    req: GenerationRequest,
    jobs_to_refill: list[tuple[GenerationJob, int]],
    current_cycle: int = 2,
    max_cycles: int = 3,
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
            final_b = await refresh_batch_aggregates(batch_id, allow_complete=True)
            if final_b and final_b.status in ("completed", "partially_completed"):
                await promote_completed_batch_questions(batch_id)
    except asyncio.CancelledError:
        logger.info(f"In-set refill for batch {batch_id} was cancelled.")
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await refresh_batch_aggregates(batch_id)
        raise
    except Exception as e:
        logger.error(f"Error during in-set refill for batch {batch_id}: {e}", exc_info=True)
        b = await get_batch_by_id(batch_id)
        if b:
            b.status = "failed"
            b.error_message = str(e)
            await save_batch(b)
    finally:
        unregister_batch_task(batch_id, asyncio.current_task())


async def _execute_batch_workflow(
    batch_id: str,
    req: GenerationRequest,
    target_jobs: list[GenerationJob] | None = None,
    current_cycle: int = 1,
    max_cycles: int = 3,
) -> None:
    """Coordinates the execution of jobs within a batch using the global worker semaphore."""
    tasks: list[asyncio.Task[Any]] = []
    try:
        jobs = target_jobs or await get_jobs_by_batch_id(batch_id)
        if not jobs:
            logger.error(f"No jobs found for batch {batch_id}")
            return

        # Execute jobs that need work (pending or running or failed/cancelled on retry)
        executable_jobs = [
            j for j in jobs if j.status in ("pending", "running", "failed", "cancelled")
        ]
        if not executable_jobs:
            logger.info(f"Batch {batch_id} has no pending jobs to execute.")
            await refresh_batch_aggregates(batch_id)
            return

        # Acquire slots from the shared global worker pool
        semaphore = get_global_job_semaphore()
        tasks = [
            asyncio.create_task(_run_single_job(batch_id, job, req, semaphore))
            for job in executable_jobs
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Finalize batch state atomically without premature completion
        updated_batch = await refresh_batch_aggregates(batch_id, allow_complete=False)
        if updated_batch:
            logger.info(
                f"Batch {batch_id} finished execution. Status: {updated_batch.status} "
                f"({updated_batch.completed_jobs}/{updated_batch.total_jobs} jobs, "
                f"{updated_batch.actual_count}/{updated_batch.target_count} questions)."
            )

        # Autonomous duplicate resolution and refill
        refill_result = await auto_resolve_batch_and_refill(
            batch_id, current_cycle=current_cycle, max_cycles=max_cycles
        )
        if not refill_result.get("refill_launched"):
            # Batch has fully concluded all processing, deduplication, and refilling
            final_b = await refresh_batch_aggregates(batch_id, allow_complete=True)
            if final_b and final_b.status in ("completed", "partially_completed"):
                await promote_completed_batch_questions(batch_id)

    except asyncio.CancelledError:
        logger.info(f"Batch {batch_id} execution was cancelled; terminating all sub-tasks...")
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await refresh_batch_aggregates(batch_id)
        raise
    except Exception as e:
        logger.error(f"Fatal error in batch {batch_id} execution: {e}", exc_info=True)
        b = await get_batch_by_id(batch_id)
        if b:
            b.status = "failed"
            b.error_message = str(e)
            await save_batch(b)
    finally:
        unregister_batch_task(batch_id, asyncio.current_task())


async def auto_resolve_batch_and_refill(
    batch_id: str,
    current_cycle: int = 1,
    max_cycles: int = 3,
    threshold: float = 0.75,
) -> dict[str, Any]:
    """
    Evaluates active questions in a batch for duplicate clusters, permanently deletes
    redundant duplicates in favor of the highest-scoring question in each cluster,
    and automatically triggers in-set replenishment within affected sets if a deficit exists,
    capped at max_cycles (up to 3 cycles). Also trims excess questions within sets to exact target.
    """
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
            f"Auto-resolved {len(clusters)} duplicate cluster(s) in batch {batch_id}; "
            f"permanently deleted {len(duplicate_ids_to_purge)} duplicate question(s)."
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
                    f"Trimmed Set #{job.job_number} (Job {job.id}) to target count {job.target_count}: "
                    f"permanently deleted {len(excess_to_delete)} excess question(s)."
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
        buffer = 1 if deficit < 5 else 2
        refill_target = min(target, deficit + buffer)
        logger.info(
            f"Auto-refill triggered for batch {batch_id}: deficit={deficit}, "
            f"refill_target={refill_target} (buffer={buffer}), "
            f"cycle={current_cycle + 1}/{max_cycles}"
        )
        await refill_batch_deficit(
            batch_id, refill_target, cycle=current_cycle + 1, max_cycles=max_cycles
        )
        refill_launched = True
    elif remaining_active > target:
        excess_buffer_ids = identify_batch_buffer_excess(valid_active, target)
        if excess_buffer_ids:
            await batch_update_question_status(excess_buffer_ids, status="discarded")
            logger.info(
                f"Capped batch {batch_id} to exact target {target}: archived {len(excess_buffer_ids)} excess buffer question(s)."
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
    # Strictly enforce 3-trial ceiling: only jobs with trial_count < 3 are eligible for retry/resume
    retryable_jobs = [
        j
        for j in jobs
        if (j.trial_count or 1) < 3
        and (
            j.status in ("failed", "cancelled", "pending")
            or (j.actual_count < (j.target_count or 5))
        )
    ]
    if not retryable_jobs:
        return b, []

    # Reset retryable jobs to pending while preserving their current trial count
    for j in retryable_jobs:
        await update_job_progress(
            j.id,
            status="pending",
            error_message=None,
            started_at=None,
            completed_at=None,
        )

    b.status = "in_progress"
    b.error_message = None
    await save_batch(b)

    # Resolve GenerationRequest
    effective_req = req or get_stored_batch_request(batch_id)
    if not effective_req and b and b.request_payload:
        try:
            effective_req = GenerationRequest(**b.request_payload)
        except Exception as err:
            logger.warning(f"Could not deserialize stored batch request_payload: {err}")
    if not effective_req:
        effective_req = GenerationRequest(
            section=b.section or "chem_phys",
            difficulty=b.difficulty or "medium",
            subtopic=b.subtopic,
            passage_mode=b.passage_mode,
            questions_to_generate=5,
        )

    task = asyncio.create_task(_execute_batch_workflow(batch_id, effective_req, retryable_jobs))
    register_batch_task(batch_id, task)

    refreshed_batch = await get_batch_by_id(batch_id)
    all_jobs = await get_jobs_by_batch_id(batch_id)
    return refreshed_batch, all_jobs


async def refill_batch_deficit(
    batch_id: str,
    deficit: int,
    cycle: int = 2,
    max_cycles: int = 3,
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
        logger.info(f"No existing jobs in batch {batch_id} have deficits to refill.")
        return b, []

    b.status = "in_progress"
    b.error_message = None
    await save_batch(b)

    effective_req = get_stored_batch_request(batch_id)
    if not effective_req and b and b.request_payload:
        try:
            effective_req = GenerationRequest(**b.request_payload)
        except Exception as err:
            logger.warning(f"Could not deserialize stored batch request_payload: {err}")
    if not effective_req:
        effective_req = GenerationRequest(
            section=b.section or "chem_phys",
            difficulty=b.difficulty or "medium",
            subtopic=b.subtopic,
            passage_mode=b.passage_mode,
            questions_to_generate=5,
        )

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
        status="in_progress",
        request_payload=req.model_dump(),
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
            status="pending",
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
