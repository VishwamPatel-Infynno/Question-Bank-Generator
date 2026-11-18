"""
node_generator.py - Fused Question Generator and self-critique agent node.

Handles initial question drafting and optional simultaneous self-evaluation,
as well as agent token usage accounting.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.generator import (
    generate_question,
    generate_question_with_self_critique,
)
from app.agents.option_balancer import calculate_option_symmetry
from app.core.config import config
from app.schemas import GenerationRequest, TokenUsage
from app.workflow.state import AgentUsageEntry, AgentWorkflowState

logger = logging.getLogger(__name__)

__all__ = [
    "_record_agent_usage",
    "agent_usage_entry",
    "fused_generator_node",
    "record_agent_usage",
]


def agent_usage_entry(agent_name: str, usage: TokenUsage, iteration: int = 1) -> AgentUsageEntry:
    """Constructs an itemized AgentUsageEntry record for a single agent invocation."""
    entry: AgentUsageEntry = {
        "agent": agent_name,
        "iteration": iteration,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "cost_usd": usage.cost_usd,
        "calls": usage.calls,
    }
    if usage.duration_ms is not None:
        entry["duration_ms"] = usage.duration_ms
    return entry


def record_agent_usage(
    state: AgentWorkflowState,
    agent_name: str,
    usage: TokenUsage,
    iteration: int = 1,
) -> dict[str, Any]:
    """The state update that records one agent call: new run totals and the extended breakdown."""
    breakdown = [
        *state.get("agent_usage_breakdown", []),
        agent_usage_entry(agent_name, usage, iteration),
    ]
    return {
        "total_tokens": state.get("total_tokens", 0) + usage.total_tokens,
        "total_prompt_tokens": state.get("total_prompt_tokens", 0) + usage.prompt_tokens,
        "total_completion_tokens": state.get("total_completion_tokens", 0)
        + usage.completion_tokens,
        "total_cost_usd": round(state.get("total_cost_usd", 0.0) + usage.cost_usd, 7),
        "agent_usage_breakdown": breakdown,
    }


_record_agent_usage = record_agent_usage


async def fused_generator_node(state: AgentWorkflowState) -> dict[str, Any]:
    """
    Fused Draft-and-Critique node:
    Generates the question AND self-scores it in a single LLM round-trip.
    If self_score > passing_threshold (default 80), sets fused_self_passed=True to bypass redundant review calls.
    If self_score <= passing_threshold or critique is missing, sets fused_self_passed=False to route
    to the standard Reviewer node for a full independent audit and remediation loop.
    """
    req = GenerationRequest(**state["request"])
    diversity_context = state.get("diversity_context")
    if config.ALWAYS_INDEPENDENT_REVIEW:
        # The independent reviewer re-scores every draft anyway, so a self-critique would be paid
        # for in output tokens and then discarded. Draft only.
        logger.info("Executing Question Generator Agent (independent review follows)...")
        draft, usage = await generate_question(req, diversity_context=diversity_context)
        self_review = None
    else:
        logger.info("Executing Fused Question Generator & Self-Critique Agent...")
        draft, self_review, usage = await generate_question_with_self_critique(
            req, diversity_context=diversity_context
        )

    usage_update = _record_agent_usage(state, "Question Generator", usage, iteration=1)

    outcomes = dict(state.get("stage_outcomes", {}))
    outcomes["drafting"] = draft.model_dump()
    outcomes["option_symmetry"] = calculate_option_symmetry(draft.options, draft.correct_answer_ids)
    if self_review:
        outcomes["self_critique"] = self_review.model_dump()
        outcomes["quality_audit"] = self_review.model_dump()

    passing_threshold = state.get("passing_threshold") or config.PASSING_SCORE_THRESHOLD
    fused_self_passed = (
        not config.ALWAYS_INDEPENDENT_REVIEW
        and self_review is not None
        and self_review.total_score > passing_threshold
    )
    logger.info(
        "FUSED EVAL: fused_self_passed=%s, self_review_score=%s, threshold=%s",
        fused_self_passed,
        self_review.total_score if self_review else None,
        passing_threshold,
    )

    existing_history = list(state.get("iterations_history", []))
    if self_review:
        existing_history.append(
            {
                "iteration": 1,
                "draft": draft.model_dump(),
                "review": self_review.model_dump(),
                "usage": usage.model_dump(),
            }
        )

    return {
        "current_draft": draft.model_dump(),
        "current_review": self_review.model_dump() if self_review else None,
        "active_agent": "Question Generator",
        "status": "fused_passed" if fused_self_passed else "fused_drafted",
        "iteration_count": 1,
        "iterations_history": existing_history,
        **usage_update,
        "latest_usage": usage.model_dump(),
        "stage_outcomes": outcomes,
        "fused_self_passed": fused_self_passed,
    }
