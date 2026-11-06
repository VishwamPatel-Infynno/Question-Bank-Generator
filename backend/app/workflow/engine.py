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
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
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
    BatchStatus,
    GenerationBatch,
    GenerationJob,
    GenerationRequest,
    JobStatus,
    Question,
    WorkflowEvent,
)
from app.workflow._section_utils import is_cars_section
from app.workflow.dedup_inflight import (
    _refresh_duplicate_info_after_review,
    _run_deduplication_anti_collision_loop,
    clear_in_flight_batch,
    remove_in_flight_draft,
)
from app.workflow.live_job_store import (
    _finalize_live_job_progress,
    _handle_live_job_cancellation,
    _handle_live_job_failure,
    _persist_live_question,
)
from app.workflow.nodes import (
    finalize_node,
    fused_generator_node,
    image_node,
)
from app.workflow.passage_prep import (
    SharedPassageState,
    _build_batch_worker_request,
    _determine_item_diagram_requirement,
    _prepare_shared_passage_and_visual,
)
from app.workflow.review_loop import _run_question_review_loop, count_llm_calls
from app.workflow.state import AgentWorkflowState

logger = logging.getLogger(__name__)

# Max buffered SSE events before workers wait for the consumer to catch up
_EVENT_QUEUE_MAX = 256

# Attempts per question slot (replenishing it after a rejection or error) before moving on
MAX_SLOT_ATTEMPTS = 3
SLOT_REPLENISH_DELAY_SECONDS = 0.5  # pause before re-drafting a rejected slot
SLOT_ERROR_RETRY_DELAY_SECONDS = 1.0  # pause before retrying a slot after an error
# Workers start slightly apart so siblings can see each other's in-flight stems for dedup
WORKER_STAGGER_SECONDS = 0.35
WORKER_STAGGER_MAX_SECONDS = 2.0
EVENT_POLL_SECONDS = 1.0  # how often the stream loop re-checks that the workers are still running


def _enum_value(value: Any) -> str:
    """The wire value of an enum member, or the string form of anything else."""
    return value.value if hasattr(value, "value") else str(value)


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
    total_qty = max(1, req.questions_to_generate) if req.questions_to_generate is not None else 5
    is_independent = not is_cars_section(req.section) and (
        req.passage_mode == "independent"
        or str(req.passage_required).lower() in ("no", "false", "0")
        or (req.passage_question_count == 0 and not req.shared_stimulus)
    )
    is_single_passage_set = not is_independent
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
        sec_val = _enum_value(req.section)
        if not await get_batch_by_id(layout.batch_id):
            await save_batch(
                GenerationBatch(
                    id=layout.batch_id,
                    section=sec_val,
                    subtopic=req.subtopic or f"{sec_val} Mini-Batch",
                    difficulty=_enum_value(req.difficulty),
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
    usage: list[list[dict[str, Any]]]
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

    def all_usage(self) -> list[dict[str, Any]]:
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
    return (
        getattr(item_req, "passing_threshold", None)
        or getattr(req, "passing_threshold", None)
        or config.PASSING_SCORE_THRESHOLD
    )


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
        yield f"data: {start_evt.model_dump_json()}\n\n"

        # Worker Pool Concurrency
        semaphore = get_global_pipeline_semaphore()
        # Bounded so a stalled SSE consumer applies backpressure to the workers instead of letting
        # events (each with a full question payload) pile up in memory. Nothing is dropped.
        event_queue: asyncio.Queue[WorkflowEvent | None] = asyncio.Queue(maxsize=_EVENT_QUEUE_MAX)
        monitor_done = asyncio.Event()

        outcomes_questions: list[dict[str, Any] | None] = [None] * total_qty
        outcomes_rejections: list[dict[str, Any]] = []
        # Spend per slot across all of its attempts (calls feed MAX_LLM_CALLS_PER_SLOT)
        ledger = SlotLedger.for_slots(total_qty)
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
            logger.warning("Could not load reference questions for deduplication: %s", ref_err)

        async def _worker(idx: int) -> None:
            max_slot_attempts = MAX_SLOT_ATTEMPTS
            for attempt in range(max_slot_attempts):
                if attempt > 0 and ledger.budget_spent(idx, config.MAX_LLM_CALLS_PER_SLOT):
                    logger.warning(
                        "Question %s: LLM call budget exhausted after %s calls; not starting attempt %s.",
                        idx + 1,
                        ledger.calls[idx],
                        attempt + 1,
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

                        diversity_context = _build_diversity_context(
                            idx, total_qty, attempt, shared_used_traps, shared_used_mistakes
                        )

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
                        is_sibling_collision = _is_sibling_collision(dup_info, outcomes_questions)

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

                            ledger.fold(idx, state)
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
                            "Question %s attempt %s/%s not satisfied (passed=%s, is_dup=%s). Auto-replenishing slot...",
                            idx + 1,
                            attempt + 1,
                            max_slot_attempts,
                            question_passed,
                            is_hard_dup,
                        )
                        ledger.fold(idx, state)
                        attempt_state = None  # already counted
                        await remove_in_flight_draft(batch_id, idx)
                        await asyncio.sleep(SLOT_REPLENISH_DELAY_SECONDS)
                        continue

                except asyncio.CancelledError:
                    ledger.fold(idx, attempt_state)
                    await remove_in_flight_draft(batch_id, idx)
                    raise
                except Exception as worker_err:
                    ledger.fold(idx, attempt_state)
                    # A question staged in this failed attempt must not linger beside the retry
                    outcomes_questions[idx] = None
                    await remove_in_flight_draft(batch_id, idx)
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
                            data={
                                "index": idx + 1,
                                "error": str(worker_err),
                                # The batch worker stops reading at the first error event, so the
                                # spend of this failed run must travel with it.
                                "cumulative_usage": ledger.cumulative(passage_state),
                            },
                            run_id=req.run_id,
                        )
                        await event_queue.put(err_evt)
                    return

        async def _staggered_worker(w_idx: int) -> None:
            if w_idx > 0:
                # Small bounded stagger so siblings can see each other's in-flight stems for dedup,
                # without delaying the last worker of a 50-question run by ~17 seconds.
                await asyncio.sleep(min(WORKER_STAGGER_SECONDS * w_idx, WORKER_STAGGER_MAX_SECONDS))
            with bind_log_context(batch_id=batch_id, run_id=req.run_id, slot=w_idx + 1):
                await _worker(w_idx)

        tasks.extend([asyncio.create_task(_staggered_worker(i)) for i in range(total_qty)])

        async def _monitor_tasks():
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

        while True:
            try:
                evt = await asyncio.wait_for(event_queue.get(), timeout=EVENT_POLL_SECONDS)
            except TimeoutError:
                if monitor_done.is_set() and event_queue.empty():
                    break
                continue
            if evt is None:
                break
            yield f"data: {evt.model_dump_json()}\n\n"

        await monitor_task

        all_staged_questions = [q for q in outcomes_questions if q is not None]
        usage_totals = ledger.cumulative(passage_state)
        cumulative_tokens = usage_totals["total_tokens"]
        cumulative_prompt_tokens = usage_totals["total_prompt_tokens"]
        cumulative_completion_tokens = usage_totals["total_completion_tokens"]
        cumulative_cost = usage_totals["total_cost_usd"]
        all_agent_usage.extend(ledger.all_usage())

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
                        "cumulative_usage": usage_totals,
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
                    data={"error": error_msg, "cumulative_usage": usage_totals},
                )
                yield f"data: {error_evt.model_dump_json()}\n\n"
                return

        complete_evt = make_event(
            event_type="workflow_complete",
            agent_name="System",
            message=_complete_message(layout, all_staged_questions, usage_totals),
            data={
                "questions": all_staged_questions,
                "question": all_staged_questions[0] if all_staged_questions else None,
                "batch_id": batch_id,
                "passage_id": shared_passage_id if is_single_passage_set else None,
                **_shared_passage_payload(layout, passage_state),
                "cumulative_usage": usage_totals,
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
        logger.error("Workflow stream error: %s", e)
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
