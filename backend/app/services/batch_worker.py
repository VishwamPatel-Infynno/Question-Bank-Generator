"""
batch_worker.py - Single job worker execution and autonomous in-flight trial replenishment.

Governs workflow stream invocation for individual GenerationJobs within a batch,
enforcing autonomous in-flight retries (up to 3 trials) to fulfill target count guarantees.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.config import config
from app.repositories.batch_repository import (
    get_batch_by_id,
    refresh_batch_aggregates,
)
from app.repositories.job_repository import (
    get_jobs_by_batch_id,
    update_job_progress,
)
from app.repositories.question_repository import (
    get_questions,
    save_question,
)
from app.schemas import (
    GenerationJob,
    GenerationRequest,
    Question,
    is_question_active,
)
from app.workflow._section_utils import is_cars_section as _is_cars_section

logger = logging.getLogger(__name__)

# Each generation job targets exactly 5 questions
QUESTIONS_PER_JOB: int = 5

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
