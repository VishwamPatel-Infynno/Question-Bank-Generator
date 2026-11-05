"""Blind solver: robust key parsing, layout-varied sampling and majority voting."""

import pytest
from app.agents import blind_solver as bs
from app.core.config import config
from app.schemas import GenerationRequest, OptionChoice, QuestionDraft, TokenUsage


def _base_module():
    """call_llm_validated resolves call_llm in app.agents.base, so patch it there."""
    import app.agents.base as base_mod

    return base_mod


def _draft(texts=None, key="A"):
    texts = texts or ["Alpha result", "Beta result", "Gamma result", "Delta result"]
    return QuestionDraft(
        question_stem="Which is correct?",
        options=[OptionChoice(id=i, text=t) for i, t in zip("ABCD", texts, strict=True)],
        correct_answer_id=key,
        explanation="Because.",
    )


def _req():
    return GenerationRequest(section="CP", subtopic="Kinetics", difficulty="Medium")


def _usage():
    return TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15, cost_usd=0.001)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("B", "B"), ("b.", "B"), ("Option C", "C"), ("THE ANSWER IS D", "D"), ("choice a", "A")],
)
def test_key_extraction_handles_prose_answers(raw, expected):
    assert bs._extract_key(raw) == expected


def test_key_extraction_rejects_garbage():
    with pytest.raises(ValueError):
        bs._extract_key("none of these")


def test_layout_variation_is_skipped_when_options_reference_letters():
    plain = _draft()
    assert bs._display_order(plain, 1) == [3, 2, 1, 0]
    refs = _draft(["Alpha", "Both A and B", "Gamma", "Delta"])
    assert bs._display_order(refs, 1) == [0, 1, 2, 3]


def _solver_that_answers(correct_text_for_key, monkeypatch, confidence=95, ambiguous=False):
    """Fake solver that always picks the option whose text it believes is right."""

    async def fake(*_a, **kwargs):
        shown = next(
            line.split(".", 1)[0]
            for line in kwargs["prompt"].splitlines()
            if line[1:3] == ". " and line[3:] == correct_text_for_key
        )
        body = (
            f'{{"solver_rationale": "r", "ambiguity_notes": "", "is_ambiguous": '
            f'{str(ambiguous).lower()}, "confidence": {confidence}, "selected_key": "{shown}"}}'
        )
        return body, _usage()

    monkeypatch.setattr(_base_module(), "call_llm", fake)


@pytest.mark.asyncio
async def test_correct_key_verified_even_though_layouts_differ(monkeypatch):
    _solver_that_answers("Alpha result", monkeypatch)
    result, usage = await bs.blind_solve_question(_draft(), _req())
    assert result.is_verified and result.selected_key == "A"
    assert usage.total_tokens == 30  # both samples are billed


@pytest.mark.asyncio
async def test_wrong_key_is_rejected_by_majority(monkeypatch):
    _solver_that_answers("Gamma result", monkeypatch)  # solver believes C; author said A
    result, _ = await bs.blind_solve_question(_draft(), _req())
    assert not result.is_verified and result.selected_key == "C"
    assert result.agrees_with_key is False


@pytest.mark.asyncio
async def test_split_vote_is_never_verified(monkeypatch):
    monkeypatch.setattr(config, "BLIND_SOLVER_SAMPLES", 3)
    # Displayed letters chosen per layout so the ORIGINAL keys come out as A, C and D
    answers = iter(["A", "B", "B"])

    async def fake(*_a, **_k):
        key = next(answers)
        body = (
            '{"solver_rationale": "r", "ambiguity_notes": "", "is_ambiguous": false, '
            f'"confidence": 99, "selected_key": "{key}"}}'
        )
        return body, _usage()

    monkeypatch.setattr(_base_module(), "call_llm", fake)
    result, _ = await bs.blind_solve_question(_draft(), _req())
    assert not result.is_verified and result.is_ambiguous


@pytest.mark.asyncio
async def test_low_confidence_or_ambiguity_blocks_verification(monkeypatch):
    _solver_that_answers("Alpha result", monkeypatch, confidence=70)
    low, _ = await bs.blind_solve_question(_draft(), _req())
    assert not low.is_verified

    _solver_that_answers("Alpha result", monkeypatch, ambiguous=True)
    amb, _ = await bs.blind_solve_question(_draft(), _req())
    assert not amb.is_verified


@pytest.mark.asyncio
async def test_dedicated_solver_model_does_not_receive_the_clients_key(monkeypatch):
    seen = {}

    async def fake(*_a, **kwargs):
        seen.update(model=kwargs["model"], api_key=kwargs["api_key"])
        body = (
            '{"solver_rationale": "r", "ambiguity_notes": "", "is_ambiguous": false, '
            '"confidence": 95, "selected_key": "A"}'
        )
        return body, _usage()

    monkeypatch.setattr(_base_module(), "call_llm", fake)
    monkeypatch.setattr(config, "BLIND_SOLVER_MODEL", "solver-model")
    monkeypatch.setattr(config, "BLIND_SOLVER_SAMPLES", 1)
    req = _req().model_copy(update={"api_key": "client-key", "model_name": "gen-model"})
    await bs.blind_solve_question(_draft(), req)
    assert seen == {"model": "solver-model", "api_key": None}
