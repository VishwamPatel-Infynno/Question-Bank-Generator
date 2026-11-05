"""Tests that the deterministic validator gate runs before LLM review in the review loop."""

import asyncio

import pytest
from app.core.config import config
from app.schemas import GenerationRequest, OptionChoice, QuestionDraft, ReviewScore
from app.workflow import engine_helpers
from app.workflow.engine_helpers import (
    _apply_deterministic_gate,
    _run_question_review_loop,
    _validator_review,
)


def _draft(key="A", stem="Which statement best explains the observed rate change?"):
    return QuestionDraft(
        question_stem=stem,
        options=[
            OptionChoice(id="A", text="The catalyst lowers activation energy"),
            OptionChoice(id="B", text="The reaction becomes thermodynamically favored"),
            OptionChoice(id="C", text="The equilibrium constant increases sharply"),
            OptionChoice(id="D", text="The reactant concentration is held constant"),
        ],
        correct_answer_id=key,
        explanation="Option A is right. Option B is wrong. Option C is wrong. Option D is wrong.",
    )


def _state(draft: QuestionDraft) -> dict:
    req = GenerationRequest(section="CP", subtopic="Kinetics", difficulty="Medium")
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


@pytest.mark.asyncio
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

    monkeypatch.setattr(engine_helpers, "regenerator_node", fake_regen)
    monkeypatch.setattr(engine_helpers, "reviewer_node", fake_review)
    monkeypatch.setattr(config, "ENABLE_BLIND_SOLVER", False)

    queue: asyncio.Queue = asyncio.Queue()
    ok = await _run_question_review_loop(state, 0, 1, "run-1", queue, _make_event)
    assert ok is True
    assert calls == ["regen", "review"]


@pytest.mark.asyncio
async def test_loop_rejects_when_structural_defect_persists(monkeypatch):
    state = _state(_draft(key="Z"))
    state["iteration_count"] = config.MAX_REGENERATION_ATTEMPTS

    async def boom(s):
        raise AssertionError("no LLM call may be spent on a structurally invalid draft")

    monkeypatch.setattr(engine_helpers, "regenerator_node", boom)
    monkeypatch.setattr(engine_helpers, "reviewer_node", boom)

    queue: asyncio.Queue = asyncio.Queue()
    ok = await _run_question_review_loop(state, 0, 1, "run-1", queue, _make_event)
    assert ok is False
    assert state["status"] == "rejected_below_threshold"


@pytest.mark.asyncio
async def test_reviewer_and_solver_fail_closed_on_provider_errors(monkeypatch):
    import app.agents.blind_solver as solver_mod
    import app.agents.reviewer as reviewer_mod
    from app.agents.base import QualityCheckUnavailableError

    async def broken(*_a, **_k):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(reviewer_mod, "call_llm", broken)
    monkeypatch.setattr(solver_mod, "call_llm", broken)
    req = GenerationRequest(section="CP", subtopic="Kinetics", difficulty="Medium")

    with pytest.raises(QualityCheckUnavailableError):
        await reviewer_mod.review_question(_draft(), req)
    with pytest.raises(QualityCheckUnavailableError):
        await solver_mod.blind_solve_question(_draft(), req)


def test_reviewer_rejects_missing_or_out_of_range_scores():
    from app.agents.reviewer import _parse_review

    with pytest.raises(ValueError):
        _parse_review({"authenticity_score": 24, "clarity_score": 24})
    with pytest.raises(ValueError):
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


@pytest.mark.asyncio
async def test_generator_does_not_substitute_mock_questions_for_real_failures(monkeypatch):
    import app.agents.generator as gen_mod

    async def broken(*_a, **_k):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(gen_mod, "call_llm", broken)
    req = GenerationRequest(section="CP", subtopic="Kinetics", difficulty="Medium")
    with pytest.raises(RuntimeError):
        await gen_mod.generate_question_with_self_critique(req)
