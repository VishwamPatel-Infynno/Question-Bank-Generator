"""
engine.py - Core streaming workflow engine for MCAT Question Generation.

Orchestrates multi-agent pipelines for generating single or multiple questions
(passage sets or independent discretes). Streams real-time Server-Sent Events (SSE)
to the client, manages worker pool concurrency, and stages questions for user confirmation.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from app.agents.base import LLMNotConfiguredError
from app.agents.generator import generate_passage_stimulus
from app.agents.image_generator import generate_image_stimulus
from app.core.concurrency import get_global_pipeline_semaphore
from app.core.config import config
from app.core.logging import bind_log_context
from app.repositories import (
    get_batch_by_id,
    get_subtopic_reference_questions,
    save_batch,
    save_job,
)
from app.schemas import (
    ALT_TRAP_ROTATION,
    GenerationBatch,
    GenerationJob,
    GenerationRequest,
    Question,
    WorkflowEvent,
)
from app.workflow._section_utils import is_cars_section
from app.workflow.engine_helpers import (
    _build_batch_worker_request,
    _determine_item_diagram_requirement,
    _finalize_live_job_progress,
    _handle_live_job_cancellation,
    _handle_live_job_failure,
    _persist_live_question,
    _prepare_shared_passage_and_visual,
    _refresh_duplicate_info_after_review,
    _run_deduplication_anti_collision_loop,
    _run_question_review_loop,
    clear_in_flight_batch,
    count_llm_calls,
    remove_in_flight_draft,
)
from app.workflow.nodes import (
    finalize_node,
    fused_generator_node,
    image_node,
)
from app.workflow.state import AgentWorkflowState

logger = logging.getLogger(__name__)

# Max buffered SSE events before workers wait for the consumer to catch up
_EVENT_QUEUE_MAX = 256


async def run_workflow_stream(req: GenerationRequest) -> AsyncGenerator[str, None]:
    """
    Streams multi-agent workflow events in real time as Server-Sent Events (SSE).
    Supports generating single or multiple questions in one shot (batch).
    Emits batch_progress and question_generated as each question finishes,
    culminating in workflow_complete with all staged questions for user confirmation.
    """
    total_qty = max(1, req.questions_to_generate) if req.questions_to_generate is not None else 5
    batch_id = req.batch_id or str(uuid.uuid4())
    job_id = req.job_id or str(uuid.uuid4())
    is_standalone_live_run = req.job_id is None

    # Resolve binary passage mode: either all 5 linked or all 5 independent
    is_cars = is_cars_section(req.section)
    is_independent = not is_cars and (
        req.passage_mode == "independent"
        or str(req.passage_required).lower() in ("no", "false", "0")
        or (req.passage_question_count == 0 and not req.shared_stimulus)
    )

    if is_independent:
        effective_passage_count = 0
        is_single_passage_set = False
        independent_count = total_qty
    else:
        effective_passage_count = total_qty
        is_single_passage_set = True
        independent_count = 0

    shared_passage_id = req.passage_id or (str(uuid.uuid4()) if is_single_passage_set else None)
    shared_passage_text = req.shared_stimulus

    # Auto-initialize Batch and Job records in PostgreSQL for live interactive runs
    if is_standalone_live_run:
        try:
            now_iso = datetime.now(UTC).isoformat()
            sec_val = req.section.value if hasattr(req.section, "value") else str(req.section)
            diff_val = (
                req.difficulty.value if hasattr(req.difficulty, "value") else str(req.difficulty)
            )

            existing_b = await get_batch_by_id(batch_id)
            if not existing_b:
                batch_record = GenerationBatch(
                    id=batch_id,
                    section=sec_val,
                    subtopic=req.subtopic or f"{sec_val} Mini-Batch",
                    difficulty=diff_val,
                    passage_mode=req.passage_mode
                    or ("single_passage" if is_single_passage_set else "independent"),
                    target_count=total_qty,
                    actual_count=0,
                    total_jobs=1,
                    completed_jobs=0,
                    failed_jobs=0,
                    status="in_progress",
                    created_at=now_iso,
                )
                await save_batch(batch_record)

            job_record = GenerationJob(
                id=job_id,
                batch_id=batch_id,
                job_number=1,
                status="running",
                target_count=total_qty,
                actual_count=0,
                passage_id=shared_passage_id,
                created_at=now_iso,
                started_at=now_iso,
            )
            await save_job(job_record)
        except Exception as db_err:
            logger.warning(f"Live batch/job persistence skipped (DB offline): {db_err}")

    def make_event(
        event_type: str,
        agent_name: str,
        message: str,
        data: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> WorkflowEvent:
        """
        Factory closure that creates a WorkflowEvent, automatically injecting
        the current batch_id and job_id into event data when not already present.
        """
        event_data = dict(data or {})
        if "batch_id" not in event_data and batch_id:
            event_data["batch_id"] = batch_id
        if "job_id" not in event_data and job_id:
            event_data["job_id"] = job_id
        return WorkflowEvent(
            run_id=run_id or req.run_id,
            batch_id=batch_id,
            event_type=event_type,
            agent_name=agent_name,
            message=message,
            data=event_data,
        )

    all_staged_questions: list[dict[str, Any]] = []
    all_agent_usage: list[dict[str, Any]] = []
    tasks: list[asyncio.Task] = []
    monitor_task: asyncio.Task | None = None
    # Declared up front so cancellation handlers work even if the stream is closed early.
    outcomes_questions: list[dict[str, Any] | None] = []
    # Once the live job row is finalized, a later consumer disconnect must not overwrite it.
    job_finalized = False

    try:
        # Step 0: Draft Shared Reading Passage and Diagram (if passage-set mode)
        (
            passage_state,
            passage_events,
        ) = await _prepare_shared_passage_and_visual(
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
        )
        for p_evt in passage_events:
            yield f"data: {p_evt.model_dump_json()}\n\n"

        shared_passage_text = passage_state.passage_text
        shared_passage_image_url = passage_state.image_url
        shared_passage_image_svg = passage_state.image_svg
        shared_passage_image_desc = passage_state.image_desc
        passage_tokens = passage_state.tokens
        passage_prompt_tokens = passage_state.prompt_tokens
        passage_completion_tokens = passage_state.completion_tokens
        passage_cost = passage_state.cost
        all_agent_usage.extend(passage_state.usage_breakdown)

        # Initial workflow start
        if is_single_passage_set:
            start_msg = f"Starting AAMC MCAT Passage Set ({total_qty} questions) on shared reading passage..."
        elif total_qty == 1:
            start_msg = f"Starting AAMC MCAT Generation Workflow for {req.section.value} ({req.difficulty.value}) using Infynno Cognitive Architecture..."
        else:
            start_msg = f"Starting AAMC MCAT Independent Discretes Batch ({total_qty} standalone questions) in parallel..."

        start_evt = make_event(
            event_type="workflow_start",
            agent_name="System",
            message=start_msg,
            data={
                "total_questions": total_qty,
                "single_count": total_qty,
                "passage_count": effective_passage_count,
                "passage_question_count": effective_passage_count,
                "independent_question_count": independent_count,
                "batch_id": batch_id,
                "passage_id": shared_passage_id,
                "passage_mode": "single_passage" if is_single_passage_set else "independent",
                "shared_passage": shared_passage_text if is_single_passage_set else None,
                "shared_passage_image_svg": shared_passage_image_svg
                if is_single_passage_set
                else None,
                "shared_passage_image_url": shared_passage_image_url
                if is_single_passage_set
                else None,
                "shared_passage_image_description": shared_passage_image_desc
                if is_single_passage_set
                else None,
            },
        )
        yield f"data: {start_evt.model_dump_json()}\n\n"

        # Worker Pool Concurrency
        semaphore = get_global_pipeline_semaphore()
        # Bounded so a stalled SSE consumer applies backpressure to the workers instead of letting
        # events (each with a full question payload) pile up in memory. Nothing is dropped.
        event_queue: asyncio.Queue[WorkflowEvent | None] = asyncio.Queue(maxsize=_EVENT_QUEUE_MAX)
        monitor_done = asyncio.Event()

        outcomes_questions: list[dict[str, Any] | None] = [None] * total_qty
        outcomes_rejections: list[dict[str, Any]] = []
        outcomes_tokens: list[int] = [0] * total_qty
        outcomes_prompt_tokens: list[int] = [0] * total_qty
        outcomes_completion_tokens: list[int] = [0] * total_qty
        outcomes_costs: list[float] = [0.0] * total_qty
        outcomes_usage: list[list[dict[str, Any]]] = [[] for _ in range(total_qty)]
        # LLM calls spent per slot across all of its attempts (feeds MAX_LLM_CALLS_PER_SLOT)
        outcomes_calls: list[int] = [0] * total_qty
        shared_used_traps: list[str] = []
        shared_used_mistakes: list[str] = []

        # Reference pool for duplicate detection (same section & subtopic from DB)
        db_reference_pool: list[Question] = []
        try:
            sec_str = req.section.value if hasattr(req.section, "value") else str(req.section)
            db_reference_pool = await get_subtopic_reference_questions(
                section=sec_str,
                subtopic=req.subtopic,
                limit=50,
            )
        except Exception as ref_err:
            logger.warning(f"Could not load reference questions for deduplication: {ref_err}")

        def _fold_attempt_usage(idx: int, st: AgentWorkflowState | None) -> None:
            """Adds one attempt's complete spend (tokens, split, cost, breakdown) to the slot."""
            if not st:
                return
            outcomes_tokens[idx] += st.get("total_tokens", 0)
            outcomes_prompt_tokens[idx] += st.get("total_prompt_tokens", 0)
            outcomes_completion_tokens[idx] += st.get("total_completion_tokens", 0)
            outcomes_costs[idx] += st.get("total_cost_usd", 0.0)
            outcomes_usage[idx].extend(st.get("agent_usage_breakdown", []))
            outcomes_calls[idx] += count_llm_calls(st)

        def _slot_budget_spent(idx: int) -> bool:
            limit = config.MAX_LLM_CALLS_PER_SLOT
            return limit > 0 and outcomes_calls[idx] >= limit

        async def _worker(idx: int) -> None:
            max_slot_attempts = 3  # Try up to 3 times max per slot, then move forward
            for attempt in range(max_slot_attempts):
                if attempt > 0 and _slot_budget_spent(idx):
                    logger.warning(
                        f"Question {idx + 1}: LLM call budget exhausted after "
                        f"{outcomes_calls[idx]} calls; not starting attempt {attempt + 1}."
                    )
                    return
                # Reset per attempt so an error before the new state exists can never fold the
                # previous attempt's (already counted) usage a second time.
                attempt_state: AgentWorkflowState | None = None
                try:
                    async with semaphore:
                        item_req, item_run_id, is_passage_item, item_interaction = (
                            _build_batch_worker_request(
                                req=req,
                                idx=idx,
                                total_qty=total_qty,
                                batch_id=batch_id,
                                effective_passage_count=effective_passage_count,
                                shared_passage_id=shared_passage_id,
                                shared_passage_text=shared_passage_text,
                            )
                        )
                        if attempt > 0:
                            item_req.thematic_angle = (
                                f"Question Item {idx + 1} Attempt {attempt + 1}"
                            )

                        diversity_context = None
                        if total_qty > 1 or attempt > 0:
                            parts = [f"Item {idx + 1} of {total_qty} in this question set."]
                            if attempt > 0:
                                alt_trap = ALT_TRAP_ROTATION[
                                    (idx + attempt) % len(ALT_TRAP_ROTATION)
                                ]
                                parts.append(
                                    f"REPLENISHMENT ATTEMPT {attempt + 1}: The previous attempt did not satisfy quality or uniqueness standards. "
                                    f"You MUST formulate a fresh scenario testing cognitive trap '{alt_trap}' for variety."
                                )
                            elif shared_used_traps:
                                parts.append(
                                    f"Previously calibrated traps: {', '.join(shared_used_traps[-4:])}. Please select a complementary AAMC trap for variety."
                                )
                            if shared_used_mistakes:
                                parts.append(
                                    f"Previously targeted misconceptions: {', '.join(shared_used_mistakes[-3:])}. Diversify the targeted misconception."
                                )
                            diversity_context = " ".join(parts)

                        if total_qty > 1:
                            if attempt > 0:
                                worker_msg = f"[{idx + 1}/{total_qty}] Calibrating alternative scientific angle for Question {idx + 1}..."
                            elif is_passage_item:
                                worker_msg = f"[{idx + 1}/{total_qty}] Writing linked {item_interaction.replace('_', ' ').title()} question from shared passage..."
                            else:
                                worker_msg = f"[{idx + 1}/{total_qty}] Writing independent {item_interaction.replace('_', ' ').title()} question (direct question)..."

                            batch_prog_evt = make_event(
                                event_type="batch_progress",
                                agent_name="System",
                                message=worker_msg,
                                data={
                                    "current_index": idx + 1,
                                    "total_count": total_qty,
                                    "interaction_type": item_interaction,
                                    "passage_required": item_req.passage_required,
                                    "passage_mode": item_req.passage_mode,
                                    "passage_id": item_req.passage_id,
                                    "is_passage_item": is_passage_item,
                                    "batch_id": batch_id,
                                    "stage": "drafting",
                                },
                                run_id=item_run_id,
                            )
                            await event_queue.put(batch_prog_evt)

                        effective_threshold = (
                            getattr(item_req, "passing_threshold", None)
                            or getattr(req, "passing_threshold", None)
                            or config.PASSING_SCORE_THRESHOLD
                        )
                        state: AgentWorkflowState = {
                            "request": item_req.model_dump(),
                            "run_id": item_run_id,
                            "batch_id": batch_id,
                            "iteration_count": 1,
                            "iterations_history": [],
                            "log_messages": [],
                            "total_tokens": 0,
                            "total_prompt_tokens": 0,
                            "total_completion_tokens": 0,
                            "total_cost_usd": 0.0,
                            "agent_usage_breakdown": [],
                            # Marks results produced from mock fixtures so they are never mistaken for real
                            "stage_outcomes": {"offline_mode": True} if config.OFFLINE_MODE else {},
                            "diversity_context": diversity_context,
                            "passing_threshold": effective_threshold,
                            "slot_prior_calls": outcomes_calls[idx],
                        }
                        attempt_state = state

                        # Step 1: Question Writer & Reviewer (Fused Authoring & 100-pt Audit)
                        gen_evt = make_event(
                            event_type="agent_start",
                            agent_name="Question Writer & Reviewer",
                            message=f"Drafting and auditing question {idx + 1}/{total_qty} (Single Choice)...",
                            data={
                                "index": idx + 1,
                                "total": total_qty,
                                "stage": "drafting",
                                "interaction_type": item_interaction,
                                "passage_required": item_req.passage_required,
                            },
                            run_id=item_run_id,
                        )
                        await event_queue.put(gen_evt)

                        gen_res = await fused_generator_node(state)
                        state.update(gen_res)

                        # Step 1.5: Deduplication Check & Anti-Collision Loop
                        await _run_deduplication_anti_collision_loop(
                            state=state,
                            idx=idx,
                            total_qty=total_qty,
                            item_run_id=item_run_id,
                            req=req,
                            db_reference_pool=db_reference_pool,
                            outcomes_questions=outcomes_questions,
                            event_queue=event_queue,
                            make_event=make_event,
                            batch_key=batch_id,
                        )

                        cur_draft = state.get("current_draft") or {}
                        c_trap = cur_draft.get("primary_trap")
                        c_mistake = cur_draft.get("likely_mistake_pattern")
                        if c_trap and c_trap not in shared_used_traps:
                            shared_used_traps.append(c_trap)
                        if c_mistake and c_mistake not in shared_used_mistakes:
                            shared_used_mistakes.append(c_mistake)

                        gen_usage = state.get("latest_usage", {})
                        self_score = (state.get("current_review") or {}).get("total_score")
                        usage_note = (
                            f"{gen_usage.get('total_tokens', 0)} tokens, "
                            f"${gen_usage.get('cost_usd', 0.0):.5f}"
                        )
                        draft_message = (
                            f"Draft authored and audited for Question {idx + 1} "
                            f"(Score: {self_score}/100, {usage_note})."
                            if self_score is not None
                            else f"Draft authored for Question {idx + 1} "
                            f"(independent review next, {usage_note})."
                        )
                        gen_done_evt = make_event(
                            event_type="agent_complete",
                            agent_name="Question Writer & Reviewer",
                            message=draft_message,
                            data={
                                "draft": state["current_draft"],
                                "review": state.get("current_review"),
                                "score": self_score,
                                "latest_usage": gen_usage,
                                "index": idx + 1,
                                "total": total_qty,
                                "stage": "drafting",
                            },
                            run_id=item_run_id,
                        )
                        await event_queue.put(gen_done_evt)

                        # Step 2: Quality Review / Remediation Loop
                        async def _recheck_duplicate(
                            st: AgentWorkflowState, _idx: int = idx
                        ) -> None:
                            await _refresh_duplicate_info_after_review(
                                st,
                                _idx,
                                req,
                                db_reference_pool,
                                outcomes_questions,
                                batch_key=batch_id,
                            )

                        question_passed = await _run_question_review_loop(
                            state=state,
                            idx=idx,
                            total_qty=total_qty,
                            item_run_id=item_run_id,
                            event_queue=event_queue,
                            make_event=make_event,
                            # Offline mock fixtures cannot change their stem when told to, so the
                            # duplicate-rewrite loop only applies to real generations
                            recheck_duplicate=None if config.OFFLINE_MODE else _recheck_duplicate,
                        )

                        if question_passed:
                            await _refresh_duplicate_info_after_review(
                                state,
                                idx,
                                req,
                                db_reference_pool,
                                outcomes_questions,
                                batch_key=batch_id,
                            )

                        dup_info = state.get("duplicate_info") or {}
                        is_hard_dup = bool(dup_info.get("is_duplicate", False))
                        matched_id = str(dup_info.get("matched_question_id") or "")
                        sibling_ids = {
                            str(q.get("id"))
                            for q in outcomes_questions
                            if q is not None and "id" in q
                        }
                        is_sibling_collision = is_hard_dup and (
                            matched_id in sibling_ids or matched_id.startswith("in_flight_")
                        )

                        # Accept if question passed quality audit and does not collide with a sibling in this batch
                        if question_passed and (
                            not is_sibling_collision or attempt == max_slot_attempts - 1
                        ):
                            is_passage_item_check = (
                                is_single_passage_set and idx < effective_passage_count
                            )

                            # Attach shared passage diagram reference if applicable
                            if is_passage_item_check and (
                                shared_passage_image_svg or shared_passage_image_url
                            ):
                                state["image_url"] = shared_passage_image_url
                                state["image_svg"] = shared_passage_image_svg
                                state["image_description"] = shared_passage_image_desc
                                outcomes = state.setdefault("stage_outcomes", {})
                                outcomes["passage_visual_stimulus"] = {
                                    "image_url": shared_passage_image_url,
                                    "image_svg": shared_passage_image_svg,
                                    "image_description": shared_passage_image_desc,
                                    "note": "Visual stimulus belongs to shared reading passage",
                                }

                            requires_image = _determine_item_diagram_requirement(
                                state=state,
                                idx=idx,
                                is_passage_item=is_passage_item_check,
                            )

                            if requires_image:
                                img_start_evt = make_event(
                                    event_type="agent_start",
                                    agent_name="Diagram & Chart Maker",
                                    message=f"Drawing visual stimulus diagram for Question {idx + 1}...",
                                    data={
                                        "index": idx + 1,
                                        "total": total_qty,
                                        "stage": "image",
                                    },
                                    run_id=item_run_id,
                                )
                                await event_queue.put(img_start_evt)

                                img_res = await image_node(state)
                                state.update(img_res)

                                img_done_evt = make_event(
                                    event_type="agent_complete",
                                    agent_name="Diagram & Chart Maker",
                                    message=f"Visual diagram drawn and attached to Question {idx + 1}.",
                                    data={
                                        "has_svg": bool(state.get("image_svg")),
                                        "image_url": state.get("image_url"),
                                        "usage": state.get("latest_usage"),
                                        "index": idx + 1,
                                        "total": total_qty,
                                        "stage": "image",
                                    },
                                    run_id=item_run_id,
                                )
                                await event_queue.put(img_done_evt)

                            # Finalize Question Object
                            fin_res = await finalize_node(state)
                            state.update(fin_res)

                            final_q_dict = state["final_question"]
                            final_q_dict["index"] = idx + 1
                            final_q_dict["batch_id"] = batch_id
                            final_q_dict["job_id"] = job_id
                            outcomes_questions[idx] = final_q_dict

                            if is_standalone_live_run:
                                completed_so_far = sum(
                                    1 for q in outcomes_questions if q is not None
                                )
                                await _persist_live_question(
                                    final_q_dict=final_q_dict,
                                    batch_id=batch_id,
                                    job_id=job_id,
                                    item_run_id=item_run_id,
                                    shared_passage_id=shared_passage_id,
                                    completed_so_far=completed_so_far,
                                    idx=idx,
                                )

                            # Emit question_generated event
                            q_gen_evt = make_event(
                                event_type="question_generated",
                                agent_name="System",
                                message=f"Question {idx + 1} of {total_qty} passed quality check (Score: {final_q_dict.get('final_score')}/100) and is ready for review.",
                                data={
                                    "question": final_q_dict,
                                    "index": idx + 1,
                                    "total": total_qty,
                                    "batch_id": batch_id,
                                    "job_id": job_id,
                                    "stage": "completed",
                                },
                                run_id=item_run_id,
                            )
                            await event_queue.put(q_gen_evt)

                            _fold_attempt_usage(idx, state)
                            attempt_state = None  # already counted
                            await remove_in_flight_draft(batch_id, idx)
                            return  # Successfully completed this slot!

                        # Rejection or collision - auto-replenish slot
                        rej_data = state.get("rejection_data") or {
                            "index": idx + 1,
                            "stage": "rejected",
                            "reason": "Duplicate collision"
                            if is_hard_dup
                            else "Quality score below threshold",
                        }
                        outcomes_rejections.append(rej_data)
                        logger.warning(
                            f"Question {idx + 1} attempt {attempt + 1}/{max_slot_attempts} not satisfied "
                            f"(passed={question_passed}, is_dup={is_hard_dup}). Auto-replenishing slot..."
                        )
                        _fold_attempt_usage(idx, state)
                        attempt_state = None  # already counted
                        await remove_in_flight_draft(batch_id, idx)
                        await asyncio.sleep(0.5)
                        continue

                except asyncio.CancelledError:
                    _fold_attempt_usage(idx, attempt_state)
                    await remove_in_flight_draft(batch_id, idx)
                    raise
                except Exception as worker_err:
                    _fold_attempt_usage(idx, attempt_state)
                    # A question staged in this failed attempt must not linger beside the retry
                    outcomes_questions[idx] = None
                    await remove_in_flight_draft(batch_id, idx)
                    # A missing-credentials error cannot succeed on retry: fail fast with the message
                    if (
                        attempt < max_slot_attempts - 1
                        and not isinstance(worker_err, LLMNotConfiguredError)
                        and not _slot_budget_spent(idx)
                    ):
                        logger.warning(
                            f"Worker {idx + 1} encountered error (attempt {attempt + 1}/{max_slot_attempts}): {worker_err}. Auto-replenishing slot in 1.0s..."
                        )
                        await asyncio.sleep(1.0)
                        continue

                    logger.error(
                        f"Worker {idx + 1} exhausted all {max_slot_attempts} replenishment attempts: {worker_err}",
                        exc_info=worker_err,
                    )
                    if total_qty > 1:
                        err_evt = make_event(
                            event_type="question_failed",
                            agent_name="System",
                            message=f"Generation failed for Question {idx + 1} after retries: {worker_err!s}",
                            data={"index": idx + 1, "error": str(worker_err)},
                            run_id=req.run_id,
                        )
                        await event_queue.put(err_evt)
                    else:
                        err_evt = make_event(
                            event_type="workflow_error",
                            agent_name="System",
                            message=f"Generation failed for Question {idx + 1}: {worker_err!s}",
                            data={"index": idx + 1, "error": str(worker_err)},
                            run_id=req.run_id,
                        )
                        await event_queue.put(err_evt)
                    return

        async def _staggered_worker(w_idx: int) -> None:
            if w_idx > 0:
                # Small bounded stagger so siblings can see each other's in-flight stems for dedup,
                # without delaying the last worker of a 50-question run by ~17 seconds.
                await asyncio.sleep(min(0.35 * w_idx, 2.0))
            with bind_log_context(batch_id=batch_id, run_id=req.run_id, slot=w_idx + 1):
                await _worker(w_idx)

        tasks.extend([asyncio.create_task(_staggered_worker(i)) for i in range(total_qty)])

        async def _monitor_tasks():
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for idx_t, res in enumerate(results):
                    if isinstance(res, Exception):
                        logger.error(
                            f"Worker task {idx_t + 1} raised unhandled exception: {res}",
                            exc_info=res,
                        )
            finally:
                # Never block here: when the queue is full (or this task is being cancelled) the
                # flag alone ends the consumer loop once it has drained what is queued.
                monitor_done.set()
                with contextlib.suppress(asyncio.QueueFull):
                    event_queue.put_nowait(None)

        monitor_task = asyncio.create_task(_monitor_tasks())

        while True:
            try:
                evt = await asyncio.wait_for(event_queue.get(), timeout=1.0)
            except TimeoutError:
                if monitor_done.is_set() and event_queue.empty():
                    break
                continue
            if evt is None:
                break
            yield f"data: {evt.model_dump_json()}\n\n"

        await monitor_task

        all_staged_questions = [q for q in outcomes_questions if q is not None]
        cumulative_tokens = sum(outcomes_tokens) + passage_tokens
        cumulative_prompt_tokens = sum(outcomes_prompt_tokens) + passage_prompt_tokens
        cumulative_completion_tokens = sum(outcomes_completion_tokens) + passage_completion_tokens
        cumulative_cost = round(sum(outcomes_costs) + passage_cost, 7)
        for usage_list in outcomes_usage:
            all_agent_usage.extend(usage_list)

        def _cumulative_usage_dict() -> dict[str, Any]:
            return {
                "total_tokens": cumulative_tokens,
                "total_prompt_tokens": cumulative_prompt_tokens,
                "total_completion_tokens": cumulative_completion_tokens,
                "total_cost_usd": cumulative_cost,
            }

        if not all_staged_questions:
            if is_standalone_live_run:
                # Nothing was produced: mark the job failed instead of leaving it "running".
                await _finalize_live_job_progress(
                    job_id=job_id,
                    batch_id=batch_id,
                    completed_total=0,
                    total_qty=total_qty,
                    cumulative_tokens=cumulative_tokens,
                    cumulative_prompt_tokens=cumulative_prompt_tokens,
                    cumulative_completion_tokens=cumulative_completion_tokens,
                    cumulative_cost=cumulative_cost,
                )
                job_finalized = True
            if outcomes_rejections:
                rej_msg = f"All {total_qty} questions in the run were rejected by the Quality Gate (score <= {req.passing_threshold or config.PASSING_SCORE_THRESHOLD})."
                rej_evt = make_event(
                    event_type="workflow_rejected",
                    agent_name="Quality Gate",
                    message=rej_msg,
                    data={
                        "rejections": outcomes_rejections,
                        "total_rejected": len(outcomes_rejections),
                        "cumulative_usage": _cumulative_usage_dict(),
                    },
                )
                yield f"data: {rej_evt.model_dump_json()}\n\n"
                return
            else:
                error_msg = (
                    f"All {total_qty} questions in the run failed to generate after retries."
                )
                error_evt = make_event(
                    event_type="workflow_error",
                    agent_name="System",
                    message=error_msg,
                    data={"error": error_msg, "cumulative_usage": _cumulative_usage_dict()},
                )
                yield f"data: {error_evt.model_dump_json()}\n\n"
                return

        if is_single_passage_set and total_qty > 1:
            complete_msg = f"Passage Set generated! {len(all_staged_questions)} questions linked to shared reading passage staged for Review. Total: {cumulative_tokens} tokens (${cumulative_cost:.5f})."
        elif total_qty > 1:
            complete_msg = f"Parallel batch generation completed! {len(all_staged_questions)} of {total_qty} questions staged for User Confirmation. Total: {cumulative_tokens} tokens (${cumulative_cost:.5f})."
        else:
            complete_msg = f"Multi-Agent workflow completed! Candidate question scored {all_staged_questions[0].get('final_score', 95) if all_staged_questions else 95}/100 and is staged for Confirmation. Total: {cumulative_tokens} tokens (${cumulative_cost:.5f})."

        complete_evt = make_event(
            event_type="workflow_complete",
            agent_name="System",
            message=complete_msg,
            data={
                "questions": all_staged_questions,
                "question": all_staged_questions[0] if all_staged_questions else None,
                "batch_id": batch_id,
                "passage_id": shared_passage_id if is_single_passage_set else None,
                "passage_mode": "single_passage" if is_single_passage_set else "independent",
                "passage_question_count": effective_passage_count,
                "independent_question_count": independent_count,
                "shared_passage": shared_passage_text if is_single_passage_set else None,
                "shared_passage_image_svg": shared_passage_image_svg
                if is_single_passage_set
                else None,
                "shared_passage_image_url": shared_passage_image_url
                if is_single_passage_set
                else None,
                "shared_passage_image_description": shared_passage_image_desc
                if is_single_passage_set
                else None,
                "cumulative_usage": {
                    "total_tokens": cumulative_tokens,
                    "total_prompt_tokens": cumulative_prompt_tokens,
                    "total_completion_tokens": cumulative_completion_tokens,
                    "total_cost_usd": cumulative_cost,
                },
                "usage_breakdown": all_agent_usage,
            },
        )
        # Finalize BEFORE the terminal event: a client that closes the stream on
        # workflow_complete must not leave the job cancelled or its spend unsaved.
        if is_standalone_live_run:
            completed_total = sum(1 for q in outcomes_questions if q is not None)
            await _finalize_live_job_progress(
                job_id=job_id,
                batch_id=batch_id,
                completed_total=completed_total,
                total_qty=total_qty,
                cumulative_tokens=cumulative_tokens,
                cumulative_prompt_tokens=cumulative_prompt_tokens,
                cumulative_completion_tokens=cumulative_completion_tokens,
                cumulative_cost=cumulative_cost,
            )
            job_finalized = True
        yield f"data: {complete_evt.model_dump_json()}\n\n"
    except asyncio.CancelledError:
        logger.info("Workflow stream cancelled by client disconnect.")
        for t in tasks:
            if not t.done():
                t.cancel()
        if is_standalone_live_run and not job_finalized:
            completed_total = sum(1 for q in outcomes_questions if q is not None)
            await _handle_live_job_cancellation(
                job_id=job_id,
                batch_id=batch_id,
                completed_total=completed_total,
            )
        raise
    except GeneratorExit:
        # Consumer closed the stream (client disconnect delivered as GeneratorExit, not
        # CancelledError): treat it exactly like a cancellation so jobs do not stay "running".
        logger.info("Workflow stream closed by consumer.")
        if is_standalone_live_run and not job_finalized:
            completed_total = sum(1 for q in outcomes_questions if q is not None)
            await _handle_live_job_cancellation(
                job_id=job_id,
                batch_id=batch_id,
                completed_total=completed_total,
            )
        raise
    except Exception as e:
        logger.error(f"Workflow stream error: {e}")
        if is_standalone_live_run:
            await _handle_live_job_failure(
                job_id=job_id,
                batch_id=batch_id,
                error_msg=str(e),
            )
        err_msg = str(e)
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
        await clear_in_flight_batch(batch_id)


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
    async for raw_chunk in run_workflow_stream(req):
        line = raw_chunk.strip()
        if line.startswith("data: "):
            evt = json.loads(line[6:])
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
            elif etype == "workflow_error":
                if status != "rejected_below_threshold":
                    status = "error"
                    final_data = evt.get("data", {})
    return WorkflowRunResult(status, final_data)
