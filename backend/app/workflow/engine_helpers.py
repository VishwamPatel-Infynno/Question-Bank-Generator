"""
engine_helpers.py - Helper functions for the workflow engine.

Extracted from engine.py to keep the main streaming generator focused
on orchestration. Contains request building, visual requirements determination,
passage drafting and visual preparation, review/critique loops, and live job persistence.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.agents.generator import generate_passage_stimulus
from app.agents.image_generator import generate_image_stimulus
from app.agents.validators import (
    Violation,
    blocking,
    format_violations,
    sanitize_draft_dashes,
    validate_question_draft,
)
from app.core.config import config
from app.repositories import (
    promote_completed_batch_questions,
    refresh_batch_aggregates,
    save_question,
    update_job_progress,
)
from app.schemas import (
    ALT_TRAP_ROTATION,
    KNOWN_VISUAL_TYPES,
    GenerationRequest,
    OptionChoice,
    Question,
    QuestionDraft,
    ReviewScore,
    WorkflowEvent,
    determine_question_status,
)
from app.services.deduplication import evaluate_duplicate
from app.workflow._section_utils import is_cars_section
from app.workflow.nodes import (
    blind_solver_node,
    build_review_update,
    build_solver_update,
    build_usage_only_update,
    fused_generator_node,
    regenerator_node,
    reject_node,
    reviewer_node,
    run_review_and_solve,
)
from app.workflow.routes import route_after_review
from app.workflow.state import AgentWorkflowState

logger = logging.getLogger(__name__)


@dataclass
class SharedPassageState:
    """Encapsulates the generated state, tokens, and cost of a shared reading passage and diagram."""

    passage_text: str | None = None
    image_url: str | None = None
    image_svg: str | None = None
    image_desc: str | None = None
    tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    usage_breakdown: list[dict[str, Any]] = field(default_factory=list)


def _build_batch_worker_request(
    req: GenerationRequest,
    idx: int,
    total_qty: int,
    batch_id: str | None,
    effective_passage_count: int,
    shared_passage_id: str | None,
    shared_passage_text: str | None,
) -> tuple[GenerationRequest, str, bool, str]:
    """
    Builds an isolated GenerationRequest for an individual question worker within a batch,
    resolving whether the question is passage-linked or independent (strictly single-choice MCAT format).

    Args:
        req: The parent GenerationRequest for the batch.
        idx: Zero-based index of this question within the batch.
        total_qty: Total number of questions in the batch.
        batch_id: UUID of the parent batch record.
        effective_passage_count: Number of questions that are passage-linked (0 = all independent).
        shared_passage_id: UUID shared by all passage-linked items in this batch.
        shared_passage_text: Pre-generated passage text, or None if not yet generated.

    Returns:
        Tuple of (item_req, item_run_id, is_passage_item, item_interaction) where:
        - item_req: Cloned GenerationRequest scoped to a single question.
        - item_run_id: Unique UUID for this question's run.
        - is_passage_item: True if this question is linked to the shared passage.
        - item_interaction: Always "single_choice" (official MCAT format).
    """
    item_run_id = str(uuid.uuid4()) if total_qty > 1 else req.run_id
    is_passage_item = idx < effective_passage_count
    item_interaction = "single_choice"

    if is_passage_item:
        item_passage = "Yes"
        item_passage_mode = "single_passage"
        item_passage_id = shared_passage_id
        item_stimulus = shared_passage_text
    else:
        item_passage = "No"
        item_passage_mode = "independent"
        item_passage_id = None
        item_stimulus = None

    # For independent questions in science sections, when AI diagrams are permitted,
    # calibrate authentic AAMC frequency (~40%: items 0 and 2 in every 5 questions, or single question)
    sec_is_cars = is_cars_section(req.section)
    has_diagrams_enabled = (
        req.allow_ai_images or req.require_image or req.visual_type in KNOWN_VISUAL_TYPES
    )
    should_require_item_image = bool(
        not sec_is_cars
        and not is_passage_item
        and has_diagrams_enabled
        and (total_qty == 1 or (idx % 5 in (0, 2)))
    )

    item_req = req.model_copy(
        update={
            "run_id": item_run_id,
            "batch_id": batch_id,
            "questions_to_generate": 1,
            "interaction_type": item_interaction,
            "passage_required": item_passage,
            "passage_mode": item_passage_mode,
            "passage_id": item_passage_id,
            "shared_stimulus": item_stimulus,
            "require_image": should_require_item_image or req.require_image,
            "thematic_angle": req.thematic_angle or f"Question Item {idx + 1}",
            "visual_type": "AI_FLUX_Image"
            if (should_require_item_image or req.require_image)
            else req.visual_type,
        }
    )
    return item_req, item_run_id, is_passage_item, item_interaction


def _determine_item_diagram_requirement(
    state: AgentWorkflowState,
    idx: int,
    is_passage_item: bool,
) -> bool:
    """
    Evaluates whether a specific question item within a batch requires a visual stimulus diagram.

    Respects section type (CARS never has diagrams), passage attachment (passage-linked items
    share the passage diagram and never have their own), explicit image flags from the request,
    and the autonomous AI decision stored in the generated draft.

    Args:
        state: Current AgentWorkflowState for this question worker.
        idx: Zero-based index of this question (informational; not used in logic).
        is_passage_item: Whether this question is linked to the shared reading passage.

    Returns:
        True if a visual stimulus diagram should be generated for this question.
    """
    _ = idx  # Informational parameter reserved for item-index specific diagram rules
    req_data = state["request"]
    sec_raw = req_data.get("section", "")
    section_val = sec_raw.value if hasattr(sec_raw, "value") else str(sec_raw)
    allow_ai_images = req_data.get("allow_ai_images", False)
    explicit_image = req_data.get("require_image", False)
    visual_type = req_data.get("visual_type", "None")

    # CARS strictly has no figures, data tables or diagrams in official AAMC format
    if is_cars_section(section_val):
        return False
    if is_passage_item:
        # Passage question items share the passage diagram; they never have internal images
        return False

    # Check if visual generation is permitted at all
    visuals_permitted = allow_ai_images or explicit_image or visual_type in KNOWN_VISUAL_TYPES
    if not visuals_permitted:
        return False

    if explicit_image:
        return True

    # Autonomous AI determination for independent items
    return bool(state.get("current_draft", {}).get("image_needed", False))


def count_llm_calls(state: AgentWorkflowState) -> int:
    """LLM calls recorded so far in this attempt (mock/heuristic results count as zero)."""
    return sum(int(e.get("calls", 0) or 0) for e in state.get("agent_usage_breakdown", []))


def llm_budget_exhausted(state: AgentWorkflowState) -> bool:
    """True once this slot (earlier attempts plus the current one) has spent its call budget."""
    limit = config.MAX_LLM_CALLS_PER_SLOT
    if limit <= 0:
        return False
    return state.get("slot_prior_calls", 0) + count_llm_calls(state) >= limit


async def _regenerate(state: AgentWorkflowState) -> dict[str, Any]:
    """Regenerates the draft and marks it for a free duplicate re-check before the next review."""
    result = await regenerator_node(state)
    state["regenerated_pending_dedup"] = True
    return result


def _duplicate_blockers(state: AgentWorkflowState) -> list[Violation]:
    """A hard duplicate of an existing question is a defect to fix before any paid review."""
    info = state.get("duplicate_info") or {}
    if not info.get("is_duplicate"):
        return []
    pct = int(float(info.get("similarity_score", 0.0)) * 100)
    matched = (info.get("matched_question_stem") or "an existing question")[:240]
    return [
        Violation(
            "duplicate_question",
            f"Too similar ({pct}%) to: {matched}. Rewrite it to test a clearly different scenario.",
        )
    ]


def _apply_deterministic_gate(state: AgentWorkflowState) -> list[Violation]:
    """Auto-repairs forbidden dashes, then runs the free structural validators on the draft.

    Mutates ``state`` (repaired draft, validation record in ``stage_outcomes``) and returns all
    findings. Blocking findings must be remediated before any LLM review is spent on the draft.
    """
    draft = QuestionDraft(**state["current_draft"])
    if sanitize_draft_dashes(draft):
        state["current_draft"] = draft.model_dump()
    # Passage text is owned by the shared-passage pipeline, so passage rules are not checked here.
    # Offline mock fixtures are canned and cannot be repaired, so they are exempt from the
    # blocking length rule (real runs are not).
    violations = validate_question_draft(
        draft, check_passage=False, enforce_length_spread=not config.OFFLINE_MODE
    )
    outcomes = dict(state.get("stage_outcomes", {}))
    outcomes["deterministic_validation"] = {
        "iteration": state.get("iteration_count", 1),
        "blocking": [v.code for v in blocking(violations)],
        "warnings": [v.code for v in violations if v.severity == "warning"],
    }
    state["stage_outcomes"] = outcomes
    return violations


def _validator_review(blockers: list[Violation]) -> dict[str, Any]:
    """Builds a failing review carrying validator findings so the regenerator can act on them."""
    return ReviewScore(
        authenticity_score=15,
        clarity_score=15,
        distractor_score=15,
        explanation_score=15,
        total_score=60,
        weaknesses=[v.message for v in blockers],
        recommendations=[f"Fix structural defect [{v.code}]: {v.message}" for v in blockers],
        passed=False,
    ).model_dump()


async def _run_question_review_loop(
    state: AgentWorkflowState,
    idx: int,
    total_qty: int,
    item_run_id: str,
    event_queue: asyncio.Queue[WorkflowEvent | None],
    make_event: Callable[..., WorkflowEvent],
    recheck_duplicate: Callable[[AgentWorkflowState], Awaitable[None]] | None = None,
) -> bool:
    """
    Executes the quality review, critique, remediation (regeneration), and quality gate routing
    for a question draft. Integrates Blind-Solver Dual Validation to verify indisputability.

    Returns:
        True if question passes quality benchmark; False if rejected.
    """
    while True:
        iteration = state.get("iteration_count", 1)

        prefetched_solver = None

        # Hard call budget: stop before paying for another review, solve or rewrite
        if llm_budget_exhausted(state):
            state.update(await reject_node(state))
            rej_data = state.get("rejection_data") or {}
            if isinstance(rej_data, dict):
                rej_data["index"] = idx + 1
                rej_data["stage"] = "rejected"
                rej_data["reason"] = (
                    f"LLM call budget ({config.MAX_LLM_CALLS_PER_SLOT}) exhausted for this question slot."
                )
            await event_queue.put(
                make_event(
                    event_type="question_rejected",
                    agent_name="Quality Gate",
                    message=f"Question {idx + 1} stopped: LLM call budget exhausted.",
                    data=rej_data,
                    run_id=item_run_id,
                )
            )
            return False

        # Step 0: Free checks before any LLM review is spent: structure, then (after a rewrite)
        # duplicate similarity, so a duplicate is rewritten without being reviewed or solved first
        blockers = blocking(_apply_deterministic_gate(state))
        if (
            not blockers
            and recheck_duplicate is not None
            and state.get("regenerated_pending_dedup")
        ):
            state["regenerated_pending_dedup"] = False
            await recheck_duplicate(state)
            blockers = _duplicate_blockers(state)
        if blockers:
            state["current_review"] = _validator_review(blockers)
            state["fused_self_passed"] = False
            await event_queue.put(
                make_event(
                    event_type="agent_complete",
                    agent_name="Quality Gate",
                    message=f"Question {idx + 1} failed structural checks: {format_violations(blockers)}",
                    data={
                        "index": idx + 1,
                        "total": total_qty,
                        "stage": "validating",
                        "iteration": iteration,
                        "passed": False,
                        "violations": [v.code for v in blockers],
                    },
                    run_id=item_run_id,
                )
            )
            if iteration < config.MAX_REGENERATION_ATTEMPTS:
                state.update(await _regenerate(state))
                continue
            state.update(await reject_node(state))
            rej_data = state.get("rejection_data") or {}
            if isinstance(rej_data, dict):
                rej_data["index"] = idx + 1
                rej_data["stage"] = "rejected"
            await event_queue.put(
                make_event(
                    event_type="question_rejected",
                    agent_name="Quality Gate",
                    message=f"Question {idx + 1} could not be repaired after {iteration} attempts: {format_violations(blockers)}",
                    data=rej_data,
                    run_id=item_run_id,
                )
            )
            return False

        # Step 1: Run Reviewer if fused self-review is absent or unverified
        if not state.get("fused_self_passed"):
            rev_start_evt = make_event(
                event_type="agent_start",
                agent_name="Quality Reviewer",
                message=f"Reviewing draft {idx + 1}/{total_qty} (Round {iteration}) against 90+ quality standards...",
                data={
                    "index": idx + 1,
                    "total": total_qty,
                    "stage": "reviewing",
                    "iteration": iteration,
                },
                run_id=item_run_id,
            )
            await event_queue.put(rev_start_evt)

            if config.ENABLE_BLIND_SOLVER and config.PARALLEL_REVIEW_AND_SOLVE:
                outcome = await run_review_and_solve(state)
                state.update(build_review_update(state, outcome.review, outcome.review_usage))
                prefetched_solver = outcome
            else:
                state.update(await reviewer_node(state))

            review = state["current_review"]
            score = review["total_score"]
            rev_usage = state.get("latest_usage", {})

            rev_done_evt = make_event(
                event_type="agent_complete",
                agent_name="Quality Reviewer",
                message=f"Quality review completed for Question {idx + 1}. Score: {score}/100.",
                data={
                    "review": review,
                    "iteration": iteration,
                    "latest_usage": rev_usage,
                    "index": idx + 1,
                    "total": total_qty,
                    "stage": "reviewing",
                    "score": score,
                },
                run_id=item_run_id,
            )
            await event_queue.put(rev_done_evt)

            next_step = route_after_review(state)
            # The solver verdict is moot for a failing review, but its spend is real.
            if (
                prefetched_solver is not None
                and prefetched_solver.solver_usage is not None
                and next_step in ("regenerator", "reject")
            ):
                state.update(
                    build_usage_only_update(
                        state, "Blind-Solver Dual Validation", prefetched_solver.solver_usage
                    )
                )
            if next_step == "regenerator":
                regen_start_evt = make_event(
                    event_type="agent_start",
                    agent_name="Question Improver",
                    message=f"Question {idx + 1} score {score}/100 needs improvement. Question Improver is refining answer options...",
                    data={
                        "index": idx + 1,
                        "total": total_qty,
                        "stage": "remediating",
                        "iteration": iteration,
                        "score": score,
                    },
                    run_id=item_run_id,
                )
                await event_queue.put(regen_start_evt)

                regen_res = await _regenerate(state)
                state.update(regen_res)

                regen_usage = state.get("latest_usage", {})
                regen_done_evt = make_event(
                    event_type="agent_complete",
                    agent_name="Question Improver",
                    message=f"Question {idx + 1} improved (Draft v{state['iteration_count']} • {regen_usage.get('total_tokens', 0)} tokens, ${regen_usage.get('cost_usd', 0.0):.5f}). Re-checking with Quality Reviewer...",
                    data={
                        "draft": state["current_draft"],
                        "latest_usage": regen_usage,
                        "index": idx + 1,
                        "total": total_qty,
                        "stage": "remediating",
                    },
                    run_id=item_run_id,
                )
                await event_queue.put(regen_done_evt)
                continue
            if next_step == "reject":
                rej_res = await reject_node(state)
                state.update(rej_res)
                rej_data = state.get("rejection_data") or {}
                if isinstance(rej_data, dict):
                    rej_data["index"] = idx + 1
                    rej_data["stage"] = "rejected"
                rej_evt = make_event(
                    event_type="question_rejected",
                    agent_name="Quality Gate",
                    message=f"Quality check not passed for Question {idx + 1} (Score {score}/100 after {iteration} attempts).",
                    data=rej_data,
                    run_id=item_run_id,
                )
                await event_queue.put(rej_evt)
                return False

        # Step 2: Blind-Solver Dual Validation Agent Pass
        if config.ENABLE_BLIND_SOLVER:
            bs_start_evt = make_event(
                event_type="agent_start",
                agent_name="Blind-Solver Dual Validation",
                message=f"Running independent Blind-Solver Dual Validation on Question {idx + 1}...",
                data={
                    "index": idx + 1,
                    "total": total_qty,
                    "stage": "blind_solving",
                    "iteration": iteration,
                },
                run_id=item_run_id,
            )
            await event_queue.put(bs_start_evt)

            if prefetched_solver is not None:
                if prefetched_solver.solver_error is not None:
                    raise prefetched_solver.solver_error
                state.update(
                    build_solver_update(
                        state, prefetched_solver.solver_result, prefetched_solver.solver_usage
                    )
                )
            else:
                state.update(await blind_solver_node(state))

            bs_data = state.get("blind_solver_result") or {}
            bs_passed = state.get("blind_solver_passed", True)
            bs_usage = state.get("latest_usage", {})

            if bs_passed:
                bs_done_evt = make_event(
                    event_type="agent_complete",
                    agent_name="Blind-Solver Dual Validation",
                    message=f"Blind-Solver validated Question {idx + 1} (Selected Option {bs_data.get('selected_key')} matches key, confidence: {bs_data.get('confidence')}%, unambiguous).",
                    data={
                        "blind_solver": bs_data,
                        "latest_usage": bs_usage,
                        "index": idx + 1,
                        "total": total_qty,
                        "stage": "blind_solving",
                        "passed": True,
                    },
                    run_id=item_run_id,
                )
                await event_queue.put(bs_done_evt)
                return True

            bs_fail_evt = make_event(
                event_type="agent_complete",
                agent_name="Blind-Solver Dual Validation",
                message=f"Blind-Solver flagged discrepancy for Question {idx + 1}: Selected Option {bs_data.get('selected_key')} (Confidence: {bs_data.get('confidence')}%). Remediation required.",
                data={
                    "blind_solver": bs_data,
                    "latest_usage": bs_usage,
                    "index": idx + 1,
                    "total": total_qty,
                    "stage": "blind_solving",
                    "passed": False,
                },
                run_id=item_run_id,
            )
            await event_queue.put(bs_fail_evt)

            # Route to Question Improver for remediation if within attempt limits
            max_attempts = config.MAX_REGENERATION_ATTEMPTS
            if iteration < max_attempts:
                state["fused_self_passed"] = False
                regen_start_evt = make_event(
                    event_type="agent_start",
                    agent_name="Question Improver",
                    message=f"Question Improver is remediating question {idx + 1} based on blind-solver critique...",
                    data={
                        "index": idx + 1,
                        "total": total_qty,
                        "stage": "remediating",
                        "iteration": iteration,
                    },
                    run_id=item_run_id,
                )
                await event_queue.put(regen_start_evt)

                regen_res = await _regenerate(state)
                state.update(regen_res)

                regen_usage = state.get("latest_usage", {})
                regen_done_evt = make_event(
                    event_type="agent_complete",
                    agent_name="Question Improver",
                    message=f"Question {idx + 1} remediated (Draft v{state['iteration_count']}). Re-running validation...",
                    data={
                        "draft": state["current_draft"],
                        "latest_usage": regen_usage,
                        "index": idx + 1,
                        "total": total_qty,
                        "stage": "remediating",
                    },
                    run_id=item_run_id,
                )
                await event_queue.put(regen_done_evt)
                continue

            rej_res = await reject_node(state)
            state.update(rej_res)
            rej_evt = make_event(
                event_type="question_rejected",
                agent_name="Quality Gate",
                message=f"Blind-Solver validation failed after {iteration} attempts for Question {idx + 1}.",
                data=state.get("rejection_data") or {},
                run_id=item_run_id,
            )
            await event_queue.put(rej_evt)
            return False

        return True


async def _prepare_shared_passage_and_visual(
    req: GenerationRequest,
    batch_id: str,
    shared_passage_id: str | None,
    shared_passage_text: str | None,
    is_single_passage_set: bool,
    effective_passage_count: int,
    independent_count: int,
    total_qty: int,
    make_event: Callable[..., WorkflowEvent],
    passage_generator_fn: Callable[..., Any] | None = None,
    image_generator_fn: Callable[..., Any] | None = None,
) -> tuple[SharedPassageState, list[WorkflowEvent]]:
    """
    Drafts a shared reading passage and associated visual stimulus diagram when requested.

    Returns:
        Tuple of (SharedPassageState, events_to_emit).
    """
    events: list[WorkflowEvent] = []
    state = SharedPassageState(passage_text=shared_passage_text)

    actual_passage_gen = passage_generator_fn or generate_passage_stimulus
    actual_image_gen = image_generator_fn or generate_image_stimulus

    passage_image_needed = False
    passage_image_prompt = None

    if is_single_passage_set and not shared_passage_text:
        passage_start_evt = make_event(
            event_type="agent_start",
            agent_name="Passage Writer",
            message=f"Writing shared reading passage for {effective_passage_count} linked questions ({req.section.value})...",
            data={
                "stage": "passage_drafting",
                "total_questions": total_qty,
                "passage_question_count": effective_passage_count,
                "independent_question_count": independent_count,
                "batch_id": batch_id,
                "passage_id": shared_passage_id,
            },
        )
        events.append(passage_start_evt)

        (
            shared_passage_text,
            passage_usage,
            passage_image_needed,
            passage_image_prompt,
        ) = await actual_passage_gen(req)

        state.passage_text = shared_passage_text
        state.tokens = passage_usage.total_tokens
        state.prompt_tokens = passage_usage.prompt_tokens
        state.completion_tokens = passage_usage.completion_tokens
        state.cost = passage_usage.cost_usd

        state.usage_breakdown.append(
            {
                "agent": "Passage Writer",
                "iteration": 1,
                "prompt_tokens": passage_usage.prompt_tokens,
                "completion_tokens": passage_usage.completion_tokens,
                "total_tokens": passage_usage.total_tokens,
                "cost_usd": passage_usage.cost_usd,
            }
        )

        word_count = len(shared_passage_text.split())
        passage_done_evt = make_event(
            event_type="agent_complete",
            agent_name="Passage Writer",
            message=f"Shared reading passage completed ({word_count} words). Now drafting questions ({effective_passage_count} linked, {independent_count} independent)...",
            data={
                "stage": "passage_drafting",
                "passage_text": shared_passage_text,
                "passage_id": shared_passage_id,
                "word_count": word_count,
                "latest_usage": passage_usage.model_dump(),
            },
        )
        events.append(passage_done_evt)

    requires_passage_image = bool(
        not is_cars_section(req.section)
        and (
            req.allow_ai_images
            or passage_image_needed
            or req.require_passage_image
            or req.require_image
            or req.visual_type in KNOWN_VISUAL_TYPES
        )
    )

    # Generate shared visual stimulus diagram for the passage if required
    if is_single_passage_set and requires_passage_image and state.passage_text:
        p_img_start_evt = make_event(
            event_type="agent_start",
            agent_name="Diagram & Chart Maker",
            message="Drawing shared visual stimulus diagram for reading passage...",
            data={
                "stage": "passage_image",
                "passage_id": shared_passage_id,
                "batch_id": batch_id,
            },
        )
        events.append(p_img_start_evt)

        p_draft = QuestionDraft(
            stimulus_text=state.passage_text,
            question_stem=f"Visual stimulus diagram for {req.section.value} passage",
            options=[
                OptionChoice(id="A", text="Option A"),
                OptionChoice(id="B", text="Option B"),
                OptionChoice(id="C", text="Option C"),
                OptionChoice(id="D", text="Option D"),
            ],
            correct_answer_id="A",
            explanation="Shared passage visual stimulus reference",
            image_needed=True,
            image_prompt_or_type=passage_image_prompt
            or req.custom_prompt
            or f"Scientific clinical diagram for: {state.passage_text[:120]}",
        )

        (
            img_url,
            img_svg,
            img_desc,
            p_img_usage,
        ) = await actual_image_gen(p_draft, req)

        state.image_url = img_url
        state.image_svg = img_svg
        state.image_desc = img_desc

        if p_img_usage and p_img_usage.get("cost_usd"):
            state.cost += p_img_usage["cost_usd"]

        p_img_done_evt = make_event(
            event_type="agent_complete",
            agent_name="Diagram & Chart Maker",
            message="Shared visual stimulus diagram ready for reading passage.",
            data={
                "stage": "passage_image",
                "passage_id": shared_passage_id,
                "image_url": img_url,
                "image_svg": img_svg,
                "image_description": img_desc,
                "batch_id": batch_id,
            },
        )
        events.append(p_img_done_evt)

    return state, events


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
            f"Could not auto-persist question {idx + 1} for live batch {batch_id}: {q_save_err}",
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
        job_status = "completed" if completed_total > 0 else "failed"
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
        if job_status == "completed":
            await promote_completed_batch_questions(batch_id)
    except (SQLAlchemyError, OSError) as db_err:
        logger.warning(f"Could not finalize live job progress (DB offline): {db_err}")


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
            status="cancelled",
            actual_count=completed_total,
            completed_at=now_iso,
        )
        # A live (streamed) run has no background task to finish the batch later, so resolve it now
        await refresh_batch_aggregates(batch_id, allow_complete=True)
    except (SQLAlchemyError, OSError) as clean_err:
        logger.warning(f"Error updating cancelled live batch {batch_id}: {clean_err}")


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
            status="failed",
            error_message=error_msg,
            completed_at=now_iso,
        )
        await refresh_batch_aggregates(batch_id, allow_complete=True)
    except (SQLAlchemyError, OSError) as clean_err:
        logger.warning(f"Error updating failed live batch {batch_id}: {clean_err}")


# Pools at least this large are scored in a worker thread so the event loop (SSE, polling, other
# slots) is not blocked by pure-CPU string matching.
_DEDUP_THREAD_POOL_MIN = 150


async def _evaluate_duplicate_async(
    draft: dict[str, Any], ref_pool: list[Any], *, threshold: float, soft_threshold: float
):
    if len(ref_pool) >= _DEDUP_THREAD_POOL_MIN:
        return await asyncio.to_thread(
            evaluate_duplicate, draft, ref_pool, threshold=threshold, soft_threshold=soft_threshold
        )
    return evaluate_duplicate(draft, ref_pool, threshold=threshold, soft_threshold=soft_threshold)


_IN_FLIGHT_BATCH_STEMS: dict[str, list[dict[str, Any]]] = {}
_IN_FLIGHT_LOCK = asyncio.Lock()


async def register_in_flight_draft(
    batch_id: str | None, draft: dict[str, Any], worker_idx: int
) -> None:
    """Registers a freshly drafted question stem into the active batch pool to alert concurrent siblings."""
    if not batch_id:
        return
    async with _IN_FLIGHT_LOCK:
        pool = _IN_FLIGHT_BATCH_STEMS.setdefault(batch_id, [])
        pool[:] = [item for item in pool if item.get("_worker_idx") != worker_idx]
        item = dict(draft)
        item["_worker_idx"] = worker_idx
        # Synthetic id so a collision with an in-flight sibling is recognisable as such.
        item["id"] = f"in_flight_{worker_idx}"
        pool.append(item)


async def get_in_flight_drafts(
    batch_id: str | None, current_worker_idx: int
) -> list[dict[str, Any]]:
    """Returns all active in-flight candidate questions in this batch excluding the current worker."""
    if not batch_id:
        return []
    async with _IN_FLIGHT_LOCK:
        pool = _IN_FLIGHT_BATCH_STEMS.get(batch_id, [])
        return [item for item in pool if item.get("_worker_idx") != current_worker_idx]


async def remove_in_flight_draft(batch_id: str | None, worker_idx: int) -> None:
    """Removes a worker's draft from in-flight cache when finalized or cancelled."""
    if not batch_id:
        return
    async with _IN_FLIGHT_LOCK:
        pool = _IN_FLIGHT_BATCH_STEMS.get(batch_id, [])
        pool[:] = [item for item in pool if item.get("_worker_idx") != worker_idx]
        if not pool and batch_id in _IN_FLIGHT_BATCH_STEMS:
            _IN_FLIGHT_BATCH_STEMS.pop(batch_id, None)


async def clear_in_flight_batch(batch_id: str | None) -> None:
    """Forgets every in-flight draft of a batch (end of run, whatever the exit path)."""
    if not batch_id:
        return
    async with _IN_FLIGHT_LOCK:
        _IN_FLIGHT_BATCH_STEMS.pop(batch_id, None)


async def _refresh_duplicate_info_after_review(
    state: AgentWorkflowState,
    idx: int,
    req: GenerationRequest,
    db_reference_pool: list[Question],
    outcomes_questions: list[dict[str, Any] | None],
    threshold: float = config.DUPLICATE_HARD_THRESHOLD,
    soft_threshold: float = config.DUPLICATE_SOFT_THRESHOLD,
    batch_key: str | None = None,
) -> None:
    """Re-checks duplicates for a draft that the review loop rewrote.

    The first dedup pass ran on the original draft; regeneration can change the stem, so the
    stored duplicate verdict would otherwise describe a question that no longer exists.
    """
    if state.get("iteration_count", 1) <= 1:
        return
    cur_draft = state.get("current_draft") or {}
    batch_key = batch_key or req.batch_id or req.run_id
    await register_in_flight_draft(batch_key, cur_draft, idx)
    in_flight = await get_in_flight_drafts(batch_key, idx)
    ref_pool = (
        list(db_reference_pool) + [q for q in outcomes_questions if q is not None] + in_flight
    )
    result = await _evaluate_duplicate_async(
        cur_draft, ref_pool, threshold=threshold, soft_threshold=soft_threshold
    )
    state["duplicate_info"] = result.model_dump()
    state.setdefault("stage_outcomes", {})["duplicate_check"] = result.model_dump()


async def _run_deduplication_anti_collision_loop(
    state: AgentWorkflowState,
    idx: int,
    total_qty: int,
    item_run_id: str,
    req: GenerationRequest,
    db_reference_pool: list[Question],
    outcomes_questions: list[dict[str, Any] | None],
    event_queue: asyncio.Queue[WorkflowEvent | None],
    make_event: Callable[..., WorkflowEvent],
    max_retries: int = 3,
    threshold: float = config.DUPLICATE_HARD_THRESHOLD,
    soft_threshold: float = config.DUPLICATE_SOFT_THRESHOLD,
    batch_key: str | None = None,
) -> None:
    """
    Evaluates candidate draft against database reference pool, sibling batch questions,
    and active in-flight drafted stems. Uses a two-tier threshold:
    - If similarity >= 0.75 (Hard Duplicate): automatically re-prompts the fused generator with
      anti-collision instructions and alternate trap re-seeding up to max_retries.
    - If 0.60 <= similarity < 0.75 (Soft Warning): emits a variety warning and logs collision rationale.
    """
    cur_draft = state.get("current_draft") or {}
    # Must match the key the engine uses to remove drafts, or every run leaks its registry entry.
    batch_key = batch_key or req.batch_id or req.run_id

    # Immediately register candidate draft so concurrent siblings detect this stem in flight
    await register_in_flight_draft(batch_key, cur_draft, idx)

    in_flight = await get_in_flight_drafts(batch_key, idx)
    active_siblings = [q for q in outcomes_questions if q is not None]
    ref_pool = list(db_reference_pool) + active_siblings + in_flight

    dup_result = await _evaluate_duplicate_async(
        cur_draft, ref_pool, threshold=threshold, soft_threshold=soft_threshold
    )

    dedup_retry = 0
    while dup_result.is_duplicate and dedup_retry < max_retries and not llm_budget_exhausted(state):
        dedup_retry += 1
        alt_trap = ALT_TRAP_ROTATION[(idx + dedup_retry) % len(ALT_TRAP_ROTATION)]
        logger.warning(
            f"Worker {idx + 1} generated duplicate question ({int(dup_result.similarity_score * 100)}% match). "
            f"Triggering anti-collision regeneration with trap '{alt_trap}' (attempt {dedup_retry}/{max_retries})..."
        )
        dup_evt = make_event(
            event_type="agent_action",
            agent_name="Question Writer & Reviewer",
            message=f"Duplicate question detected ({int(dup_result.similarity_score * 100)}% match with {dup_result.matched_question_id or 'existing'}). Regenerating with alternate trap '{alt_trap}'...",
            data={
                "index": idx + 1,
                "total": total_qty,
                "stage": "anti_collision_regeneration",
                "similarity_score": dup_result.similarity_score,
                "matched_question_stem": dup_result.matched_question_stem,
                "reason": dup_result.match_reason,
                "assigned_trap": alt_trap,
            },
            run_id=item_run_id,
        )
        await event_queue.put(dup_evt)

        collision_hint = (
            f"CRITICAL ANTI-COLLISION REQUIREMENT: Your previous draft had high similarity ({int(dup_result.similarity_score * 100)}%) "
            f"with existing question: '{dup_result.matched_question_stem}'. "
            f"You MUST NOT write a question testing this same calculation or scenario. "
            f"Formulate a completely distinct scientific scenario testing cognitive trap {alt_trap} for {req.subtopic or 'this topic'}."
        )
        state["diversity_context"] = (
            f"{state.get('diversity_context') or ''} {collision_hint}".strip()
        )
        if "request" in state and isinstance(state["request"], dict):
            state["request"]["thematic_angle"] = (
                f"Question Item {idx + 1} Retry {dedup_retry} Trap {alt_trap}"
            )
            state["request"]["primary_trap"] = alt_trap

        regen_res = await fused_generator_node(state)
        state.update(regen_res)
        cur_draft = state.get("current_draft") or {}

        # Update in-flight registration with new draft
        await register_in_flight_draft(batch_key, cur_draft, idx)
        in_flight = await get_in_flight_drafts(batch_key, idx)
        ref_pool = list(db_reference_pool) + active_siblings + in_flight
        dup_result = await _evaluate_duplicate_async(
            cur_draft, ref_pool, threshold=threshold, soft_threshold=soft_threshold
        )

    if dup_result.is_soft_warning and not dup_result.is_duplicate:
        soft_evt = make_event(
            event_type="agent_action",
            agent_name="Question Writer & Reviewer",
            message=f"Soft conceptual overlap detected ({int(dup_result.similarity_score * 100)}% match with '{dup_result.matched_question_stem}'). Retaining as valid variation.",
            data={
                "index": idx + 1,
                "total": total_qty,
                "stage": "soft_collision_warning",
                "similarity_score": dup_result.similarity_score,
                "matched_question_stem": dup_result.matched_question_stem,
                "reason": dup_result.match_reason,
            },
            run_id=item_run_id,
        )
        await event_queue.put(soft_evt)

    state["duplicate_info"] = dup_result.model_dump()
    stage_outcomes = state.setdefault("stage_outcomes", {})
    stage_outcomes["duplicate_check"] = dup_result.model_dump()
