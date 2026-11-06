"""Tests that the deterministic validator gate runs before LLM review in the review loop."""

import asyncio

import pytest
from app.core.config import config
from app.schemas import QuestionDraft, ReviewScore
from app.workflow import review_loop
from app.workflow.review_loop import (
    _apply_deterministic_gate,
    _run_question_review_loop,
    _validator_review,
)
from factories import make_draft, make_request, make_usage


def _draft(key="A", stem="Which statement best explains the observed rate change?"):
    return make_draft(correct_answer_id=key, question_stem=stem)


def _state(draft: QuestionDraft) -> dict:
    req = make_request()
    return {
        "request": req.model_dump(),
        "current_draft": draft.model_dump(),
        "iteration_count": 1,
        "fused_self_passed": True,
        "stage_outcomes": {},
    }


def _make_event(**kwargs):
    return kwargs


def test_gate_repairs_dashes_in_place_without_blocking():
    state = _state(_draft(stem="Which is best — and why?"))
    violations = _apply_deterministic_gate(state)
    assert not [v for v in violations if v.severity == "error"]
    assert "—" not in state["current_draft"]["question_stem"]
    assert state["stage_outcomes"]["deterministic_validation"]["blocking"] == []


def test_validator_review_is_failing_and_carries_findings():
    state = _state(_draft(key="Z"))
    blockers = [v for v in _apply_deterministic_gate(state) if v.severity == "error"]
    review = ReviewScore(**_validator_review(blockers))
    assert review.passed is False and review.total_score <= config.PASSING_SCORE_THRESHOLD
    assert any("invalid_key" in r for r in review.recommendations)


async def test_loop_regenerates_invalid_draft_before_any_review(monkeypatch):
    calls: list[str] = []
    state = _state(_draft(key="Z"))

    async def fake_regen(s):
        calls.append("regen")
        return {"current_draft": _draft().model_dump(), "iteration_count": 2, "latest_usage": {}}

    async def fake_review(s):
        calls.append("review")
        good = ReviewScore(
            authenticity_score=24,
            clarity_score=24,
            distractor_score=24,
            explanation_score=24,
            total_score=96,
            passed=True,
        )
        return {"current_review": good.model_dump(), "latest_usage": {}}

    monkeypatch.setattr(review_loop, "regenerator_node", fake_regen)
    monkeypatch.setattr(review_loop, "reviewer_node", fake_review)
    monkeypatch.setattr(config, "ENABLE_BLIND_SOLVER", False)

    queue: asyncio.Queue = asyncio.Queue()
    ok = await _run_question_review_loop(state, 0, 1, "run-1", queue, _make_event)
    assert ok is True
    assert calls == ["regen", "review"]


async def test_loop_rejects_when_structural_defect_persists(monkeypatch):
    state = _state(_draft(key="Z"))
    state["iteration_count"] = config.MAX_REGENERATION_ATTEMPTS

    async def boom(s):
        raise AssertionError("no LLM call may be spent on a structurally invalid draft")

    monkeypatch.setattr(review_loop, "regenerator_node", boom)
    monkeypatch.setattr(review_loop, "reviewer_node", boom)

    queue: asyncio.Queue = asyncio.Queue()
    ok = await _run_question_review_loop(state, 0, 1, "run-1", queue, _make_event)
    assert ok is False
    assert state["status"] == "rejected_below_threshold"


async def test_reviewer_and_solver_fail_closed_on_provider_errors(monkeypatch, patch_llm):
    import app.agents.blind_solver as solver_mod
    import app.agents.reviewer as reviewer_mod
    from app.agents.base import QualityCheckUnavailableError

    async def broken(*_a, **_k):
        raise RuntimeError("provider exploded")

    patch_llm(broken)
    patch_llm(broken)
    req = make_request()

    with pytest.raises(QualityCheckUnavailableError):
        await reviewer_mod.review_question(_draft(), req)
    with pytest.raises(QualityCheckUnavailableError):
        await solver_mod.blind_solve_question(_draft(), req)


def test_reviewer_rejects_missing_or_out_of_range_scores():
    from app.agents.reviewer import _parse_review

    with pytest.raises(ValueError, match="missing"):
        _parse_review({"authenticity_score": 24, "clarity_score": 24})
    with pytest.raises(ValueError, match="outside 0-25"):
        _parse_review(
            {
                "authenticity_score": 30,
                "clarity_score": 24,
                "distractor_score": 24,
                "explanation_score": 24,
            }
        )
    ok = _parse_review(
        {
            "authenticity_score": 24,
            "clarity_score": 24,
            "distractor_score": 24,
            "explanation_score": 24,
        }
    )
    assert ok.total_score == 96 and ok.passed is True


async def test_generator_does_not_substitute_mock_questions_for_real_failures(monkeypatch):
    import app.agents.generator as gen_mod

    async def broken(*_a, **_k):
        raise RuntimeError("provider exploded")

    import app.agents.base as base_mod

    monkeypatch.setattr(base_mod, "call_llm", broken)
    req = make_request()
    with pytest.raises(RuntimeError):
        await gen_mod.generate_question_with_self_critique(req)


def _solver_result(agrees: bool = True):
    from app.agents.blind_solver import BlindSolverResult

    return BlindSolverResult(
        selected_key="A" if agrees else "B",
        confidence=95,
        is_ambiguous=False,
        ambiguity_notes="",
        solver_rationale="ok",
        agrees_with_key=agrees,
        is_verified=agrees,
        usage=make_usage(0, 0.0),
    )


def _review(total: int) -> ReviewScore:
    pillar = total // 4
    return ReviewScore(
        authenticity_score=pillar,
        clarity_score=pillar,
        distractor_score=pillar,
        explanation_score=total - 3 * pillar,
        total_score=total,
        passed=total > config.PASSING_SCORE_THRESHOLD,
    )


async def test_review_and_solver_run_concurrently_and_both_costs_are_counted(monkeypatch):
    import app.workflow.nodes as nodes_mod

    started: list[str] = []
    both_started = asyncio.Event()

    async def fake_review(*_a, **_k):
        started.append("review")
        if len(started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=1)  # fails if run serially
        return _review(96), make_usage(100, 0.01)

    async def fake_solve(*_a, **_k):
        started.append("solve")
        if len(started) == 2:
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=1)
        return _solver_result(), make_usage(50, 0.005)

    monkeypatch.setattr(nodes_mod, "review_question", fake_review)
    monkeypatch.setattr(nodes_mod, "blind_solve_question", fake_solve)
    monkeypatch.setattr(config, "ENABLE_BLIND_SOLVER", True)
    monkeypatch.setattr(config, "PARALLEL_REVIEW_AND_SOLVE", True)

    state = _state(_draft())
    state["fused_self_passed"] = False
    queue: asyncio.Queue = asyncio.Queue()
    ok = await _run_question_review_loop(state, 0, 1, "run-1", queue, _make_event)

    assert ok is True
    assert state["total_tokens"] == 150
    assert round(state["total_cost_usd"], 6) == 0.015
    agents = [e["agent"] for e in state["agent_usage_breakdown"]]
    assert agents == ["Question Reviewer", "Blind-Solver Dual Validation"]


async def test_failing_review_still_accounts_solver_spend_and_ignores_solver_error(monkeypatch):
    import app.workflow.nodes as nodes_mod

    async def fake_review(*_a, **_k):
        return _review(60), make_usage(100, 0.01)

    async def broken_solve(*_a, **_k):
        raise RuntimeError("solver down")

    async def fake_regen(s):
        return {"current_draft": _draft().model_dump(), "iteration_count": 99, "latest_usage": {}}

    monkeypatch.setattr(nodes_mod, "review_question", fake_review)
    monkeypatch.setattr(nodes_mod, "blind_solve_question", broken_solve)
    monkeypatch.setattr(review_loop, "regenerator_node", fake_regen)
    monkeypatch.setattr(config, "ENABLE_BLIND_SOLVER", True)
    monkeypatch.setattr(config, "PARALLEL_REVIEW_AND_SOLVE", True)

    state = _state(_draft())
    state["fused_self_passed"] = False
    state["iteration_count"] = config.MAX_REGENERATION_ATTEMPTS  # forces reject, not regen
    queue: asyncio.Queue = asyncio.Queue()
    ok = await _run_question_review_loop(state, 0, 1, "run-1", queue, _make_event)

    assert ok is False
    assert state["total_tokens"] == 100  # solver errored, so only the review spend exists
