"""
test_draft_parser.py - Unit tests for decoupled Question Draft Parser & Cognitive Trap Extraction.
"""

import pytest
from app.agents import draft_parser, generator
from app.schemas import GenerationRequest, MCATSection, OptionChoice


def _make_req(**overrides) -> GenerationRequest:
    base = {
        "section": MCATSection.BIO_BIOCHEM,
        "topic": "Enzymes",
        "subtopic": "Kinetics",
    }
    base.update(overrides)
    return GenerationRequest(**base)


def test_parse_option_choices_standard_list():
    raw = [
        {"id": "A", "text": "Increases Km"},
        {"id": "B", "text": "Decreases Km"},
        {"id": "C", "text": "Increases Vmax"},
        {"id": "D", "text": "Decreases Vmax"},
    ]
    options = draft_parser.parse_option_choices(raw)
    assert len(options) == 4
    assert [o.id for o in options] == ["A", "B", "C", "D"]
    assert options[0].text == "Increases Km"


def test_parse_option_choices_dict_mapping():
    raw_dict = {
        "A": "Substrate binding",
        "B": "Allosteric regulation",
        "C": "Covalent modification",
        "D": "Competitive inhibition",
    }
    options = draft_parser.parse_option_choices(raw_dict)
    assert len(options) == 4
    assert [o.id for o in options] == ["A", "B", "C", "D"]
    assert options[1].text == "Allosteric regulation"


def test_parse_option_choices_string_prefixes():
    raw_strings = [
        "A: Michaelis constant increases",
        "B. Michaelis constant decreases",
        "C) Maximal velocity increases",
        "D: Maximal velocity decreases",
    ]
    options = draft_parser.parse_option_choices(raw_strings)
    assert len(options) == 4
    assert [o.id for o in options] == ["A", "B", "C", "D"]
    assert options[0].text == "Michaelis constant increases"
    assert options[1].text == "Michaelis constant decreases"


def test_parse_option_choices_nested_candidate_keys():
    data_with_choices = {
        "choices": [
            {"id": "A", "text": "Alpha"},
            {"id": "B", "text": "Beta"},
            {"id": "C", "text": "Gamma"},
            {"id": "D", "text": "Delta"},
        ]
    }
    options = draft_parser.parse_option_choices(None, data=data_with_choices)
    assert len(options) == 4
    assert options[2].text == "Gamma"


def test_parse_option_choices_invalid_count_raises():
    raw_three = [
        {"id": "A", "text": "Opt 1"},
        {"id": "B", "text": "Opt 2"},
        {"id": "C", "text": "Opt 3"},
    ]
    with pytest.raises(ValueError, match="Expected exactly 4 options"):
        draft_parser.parse_option_choices(raw_three)


def test_parse_correct_keys_valid():
    options = [
        OptionChoice(id="A", text="Opt A"),
        OptionChoice(id="B", text="Opt B"),
        OptionChoice(id="C", text="Opt C"),
        OptionChoice(id="D", text="Opt D"),
    ]
    # Single key string
    key_str, keys_list = draft_parser.parse_correct_keys({"correct_answer_id": "B"}, options)
    assert key_str == "B"
    assert keys_list == ["B"]

    # Multiple keys list
    key_str2, keys_list2 = draft_parser.parse_correct_keys(
        {"correct_answer_ids": ["A", "C"]}, options
    )
    assert key_str2 == "A, C"
    assert keys_list2 == ["A", "C"]

    # Fallback keys
    key_str3, keys_list3 = draft_parser.parse_correct_keys({}, options, fallback_keys=["D"])
    assert key_str3 == "D"
    assert keys_list3 == ["D"]


def test_parse_correct_keys_errors():
    options = [
        OptionChoice(id="A", text="Opt A"),
        OptionChoice(id="B", text="Opt B"),
        OptionChoice(id="C", text="Opt C"),
        OptionChoice(id="D", text="Opt D"),
    ]
    # Missing key
    with pytest.raises(ValueError, match="Model output has no correct_answer_id"):
        draft_parser.parse_correct_keys({}, options)

    # Unknown key ID
    with pytest.raises(ValueError, match="not among the options"):
        draft_parser.parse_correct_keys({"correct_answer_id": "Z"}, options)


def test_detect_primary_trap():
    req = _make_req()

    # Explicit in data
    assert (
        draft_parser.detect_primary_trap({"primary_trap": "FORMULA_MISAPPLICATION"}, req)
        == "FORMULA_MISAPPLICATION"
    )

    # Inferred from explanation regex
    expl = "The student made a classic Proportionality Error by inverting the ratio."
    assert draft_parser.detect_primary_trap({"explanation": expl}, req) == "PROPORTIONALITY_ERROR"

    # Default fallback
    assert draft_parser.detect_primary_trap({"explanation": "General question."}, req) == "SCOPE_SHIFT"


def test_detect_mistake_pattern():
    req = _make_req()
    expl = "Common mistake: fails to account for competitive inhibitor equilibrium displacement."
    pattern = draft_parser.detect_mistake_pattern({"explanation": expl}, req)
    assert "fails to account" in pattern.lower() or "equilibrium" in pattern.lower()


def test_require_text():
    assert draft_parser.require_text({"stem": "What is the Km?"}, "stem") == "What is the Km?"
    with pytest.raises(ValueError, match="missing a non-empty 'missing'"):
        draft_parser.require_text({"stem": "Test"}, "missing")
    with pytest.raises(ValueError, match="missing a non-empty 'empty'"):
        draft_parser.require_text({"empty": "   "}, "empty")


def test_generator_reexport_identity():
    """Confirms generator.py re-exports draft_parser functions with 100% identity parity."""
    assert generator.parse_option_choices is draft_parser.parse_option_choices
    assert generator._parse_option_choices is draft_parser.parse_option_choices
    assert generator.parse_correct_keys is draft_parser.parse_correct_keys
    assert generator._parse_correct_keys is draft_parser.parse_correct_keys
    assert generator.require_text is draft_parser.require_text
    assert generator._require_text is draft_parser.require_text
    assert generator.parse_question_draft_data is draft_parser.parse_question_draft_data
    assert generator._parse_question_draft_data is draft_parser.parse_question_draft_data
