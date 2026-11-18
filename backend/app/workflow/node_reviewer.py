"""
node_reviewer.py - Quality audit, dual validation blind solver, and remediation nodes.

Handles independent quality review scoring, concurrent blind-solving validation,
and iterative question regeneration upon sub-threshold audit results.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from app.agents.blind_solver import BlindSolverResult, blind_solve_question
from app.agents.option_balancer import (
    balance_and_shuffle_options,
    calculate_option_symmetry,
)
from app.agents.regenerator import regenerate_question
from app.agents.reviewer import review_question
from app.core.config import config
from app.schemas import (
    GenerationRequest,
    QuestionDraft,
    ReviewScore,
    TokenUsage,
)
from app.workflow.node_generator import record_agent_usage
from app.workflow.state import AgentWorkflowState

logger = logging.getLogger(__name__)


def build_review_update(
    state: AgentWorkflowState, review: ReviewScore, usage: TokenUsage
) -> dict[str, Any]:
    """Folds a completed review (and its usage) into a state update."""
    draft = QuestionDraft(**state["current_draft"])
    iteration = state.get("iteration_count", 1)

    usage_update = record_agent_usage(state, "Question Reviewer", usage, iteration=iteration)

    history_entry = {
        "iteration": iteration,
        "draft": draft.model_dump(),
        "review": review.model_dump(),
        "usage": usage.model_dump(),
    }

    existing_history = list(state.get("iterations_history", []))
    existing_history.append(history_entry)

    outcomes = dict(state.get("stage_outcomes", {}))
    outcomes["quality_audit"] = review.model_dump()

    return {
        "current_review": review.model_dump(),
        "iterations_history": existing_history,
        "active_agent": "Question Reviewer",
        "status": f"reviewed_iteration_{iteration}",
        **usage_update,
        "latest_usage": usage.model_dump(),
        "stage_outcomes": outcomes,
    }


async def reviewer_node(state: AgentWorkflowState) -> dict[str, Any]:
    """Executes the independent 100-point rubric evaluation for the candidate draft."""
    req = GenerationRequest(**state["request"])
    draft = QuestionDraft(**state["current_draft"])
    iteration = state.get("iteration_count", 1)

    logger.info("Executing Question Reviewer Agent (Iteration %s)...", iteration)
    review, usage = await review_question(draft, req, iteration)
    return build_review_update(state, review, usage)


@dataclass
class ReviewAndSolveOutcome:
    """Results of running the reviewer and blind solver concurrently on one draft."""

    review: ReviewScore
    review_usage: TokenUsage
    solver_result: BlindSolverResult | None
    solver_usage: TokenUsage | None
    solver_error: BaseException | None


async def run_review_and_solve(state: AgentWorkflowState) -> ReviewAndSolveOutcome:
    """Runs the independent reviewer and the blind solver concurrently.

    They are independent read-only checks of the same draft, so running them together saves one
    full LLM round trip per question. A reviewer failure is raised immediately; a solver failure
    is carried in the outcome and only matters if the review passes.
    """
    req = GenerationRequest(**state["request"])
    draft = QuestionDraft(**state["current_draft"])
    iteration = state.get("iteration_count", 1)
    logger.info("Executing Reviewer and Blind-Solver concurrently (Iteration %s)...", iteration)

    review_out, solve_out = await asyncio.gather(
        review_question(draft, req, iteration),
        blind_solve_question(draft, req),
        return_exceptions=True,
    )
    if isinstance(review_out, BaseException):
        raise review_out
    review, review_usage = review_out
    if isinstance(solve_out, BaseException):
        return ReviewAndSolveOutcome(review, review_usage, None, None, solve_out)
    solver_result, solver_usage = solve_out
    return ReviewAndSolveOutcome(review, review_usage, solver_result, solver_usage, None)


def build_usage_only_update(
    state: AgentWorkflowState, agent_name: str, usage: TokenUsage
) -> dict[str, Any]:
    """Accounts for real spend (tokens and cost) of a result whose verdict is not used."""
    usage_update = record_agent_usage(
        state, agent_name, usage, iteration=state.get("iteration_count", 1)
    )
    return {
        **usage_update,
    }


def build_solver_update(
    state: AgentWorkflowState, result: BlindSolverResult, usage: TokenUsage
) -> dict[str, Any]:
    """Folds a completed blind-solver verdict (and its usage) into a state update."""
    draft = QuestionDraft(**state["current_draft"])
    iteration = state.get("iteration_count", 1)

    usage_update = record_agent_usage(
        state, "Blind-Solver Dual Validation", usage, iteration=iteration
    )

    outcomes = dict(state.get("stage_outcomes", {}))
    outcomes["blind_solver_validation"] = result.model_dump()

    blind_passed = result.is_verified
    cur_review = dict(state.get("current_review") or {})

    if not blind_passed:
        # Build actionable critique for regenerator
        expected_key = draft.correct_answer_id
        critique_msg = (
            f"Blind Solver selected Option {result.selected_key} instead of intended Option {expected_key}. "
            f"Solver rationale: {result.solver_rationale}. "
            f"Ambiguity noted: {result.ambiguity_notes or 'Stem or distractors permit dual interpretation.'} "
            f"Confidence: {result.confidence}%."
        )
        cur_review["total_score"] = min(int(cur_review.get("total_score", 95)), 75)
        cur_review["passed"] = False
        weaknesses = list(cur_review.get("weaknesses", []))
        weaknesses.append(critique_msg)
        cur_review["weaknesses"] = weaknesses

        recommendations = list(cur_review.get("recommendations", []))
        recommendations.append(
            f"Clarify question stem to eliminate ambiguity between intended Option {expected_key} and Option {result.selected_key}."
        )
        cur_review["recommendations"] = recommendations

    return {
        "blind_solver_result": result.model_dump(),
        "blind_solver_passed": blind_passed,
        "current_review": cur_review,
        "active_agent": "Blind-Solver Dual Validation",
        "status": "blind_solver_passed" if blind_passed else "blind_solver_failed",
        **usage_update,
        "latest_usage": usage.model_dump(),
        "stage_outcomes": outcomes,
    }


async def blind_solver_node(state: AgentWorkflowState) -> dict[str, Any]:
    """
    Blind-Solver Dual Validation Node:
    Tests candidate question against an independent top-score solver without
    providing the intended key or explanation. Verifies indisputability and flags ambiguities.
    """
    req = GenerationRequest(**state["request"])
    draft = QuestionDraft(**state["current_draft"])
    iteration = state.get("iteration_count", 1)

    logger.info("Executing Blind-Solver Dual Validation Agent (Iteration %s)...", iteration)
    result, usage = await blind_solve_question(draft, req)
    return build_solver_update(state, result, usage)


async def regenerator_node(state: AgentWorkflowState) -> dict[str, Any]:
    """Remediates and re-generates an improved draft when an audit score falls below threshold."""
    req = GenerationRequest(**state["request"])
    draft = QuestionDraft(**state["current_draft"])
    review = ReviewScore(**state["current_review"])
    next_iteration = state.get("iteration_count", 1) + 1

    threshold = state.get("passing_threshold") or config.PASSING_SCORE_THRESHOLD
    logger.info(
        "Executing Question Re-Generator Agent (Score %s <= %s -> Iteration %s)...",
        review.total_score,
        threshold,
        next_iteration,
    )
    new_draft, usage = await regenerate_question(draft, review, req, next_iteration)
    new_draft, _ = balance_and_shuffle_options(new_draft)
    reg_symmetry = calculate_option_symmetry(new_draft.options, new_draft.correct_answer_ids)

    usage_update = record_agent_usage(
        state, "Question Re-Generator", usage, iteration=next_iteration
    )

    outcomes = dict(state.get("stage_outcomes", {}))
    outcomes["option_symmetry"] = reg_symmetry
    outcomes["polish_refine"] = {
        "iteration": next_iteration,
        "improved_draft": new_draft.model_dump(),
        "usage": usage.model_dump(),
    }

    return {
        "current_draft": new_draft.model_dump(),
        "iteration_count": next_iteration,
        "active_agent": "Question Re-Generator",
        "status": f"regenerated_draft_{next_iteration}",
        **usage_update,
        "latest_usage": usage.model_dump(),
        "stage_outcomes": outcomes,
    }
