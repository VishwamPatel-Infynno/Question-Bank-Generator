"""Persistence of questions and job/batch progress for standalone live (streamed) runs."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.repositories import (
    promote_completed_batch_questions,
    refresh_batch_aggregates,
    save_question,
    update_job_progress,
)
from app.schemas import JobStatus, Question, determine_question_status

logger = logging.getLogger(__name__)


async def _persist_live_question(
    final_q_dict: dict[str, Any],
    batch_id: str,
    job_id: str,
    item_run_id: str,
    shared_passage_id: str | None,
    completed_so_far: int,
    idx: int,
) -> None:
    """Auto-persists a generated question and updates job progress for interactive live runs."""
    try:
        q_obj = Question(**final_q_dict)
        q_obj.batch_id = batch_id
        q_obj.job_id = job_id
        q_obj.run_id = item_run_id
        if shared_passage_id and not q_obj.passage_id:
            q_obj.passage_id = shared_passage_id
        # While live generation is streaming, keep active questions in 'batch_only'
        # until the workflow successfully completes all questions.
        score = q_obj.final_score or 0
        q_obj.status = determine_question_status(score, is_in_progress_batch=True)
        await save_question(q_obj)
        await update_job_progress(job_id, actual_count=completed_so_far)
    except (SQLAlchemyError, OSError) as q_save_err:
        logger.warning(
            "Could not auto-persist question %s for live batch %s: %s",
            idx + 1,
            batch_id,
            q_save_err,
            exc_info=True,
        )


async def _finalize_live_job_progress(
    job_id: str,
    batch_id: str,
    completed_total: int,
    total_qty: int,
    cumulative_tokens: int,
    cumulative_prompt_tokens: int,
    cumulative_completion_tokens: int,
    cumulative_cost: float,
) -> None:
    """Updates job and batch status to completed or partially_completed upon workflow termination."""
    try:
        now_iso = datetime.now(UTC).isoformat()
        # The jobs table has no 'partially_completed' status; a short job is 'completed' with
        # actual_count below target (the retry flow re-launches any such job).
        job_status = JobStatus.COMPLETED if completed_total > 0 else JobStatus.FAILED
        await update_job_progress(
            job_id,
            status=job_status,
            actual_count=completed_total,
            total_tokens=cumulative_tokens,
            prompt_tokens=cumulative_prompt_tokens,
            completion_tokens=cumulative_completion_tokens,
            cost_usd=cumulative_cost,
            completed_at=now_iso,
        )
        await refresh_batch_aggregates(batch_id, allow_complete=True)
        if job_status == JobStatus.COMPLETED:
            await promote_completed_batch_questions(batch_id)
    except (SQLAlchemyError, OSError) as db_err:
        logger.warning("Could not finalize live job progress (DB offline): %s", db_err)


async def _handle_live_job_cancellation(
    job_id: str,
    batch_id: str,
    completed_total: int,
) -> None:
    """Safely transitions job progress to cancelled when client disconnects."""
    try:
        now_iso = datetime.now(UTC).isoformat()
        await update_job_progress(
            job_id,
            status=JobStatus.CANCELLED,
            actual_count=completed_total,
            completed_at=now_iso,
        )
        # A live (streamed) run has no background task to finish the batch later, so resolve it now
        await refresh_batch_aggregates(batch_id, allow_complete=True)
    except (SQLAlchemyError, OSError) as clean_err:
        logger.warning("Error updating cancelled live batch %s: %s", batch_id, clean_err)


async def _handle_live_job_failure(
    job_id: str,
    batch_id: str,
    error_msg: str,
) -> None:
    """Safely transitions job progress to failed upon unhandled exceptions."""
    try:
        now_iso = datetime.now(UTC).isoformat()
        await update_job_progress(
            job_id,
            status=JobStatus.FAILED,
            error_message=error_msg,
            completed_at=now_iso,
        )
        await refresh_batch_aggregates(batch_id, allow_complete=True)
    except (SQLAlchemyError, OSError) as clean_err:
        logger.warning("Error updating failed live batch %s: %s", batch_id, clean_err)
