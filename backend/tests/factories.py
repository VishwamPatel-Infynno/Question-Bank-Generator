"""Shared builders for tests (import as ``from factories import make_draft, make_question``)."""

from __future__ import annotations

import uuid
from typing import Any

from app.schemas import OptionChoice, Question, QuestionDraft

_DEFAULT_OPTIONS = (
    "The catalyst lowers activation energy",
    "The reaction becomes thermodynamically favored",
    "The equilibrium constant increases sharply",
    "The reactant concentration is held constant",
)


def make_draft(**overrides: Any) -> QuestionDraft:
    """A valid four-option draft (answer A); keyword arguments replace any field.

    ``options`` may be given as plain strings (ids A-D are assigned) or as OptionChoice objects.
    """
    options = overrides.pop("options", None)
    if options is None:
        options = _DEFAULT_OPTIONS
    options = [
        o if isinstance(o, OptionChoice) else OptionChoice(id="ABCDE"[i], text=o)
        for i, o in enumerate(options)
    ]
    fields: dict[str, Any] = {
        "question_stem": "Which statement best explains the observed rate change?",
        "options": options,
        "correct_answer_id": "A",
        "explanation": "Option A is right. Option B is wrong. Option C is wrong. Option D is wrong.",
    }
    fields.update(overrides)
    return QuestionDraft(**fields)


def make_question(**overrides: Any) -> Question:
    """A valid saved-question schema object with a unique id and stem; keyword arguments override."""
    fields: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "section": "CPBS",
        "section_label": "Chemical and Physical Foundations of Biological Systems",
        "subtopic": "Kinetics",
        "difficulty": "medium",
        "question_stem": f"Stem {uuid.uuid4()} about kinetics",
        "options": [{"id": "A", "text": "opt A"}, {"id": "B", "text": "opt B"}],
        "correct_answer_id": "A",
        "explanation": "Because.",
        "final_score": 95,
        "status": "in_bank",
    }
    fields.update(overrides)
    return Question(**fields)
