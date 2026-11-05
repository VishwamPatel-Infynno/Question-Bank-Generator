"""Deterministic validators for generated MCAT question drafts.

These checks are pure, free (no LLM calls) and run before any model-based review, so
structural defects are caught for certain instead of depending on a model's opinion.

Severity model:
- ``error``: the item is structurally invalid and must be repaired or regenerated.
- ``warning``: a quality concern that is recorded for audit but does not block by itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.agents.option_balancer import count_words
from app.agents.standards import (
    OPTION_SPREAD_BLOCKING_MULTIPLE,
    option_spread_limit,
    passage_band,
)
from app.schemas import QuestionDraft

Severity = Literal["error", "warning"]

VALID_OPTION_IDS = ("A", "B", "C", "D")
# A passage this far outside the prompt's band is a defect, not a style difference
PASSAGE_BLOCKING_TOLERANCE = 0.25

_DASH_RE = re.compile(r"[–—]|--")
_FORBIDDEN_OPTION_RE = re.compile(r"\b(all|none) of the above\b", re.IGNORECASE)


@dataclass(frozen=True)
class Violation:
    """A single validator finding."""

    code: str
    message: str
    severity: Severity = "error"


def has_forbidden_dash(text: str | None) -> bool:
    """True if the text contains an em dash, en dash, or double hyphen."""
    return bool(text and _DASH_RE.search(text))


def sanitize_dashes(text: str) -> str:
    """Replaces em dashes, en dashes and double hyphens with a single hyphen.

    Spaced dashes stay spaced ("a — b" becomes "a - b"); unspaced ones stay joined.
    """
    return _DASH_RE.sub("-", text) if text else text


def sanitize_draft_dashes(draft: QuestionDraft) -> bool:
    """Applies :func:`sanitize_dashes` in place to every text field of the draft.

    Returns True if anything changed.
    """
    changed = False
    for attr in ("stimulus_text", "question_stem", "explanation"):
        old = getattr(draft, attr, "") or ""
        new = sanitize_dashes(old)
        if new != old:
            setattr(draft, attr, new)
            changed = True
    for opt in draft.options:
        new = sanitize_dashes(opt.text)
        if new != opt.text:
            opt.text = new
            changed = True
    return changed


def _distractor_unaddressed(explanation: str, option_id: str) -> bool:
    pattern = rf"(?:option|choice|answer)\s*\(?{option_id}\)?\b|\({option_id}\)|\b{option_id}[.):]"
    return not re.search(pattern, explanation, re.IGNORECASE)


def validate_question_draft(
    draft: QuestionDraft,
    *,
    passage_required: bool = False,
    is_cars: bool = False,
    single_choice: bool = True,
    check_passage: bool = True,
    enforce_length_spread: bool = True,
) -> list[Violation]:
    """Runs every deterministic check and returns all findings (empty list means clean)."""
    found: list[Violation] = []

    ids = [o.id.strip().upper() for o in draft.options]
    if sorted(ids) != list(VALID_OPTION_IDS):
        found.append(
            Violation("option_ids", f"Options must be exactly A, B, C, D once each; got {ids}")
        )
    for opt in draft.options:
        if not opt.text or not opt.text.strip():
            found.append(Violation("empty_option", f"Option {opt.id} is empty"))

    if not (draft.question_stem or "").strip():
        found.append(Violation("empty_stem", "Question stem is empty"))
    if not (draft.explanation or "").strip():
        found.append(Violation("empty_explanation", "Explanation is empty"))

    keys = [k.strip().upper() for k in draft.correct_answer_ids if k.strip()]
    if not keys:
        found.append(Violation("missing_key", "No correct answer key was provided"))
    else:
        bad = [k for k in keys if k not in ids]
        if bad:
            found.append(Violation("invalid_key", f"Key {bad} is not among the options {ids}"))
        if single_choice and len(set(keys)) != 1:
            found.append(
                Violation("multiple_keys", f"Single-best-answer item has keys {sorted(set(keys))}")
            )

    texts = {
        "stimulus": draft.stimulus_text,
        "stem": draft.question_stem,
        "explanation": draft.explanation,
        **{f"option {o.id}": o.text for o in draft.options},
    }
    for where, text in texts.items():
        if has_forbidden_dash(text):
            found.append(Violation("forbidden_dash", f"Em/en dash or '--' found in {where}"))
        if where.startswith("option") and _FORBIDDEN_OPTION_RE.search(text or ""):
            found.append(Violation("all_none_of_above", f"'{where}' uses all/none of the above"))

    has_passage = bool((draft.stimulus_text or "").strip())
    if not check_passage:
        pass
    elif not passage_required and has_passage:
        found.append(
            Violation(
                "unexpected_passage", "Discrete item must not carry a passage", severity="warning"
            )
        )
    if check_passage and passage_required and not has_passage:
        found.append(Violation("missing_passage", "Passage-based item has no passage"))
    if check_passage and passage_required and has_passage:
        lo, hi = passage_band(is_cars)
        words = count_words(draft.stimulus_text)
        if not lo <= words <= hi:
            far = words < lo * (1 - PASSAGE_BLOCKING_TOLERANCE) or words > hi * (
                1 + PASSAGE_BLOCKING_TOLERANCE
            )
            found.append(
                Violation(
                    "passage_length",
                    f"Passage has {words} words; expected {lo}-{hi}",
                    severity="error" if far else "warning",
                )
            )

    if len(draft.options) == 4:
        counts = {o.id.strip().upper(): count_words(o.text) for o in draft.options}
        mean = sum(counts.values()) / len(counts)
        spread = max(counts.values()) - min(counts.values())
        limit = option_spread_limit(mean)
        if spread > limit:
            found.append(
                Violation(
                    "option_length_spread",
                    f"Option lengths differ by {spread} words (limit {limit}): {counts}",
                    severity=(
                        "error"
                        if enforce_length_spread
                        and spread > limit * OPTION_SPREAD_BLOCKING_MULTIPLE
                        else "warning"
                    ),
                )
            )
        correct = [counts[k] for k in keys if k in counts]
        distractors = [n for k, n in counts.items() if k not in keys]
        if (
            correct
            and distractors
            and max(correct) - (sum(distractors) / len(distractors)) > (limit / 2)
        ):
            found.append(
                Violation(
                    "key_is_longest",
                    "Correct option is noticeably longer than the distractors",
                    severity="warning",
                )
            )

    if (draft.explanation or "").strip() and keys:
        missing = [
            i for i in ids if i not in keys and _distractor_unaddressed(draft.explanation, i)
        ]
        if missing:
            found.append(
                Violation(
                    "distractor_unaddressed",
                    f"Explanation never addresses distractor(s) {missing}",
                    severity="warning",
                )
            )

    return found


def blocking(violations: list[Violation]) -> list[Violation]:
    """Returns only the findings that must block the item."""
    return [v for v in violations if v.severity == "error"]


def format_violations(violations: list[Violation]) -> str:
    """Compact human-readable list, suitable for feeding back to the regenerator."""
    return "; ".join(f"[{v.code}] {v.message}" for v in violations)
