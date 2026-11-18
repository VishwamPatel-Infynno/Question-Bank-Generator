"""
state.py - Core Agent Workflow State Models and Typed Dictionaries.

Defines the structured runtime state dictionaries propagated through the LangGraph-style
multi-agent workflow pipeline (Question Generator, Option Balancer, Reviewer, Blind Solver,
Deduplicator, and Image Generator).

Every TypedDict uses total=False to accommodate progressive stage population while
guaranteeing full static typing, IDE autocompletion, and robust serialization.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentUsageEntry(TypedDict, total=False):
    """
    Represents an itemized resource utilization record for a single agent invocation.

    Captures model call metrics, latency, token spend, and financial cost to support
    per-stage telemetry and fine-grained budget tracking.
    """

    agent: str
    iteration: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    duration_ms: float | None
    calls: int


class IterationHistoryEntry(TypedDict, total=False):
    """
    Captures a point-in-time snapshot of a question draft and its quality audit during
    an authoring or remediation cycle.

    Provides a complete psychometric audit trail showing how question stems, distractors,
    and explanations evolved across successive review-and-remediation iterations.
    """

    iteration: int
    draft: dict[str, Any]
    review: dict[str, Any] | None
    usage: dict[str, Any] | None


class RejectionData(TypedDict, total=False):
    """
    Diagnostic payload assembled when a question fails to satisfy the AAMC quality benchmark
    after exhausting all allowed remediation cycles.

    Persisted in rejection telemetry for administrator quality review without polluting
    the active Question Bank.
    """

    question_id: str | None
    score: int
    threshold: int | float
    review: dict[str, Any]
    iteration_count: int
    iterations_history: list[IterationHistoryEntry]
    draft: dict[str, Any]
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float
    agent_usage_breakdown: list[AgentUsageEntry]
    reason: str


class StageOutcomes(TypedDict, total=False):
    """
    Diagnostic stage outputs collected throughout the lifecycle of a question generation run.

    Maintains raw outputs from drafting, quality audit, option balancing, blind solving,
    and image generation for auditability.
    """

    drafting: dict[str, Any]
    quality_audit: dict[str, Any]
    solver: dict[str, Any]
    balancing: dict[str, Any]
    image: dict[str, Any]
    offline_mode: bool


class DuplicateInfoDict(TypedDict, total=False):
    """
    Semantic and token-overlap duplicate detection assessment against existing bank questions
    and concurrent batch siblings.
    """

    is_duplicate: bool
    is_soft_warning: bool
    similarity_score: float
    matched_question_id: str | None
    matched_question_stem: str | None
    reason: str | None


class AgentWorkflowState(TypedDict, total=False):
    """
    Comprehensive state container flowing through the multi-agent question authoring pipeline.

    Maintains the authoring request parameters, active draft, review rubrics, visual stimuli,
    deduplication results, and cumulative resource usage across all workflow nodes.
    """

    # Request & context configuration
    request: dict[str, Any]
    run_id: str
    batch_id: str | None
    diversity_context: str | None
    passing_threshold: float
    slot_prior_calls: int

    # Authoring & Review lifecycle
    current_draft: dict[str, Any] | None
    current_review: dict[str, Any] | None
    iteration_count: int
    iterations_history: list[IterationHistoryEntry]
    fused_self_passed: bool
    status: str
    active_agent: str
    log_messages: list[str]

    # Deduplication state
    duplicate_info: DuplicateInfoDict | None
    regenerated_pending_dedup: bool

    # Visual stimulus & medical imaging
    image_url: str | None
    image_svg: str | None
    image_description: str | None
    visual_medical_category: str | None
    visual_clinical_description: str | None

    # Finalization & rejection payloads
    final_question: dict[str, Any] | None
    rejection_data: RejectionData | None

    # Telemetry, tokens, and billing
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float
    agent_usage_breakdown: list[AgentUsageEntry]
    latest_usage: dict[str, Any] | None
    stage_outcomes: StageOutcomes
