"""Unit tests for the deterministic question validators (no LLM, no database)."""

from app.agents.validators import (
    blocking,
    format_violations,
    has_forbidden_dash,
    sanitize_dashes,
    sanitize_draft_dashes,
    validate_question_draft,
)
from app.schemas import OptionChoice, QuestionDraft


def _draft(**overrides) -> QuestionDraft:
    base = {
        "stimulus_text": "",
        "question_stem": "Which statement best explains the observed rate change?",
        "options": [
            OptionChoice(id="A", text="The catalyst lowers activation energy"),
            OptionChoice(id="B", text="The reaction becomes thermodynamically favored"),
            OptionChoice(id="C", text="The equilibrium constant increases sharply"),
            OptionChoice(id="D", text="The reactant concentration is held constant"),
        ],
        "correct_answer_id": "A",
        "explanation": (
            "Option A is correct because catalysts lower activation energy. "
            "Option B is wrong, thermodynamics is unchanged. "
            "Option C is wrong, K is unchanged. "
            "Option D is wrong, concentration does not explain a rate change."
        ),
    }
    base.update(overrides)
    return QuestionDraft(**base)


def _codes(violations):
    return {v.code for v in violations}


def test_clean_discrete_draft_has_no_violations():
    assert validate_question_draft(_draft()) == []


def test_duplicate_option_ids_block():
    d = _draft(
        options=[
            OptionChoice(id=i, text=f"Option text number {n} here") for n, i in enumerate("AABD")
        ]
    )
    v = validate_question_draft(d)
    assert "option_ids" in _codes(blocking(v))


def test_key_not_in_options_blocks():
    d = _draft(correct_answer_id="E", correct_answer_ids=["E"])
    assert "invalid_key" in _codes(blocking(validate_question_draft(d)))


def test_multiple_keys_block_for_single_choice_only():
    d = _draft(correct_answer_id="A, B", correct_answer_ids=["A", "B"])
    assert "multiple_keys" in _codes(blocking(validate_question_draft(d)))
    assert "multiple_keys" not in _codes(validate_question_draft(d, single_choice=False))


def test_dash_detection_and_sanitizing():
    assert has_forbidden_dash("a — b") and has_forbidden_dash("1–5") and has_forbidden_dash("a--b")
    assert not has_forbidden_dash("well-known - fine")
    assert sanitize_dashes("a — b–c--d") == "a - b-c-d"


def test_forbidden_dash_blocks_then_sanitize_clears():
    d = _draft(question_stem="Which is best — and why?")
    assert "forbidden_dash" in _codes(blocking(validate_question_draft(d)))
    assert sanitize_draft_dashes(d) is True
    assert "forbidden_dash" not in _codes(validate_question_draft(d))
    assert sanitize_draft_dashes(d) is False


def test_all_of_the_above_blocks():
    opts = [
        OptionChoice(id=i, text=t)
        for i, t in zip(
            "ABCD",
            ["One thing here", "Two things here", "Three things here", "All of the above"],
            strict=True,
        )
    ]
    assert "all_none_of_above" in _codes(blocking(validate_question_draft(_draft(options=opts))))


def test_passage_rules():
    assert "missing_passage" in _codes(
        blocking(validate_question_draft(_draft(), passage_required=True))
    )
    unexpected = validate_question_draft(_draft(stimulus_text="word " * 400))
    assert "unexpected_passage" in _codes(unexpected) and not blocking(unexpected)
    short = validate_question_draft(_draft(stimulus_text="word " * 50), passage_required=True)
    assert "passage_length" in _codes(short) and not blocking(short)
    ok = validate_question_draft(
        _draft(stimulus_text="word " * 600), passage_required=True, is_cars=True
    )
    assert "passage_length" not in _codes(ok)


def test_length_parity_and_longest_key_are_warnings():
    opts = [
        OptionChoice(
            id="A", text="a very long and detailed correct answer with many extra words in it"
        ),
        OptionChoice(id="B", text="short one"),
        OptionChoice(id="C", text="short two"),
        OptionChoice(id="D", text="short three"),
    ]
    v = validate_question_draft(_draft(options=opts))
    assert {"option_length_ratio", "key_is_longest"} <= _codes(v)
    assert not blocking(v)


def test_unaddressed_distractor_warns():
    v = validate_question_draft(_draft(explanation="Option A is correct because of catalysis."))
    assert "distractor_unaddressed" in _codes(v)
    assert not blocking(v)


def test_format_violations_lists_codes():
    v = validate_question_draft(_draft(correct_answer_id="E", correct_answer_ids=["E"]))
    assert "[invalid_key]" in format_violations(v)
