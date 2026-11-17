"""
extractors.py - Polymorphic field extractors and normalizers for Question models and dicts.

Provides safe, unified accessor routines for reading options, answer keys, stems,
and arbitrary fields across Pydantic models (Question, QuestionDraft) and raw dicts.
"""

from __future__ import annotations

from typing import Any


def extract_field(obj: Any, key: str, default: Any = None) -> Any:
    """Reads key from a dict or an attribute from an object, returning default if absent or obj is None."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def extract_option_choices(q: Any) -> list[dict[str, Any]]:
    """
    Extracts a standardized list of option dicts [{'id': 'A', 'text': '...'}]
    from any question representation (Question, QuestionDraft, dict).
    """
    opts = extract_field(q, "options", [])
    result = []
    for o in opts or []:
        if isinstance(o, dict):
            opt_id = str(o.get("id", "")).strip().upper()
            opt_text = str(o.get("text", "")).strip()
            result.append({"id": opt_id, "text": opt_text})
        else:
            opt_id = str(getattr(o, "id", "")).strip().upper()
            opt_text = str(getattr(o, "text", "")).strip()
            result.append({"id": opt_id, "text": opt_text})
    return result


def extract_correct_answer_ids(q: Any) -> set[str]:
    """
    Resolves correct option IDs as a clean set of uppercase strings e.g. {'A'} or {'A', 'C'}.
    Handles list, comma-separated string, or options with is_correct flags.
    """
    raw_ids = (
        extract_field(q, "correct_answer_ids")
        or extract_field(q, "correct_answer_id")
        or extract_field(q, "correct_answer")
    )
    if not raw_ids:
        # Check options for boolean markers
        options = extract_field(q, "options", [])
        return {
            str(extract_field(opt, "id", "")).strip().upper()
            for opt in (options or [])
            if extract_field(opt, "is_correct") or extract_field(opt, "correct")
        }

    if isinstance(raw_ids, (list, tuple, set)):
        return {str(x).strip().upper() for x in raw_ids if str(x).strip()}
    return {str(x).strip().upper() for x in str(raw_ids).replace(",", " ").split() if x.strip()}


def extract_correct_answer_text(q: Any) -> str:
    """
    Extracts the joined substantive text of the correct answer choice(s) for comparison and audit.
    """
    target_ids = extract_correct_answer_ids(q)
    options = extract_option_choices(q)
    matched = [opt["text"] for opt in options if opt["id"] in target_ids and opt["text"]]
    return " ".join(matched)


__all__ = [
    "extract_correct_answer_ids",
    "extract_correct_answer_text",
    "extract_field",
    "extract_option_choices",
]
