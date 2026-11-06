"""Blind solver: robust key parsing, layout-varied sampling and majority voting."""

import pytest
from app.agents import blind_solver as bs
from app.core.config import config
from factories import make_draft, make_request, make_usage


def _draft(texts=None, key="A"):
    texts = texts or ["Alpha result", "Beta result", "Gamma result", "Delta result"]
    return make_draft(
        question_stem="Which is correct?",
        options=texts,
        correct_answer_id=key,
        explanation="Because.",
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("B", "B"), ("b.", "B"), ("Option C", "C"), ("THE ANSWER IS D", "D"), ("choice a", "A")],
)
def test_key_extraction_handles_prose_answers(raw, expected):
    assert bs._extract_key(raw) == expected


def test_key_extraction_rejects_garbage():
    with pytest.raises(ValueError, match="invalid key"):
        bs._extract_key("none of these")


def test_layout_variation_is_skipped_when_options_reference_letters():
    plain = _draft()
    assert bs._display_order(plain, 1) == [3, 2, 1, 0]
    refs = _draft(["Alpha", "Both A and B", "Gamma", "Delta"])
    assert bs._display_order(refs, 1) == [0, 1, 2, 3]


def _solver_that_answers(correct_text_for_key, patch_llm, confidence=95, ambiguous=False):
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
        return body, make_usage()

    patch_llm(fake)


async def test_correct_key_verified_even_though_layouts_differ(patch_llm):
    _solver_that_answers("Alpha result", patch_llm)
    result, usage = await bs.blind_solve_question(_draft(), make_request())
    assert result.is_verified and result.selected_key == "A"
    assert usage.total_tokens == 30  # both samples are billed


async def test_wrong_key_is_rejected_by_majority(patch_llm):
    _solver_that_answers("Gamma result", patch_llm)  # solver believes C; author said A
    result, _ = await bs.blind_solve_question(_draft(), make_request())
    assert not result.is_verified and result.selected_key == "C"
    assert result.agrees_with_key is False


async def test_split_vote_is_never_verified(monkeypatch, patch_llm):
    monkeypatch.setattr(config, "BLIND_SOLVER_SAMPLES", 3)
    # Displayed letters chosen per layout so the ORIGINAL keys come out as A, C and D
    answers = iter(["A", "B", "B"])

    async def fake(*_a, **_k):
        key = next(answers)
        body = (
            '{"solver_rationale": "r", "ambiguity_notes": "", "is_ambiguous": false, '
            f'"confidence": 99, "selected_key": "{key}"}}'
        )
        return body, make_usage()

    patch_llm(fake)
    result, _ = await bs.blind_solve_question(_draft(), make_request())
    assert not result.is_verified and result.is_ambiguous


async def test_low_confidence_or_ambiguity_blocks_verification(patch_llm):
    _solver_that_answers("Alpha result", patch_llm, confidence=70)
    low, _ = await bs.blind_solve_question(_draft(), make_request())
    assert not low.is_verified

    _solver_that_answers("Alpha result", patch_llm, ambiguous=True)
    amb, _ = await bs.blind_solve_question(_draft(), make_request())
    assert not amb.is_verified


async def test_dedicated_solver_model_does_not_receive_the_clients_key(monkeypatch, patch_llm):
    seen = {}

    async def fake(*_a, **kwargs):
        seen.update(model=kwargs["model"], api_key=kwargs["api_key"])
        body = (
            '{"solver_rationale": "r", "ambiguity_notes": "", "is_ambiguous": false, '
            '"confidence": 95, "selected_key": "A"}'
        )
        return body, make_usage()

    patch_llm(fake)
    monkeypatch.setattr(config, "BLIND_SOLVER_MODEL", "solver-model")
    monkeypatch.setattr(config, "BLIND_SOLVER_SAMPLES", 1)
    req = make_request().model_copy(update={"api_key": "client-key", "model_name": "gen-model"})
    await bs.blind_solve_question(_draft(), req)
    assert seen == {"model": "solver-model", "api_key": None}
