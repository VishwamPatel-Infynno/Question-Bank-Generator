"""
batch_worker.py - Single job worker execution and autonomous in-flight trial replenishment.

Governs workflow stream invocation for individual GenerationJobs within a batch,
enforcing autonomous in-flight retries (up to 3 trials) to fulfill target count guarantees.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from app.core.config import config
from app.core.errors import sanitize_error_text
from app.core.logging import bind_log_context
from app.repositories import (
    batch_exists,
    get_active_job_question_heads,
    get_batch_by_id,
    refresh_batch_aggregates,
    save_question,
    update_job_progress,
)
from app.repositories.question_repository import QuestionHead
from app.schemas import (
    GenerationJob,
    GenerationRequest,
    JobStatus,
    Question,
    determine_question_status,
)
from app.workflow import engine as workflow_engine
from app.workflow.sse import iter_sse_events

logger = logging.getLogger(__name__)

# Each generation job targets exactly 5 questions
QUESTIONS_PER_JOB: int = 5
# Autonomous in-flight attempts per job (initial run plus replenishments)
MAX_JOB_TRIALS: int = 3
# Duplicate-resolution/refill rounds a batch may go through before it is finalized
MAX_REFILL_CYCLES: int = 3

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
        q_obj.status = determine_question_status(score, is_in_progress_batch=True)

        if not await batch_exists(batch_id):
            logger.info("Batch %s no longer exists; aborting job %s.", batch_id, job_id)
            return (None, True)

        if passage_id and not q_obj.passage_id:
            q_obj.passage_id = passage_id

        if not any(existing.id == q_obj.id for existing in job_questions):
            saved_q = await save_question(q_obj)
            job_questions.append(saved_q)
            return (saved_q, False)
        return (None, False)
    except Exception as q_err:
        # A generated (and paid for) question could not be stored: keep the traceback, and let the
        # job's error message say so, instead of a one-line log that nobody sees.
        logger.error("Error saving question for job %s: %s", job_id, q_err, exc_info=True)
        with contextlib.suppress(Exception):
            await update_job_progress(
                job_id,
                error_message=sanitize_error_text(
                    f"A generated question could not be saved: {q_err}"
                ),
            )
        return (None, False)


class _JobUsage:
    """Running token/cost totals for one job across all of its trials."""

    def __init__(self, job: GenerationJob):
        self.tokens = job.total_tokens or 0
        self.prompt = job.prompt_tokens or 0
        self.completion = job.completion_tokens or 0
        self.cost = job.cost_usd or 0.0

    def add(self, usage: dict[str, Any] | None) -> None:
        usage = usage or {}
        self.tokens += usage.get("total_tokens", 0)
        self.prompt += usage.get("total_prompt_tokens", 0)
        self.completion += usage.get("total_completion_tokens", 0)
        self.cost += float(usage.get("total_cost_usd", 0.0))

    def fields(self) -> dict[str, Any]:
        return {
            "total_tokens": self.tokens,
            "prompt_tokens": self.prompt,
            "completion_tokens": self.completion,
            "cost_usd": self.cost,
        }


def _batch_thematic_angle(job_number: int) -> str:
    """The pedagogical angle a job gets by its position in the batch (rotates through the list)."""
    return BATCH_THEMATIC_ANGLES[(job_number - 1) % len(BATCH_THEMATIC_ANGLES)]


def _is_passage_mode(req: GenerationRequest) -> bool:
    """Returns True when the request needs a shared passage (CARS, single-passage, or explicit)."""
    # GenerationRequest's validator already resolved the binary passage mode (CARS always linked)
    return req.passage_mode == "single_passage"


async def _get_active_job_questions(batch_id: str, job_id: str) -> list[QuestionHead]:
    """The job's questions that currently count toward its target (not deleted/discarded).

    Lightweight heads (id, status, stimulus, passage): callers only count them and read the first
    one's stimulus/passage, so no full rows are loaded.
    """
    return await get_active_job_question_heads(batch_id, job_id)


def _build_attempt_request(
    base_req: GenerationRequest,
    *,
    job: GenerationJob,
    batch_id: str,
    is_passage_mode: bool,
    passage_id: str | None,
    thematic_angle: str,
    questions_to_generate: int,
    shared_stimulus: str | None,
) -> GenerationRequest:
    """The workflow request for one attempt at (part of) a job; shared by runs and refills."""
    return base_req.model_copy(
        update={
            "run_id": job.id,
            "batch_id": batch_id,
            "job_id": job.id,
            "passing_threshold": config.BATCH_PASSING_SCORE_THRESHOLD,
            "questions_to_generate": questions_to_generate,
            "passage_mode": "single_passage" if is_passage_mode else "independent",
            "passage_required": "Yes" if is_passage_mode else "No",
            "passage_id": passage_id,
            "thematic_angle": thematic_angle,
            # Grounds replacement questions in the set's existing passage
            "shared_stimulus": shared_stimulus,
        }
    )


async def _consume_job_stream(
    stream: AsyncIterator[str],
    *,
    batch_id: str,
    job_id: str,
    passage_id: str | None,
    existing_count: int,
    new_questions: list[Question],
    usage_totals: _JobUsage,
) -> bool:
    """Reads one workflow stream: persists each question, folds token usage into the job totals.

    Returns True when the batch no longer exists (the caller must stop). Raises RuntimeError on a
    ``workflow_error`` event, after counting the spend that event carries; other failures
    propagate untouched so the caller can decide to retry.
    """
    async for evt_data in iter_sse_events(stream):
        etype = evt_data.get("event_type")
        data = evt_data.get("data") or {}

        if etype == "question_generated" and data.get("question"):
            saved_q, should_abort = await _persist_job_question(
                batch_id, job_id, passage_id, data["question"], new_questions
            )
            if should_abort:
                return True
            if saved_q:
                await update_job_progress(job_id, actual_count=existing_count + len(new_questions))

        elif etype == "workflow_complete":
            for raw_q in data.get("questions") or []:
                _, should_abort = await _persist_job_question(
                    batch_id, job_id, passage_id, raw_q, new_questions
                )
                if should_abort:
                    return True
            usage_totals.add(data.get("cumulative_usage"))

        elif etype in ("workflow_rejected", "workflow_error"):
            # A run that produced nothing still spent tokens: count them
            usage_totals.add(data.get("cumulative_usage"))
            if etype == "workflow_error":
                raise RuntimeError(data.get("error", "Unknown workflow error"))
    return False


async def _run_single_job(
    batch_id: str,
    job: GenerationJob,
    base_req: GenerationRequest,
    semaphore: asyncio.Semaphore,
) -> None:
    """Runs one job with batch/job ids bound to every log line it produces."""
    with bind_log_context(batch_id=batch_id, job_id=job.id):
        await _run_single_job_impl(batch_id, job, base_req, semaphore)


async def _run_single_job_impl(
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
    max_trials = MAX_JOB_TRIALS
    async with semaphore:
        # total_jobs is only used in log lines: read it from the batch row, not by loading every job
        batch_row = await get_batch_by_id(batch_id)
        total_jobs = (batch_row.total_jobs if batch_row else None) or 10
        is_passage_mode = _is_passage_mode(base_req)

        passage_id_for_job = job.passage_id or (str(uuid.uuid4()) if is_passage_mode else None)
        usage_totals = _JobUsage(job)

        start_trial = job.trial_count or 1
        trial = start_trial
        for current_trial in range(start_trial, max_trials + 1):
            trial = current_trial
            now_iso = datetime.now(UTC).isoformat()

            # Check existing active questions for this set
            existing_active_qs = await _get_active_job_questions(batch_id, job.id)
            deficit = max(0, (job.target_count or QUESTIONS_PER_JOB) - len(existing_active_qs))
            if deficit <= 0 and len(existing_active_qs) >= (job.target_count or QUESTIONS_PER_JOB):
                logger.info(
                    "Job %s/%s (ID: %s) already fulfilled target count.",
                    job.job_number,
                    total_jobs,
                    job.id,
                )
                break

            logger.info(
                "Executing Job %s/%s (ID: %s) for Batch %s [Trial %s/%s, deficit=%s]...",
                job.job_number,
                total_jobs,
                job.id,
                batch_id,
                trial,
                max_trials,
                deficit,
            )
            await update_job_progress(
                job.id,
                status=JobStatus.RUNNING,
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
                    f"{_batch_thematic_angle(job.job_number)} • "
                    f"In-Set Replenishment (Trial {trial}/{max_trials})"
                )
            else:
                thematic_angle = _batch_thematic_angle(job.job_number)

            attempt_req = _build_attempt_request(
                base_req,
                job=job,
                batch_id=batch_id,
                is_passage_mode=is_passage_mode,
                passage_id=passage_id_for_job,
                thematic_angle=thematic_angle,
                questions_to_generate=deficit,
                shared_stimulus=existing_stimulus,
            )

            attempt_new_qs: list[Question] = []
            stream = workflow_engine.run_workflow_stream(attempt_req)
            try:
                if await _consume_job_stream(
                    stream,
                    batch_id=batch_id,
                    job_id=job.id,
                    passage_id=passage_id_for_job,
                    existing_count=len(existing_active_qs),
                    new_questions=attempt_new_qs,
                    usage_totals=usage_totals,
                ):
                    return

            except asyncio.CancelledError:
                logger.info("Job %s/%s (ID: %s) was cancelled.", job.job_number, total_jobs, job.id)
                current_qs = await _get_active_job_questions(batch_id, job.id)
                await update_job_progress(
                    job.id,
                    status=JobStatus.CANCELLED,
                    trial_count=trial,
                    actual_count=len(current_qs),
                    completed_at=datetime.now(UTC).isoformat(),
                    **usage_totals.fields(),
                )
                await refresh_batch_aggregates(batch_id)
                raise
            except Exception as exc:
                logger.warning(
                    "Job %s/%s (ID: %s) trial %s/%s encountered error: %s",
                    job.job_number,
                    total_jobs,
                    job.id,
                    trial,
                    max_trials,
                    exc,
                )
                if trial < max_trials:
                    await asyncio.sleep(1.0)
                    continue
                logger.error(
                    "Job %s/%s (ID: %s) exhausted all %s trials: %s",
                    job.job_number,
                    total_jobs,
                    job.id,
                    max_trials,
                    exc,
                    exc_info=True,
                )
                await update_job_progress(job.id, error_message=sanitize_error_text(exc))
            finally:
                # An early return/raise would otherwise leave worker tasks spending tokens until GC
                await stream.aclose()

            # Re-evaluate active question count after attempt
            updated_active_qs = await _get_active_job_questions(batch_id, job.id)
            if len(updated_active_qs) >= (job.target_count or QUESTIONS_PER_JOB):
                logger.info(
                    "Job %s/%s (ID: %s) successfully reached target %s on Trial %s/%s.",
                    job.job_number,
                    total_jobs,
                    job.id,
                    job.target_count,
                    trial,
                    max_trials,
                )
                break

        # Finalize job progress after all attempts
        final_active_qs = await _get_active_job_questions(batch_id, job.id)
        final_count = len(final_active_qs)
        completed_now = datetime.now(UTC).isoformat()
        job_status = JobStatus.COMPLETED if final_count > 0 else JobStatus.FAILED

        await update_job_progress(
            job.id,
            status=job_status,
            actual_count=final_count,
            trial_count=trial,
            passage_id=passage_id_for_job,
            completed_at=completed_now,
            **usage_totals.fields(),
        )

        await refresh_batch_aggregates(batch_id, allow_complete=False)
        logger.info(
            "Job %s/%s (ID: %s) finished: generated %s/%s questions across %s/%s trial(s).",
            job.job_number,
            total_jobs,
            job.id,
            final_count,
            job.target_count or QUESTIONS_PER_JOB,
            trial,
            max_trials,
        )


async def _run_single_job_refill(
    batch_id: str,
    job: GenerationJob,
    job_deficit: int,
    base_req: GenerationRequest,
    semaphore: asyncio.Semaphore,
) -> None:
    """Runs a refill job with batch/job ids bound to every log line it produces."""
    with bind_log_context(batch_id=batch_id, job_id=job.id):
        await _run_single_job_refill_impl(batch_id, job, job_deficit, base_req, semaphore)


async def _run_single_job_refill_impl(
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
        new_trial = min(MAX_JOB_TRIALS, (job.trial_count or 1) + 1)
        logger.info(
            "Replenishing Set #%s (Job ID: %s) in Batch %s with %s replacement question(s) [Trial %s/%s]...",
            job.job_number,
            job.id,
            batch_id,
            job_deficit,
            new_trial,
            MAX_JOB_TRIALS,
        )
        await update_job_progress(
            job.id, status=JobStatus.RUNNING, trial_count=new_trial, started_at=now_iso
        )

        # Determine passage and stimulus from existing questions in this job
        job_existing_qs = await _get_active_job_questions(batch_id, job.id)

        is_passage_mode = _is_passage_mode(base_req)

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
            f"{_batch_thematic_angle(job.job_number)} • In-Set Replenishment Item"
        )

        refill_req = _build_attempt_request(
            base_req,
            job=job,
            batch_id=batch_id,
            is_passage_mode=is_passage_mode,
            passage_id=passage_id_for_job,
            thematic_angle=refill_thematic_angle,
            questions_to_generate=job_deficit,
            shared_stimulus=existing_stimulus,
        )

        refill_qs: list[Question] = []
        usage_totals = _JobUsage(job)

        stream = workflow_engine.run_workflow_stream(refill_req)
        try:
            if await _consume_job_stream(
                stream,
                batch_id=batch_id,
                job_id=job.id,
                passage_id=passage_id_for_job,
                existing_count=len(job_existing_qs),
                new_questions=refill_qs,
                usage_totals=usage_totals,
            ):
                return

            total_active = len(job_existing_qs) + len(refill_qs)
            completed_now = datetime.now(UTC).isoformat()
            await update_job_progress(
                job.id,
                status=JobStatus.COMPLETED if total_active > 0 else JobStatus.FAILED,
                actual_count=total_active,
                trial_count=new_trial,
                passage_id=passage_id_for_job,
                completed_at=completed_now,
                **usage_totals.fields(),
            )
            await refresh_batch_aggregates(batch_id)
            logger.info(
                "Set #%s (Job ID: %s) replenished successfully: total count is now %s/%s.",
                job.job_number,
                job.id,
                total_active,
                job.target_count,
            )
        except Exception as exc:
            logger.error(
                "Error replenishing Set #%s (Job ID: %s): %s",
                job.job_number,
                job.id,
                exc,
                exc_info=True,
            )
            await update_job_progress(
                job.id,
                status=JobStatus.FAILED,
                error_message=sanitize_error_text(exc),
                **usage_totals.fields(),
            )
        finally:
            await stream.aclose()
