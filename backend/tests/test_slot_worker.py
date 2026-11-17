"""Unit tests for SlotWorkerContext and run_slot_worker lifecycle."""

import asyncio
from unittest.mock import AsyncMock

from app.core.config import config
from app.schemas import GenerationRequest, MCATSection
from app.workflow.engine_layout import SlotLedger
from app.workflow.slot_worker import (
    SLOT_ERROR_RETRY_DELAY_SECONDS,
    SLOT_REPLENISH_DELAY_SECONDS,
    SlotWorkerContext,
    run_slot_worker,
)


def _make_context(
    idx: int = 0,
    total_qty: int = 1,
    review_loop_fn=None,
    calls_spent: int = 0,
) -> SlotWorkerContext:
    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        subtopic="Thermodynamics",
        questions_to_generate=total_qty,
        run_id="run_test",
    )
    ledger = SlotLedger.for_slots(total_qty)
    if calls_spent > 0:
        ledger.calls[idx] = calls_spent

    semaphore = asyncio.Semaphore(5)
    event_queue = asyncio.Queue()

    def make_event(event_type: str, agent_name: str, message: str, data: dict, run_id: str = ""):
        return {
            "event_type": event_type,
            "agent_name": agent_name,
            "message": message,
            "data": data,
            "run_id": run_id,
        }

    return SlotWorkerContext(
        idx=idx,
        total_qty=total_qty,
        req=req,
        batch_id="test_batch_123",
        job_id="test_job_123",
        is_single_passage_set=False,
        effective_passage_count=0,
        shared_passage_id=None,
        shared_passage_text=None,
        shared_passage_image_svg=None,
        shared_passage_image_url=None,
        shared_passage_image_desc=None,
        ledger=ledger,
        semaphore=semaphore,
        event_queue=event_queue,
        make_event=make_event,
        db_reference_pool=[],
        outcomes_questions=[None] * total_qty,
        outcomes_rejections=[],
        outcomes_errors=[],
        shared_used_traps=[],
        shared_used_mistakes=[],
        is_standalone_live_run=False,
        review_loop_fn=review_loop_fn,
    )


def test_slot_worker_constants():
    assert SLOT_REPLENISH_DELAY_SECONDS > 0
    assert SLOT_ERROR_RETRY_DELAY_SECONDS > 0


def test_slot_worker_context_init():
    ctx = _make_context(idx=2, total_qty=5)
    assert ctx.idx == 2
    assert ctx.total_qty == 5
    assert ctx.batch_id == "test_batch_123"
    assert len(ctx.outcomes_questions) == 5
    assert ctx.outcomes_questions[2] is None


async def test_slot_worker_budget_spent_exit(monkeypatch):
    """If the LLM call budget for this slot is spent, slot worker exits without starting new attempts."""
    ctx = _make_context(idx=0, total_qty=1, calls_spent=config.MAX_LLM_CALLS_PER_SLOT + 5)

    # Monkeypatch fused_generator_node to verify it is NOT called when budget is already exhausted on retry
    called = []

    async def mock_generator(state):
        called.append(True)
        return {"current_draft": {"question_stem": "test"}}

    monkeypatch.setattr("app.workflow.slot_worker.fused_generator_node", mock_generator)

    # First attempt: budget_spent check in loop only triggers on attempt > 0.
    # To test budget_spent check on attempt > 0, simulate first attempt failing then second attempt blocked
    attempt_count = [0]

    async def mock_review(state, **kwargs):
        attempt_count[0] += 1
        return False  # triggers rejection and loop retry

    ctx.review_loop_fn = mock_review
    # Ensure WORKFLOW_MAX_WORKER_RETRIES allows retry
    monkeypatch.setattr(config, "WORKFLOW_MAX_WORKER_RETRIES", 2)
    # Ensure delay is 0 for test speed
    monkeypatch.setattr("app.workflow.slot_worker.SLOT_REPLENISH_DELAY_SECONDS", 0.0)

    await run_slot_worker(ctx)

    # Should have attempted once, then on attempt 1 (second attempt) budget check stopped it
    assert len(called) == 1
    assert ctx.outcomes_questions[0] is None
    assert len(ctx.outcomes_rejections) == 1


async def test_slot_worker_successful_generation(monkeypatch):
    """Slot worker succeeds, stages final question, and emits question_generated event."""
    ctx = _make_context(idx=0, total_qty=1)

    mock_q = {
        "id": "q_test_1",
        "question_stem": "What is the change in internal energy?",
        "options": [
            {"id": "A", "text": "Zero"},
            {"id": "B", "text": "Positive"},
            {"id": "C", "text": "Negative"},
            {"id": "D", "text": "Undefined"},
        ],
        "correct_answer": "A",
        "final_score": 92,
    }

    async def mock_gen(state):
        return {
            "current_draft": {
                "question_stem": mock_q["question_stem"],
                "options": mock_q["options"],
                "correct_answer": mock_q["correct_answer"],
                "primary_trap": "SIGN_ERROR",
                "likely_mistake_pattern": "Confusing heat and work",
            },
            "current_review": {"total_score": 92},
            "latest_usage": {"total_tokens": 100, "cost_usd": 0.001},
        }

    async def mock_rev(state, **kwargs):
        return True

    async def mock_fin(state):
        return {"final_question": dict(mock_q)}

    monkeypatch.setattr("app.workflow.slot_worker.fused_generator_node", mock_gen)
    monkeypatch.setattr("app.workflow.slot_worker.finalize_node", mock_fin)
    monkeypatch.setattr(
        "app.workflow.slot_worker._run_deduplication_anti_collision_loop", AsyncMock()
    )
    monkeypatch.setattr(
        "app.workflow.slot_worker._refresh_duplicate_info_after_review", AsyncMock()
    )

    ctx.review_loop_fn = mock_rev

    await run_slot_worker(ctx)

    assert ctx.outcomes_questions[0] is not None
    assert ctx.outcomes_questions[0]["final_score"] == 92
    assert ctx.outcomes_questions[0]["index"] == 1
    assert ctx.outcomes_questions[0]["batch_id"] == "test_batch_123"

    # Verify event queue received events
    events = []
    while not ctx.event_queue.empty():
        events.append(await ctx.event_queue.get())

    q_gen_evts = [e for e in events if e.get("event_type") == "question_generated"]
    assert len(q_gen_evts) == 1
    assert q_gen_evts[0]["data"]["question"]["id"] == "q_test_1"
