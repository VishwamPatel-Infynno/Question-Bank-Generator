"""Shared builders for tests (import as ``from factories import make_draft, make_question``)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from app.schemas import GenerationRequest, OptionChoice, Question, QuestionDraft, TokenUsage
from app.workflow.sse import iter_sse_events

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


def make_request(**overrides: Any) -> GenerationRequest:
    """A minimal valid generation request (Chem/Phys, medium); keyword arguments override."""
    fields: dict[str, Any] = {"section": "CP", "subtopic": "Kinetics", "difficulty": "Medium"}
    fields.update(overrides)
    return GenerationRequest(**fields)


def make_usage(tokens: int = 15, cost: float = 0.001) -> TokenUsage:
    """Token usage with ``tokens`` prompt tokens and no completion tokens."""
    return TokenUsage(prompt_tokens=tokens, completion_tokens=0, total_tokens=tokens, cost_usd=cost)


def make_completion(
    content: str = "{}",
    finish_reason: str = "stop",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    **usage_extra: Any,
) -> SimpleNamespace:
    """A LiteLLM-shaped completion response (``choices[0].message.content`` plus ``usage``)."""
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        **usage_extra,
    )
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish_reason)
        ],
        usage=usage,
    )


def make_state(
    draft: QuestionDraft | None = None, request: GenerationRequest | None = None, **overrides: Any
) -> dict[str, Any]:
    """A workflow state at the start of the review loop; keyword arguments override fields."""
    state: dict[str, Any] = {
        "request": (request or make_request()).model_dump(),
        "current_draft": (draft or make_draft()).model_dump(),
        "iteration_count": 1,
        "fused_self_passed": False,
        "stage_outcomes": {},
    }
    state.update(overrides)
    return state


async def collect_events(stream: Any) -> list[dict[str, Any]]:
    """Every event of an SSE stream (the engine's text chunks) as dicts, in order."""
    return [evt async for evt in iter_sse_events(stream)]


def make_json_response(payload: dict[str, Any], status_code: int = 200) -> SimpleNamespace:
    """The minimum of an httpx response that the image clients read: ``status_code`` and ``json()``."""
    return SimpleNamespace(status_code=status_code, json=lambda: payload)
