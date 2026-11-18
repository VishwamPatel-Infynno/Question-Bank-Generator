"""
engine.py - Core streaming workflow engine for MCAT Question Generation.

Orchestrates multi-agent pipelines for generating single or multiple questions
(passage sets or independent discretes). Streams real-time Server-Sent Events (SSE)
to the client, manages worker pool concurrency, and stages questions for user confirmation.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator
from typing import Any

from app.agents.generator import generate_passage_stimulus
from app.agents.image_generator import generate_image_stimulus
from app.core.concurrency import get_global_pipeline_semaphore
from app.core.errors import sanitize_error_text
from app.core.logging import bind_log_context
from app.repositories import get_subtopic_reference_questions
from app.schemas import (
    GenerationRequest,
    Question,
    WorkflowEvent,
    enum_value,
)
from app.workflow.dedup_inflight import (
    clear_in_flight_batch,
)
from app.workflow.engine_layout import (
    RunLayout,
    SlotLedger,
    _build_diversity_context,
    _complete_message,
    _drafting_message,
    _init_live_records,
    _initial_attempt_state,
    _is_sibling_collision,
    _make_event_factory,
    _resolve_passing_threshold,
    _resolve_run_layout,
    _shared_passage_payload,
    _start_message,
)
from app.workflow.live_job_store import (
    _finalize_live_job_progress,
    _handle_live_job_cancellation,
    _handle_live_job_failure,
)
from app.workflow.passage_prep import (
    SharedPassageState,
    _prepare_shared_passage_and_visual,
)
from app.workflow.review_loop import (
    _run_question_review_loop,
    count_llm_calls,
    run_question_review_loop,
)
from app.workflow.slot_worker import (
    SLOT_ERROR_RETRY_DELAY_SECONDS,
    SLOT_REPLENISH_DELAY_SECONDS,
    SlotWorkerContext,
    run_slot_worker,
)
from app.workflow.sse import iter_sse_events
from app.workflow.stream_emitter import (
    build_terminal_workflow_event,
    drain_event_queue,
    format_sse_event,
)

logger = logging.getLogger(__name__)

# Max buffered SSE events before workers wait for the consumer to catch up
_EVENT_QUEUE_MAX = 256

# Workers start slightly apart so siblings can see each other's in-flight stems for dedup
WORKER_STAGGER_SECONDS = 0.35
WORKER_STAGGER_MAX_SECONDS = 2.0
EVENT_POLL_SECONDS = 1.0  # how often the stream loop re-checks that the workers are still running

__all__ = [
    "EVENT_POLL_SECONDS",
    "SLOT_ERROR_RETRY_DELAY_SECONDS",
    "SLOT_REPLENISH_DELAY_SECONDS",
    "WORKER_STAGGER_MAX_SECONDS",
    "WORKER_STAGGER_SECONDS",
    "RunLayout",
    "SlotLedger",
    "SlotWorkerContext",
    "WorkflowRunResult",
    "_build_diversity_context",
    "_complete_message",
    "_drafting_message",
    "_init_live_records",
    "_initial_attempt_state",
    "_is_sibling_collision",
    "_make_event_factory",
    "_resolve_passing_threshold",
    "_resolve_run_layout",
    "_run_question_review_loop",
    "_shared_passage_payload",
    "_start_message",
    "build_terminal_workflow_event",
    "count_llm_calls",
    "drain_event_queue",
    "format_sse_event",
    "run_question_review_loop",
    "run_slot_worker",
    "run_workflow",
    "run_workflow_stream",
]


async def run_workflow_stream(req: GenerationRequest) -> AsyncGenerator[str, None]:
    """
    Streams multi-agent workflow events in real time as Server-Sent Events (SSE).
    Supports generating single or multiple questions in one shot (batch).
    Emits batch_progress and question_generated as each question finishes,
    culminating in workflow_complete with all staged questions for user confirmation.
    """
    layout = _resolve_run_layout(req)
    total_qty = layout.total_qty
    batch_id = layout.batch_id
    job_id = layout.job_id
    is_standalone_live_run = layout.is_standalone_live_run
    is_single_passage_set = layout.is_single_passage_set
    effective_passage_count = layout.effective_passage_count
    independent_count = layout.independent_count
    shared_passage_id = layout.shared_passage_id
    shared_passage_text = req.shared_stimulus

    # Auto-initialize Batch and Job records in PostgreSQL for live interactive runs
    if is_standalone_live_run:
        await _init_live_records(req, layout)

    make_event = _make_event_factory(req, batch_id, job_id)

    all_agent_usage: list[dict[str, Any]] = []
    tasks: list[asyncio.Task] = []
    monitor_task: asyncio.Task | None = None
    # Declared up front so cancellation handlers work even if the stream is closed early.
    outcomes_questions: list[dict[str, Any] | None] = []
    # Once the live job row is finalized, a later consumer disconnect must not overwrite it.
    job_finalized = False

    async def _record_consumer_gone() -> None:
        """Marks a standalone live job cancelled unless its row was already finalized."""
        if is_standalone_live_run and not job_finalized:
            await _handle_live_job_cancellation(
                job_id=job_id,
                batch_id=batch_id,
                completed_total=sum(1 for q in outcomes_questions if q is not None),
            )

    try:
        # Step 0: Draft Shared Reading Passage and Diagram (if passage-set mode)
        passage_state = SharedPassageState(passage_text=shared_passage_text)
        passage_events = _prepare_shared_passage_and_visual(
            req=req,
            batch_id=batch_id,
            shared_passage_id=shared_passage_id,
            shared_passage_text=shared_passage_text,
            is_single_passage_set=is_single_passage_set,
            effective_passage_count=effective_passage_count,
            independent_count=independent_count,
            total_qty=total_qty,
            make_event=make_event,
            passage_generator_fn=generate_passage_stimulus,
            image_generator_fn=generate_image_stimulus,
            state=passage_state,
        )
        async for p_evt in passage_events:
            yield format_sse_event(p_evt)

        shared_passage_text = passage_state.passage_text
        shared_passage_image_url = passage_state.image_url
        shared_passage_image_svg = passage_state.image_svg
        shared_passage_image_desc = passage_state.image_desc
        all_agent_usage.extend(passage_state.usage_breakdown)

        # Initial workflow start
        start_evt = make_event(
            event_type="workflow_start",
            agent_name="System",
            message=_start_message(layout, req),
            data={
                "total_questions": total_qty,
                "single_count": total_qty,
                "passage_count": effective_passage_count,
                "batch_id": batch_id,
                "passage_id": shared_passage_id,
                **_shared_passage_payload(layout, passage_state),
            },
        )
        yield format_sse_event(start_evt)

        # Worker Pool Concurrency
        semaphore = get_global_pipeline_semaphore()
        # Bounded so a stalled SSE consumer applies backpressure to the workers instead of letting
        # events (each with a full question payload) pile up in memory. Nothing is dropped.
        event_queue: asyncio.Queue[WorkflowEvent | None] = asyncio.Queue(maxsize=_EVENT_QUEUE_MAX)
        monitor_done = asyncio.Event()

        outcomes_questions = [None] * total_qty
        outcomes_rejections: list[dict[str, Any]] = []
        outcomes_errors: list[str] = []
        # Spend per slot across all of its attempts (calls feed MAX_LLM_CALLS_PER_SLOT)
        ledger = SlotLedger.for_slots(total_qty)
        shared_used_traps: list[str] = []
        shared_used_mistakes: list[str] = []

        # Reference pool for duplicate detection (same section & subtopic from DB)
        db_reference_pool: list[Question] = []
        try:
            sec_str = enum_value(req.section)
            db_reference_pool = await get_subtopic_reference_questions(
                section=sec_str,
                subtopic=req.subtopic,
                limit=50,
            )
        except Exception as ref_err:
            logger.warning("Could not load reference questions for deduplication: %s", ref_err)

        # Worker slot attempt limit is governed by config.WORKFLOW_MAX_WORKER_RETRIES + 1
        async def _staggered_worker(w_idx: int) -> None:
            if w_idx > 0:
                # Small bounded stagger so siblings can see each other's in-flight stems for dedup,
                # without delaying the last worker of a 50-question run by ~17 seconds.
                await asyncio.sleep(min(WORKER_STAGGER_SECONDS * w_idx, WORKER_STAGGER_MAX_SECONDS))
            with bind_log_context(batch_id=batch_id, run_id=req.run_id, slot=w_idx + 1):
                ctx = SlotWorkerContext(
                    idx=w_idx,
                    total_qty=total_qty,
                    req=req,
                    batch_id=batch_id,
                    job_id=job_id,
                    is_single_passage_set=is_single_passage_set,
                    effective_passage_count=effective_passage_count,
                    shared_passage_id=shared_passage_id,
                    shared_passage_text=shared_passage_text,
                    shared_passage_image_svg=shared_passage_image_svg,
                    shared_passage_image_url=shared_passage_image_url,
                    shared_passage_image_desc=shared_passage_image_desc,
                    ledger=ledger,
                    semaphore=semaphore,
                    event_queue=event_queue,
                    make_event=make_event,
                    db_reference_pool=db_reference_pool,
                    outcomes_questions=outcomes_questions,
                    outcomes_rejections=outcomes_rejections,
                    outcomes_errors=outcomes_errors,
                    shared_used_traps=shared_used_traps,
                    shared_used_mistakes=shared_used_mistakes,
                    is_standalone_live_run=is_standalone_live_run,
                    review_loop_fn=_run_question_review_loop,
                    passage_blueprints=passage_state.blueprints,
                )
                await run_slot_worker(ctx)

        tasks.extend([asyncio.create_task(_staggered_worker(i)) for i in range(total_qty)])

        async def _monitor_tasks() -> None:
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for idx_t, res in enumerate(results):
                    if isinstance(res, Exception):
                        logger.error(
                            "Worker task %s raised unhandled exception: %s",
                            idx_t + 1,
                            res,
                            exc_info=res,
                        )
            finally:
                # Never block here: when the queue is full (or this task is being cancelled) the
                # flag alone ends the consumer loop once it has drained what is queued.
                monitor_done.set()
                with contextlib.suppress(asyncio.QueueFull):
                    event_queue.put_nowait(None)

        monitor_task = asyncio.create_task(_monitor_tasks())

        async for chunk in drain_event_queue(event_queue, monitor_done, EVENT_POLL_SECONDS):
            yield chunk

        await monitor_task

        all_staged_questions = [q for q in outcomes_questions if q is not None]
        usage_totals = ledger.cumulative(passage_state)
        cumulative_tokens = usage_totals["total_tokens"]
        cumulative_prompt_tokens = usage_totals["total_prompt_tokens"]
        cumulative_completion_tokens = usage_totals["total_completion_tokens"]
        cumulative_cost = usage_totals["total_cost_usd"]
        all_agent_usage.extend(ledger.all_usage())

        if is_standalone_live_run:
            completed_total = len(all_staged_questions)
            await _finalize_live_job_progress(
                job_id=job_id,
                batch_id=batch_id,
                completed_total=completed_total,
                cumulative_tokens=cumulative_tokens,
                cumulative_prompt_tokens=cumulative_prompt_tokens,
                cumulative_completion_tokens=cumulative_completion_tokens,
                cumulative_cost=cumulative_cost,
            )
            job_finalized = True

        terminal_evt = build_terminal_workflow_event(
            make_event=make_event,
            layout=layout,
            req=req,
            total_qty=total_qty,
            all_staged_questions=all_staged_questions,
            outcomes_rejections=outcomes_rejections,
            outcomes_errors=outcomes_errors,
            usage_totals=usage_totals,
            all_agent_usage=all_agent_usage,
            passage_state=passage_state,
            batch_id=batch_id,
            shared_passage_id=shared_passage_id,
            is_single_passage_set=is_single_passage_set,
            shared_passage_payload_fn=_shared_passage_payload,
            complete_message_fn=_complete_message,
        )
        yield format_sse_event(terminal_evt)
    except asyncio.CancelledError:
        logger.info("Workflow stream cancelled by client disconnect.")
        for t in tasks:
            if not t.done():
                t.cancel()
        await _record_consumer_gone()
        raise
    except GeneratorExit:
        # Consumer closed the stream (client disconnect delivered as GeneratorExit, not
        # CancelledError): treat it exactly like a cancellation so jobs do not stay "running".
        logger.info("Workflow stream closed by consumer.")
        await _record_consumer_gone()
        raise
    except Exception as e:
        logger.error("Workflow stream error: %s", e, exc_info=True)
        err_msg = sanitize_error_text(e)
        # A job already finalized (completed) must not be flipped to failed by a late error
        if is_standalone_live_run and not job_finalized:
            await _handle_live_job_failure(
                job_id=job_id,
                batch_id=batch_id,
                error_msg=err_msg,
            )
        error_evt = make_event(
            event_type="workflow_error",
            agent_name="System Error",
            message=err_msg,
            data={"error": err_msg},
        )
        yield f"data: {error_evt.model_dump_json()}\n\n"
    finally:
        # Whatever the exit path (success, error, cancel, consumer close), never leave worker or
        # monitor tasks running: they would keep spending LLM tokens with nobody listening.
        pending = [t for t in (*tasks, monitor_task) if t is not None and not t.done()]
        for t in pending:
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        # Drop anything a cancelled worker left in the sibling-collision pool
        await clear_in_flight_batch(batch_id, job_id=job_id)


class WorkflowRunResult:
    def __init__(self, status: str, data: dict[str, Any] | None = None):
        self.status = status
        self.data = data or {}
        raw_q = self.data.get("question")
        self.question = Question(**raw_q) if raw_q else None
        self.stage_outcomes = self.data.get("stage_outcomes", {})
        self.rejection_data = self.data.get("rejection_data")


async def run_workflow(req: GenerationRequest) -> WorkflowRunResult:
    """Non-streaming execution of the multi-agent workflow."""
    status = "failed"
    final_data = {}
    last_rejection: dict[str, Any] = {}
    async for evt in iter_sse_events(run_workflow_stream(req)):
        etype = evt.get("event_type")
        if etype == "workflow_complete":
            status = "approved"
            final_data = evt.get("data", {})
        elif etype == "question_rejected":
            # One attempt was rejected; the slot may still succeed on a retry
            last_rejection = evt.get("data", {})
        elif etype == "workflow_rejected":
            status = "rejected_below_threshold"
            final_data = last_rejection or evt.get("data", {})
        elif etype == "workflow_error" and status != "rejected_below_threshold":
            status = "error"
            final_data = evt.get("data", {})
    return WorkflowRunResult(status, final_data)
