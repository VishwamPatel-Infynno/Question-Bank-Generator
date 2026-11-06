"""Quality review, blind-solver validation and remediation for one question draft."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.agents.validators import (
    Violation,
    blocking,
    format_violations,
    sanitize_draft_dashes,
    validate_question_draft,
)
from app.core.config import config
from app.schemas import QuestionDraft, ReviewScore, WorkflowEvent
from app.workflow.nodes import (
    blind_solver_node,
    build_review_update,
    build_solver_update,
    build_usage_only_update,
    regenerator_node,
    reject_node,
    reviewer_node,
    run_review_and_solve,
)
from app.workflow.routes import route_after_review
from app.workflow.state import AgentWorkflowState

logger = logging.getLogger(__name__)


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


async def _emit_rejection(
    state: AgentWorkflowState,
    idx: int,
    item_run_id: str,
    event_queue: asyncio.Queue[WorkflowEvent | None],
    make_event: Callable[..., WorkflowEvent],
    message: str,
    *,
    reason: str | None = None,
) -> bool:
    """Runs the reject node, stamps the slot onto its rejection data and emits question_rejected.

    Always returns False so a caller can ``return await _emit_rejection(...)``.
    """
    state.update(await reject_node(state))
    rej_data = state.get("rejection_data") or {}
    if isinstance(rej_data, dict):
        rej_data["index"] = idx + 1
        rej_data["stage"] = "rejected"
        if reason is not None:
            rej_data["reason"] = reason
    await event_queue.put(
        make_event(
            event_type="question_rejected",
            agent_name="Quality Gate",
            message=message,
            data=rej_data,
            run_id=item_run_id,
        )
    )
    return False


def _improved_message(idx: int, state: AgentWorkflowState, usage: dict[str, Any]) -> str:
    return (
        f"Question {idx + 1} improved (Draft v{state['iteration_count']} • "
        f"{usage.get('total_tokens', 0)} tokens, ${usage.get('cost_usd', 0.0):.5f}). "
        "Re-checking with Quality Reviewer..."
    )


def _remediated_message(idx: int, state: AgentWorkflowState, usage: dict[str, Any]) -> str:
    _ = usage
    return f"Question {idx + 1} remediated (Draft v{state['iteration_count']}). Re-running validation..."


async def _regenerate_with_events(
    state: AgentWorkflowState,
    idx: int,
    total_qty: int,
    item_run_id: str,
    event_queue: asyncio.Queue[WorkflowEvent | None],
    make_event: Callable[..., WorkflowEvent],
    *,
    start_message: str,
    done_message: Callable[[int, AgentWorkflowState, dict[str, Any]], str],
    start_data: dict[str, Any] | None = None,
) -> None:
    """Runs the Question Improver between its agent_start and agent_complete events."""
    await event_queue.put(
        make_event(
            event_type="agent_start",
            agent_name="Question Improver",
            message=start_message,
            data={
                "index": idx + 1,
                "total": total_qty,
                "stage": "remediating",
                "iteration": state.get("iteration_count", 1),
                **(start_data or {}),
            },
            run_id=item_run_id,
        )
    )
    state.update(await _regenerate(state))
    regen_usage = state.get("latest_usage", {})
    await event_queue.put(
        make_event(
            event_type="agent_complete",
            agent_name="Question Improver",
            message=done_message(idx, state, regen_usage),
            data={
                "draft": state["current_draft"],
                "latest_usage": regen_usage,
                "index": idx + 1,
                "total": total_qty,
                "stage": "remediating",
            },
            run_id=item_run_id,
        )
    )


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
            return await _emit_rejection(
                state,
                idx,
                item_run_id,
                event_queue,
                make_event,
                f"Question {idx + 1} stopped: LLM call budget exhausted.",
                reason=f"LLM call budget ({config.MAX_LLM_CALLS_PER_SLOT}) exhausted for this question slot.",
            )

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
            return await _emit_rejection(
                state,
                idx,
                item_run_id,
                event_queue,
                make_event,
                f"Question {idx + 1} could not be repaired after {iteration} attempts: {format_violations(blockers)}",
            )

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
                await _regenerate_with_events(
                    state,
                    idx,
                    total_qty,
                    item_run_id,
                    event_queue,
                    make_event,
                    start_message=f"Question {idx + 1} score {score}/100 needs improvement. Question Improver is refining answer options...",
                    start_data={"score": score},
                    done_message=_improved_message,
                )
                continue
            if next_step == "reject":
                return await _emit_rejection(
                    state,
                    idx,
                    item_run_id,
                    event_queue,
                    make_event,
                    f"Quality check not passed for Question {idx + 1} (Score {score}/100 after {iteration} attempts).",
                )

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
                await _regenerate_with_events(
                    state,
                    idx,
                    total_qty,
                    item_run_id,
                    event_queue,
                    make_event,
                    start_message=f"Question Improver is remediating question {idx + 1} based on blind-solver critique...",
                    done_message=_remediated_message,
                )
                continue

            return await _emit_rejection(
                state,
                idx,
                item_run_id,
                event_queue,
                make_event,
                f"Blind-Solver validation failed after {iteration} attempts for Question {idx + 1}.",
            )

        return True
