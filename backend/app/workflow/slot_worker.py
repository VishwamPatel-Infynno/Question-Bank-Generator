"""
slot_worker.py - Individual slot generation worker lifecycle.

Orchestrates the authoring, quality auditing, deduplication, diagramming,
and finalization attempts for a single question slot within a batch or passage set.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.agents.base import LLMNotConfiguredError
from app.core.config import config
from app.schemas import GenerationRequest, Question, WorkflowEvent
from app.workflow.dedup_inflight import (
    _refresh_duplicate_info_after_review,
    _run_deduplication_anti_collision_loop,
    remove_in_flight_draft,
)
from app.workflow.engine_layout import (
    SlotLedger,
    _build_diversity_context,
    _drafting_message,
    _initial_attempt_state,
    _is_sibling_collision,
    _resolve_passing_threshold,
)
from app.workflow.live_job_store import persist_live_question
from app.workflow.nodes import finalize_node, fused_generator_node, image_node
from app.workflow.passage_prep import (
    _build_batch_worker_request,
    _determine_item_diagram_requirement,
)
from app.workflow.review_loop import run_question_review_loop
from app.workflow.state import AgentWorkflowState

logger = logging.getLogger(__name__)

SLOT_REPLENISH_DELAY_SECONDS = 0.5  # pause before re-drafting a rejected slot
SLOT_ERROR_RETRY_DELAY_SECONDS = 1.0  # pause before retrying a slot after an error


@dataclass
class SlotWorkerContext:
    """Encapsulates all shared workflow resources required by a single slot worker."""

    idx: int
    total_qty: int
    req: GenerationRequest
    batch_id: str
    job_id: str | None
    is_single_passage_set: bool
    effective_passage_count: int
    shared_passage_id: str | None
    shared_passage_text: str | None
    shared_passage_image_svg: str | None
    shared_passage_image_url: str | None
    shared_passage_image_desc: str | None
    ledger: SlotLedger
    semaphore: asyncio.Semaphore
    event_queue: asyncio.Queue[WorkflowEvent | None]
    make_event: Callable[..., WorkflowEvent]
    db_reference_pool: list[Question]
    outcomes_questions: list[dict[str, Any] | None]
    outcomes_rejections: list[dict[str, Any]]
    outcomes_errors: list[str]
    shared_used_traps: list[str]
    shared_used_mistakes: list[str]
    is_standalone_live_run: bool
    review_loop_fn: Callable[..., Any] | None = None
    passage_blueprints: list[dict[str, str]] | None = None


async def run_slot_worker(ctx: SlotWorkerContext) -> None:
    """Executes the attempt loop for an individual question slot."""
    idx = ctx.idx
    total_qty = ctx.total_qty
    req = ctx.req
    batch_id = ctx.batch_id
    job_id = ctx.job_id
    ledger = ctx.ledger
    semaphore = ctx.semaphore
    event_queue = ctx.event_queue
    make_event = ctx.make_event
    db_reference_pool = ctx.db_reference_pool
    outcomes_questions = ctx.outcomes_questions
    outcomes_rejections = ctx.outcomes_rejections
    outcomes_errors = ctx.outcomes_errors
    shared_used_traps = ctx.shared_used_traps
    shared_used_mistakes = ctx.shared_used_mistakes
    is_standalone_live_run = ctx.is_standalone_live_run

    # Attempts per slot: the first draft plus the configured number of replenishments
    max_slot_attempts = config.WORKFLOW_MAX_WORKER_RETRIES + 1
    for attempt in range(max_slot_attempts):
        if attempt > 0 and ledger.budget_spent(idx, config.MAX_LLM_CALLS_PER_SLOT):
            logger.warning(
                "Question %s: LLM call budget exhausted after %s calls; not starting attempt %s.",
                idx + 1,
                ledger.calls[idx],
                attempt + 1,
            )
            break

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
                        effective_passage_count=ctx.effective_passage_count,
                        shared_passage_id=ctx.shared_passage_id,
                        shared_passage_text=ctx.shared_passage_text,
                        passage_blueprints=ctx.passage_blueprints,
                    )
                )
                if attempt > 0:
                    base_angle = item_req.thematic_angle or ""
                    retry_directive = (
                        f"(Slot Replenishment Attempt {attempt + 1}: You MUST formulate a completely distinct question "
                        f"testing a separate paragraph, claim, or variable from any previous rejected attempt)"
                    )
                    item_req.thematic_angle = (
                        f"{base_angle} • {retry_directive}" if base_angle else retry_directive
                    )

                diversity_context = _build_diversity_context(
                    idx, total_qty, attempt, shared_used_traps, shared_used_mistakes
                )

                # Ground with pgvector RAG exemplars and anti-collision neighbor constraints
                if config.ENABLE_PGVECTOR_RAG:
                    try:
                        from app.services.rag import retrieve_rag_exemplar_context

                        rag_ctx = await retrieve_rag_exemplar_context(item_req, limit=2)
                        if rag_ctx.prompt_context:
                            diversity_context = (
                                f"{diversity_context}\n\n{rag_ctx.prompt_context}"
                                if diversity_context
                                else rag_ctx.prompt_context
                            )
                    except Exception as exc:
                        logger.debug("RAG exemplar grounding skipped (%s).", exc)

                if total_qty > 1:
                    batch_prog_evt = make_event(
                        event_type="batch_progress",
                        agent_name="System",
                        message=_drafting_message(
                            idx, total_qty, attempt, is_passage_item, item_interaction
                        ),
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

                state = _initial_attempt_state(
                    item_req,
                    item_run_id,
                    batch_id,
                    diversity_context,
                    _resolve_passing_threshold(item_req, req),
                    slot_prior_calls=ledger.calls[idx],
                )
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

                # Ensure candidate draft is tagged with passage and batch metadata for accurate dedup
                cur_draft = state.get("current_draft")
                if isinstance(cur_draft, dict):
                    if ctx.shared_passage_id and not cur_draft.get("passage_id"):
                        cur_draft["passage_id"] = ctx.shared_passage_id
                    if ctx.shared_passage_text and not cur_draft.get("stimulus_text"):
                        cur_draft["stimulus_text"] = ctx.shared_passage_text
                    if batch_id and not cur_draft.get("batch_id"):
                        cur_draft["batch_id"] = batch_id

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
                    job_id=job_id,
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
                        "draft": state.get("current_draft"),
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
                async def _recheck_duplicate(st: AgentWorkflowState, _idx: int = idx) -> None:
                    await _refresh_duplicate_info_after_review(
                        st,
                        _idx,
                        req,
                        db_reference_pool,
                        outcomes_questions,
                        batch_key=batch_id,
                        job_id=job_id,
                    )

                review_fn = ctx.review_loop_fn or run_question_review_loop
                question_passed = await review_fn(
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
                        job_id=job_id,
                    )

                dup_info = state.get("duplicate_info") or {}
                is_hard_dup = bool(dup_info.get("is_duplicate", False))
                is_sibling_collision = _is_sibling_collision(dup_info, outcomes_questions)

                # Accept if question passed quality audit and does not collide with a sibling in this batch
                if question_passed and (
                    not is_sibling_collision or attempt == max_slot_attempts - 1
                ):
                    is_passage_item_check = (
                        ctx.is_single_passage_set and idx < ctx.effective_passage_count
                    )

                    # Attach shared passage diagram reference if applicable
                    if is_passage_item_check and (
                        ctx.shared_passage_image_svg or ctx.shared_passage_image_url
                    ):
                        state["image_url"] = ctx.shared_passage_image_url
                        state["image_svg"] = ctx.shared_passage_image_svg
                        state["image_description"] = ctx.shared_passage_image_desc
                        outcomes = state.setdefault("stage_outcomes", {})
                        outcomes["passage_visual_stimulus"] = {
                            "image_url": ctx.shared_passage_image_url,
                            "image_svg": ctx.shared_passage_image_svg,
                            "image_description": ctx.shared_passage_image_desc,
                            "note": "Visual stimulus belongs to shared reading passage",
                        }

                    requires_image = _determine_item_diagram_requirement(
                        state=state, is_passage_item=is_passage_item_check
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
                        completed_so_far = sum(1 for q in outcomes_questions if q is not None)
                        await persist_live_question(
                            final_q_dict=final_q_dict,
                            batch_id=batch_id,
                            job_id=job_id,
                            item_run_id=item_run_id,
                            shared_passage_id=ctx.shared_passage_id,
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

                    ledger.fold(idx, state)
                    attempt_state = None  # already counted
                    await remove_in_flight_draft(batch_id, idx, job_id=job_id)
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
                    "Question %s attempt %s/%s not satisfied (passed=%s, is_dup=%s). Auto-replenishing slot...",
                    idx + 1,
                    attempt + 1,
                    max_slot_attempts,
                    question_passed,
                    is_hard_dup,
                )
                ledger.fold(idx, state)
                attempt_state = None  # already counted
                await remove_in_flight_draft(batch_id, idx, job_id=job_id)
                await asyncio.sleep(SLOT_REPLENISH_DELAY_SECONDS)
                continue

        except asyncio.CancelledError:
            ledger.fold(idx, attempt_state)
            await remove_in_flight_draft(batch_id, idx, job_id=job_id)
            raise
        except Exception as worker_err:
            ledger.fold(idx, attempt_state)
            # A question staged in this failed attempt must not linger beside the retry
            outcomes_questions[idx] = None
            await remove_in_flight_draft(batch_id, idx, job_id=job_id)
            # A missing-credentials error cannot succeed on retry: fail fast with the message
            if (
                attempt < max_slot_attempts - 1
                and not isinstance(worker_err, LLMNotConfiguredError)
                and not ledger.budget_spent(idx, config.MAX_LLM_CALLS_PER_SLOT)
            ):
                logger.warning(
                    "Worker %s encountered error (attempt %s/%s): %s. Auto-replenishing slot in 1.0s...",
                    idx + 1,
                    attempt + 1,
                    max_slot_attempts,
                    worker_err,
                )
                await asyncio.sleep(SLOT_ERROR_RETRY_DELAY_SECONDS)
                continue

            logger.error(
                "Worker %s exhausted all %s replenishment attempts: %s",
                idx + 1,
                max_slot_attempts,
                worker_err,
                exc_info=worker_err,
            )
            outcomes_errors.append(str(worker_err))
            err_evt = make_event(
                event_type="question_failed",
                agent_name="System",
                message=f"Generation failed for Question {idx + 1} after retries: {worker_err!s}",
                data={"index": idx + 1, "error": str(worker_err)},
                run_id=req.run_id,
            )
            await event_queue.put(err_evt)
            return

    # Post-loop handling: if all attempts ended without an accepted draft
    if outcomes_questions[idx] is None:
        last_rej = outcomes_rejections[-1] if outcomes_rejections else None
        reason = (
            last_rej.get("reason", "Quality or duplication checks not met")
            if isinstance(last_rej, dict)
            else "Quality score threshold or deduplication requirements not satisfied after maximum attempts"
        )
        fail_msg = f"Slot {idx + 1}/{total_qty} failed to fulfill after {max_slot_attempts} attempts: {reason}"
        logger.error(
            "Worker %s exhausted all %s attempts without an accepted draft: %s",
            idx + 1,
            max_slot_attempts,
            reason,
        )
        outcomes_errors.append(fail_msg)
        err_evt = make_event(
            event_type="question_failed",
            agent_name="System",
            message=fail_msg,
            data={
                "index": idx + 1,
                "total": total_qty,
                "error": reason,
                "attempts_exhausted": max_slot_attempts,
            },
            run_id=req.run_id,
        )
        await event_queue.put(err_evt)
