from app.schemas.extractors import (
    extract_correct_answer_ids,
    extract_correct_answer_text,
    extract_field,
    extract_option_choices,
)
from app.schemas.question import OptionChoice, QuestionDraft


def test_extract_field_from_dict_and_object():
    data = {"key_a": 123, "key_b": "value"}
    assert extract_field(data, "key_a") == 123
    assert extract_field(data, "key_missing", "default") == "default"
    assert extract_field(None, "anything", 42) == 42

    class Sample:
        def __init__(self):
            self.foo = "bar"

    s = Sample()
    assert extract_field(s, "foo") == "bar"
    assert extract_field(s, "missing", "fallback") == "fallback"


def test_extract_option_choices_dict():
    q_dict = {
        "options": [
            {"id": "a", "text": "Choice A "},
            {"id": "B", "text": "Choice B"},
        ]
    }
    opts = extract_option_choices(q_dict)
    assert len(opts) == 2
    assert opts[0] == {"id": "A", "text": "Choice A"}
    assert opts[1] == {"id": "B", "text": "Choice B"}


def test_extract_option_choices_model():
    q_draft = QuestionDraft(
        question_stem="What is the standard enthalpy of formation?",
        options=[
            OptionChoice(id="A", text="Zero for pure elements in standard state"),
            OptionChoice(id="B", text="Positive for all compounds"),
            OptionChoice(id="C", text="Negative for endothermic bonds"),
            OptionChoice(id="D", text="Independent of temperature"),
        ],
        correct_answer_id="A",
        explanation="Standard state elements have zero enthalpy of formation.",
    )
    opts = extract_option_choices(q_draft)
    assert len(opts) == 4
    assert opts[0]["id"] == "A"
    assert opts[0]["text"] == "Zero for pure elements in standard state"


def test_extract_correct_answer_ids_and_text():
    # String key
    q1 = {
        "options": [
            {"id": "A", "text": "First option"},
            {"id": "B", "text": "Second option (correct)"},
        ],
        "correct_answer_id": "b",
    }
    assert extract_correct_answer_ids(q1) == {"B"}
    assert extract_correct_answer_text(q1) == "Second option (correct)"

    # Comma-separated keys
    q2 = {
        "options": [
            {"id": "A", "text": "Alpha"},
            {"id": "B", "text": "Beta"},
            {"id": "C", "text": "Gamma"},
        ],
        "correct_answer_ids": ["A", "C"],
    }
    assert extract_correct_answer_ids(q2) == {"A", "C"}
    assert "Alpha" in extract_correct_answer_text(q2)
    assert "Gamma" in extract_correct_answer_text(q2)

    # Boolean markers in options
    q3 = {
        "options": [
            {"id": "A", "text": "Incorrect"},
            {"id": "B", "text": "Correct option", "is_correct": True},
        ]
    }
    assert extract_correct_answer_ids(q3) == {"B"}
    assert extract_correct_answer_text(q3) == "Correct option"
