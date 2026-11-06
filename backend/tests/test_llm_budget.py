"""Hard per-slot LLM call budget and the free duplicate re-check after rewrites."""

import asyncio

import pytest
from app.core.config import config
from app.workflow import review_loop
from app.workflow.review_loop import (
    _run_question_review_loop,
    count_llm_calls,
    llm_budget_exhausted,
)
from factories import make_draft, make_request


def _draft(stem="Which statement best explains the observed rate change?"):
    return make_draft(question_stem=stem)


def _state(prior=0, calls=0):
    req = make_request()
    return {
        "request": req.model_dump(),
        "current_draft": _draft().model_dump(),
        "iteration_count": 1,
        "fused_self_passed": False,
        "stage_outcomes": {},
        "slot_prior_calls": prior,
        "agent_usage_breakdown": [{"agent": "x", "calls": 1} for _ in range(calls)]
        + [{"agent": "mock", "calls": 0}],
    }


def _event(**kw):
    return kw


def test_calls_are_counted_from_usage_entries_and_mocks_cost_nothing():
    assert count_llm_calls(_state(calls=3)) == 3
    assert count_llm_calls({"agent_usage_breakdown": [{"agent": "mock"}]}) == 0


def test_budget_includes_earlier_attempts_and_can_be_disabled(monkeypatch):
    monkeypatch.setattr(config, "MAX_LLM_CALLS_PER_SLOT", 5)
    assert not llm_budget_exhausted(_state(prior=2, calls=2))
    assert llm_budget_exhausted(_state(prior=2, calls=3))
    monkeypatch.setattr(config, "MAX_LLM_CALLS_PER_SLOT", 0)
    assert not llm_budget_exhausted(_state(prior=99, calls=99))


async def test_review_loop_stops_before_paying_for_another_call_when_over_budget(monkeypatch):
    monkeypatch.setattr(config, "MAX_LLM_CALLS_PER_SLOT", 4)

    async def must_not_run(_state):
        raise AssertionError("no paid call may run once the budget is spent")

    monkeypatch.setattr(review_loop, "reviewer_node", must_not_run)
    monkeypatch.setattr(review_loop, "regenerator_node", must_not_run)

    state = _state(prior=2, calls=2)
    queue: asyncio.Queue = asyncio.Queue()
    ok = await _run_question_review_loop(state, 0, 1, "run", queue, _event)
    assert ok is False
    assert "budget" in state["rejection_data"]["reason"].lower()


async def test_duplicate_after_a_rewrite_is_rewritten_before_any_review(monkeypatch):
    monkeypatch.setattr(config, "MAX_LLM_CALLS_PER_SLOT", 0)
    events: list[str] = []

    async def fake_regen(state):
        events.append("regen")
        return {
            "current_draft": _draft(
                f"Rewritten stem number {len(events)} about rates?"
            ).model_dump(),
            "iteration_count": state.get("iteration_count", 1) + 1,
            "latest_usage": {},
        }

    async def recheck(state):
        # The first rewrite is still a duplicate, the second one is distinct
        state["duplicate_info"] = {
            "is_duplicate": len(events) < 2,
            "similarity_score": 0.9,
            "matched_question_stem": "Existing stem",
        }

    async def must_not_review(_state):
        events.append("review")
        raise AssertionError("a duplicate must not reach the reviewer")

    monkeypatch.setattr(review_loop, "regenerator_node", fake_regen)
    monkeypatch.setattr(review_loop, "reviewer_node", must_not_review)
    monkeypatch.setattr(config, "ENABLE_BLIND_SOLVER", False)

    state = _state()
    state["current_draft"] = _draft("Original stem that is invalid").model_dump()
    state["current_draft"]["correct_answer_id"] = "Z"  # force a rewrite via the validator
    state["current_draft"]["correct_answer_ids"] = ["Z"]

    queue: asyncio.Queue = asyncio.Queue()
    with pytest.raises(AssertionError):  # reaches review only after two duplicate rewrites
        await _run_question_review_loop(
            state, 0, 1, "run", queue, _event, recheck_duplicate=recheck
        )
    assert events == ["regen", "regen", "review"]
