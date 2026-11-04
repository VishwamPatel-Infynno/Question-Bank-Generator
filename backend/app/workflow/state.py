from __future__ import annotations

from typing import Any, TypedDict


class AgentWorkflowState(TypedDict, total=False):
    request: dict[str, Any]
    current_draft: dict[str, Any] | None
    current_review: dict[str, Any] | None
    iteration_count: int
    iterations_history: list[dict[str, Any]]
    image_url: str | None
    image_svg: str | None
    image_description: str | None
    final_question: dict[str, Any] | None
    rejection_data: dict[str, Any] | None
    status: str
    active_agent: str
    log_messages: list[str]
    # Token usage & cost tracking
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float
    agent_usage_breakdown: list[dict[str, Any]]
    latest_usage: dict[str, Any] | None
    stage_outcomes: dict[str, Any]
    run_id: str
    batch_id: str | None
    fused_self_passed: bool
    passing_threshold: int
