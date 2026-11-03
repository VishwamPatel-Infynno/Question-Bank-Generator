import asyncio
import contextlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.config import config
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
    save_question,
)
from app.schemas import (
    GenerationBatch,
    GenerationJob,
    GenerationRequest,
    Question,
    is_question_active,
)
from app.services.deduplication import cluster_questions

logger = logging.getLogger(__name__)

# NOTE: These module-level dicts are process-local and will be lost on restart.
# For multi-process or distributed deployments, migrate to a Redis-backed store.
_active_batch_tasks: dict[str, asyncio.Task[Any]] = {}

# In-memory store for generation requests to support 1-click retries
_batch_requests: dict[str, GenerationRequest] = {}

# Global worker pool semaphore governing concurrent jobs across ALL running batches
_GLOBAL_JOB_SEMAPHORE: asyncio.Semaphore | None = None


def get_global_job_semaphore() -> asyncio.Semaphore:
    """Returns the singleton global worker pool semaphore, lazily initialized."""
    global _GLOBAL_JOB_SEMAPHORE
    if _GLOBAL_JOB_SEMAPHORE is None:
        _GLOBAL_JOB_SEMAPHORE = asyncio.Semaphore(config.GLOBAL_MAX_CONCURRENT_JOBS)
    return _GLOBAL_JOB_SEMAPHORE


def _is_cars_section(section: Any) -> bool:
    """Returns True if the section is CARS (Critical Analysis and Reasoning Skills)."""
    val = section.value if hasattr(section, "value") else str(section)
    return val.strip().lower() in ("cars", "mcatsection.cars")


async def _persist_job_question(
    batch_id: str,
    job_id: str,
    passage_id: str | None,
    raw_q: dict[str, Any],
    job_questions: list[Question],
) -> tuple[Question | None, bool]:
    """
    Serializes, tags, verifies batch existence, and persists a job question.
    Returns: (saved_question, batch_aborted_flag)
    """
    try:
        q_obj = Question(**raw_q)
        q_obj.batch_id = batch_id
        q_obj.job_id = job_id
        q_obj.run_id = job_id
        # While a batch is actively generating, keep active questions in 'batch_only'
        # so they do NOT leak into Ready for Review until the batch successfully finishes.
        score = q_obj.final_score or 0
        if score > config.BATCH_PASSING_SCORE_THRESHOLD:
            q_obj.status = "batch_only"
        else:
            q_obj.status = "below_threshold"

        curr_b = await get_batch_by_id(batch_id)
        if not curr_b:
            logger.info(f"Batch {batch_id} no longer exists; aborting job {job_id}.")
            return (None, True)

        if passage_id and not q_obj.passage_id:
            q_obj.passage_id = passage_id

        if not any(existing.id == q_obj.id for existing in job_questions):
            saved_q = await save_question(q_obj)
            job_questions.append(saved_q)
            return (saved_q, False)
        return (None, False)
    except Exception as q_err:
        logger.error(f"Error saving question for job {job_id}: {q_err}")
        return (None, False)


BATCH_THEMATIC_ANGLES = [
    "Experimental & Analytical Instrumentation (e.g. Mass Spectrometry, deflection in electric/magnetic fields, detectors)",
    "Biomedical, Clinical & Pharmacological Diagnostics (e.g. PET radiotracers, radioactive decay therapy, cellular imaging)",
    "Nuclear Forces, Binding Energy & Stability (e.g. Strong nuclear force vs Coulomb repulsion, N/Z stability valley, decay modes)",
    "Chemical Reactivity, Bonding & Kinetic Isotope Effects (e.g. Rate-limiting transitions, zero-point energy, deuterated substrates)",
    "Historical Experiments & Foundational Atomic Models (e.g. Rutherford alpha-scattering, Thomson cathode rays, Chadwick neutrons)",
    "Metabolic Pathways & Enzyme Catalysis Mechanisms (e.g. Substrate binding, transition-state theory, cofactor kinetics)",
    "Spectroscopic Analysis & Quantum Transitions (e.g. Atomic emission/absorption, orbital transitions, selection rules)",
    "Cellular & Membrane Transport Dynamics (e.g. Ion channels, electrochemical gradients, isotopic flux)",
    "Thermodynamics, Phase Equilibria & Collisional Dynamics (e.g. Kinetic theory, vapor pressure isotope effects)",
    "Radiation Biophysics & Molecular Damage (e.g. Ionizing radiation, reactive oxygen species, DNA repair mechanisms)",
]


async def _run_single_job(
    batch_id: str,
    job: GenerationJob,
    base_req: GenerationRequest,
    semaphore: asyncio.Semaphore,
) -> None:
    """
    Executes a single job generating questions (target_count), saving them directly to the database.
    Guarantees up to 3 autonomous in-flight trials if a shortfall or error occurs,
    fulfilling the target count guarantee without stopping the batch or requiring user intervention.
    """
    max_trials = 3
    async with semaphore:
        total_jobs = len(await get_jobs_by_batch_id(batch_id)) or 10
        is_cars = _is_cars_section(base_req.section)
        is_passage_mode = (
            is_cars
            or base_req.passage_mode == "single_passage"
            or str(base_req.passage_required).lower() in ("yes", "true", "1")
        )

        passage_id_for_job = job.passage_id or (str(uuid.uuid4()) if is_passage_mode else None)
        job_tokens = job.total_tokens or 0
        job_prompt_tokens = job.prompt_tokens or 0
        job_completion_tokens = job.completion_tokens or 0
        job_cost = job.cost_usd or 0.0

        from app.workflow.engine import run_workflow_stream

        start_trial = job.trial_count or 1
        trial = start_trial
        for current_trial in range(start_trial, max_trials + 1):
            trial = current_trial
            now_iso = datetime.now(UTC).isoformat()

            # Check existing active questions for this set
            existing_active_qs = [
                q
                for q in (await get_questions(batch_id=batch_id, job_id=job.id))
                if is_question_active(q.status)
            ]
            deficit = max(0, (job.target_count or 5) - len(existing_active_qs))
            if deficit <= 0 and len(existing_active_qs) >= (job.target_count or 5):
                logger.info(
                    f"Job {job.job_number}/{total_jobs} (ID: {job.id}) already fulfilled target count."
                )
                break

            logger.info(
                f"Executing Job {job.job_number}/{total_jobs} (ID: {job.id}) for Batch {batch_id} "
                f"[Trial {trial}/{max_trials}, deficit={deficit}]..."
            )
            await update_job_progress(
                job.id,
                status="running",
                trial_count=trial,
                actual_count=len(existing_active_qs),
                passage_id=passage_id_for_job,
                started_at=now_iso,
            )
            await refresh_batch_aggregates(batch_id, allow_complete=False)

            existing_stimulus = (
                existing_active_qs[0].stimulus_text
                if (existing_active_qs and existing_active_qs[0].stimulus_text)
                else None
            )
            if existing_active_qs and existing_active_qs[0].passage_id:
                passage_id_for_job = existing_active_qs[0].passage_id

            if trial > 1:
                thematic_angle = (
                    f"{BATCH_THEMATIC_ANGLES[(job.job_number - 1) % len(BATCH_THEMATIC_ANGLES)]} • "
                    f"In-Set Replenishment (Trial {trial}/{max_trials})"
                )
            else:
                thematic_angle = BATCH_THEMATIC_ANGLES[
                    (job.job_number - 1) % len(BATCH_THEMATIC_ANGLES)
                ]

            attempt_req = base_req.model_copy(
                update={
                    "run_id": job.id,
                    "batch_id": batch_id,
                    "job_id": job.id,
                    "passing_threshold": config.BATCH_PASSING_SCORE_THRESHOLD,
                    "questions_to_generate": deficit,
                    "passage_mode": "single_passage" if is_passage_mode else "independent",
                    "passage_required": "Yes" if is_passage_mode else "No",
                    "passage_id": passage_id_for_job,
                    "thematic_angle": thematic_angle,
                    "shared_stimulus": existing_stimulus,
                }
            )

            attempt_new_qs: list[Question] = []
            try:
                async for raw_chunk in run_workflow_stream(attempt_req):
                    line = raw_chunk.strip()
                    if not line.startswith("data: "):
                        continue
                    try:
                        evt_data = json.loads(line[6:])
                        etype = evt_data.get("event_type")
                        data = evt_data.get("data") or {}

                        if etype == "question_generated" and data.get("question"):
                            saved_q, should_abort = await _persist_job_question(
                                batch_id,
                                job.id,
                                passage_id_for_job,
                                data["question"],
                                attempt_new_qs,
                            )
                            if should_abort:
                                return
                            if saved_q:
                                total_now = len(existing_active_qs) + len(attempt_new_qs)
                                await update_job_progress(job.id, actual_count=total_now)

                        elif etype == "workflow_complete":
                            completed_qs = data.get("questions") or []
                            for raw_q in completed_qs:
                                _, should_abort = await _persist_job_question(
                                    batch_id, job.id, passage_id_for_job, raw_q, attempt_new_qs
                                )
                                if should_abort:
                                    return

                            usage = data.get("cumulative_usage") or {}
                            job_tokens += usage.get("total_tokens", 0)
                            job_prompt_tokens += usage.get("total_prompt_tokens", 0)
                            job_completion_tokens += usage.get("total_completion_tokens", 0)
                            job_cost += float(usage.get("total_cost_usd", 0.0))

                        elif etype == "workflow_error":
                            raise RuntimeError(data.get("error", "Unknown workflow error"))

                    except json.JSONDecodeError:
                        continue

            except asyncio.CancelledError:
                logger.info(f"Job {job.job_number}/{total_jobs} (ID: {job.id}) was cancelled.")
                current_qs = [
                    q
                    for q in (await get_questions(batch_id=batch_id, job_id=job.id))
                    if is_question_active(q.status)
                ]
                await update_job_progress(
                    job.id,
                    status="cancelled",
                    trial_count=trial,
                    actual_count=len(current_qs),
                    completed_at=datetime.now(UTC).isoformat(),
                )
                await refresh_batch_aggregates(batch_id)
                raise
            except Exception as exc:
                logger.warning(
                    f"Job {job.job_number}/{total_jobs} (ID: {job.id}) trial {trial}/{max_trials} encountered error: {exc}"
                )
                if trial < max_trials:
                    await asyncio.sleep(1.0)
                    continue
                logger.error(
                    f"Job {job.job_number}/{total_jobs} (ID: {job.id}) exhausted all {max_trials} trials: {exc}",
                    exc_info=True,
                )
                await update_job_progress(job.id, error_message=str(exc))

            # Re-evaluate active question count after attempt
            updated_active_qs = [
                q
                for q in (await get_questions(batch_id=batch_id, job_id=job.id))
                if is_question_active(q.status)
            ]
            if len(updated_active_qs) >= (job.target_count or 5):
                logger.info(
                    f"Job {job.job_number}/{total_jobs} (ID: {job.id}) successfully reached target "
                    f"{job.target_count} on Trial {trial}/{max_trials}."
                )
                break

        # Finalize job progress after all attempts
        final_active_qs = [
            q
            for q in (await get_questions(batch_id=batch_id, job_id=job.id))
            if is_question_active(q.status)
        ]
        final_count = len(final_active_qs)
        completed_now = datetime.now(UTC).isoformat()
        job_status = "completed" if final_count > 0 else "failed"

        await update_job_progress(
            job.id,
            status=job_status,
            actual_count=final_count,
            trial_count=trial,
            passage_id=passage_id_for_job,
            total_tokens=job_tokens,
            prompt_tokens=job_prompt_tokens,
            completion_tokens=job_completion_tokens,
            cost_usd=job_cost,
            completed_at=completed_now,
        )

        await refresh_batch_aggregates(batch_id, allow_complete=False)
        logger.info(
            f"Job {job.job_number}/{total_jobs} (ID: {job.id}) finished: generated {final_count}/"
            f"{job.target_count or 5} questions across {trial}/{max_trials} trial(s)."
        )


async def _run_single_job_refill(
    batch_id: str,
    job: GenerationJob,
    job_deficit: int,
    base_req: GenerationRequest,
    semaphore: asyncio.Semaphore,
) -> None:
    """Replenishes missing questions directly inside an existing job without creating a new job."""
    if job_deficit <= 0:
        return

    async with semaphore:
        now_iso = datetime.now(UTC).isoformat()
        new_trial = min(3, (job.trial_count or 1) + 1)
        logger.info(
            f"Replenishing Set #{job.job_number} (Job ID: {job.id}) in Batch {batch_id} "
            f"with {job_deficit} replacement question(s) [Trial {new_trial}/3]..."
        )
        await update_job_progress(
            job.id, status="running", trial_count=new_trial, started_at=now_iso
        )

        # Determine passage and stimulus from existing questions in this job
        job_existing_qs = [
            q
            for q in (await get_questions(batch_id=batch_id, job_id=job.id))
            if is_question_active(q.status)
        ]

        is_cars = _is_cars_section(base_req.section)
        is_passage_mode = (
            is_cars
            or base_req.passage_mode == "single_passage"
            or str(base_req.passage_required).lower() in ("yes", "true", "1")
        )

        passage_id_for_job = job.passage_id or (
            job_existing_qs[0].passage_id if job_existing_qs else None
        )
        existing_stimulus = (
            job_existing_qs[0].stimulus_text
            if (job_existing_qs and job_existing_qs[0].stimulus_text)
            else None
        )

        if is_passage_mode and not passage_id_for_job:
            passage_id_for_job = str(uuid.uuid4())

        refill_thematic_angle = (
            f"{BATCH_THEMATIC_ANGLES[(job.job_number - 1) % len(BATCH_THEMATIC_ANGLES)]} • "
            f"In-Set Replenishment Item"
        )

        refill_req = base_req.model_copy(
            update={
                "run_id": job.id,
                "batch_id": batch_id,
                "job_id": job.id,
                "passing_threshold": config.BATCH_PASSING_SCORE_THRESHOLD,
                "questions_to_generate": job_deficit,
                "passage_mode": "single_passage" if is_passage_mode else "independent",
                "passage_required": "Yes" if is_passage_mode else "No",
                "passage_id": passage_id_for_job,
                "thematic_angle": refill_thematic_angle,
                "shared_stimulus": existing_stimulus,  # Ground replacement question in set's existing passage
            }
        )

        refill_qs: list[Question] = []
        from app.workflow.engine import run_workflow_stream

        try:
            async for raw_chunk in run_workflow_stream(refill_req):
                line = raw_chunk.strip()
                if not line.startswith("data: "):
                    continue
                try:
                    evt_data = json.loads(line[6:])
                    etype = evt_data.get("event_type")
                    data = evt_data.get("data") or {}

                    if etype == "question_generated" and data.get("question"):
                        saved_q, should_abort = await _persist_job_question(
                            batch_id, job.id, passage_id_for_job, data["question"], refill_qs
                        )
                        if should_abort:
                            return
                        if saved_q:
                            total_active = len(job_existing_qs) + len(refill_qs)
                            await update_job_progress(job.id, actual_count=total_active)

                    elif etype == "workflow_complete":
                        completed_qs = data.get("questions") or []
                        for raw_q in completed_qs:
                            _, should_abort = await _persist_job_question(
                                batch_id, job.id, passage_id_for_job, raw_q, refill_qs
                            )
                            if should_abort:
                                return

                except json.JSONDecodeError:
                    continue

            total_active = len(job_existing_qs) + len(refill_qs)
            completed_now = datetime.now(UTC).isoformat()
            await update_job_progress(
                job.id,
                status="completed" if total_active > 0 else "failed",
                actual_count=total_active,
                trial_count=new_trial,
                passage_id=passage_id_for_job,
                completed_at=completed_now,
            )
            await refresh_batch_aggregates(batch_id)
            logger.info(
                f"Set #{job.job_number} (Job ID: {job.id}) replenished successfully: "
                f"total count is now {total_active}/{job.target_count}."
            )
        except Exception as exc:
            logger.error(
                f"Error replenishing Set #{job.job_number} (Job ID: {job.id}): {exc}",
                exc_info=True,
            )
            await update_job_progress(job.id, status="failed", error_message=str(exc))


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
        if _active_batch_tasks.get(batch_id) is asyncio.current_task():
            _active_batch_tasks.pop(batch_id, None)


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
        if _active_batch_tasks.get(batch_id) is asyncio.current_task():
            _active_batch_tasks.pop(batch_id, None)


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
    q_dumps = [q.model_dump() for q in active_questions]

    clusters = cluster_questions(q_dumps, threshold=threshold)
    duplicate_ids_to_purge: list[str] = []

    if clusters:
        for c in clusters:
            leader_id = c["leader_question"]["id"]
            for d in c["duplicates"]:
                dup_id = d["question"]["id"]
                if dup_id != leader_id:
                    duplicate_ids_to_purge.append(dup_id)

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

    qs_by_job: dict[str, list[Question]] = {}
    for q in active_refreshed_qs:
        j_key = q.job_id or q.run_id
        if j_key:
            qs_by_job.setdefault(j_key, []).append(q)

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
        valid_active.sort(key=lambda q: q.final_score or 0, reverse=True)
        excess_to_delete = [q.id for q in valid_active[target:]]
        if excess_to_delete:
            await batch_update_question_status(excess_to_delete, status="discarded")
            logger.info(
                f"Capped batch {batch_id} to exact target {target}: archived {len(excess_to_delete)} excess buffer question(s)."
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


async def stop_background_batch(batch_id: str) -> bool:
    """Gracefully stops an active batch, halts running tasks, and preserves generated questions."""
    task = _active_batch_tasks.pop(batch_id, None)
    if task and not task.done():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task

    # Mark remaining pending/running jobs as cancelled
    jobs = await get_jobs_by_batch_id(batch_id)
    now_iso = datetime.now(UTC).isoformat()
    for j in jobs:
        if j.status in ("pending", "running"):
            await update_job_progress(j.id, status="cancelled", completed_at=now_iso)

    b = await get_batch_by_id(batch_id)
    if b:
        b.status = "cancelled" if (b.completed_jobs or 0) == 0 else "partially_completed"
        await save_batch(b)
    await refresh_batch_aggregates(batch_id)
    return True


async def cancel_background_batch(batch_id: str) -> bool:
    """Cancels an active background batch runner task if running."""
    return await stop_background_batch(batch_id)


async def cancel_all_background_batches() -> int:
    """Gracefully halts all active background batches, preserving generated questions."""
    batch_ids = list(_active_batch_tasks.keys())
    count = 0
    for b_id in batch_ids:
        stopped = await stop_background_batch(b_id)
        if stopped:
            count += 1
    return count


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
    effective_req = req or _batch_requests.get(batch_id)
    if not effective_req:
        effective_req = GenerationRequest(
            section=b.section or "chem_phys",
            difficulty=b.difficulty or "medium",
            subtopic=b.subtopic,
            passage_mode=b.passage_mode,
            questions_to_generate=5,
        )

    task = asyncio.create_task(_execute_batch_workflow(batch_id, effective_req, retryable_jobs))
    _active_batch_tasks[batch_id] = task

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
    preserving exact job/set counts (e.g. exactly 10 sets for 50 questions,
    1 set for 5 questions) without creating extra sets.
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

    qs_by_job: dict[str, list[Question]] = {}
    for q in active_questions:
        j_key = q.job_id or q.run_id
        if j_key:
            qs_by_job.setdefault(j_key, []).append(q)

    jobs_to_refill: list[tuple[GenerationJob, int]] = []
    for job in existing_jobs:
        job_active_count = len(qs_by_job.get(job.id, []))
        job_deficit = max(0, job.target_count - job_active_count)
        if job_deficit > 0:
            jobs_to_refill.append((job, job_deficit))

    # If no job specifically had a shortfall below target_count, allocate to any incomplete jobs
    if not jobs_to_refill and deficit > 0:
        for job in existing_jobs:
            if job.status != "completed":
                jobs_to_refill.append((job, min(deficit, job.target_count)))
                break

    if not jobs_to_refill:
        logger.info(f"No existing jobs in batch {batch_id} have deficits to refill.")
        return b, []

    b.status = "in_progress"
    b.error_message = None
    await save_batch(b)

    effective_req = _batch_requests.get(batch_id)
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
    _active_batch_tasks[batch_id] = task

    refreshed_batch = await get_batch_by_id(batch_id)
    return refreshed_batch, [j for j, _ in jobs_to_refill]


def get_active_batch_metrics() -> dict[str, Any]:
    """Returns real-time concurrency metrics for background batches."""
    return {
        "active_running_batches": len(_active_batch_tasks),
        "global_max_concurrent_jobs": config.GLOBAL_MAX_CONCURRENT_JOBS,
        "global_max_concurrent_llm_calls": config.GLOBAL_MAX_CONCURRENT_LLM_CALLS,
        "active_batch_ids": list(_active_batch_tasks.keys()),
    }


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
    total_jobs = max(1, (target_count + 4) // 5)

    # Cache request for potential 1-click retries
    _batch_requests[b_id] = req

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
        created_at=now_iso,
    )
    await save_batch(batch)

    # 2. Create GenerationJob stubs
    jobs: list[GenerationJob] = []
    for num in range(1, total_jobs + 1):
        job_target = min(5, target_count - (num - 1) * 5)
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
    _active_batch_tasks[b_id] = task

    return batch, jobs
