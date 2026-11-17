"""
engine_layout.py - Layout resolution, slot ledger, and message formatting.

Provides the fixed run layout dataclass, the per-slot spend ledger,
event factories, diversity prompts, and status messages for streaming generation.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.config import config
from app.repositories import (
    get_batch_by_id,
    save_batch,
    save_job,
)
from app.schemas import (
    ALT_TRAP_ROTATION,
    BatchStatus,
    GenerationBatch,
    GenerationJob,
    GenerationRequest,
    JobStatus,
    WorkflowEvent,
    enum_value,
)
from app.workflow.passage_prep import SharedPassageState
from app.workflow.review_loop import count_llm_calls
from app.workflow.state import AgentUsageEntry, AgentWorkflowState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunLayout:
    """The fixed shape of one run: how many questions, which ids, and the passage mode."""

    total_qty: int
    batch_id: str
    job_id: str
    is_standalone_live_run: bool
    is_single_passage_set: bool
    shared_passage_id: str | None

    @property
    def effective_passage_count(self) -> int:
        return self.total_qty if self.is_single_passage_set else 0

    @property
    def independent_count(self) -> int:
        return 0 if self.is_single_passage_set else self.total_qty

    @property
    def passage_mode(self) -> str:
        return "single_passage" if self.is_single_passage_set else "independent"


def _resolve_run_layout(req: GenerationRequest) -> RunLayout:
    """Resolves the binary passage mode (all questions linked, or all independent) and the ids."""
    total_qty = max(1, req.questions_to_generate)
    # GenerationRequest's validator already resolved the binary passage mode (CARS always linked)
    is_single_passage_set = req.passage_mode != "independent"
    return RunLayout(
        total_qty=total_qty,
        batch_id=req.batch_id or str(uuid.uuid4()),
        job_id=req.job_id or str(uuid.uuid4()),
        is_standalone_live_run=req.job_id is None,
        is_single_passage_set=is_single_passage_set,
        shared_passage_id=req.passage_id or (str(uuid.uuid4()) if is_single_passage_set else None),
    )


async def _init_live_records(req: GenerationRequest, layout: RunLayout) -> None:
    """Creates the batch (when new) and job rows for a standalone live run; DB errors only log."""
    try:
        now_iso = datetime.now(UTC).isoformat()
        sec_val = enum_value(req.section)
        if not await get_batch_by_id(layout.batch_id):
            await save_batch(
                GenerationBatch(
                    id=layout.batch_id,
                    section=sec_val,
                    subtopic=req.subtopic or f"{sec_val} Mini-Batch",
                    difficulty=enum_value(req.difficulty),
                    passage_mode=req.passage_mode or layout.passage_mode,
                    target_count=layout.total_qty,
                    actual_count=0,
                    total_jobs=1,
                    completed_jobs=0,
                    failed_jobs=0,
                    status=BatchStatus.IN_PROGRESS,
                    created_at=now_iso,
                )
            )
        await save_job(
            GenerationJob(
                id=layout.job_id,
                batch_id=layout.batch_id,
                job_number=1,
                status=JobStatus.RUNNING,
                target_count=layout.total_qty,
                actual_count=0,
                passage_id=layout.shared_passage_id,
                created_at=now_iso,
                started_at=now_iso,
            )
        )
    except Exception as db_err:
        logger.warning("Live batch/job persistence skipped (DB offline): %s", db_err)


def _make_event_factory(
    req: GenerationRequest, batch_id: str, job_id: str
) -> Callable[..., WorkflowEvent]:
    """An event factory that stamps batch_id and job_id into event data unless already present."""

    def make_event(
        event_type: str,
        agent_name: str,
        message: str,
        data: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> WorkflowEvent:
        event_data = dict(data or {})
        event_data.setdefault("batch_id", batch_id)
        event_data.setdefault("job_id", job_id)
        return WorkflowEvent(
            run_id=run_id or req.run_id,
            batch_id=batch_id,
            event_type=event_type,
            agent_name=agent_name,
            message=message,
            data=event_data,
        )

    return make_event


@dataclass
class SlotLedger:
    """Spend per question slot, summed across every attempt the slot makes."""

    tokens: list[int]
    prompt_tokens: list[int]
    completion_tokens: list[int]
    costs: list[float]
    usage: list[list[AgentUsageEntry]]
    calls: list[int] = field(default_factory=list)

    @classmethod
    def for_slots(cls, total_qty: int) -> SlotLedger:
        return cls(
            tokens=[0] * total_qty,
            prompt_tokens=[0] * total_qty,
            completion_tokens=[0] * total_qty,
            costs=[0.0] * total_qty,
            usage=[[] for _ in range(total_qty)],
            calls=[0] * total_qty,
        )

    def fold(self, idx: int, st: AgentWorkflowState | None) -> None:
        """Adds one attempt's complete spend (tokens, split, cost, breakdown, calls) to the slot."""
        if not st:
            return
        self.tokens[idx] += st.get("total_tokens", 0)
        self.prompt_tokens[idx] += st.get("total_prompt_tokens", 0)
        self.completion_tokens[idx] += st.get("total_completion_tokens", 0)
        self.costs[idx] += st.get("total_cost_usd", 0.0)
        self.usage[idx].extend(st.get("agent_usage_breakdown", []))
        self.calls[idx] += count_llm_calls(st)

    def budget_spent(self, idx: int, limit: int) -> bool:
        """True once the slot has used ``limit`` LLM calls (a limit of 0 disables the cap)."""
        return limit > 0 and self.calls[idx] >= limit

    def cumulative(self, passage: SharedPassageState | None = None) -> dict[str, Any]:
        """Run totals across every slot plus the shared passage draft, as the SSE payload shape."""
        passage = passage or SharedPassageState()
        return {
            "total_tokens": sum(self.tokens) + passage.tokens,
            "total_prompt_tokens": sum(self.prompt_tokens) + passage.prompt_tokens,
            "total_completion_tokens": sum(self.completion_tokens) + passage.completion_tokens,
            "total_cost_usd": round(sum(self.costs) + passage.cost, 7),
        }

    def all_usage(self) -> list[AgentUsageEntry]:
        return [entry for slot_usage in self.usage for entry in slot_usage]


def _build_diversity_context(
    idx: int,
    total_qty: int,
    attempt: int,
    used_traps: list[str],
    used_mistakes: list[str],
) -> str | None:
    """Prompt context steering a slot away from traps/misconceptions its siblings already used."""
    if total_qty <= 1 and attempt == 0:
        return None
    parts = [f"Item {idx + 1} of {total_qty} in this question set."]
    if attempt > 0:
        alt_trap = ALT_TRAP_ROTATION[(idx + attempt) % len(ALT_TRAP_ROTATION)]
        parts.append(
            f"REPLENISHMENT ATTEMPT {attempt + 1}: The previous attempt did not satisfy quality or uniqueness standards. "
            f"You MUST formulate a fresh scenario testing cognitive trap '{alt_trap}' for variety."
        )
    elif used_traps:
        parts.append(
            f"Previously calibrated traps: {', '.join(used_traps[-4:])}. Please select a complementary AAMC trap for variety."
        )
    if used_mistakes:
        parts.append(
            f"Previously targeted misconceptions: {', '.join(used_mistakes[-3:])}. Diversify the targeted misconception."
        )
    return " ".join(parts)


def _drafting_message(
    idx: int, total_qty: int, attempt: int, is_passage_item: bool, interaction: str
) -> str:
    prefix = f"[{idx + 1}/{total_qty}]"
    if attempt > 0:
        return f"{prefix} Calibrating alternative scientific angle for Question {idx + 1}..."
    kind = interaction.replace("_", " ").title()
    if is_passage_item:
        return f"{prefix} Writing linked {kind} question from shared passage..."
    return f"{prefix} Writing independent {kind} question (direct question)..."


def _resolve_passing_threshold(item_req: GenerationRequest, req: GenerationRequest) -> float:
    """Item override, then run override, then the configured default."""
    # item_req is a copy of req, so one lookup covers both overrides
    return item_req.passing_threshold or req.passing_threshold or config.PASSING_SCORE_THRESHOLD


def _initial_attempt_state(
    item_req: GenerationRequest,
    item_run_id: str,
    batch_id: str,
    diversity_context: str | None,
    passing_threshold: float,
    slot_prior_calls: int,
) -> AgentWorkflowState:
    """The fresh workflow state one attempt starts from."""
    return {
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
        "passing_threshold": passing_threshold,
        "slot_prior_calls": slot_prior_calls,
    }


def _is_sibling_collision(
    dup_info: dict[str, Any], outcomes_questions: list[dict[str, Any] | None]
) -> bool:
    """True when a hard duplicate matched a sibling of this run (staged or still in flight)."""
    if not dup_info.get("is_duplicate", False):
        return False
    matched_id = str(dup_info.get("matched_question_id") or "")
    sibling_ids = {str(q["id"]) for q in outcomes_questions if q is not None and "id" in q}
    return matched_id in sibling_ids or matched_id.startswith("in_flight_")


def _shared_passage_payload(layout: RunLayout, passage: SharedPassageState) -> dict[str, Any]:
    """The passage-mode fields the workflow_start and workflow_complete events both carry."""
    linked = layout.is_single_passage_set
    return {
        "passage_mode": layout.passage_mode,
        "passage_question_count": layout.effective_passage_count,
        "independent_question_count": layout.independent_count,
        "shared_passage": passage.passage_text if linked else None,
        "shared_passage_image_svg": passage.image_svg if linked else None,
        "shared_passage_image_url": passage.image_url if linked else None,
        "shared_passage_image_description": passage.image_desc if linked else None,
    }


def _start_message(layout: RunLayout, req: GenerationRequest) -> str:
    if layout.is_single_passage_set:
        return f"Starting AAMC MCAT Passage Set ({layout.total_qty} questions) on shared reading passage..."
    if layout.total_qty == 1:
        return f"Starting AAMC MCAT Generation Workflow for {req.section.value} ({req.difficulty.value}) using Infynno Cognitive Architecture..."
    return f"Starting AAMC MCAT Independent Discretes Batch ({layout.total_qty} standalone questions) in parallel..."


def _complete_message(
    layout: RunLayout, staged: list[dict[str, Any]], usage: dict[str, Any]
) -> str:
    totals = f"Total: {usage['total_tokens']} tokens (${usage['total_cost_usd']:.5f})."
    if layout.is_single_passage_set and layout.total_qty > 1:
        return f"Passage Set generated! {len(staged)} questions linked to shared reading passage staged for Review. {totals}"
    if layout.total_qty > 1:
        return f"Parallel batch generation completed! {len(staged)} of {layout.total_qty} questions staged for User Confirmation. {totals}"
    score = staged[0].get("final_score", 95) if staged else 95
    return f"Multi-Agent workflow completed! Candidate question scored {score}/100 and is staged for Confirmation. {totals}"
