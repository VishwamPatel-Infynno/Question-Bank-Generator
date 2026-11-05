"""Option Balancer & Anti-Guessability Engine for AAMC MCAT Questions.

Enforces psychometric parity across options:
1. Calculates option word-count symmetry and detects length disparities.
2. Flags test-wiseness cues (e.g., correct answer being significantly longer/more detailed).
3. Deterministically balances and permutes option positions to eliminate LLM key-letter bias (e.g. bias towards B or C),
   while dynamically updating explanation key references.
"""

from __future__ import annotations

import logging
import random
import re
import zlib
from typing import Any

from app.schemas import OptionChoice, QuestionDraft

logger = logging.getLogger(__name__)


def count_words(text: str) -> int:
    """Counts words in a string, stripping markup and whitespace."""
    if not text:
        return 0
    return len(text.strip().split())


def calculate_option_symmetry(
    options: list[OptionChoice | dict[str, Any]],
    correct_answer_id: str | list[str] | None = None,
) -> dict[str, Any]:
    """
    Computes psychometric symmetry and anti-guessability metrics across question choices.

    A high-caliber MCAT question requires options of roughly equal word count
    (disparity ratio <= 1.25), preventing candidates from guessing based on option length.
    """
    if not options:
        return {
            "disparity_ratio": 1.0,
            "symmetry_score": 100,
            "min_word_count": 0,
            "max_word_count": 0,
            "mean_word_count": 0.0,
            "word_counts": {},
            "is_balanced": True,
            "is_correct_longest": False,
            "status": "Balanced",
        }

    word_counts: dict[str, int] = {}
    for opt in options:
        opt_id = opt.get("id") if isinstance(opt, dict) else opt.id
        opt_text = opt.get("text") if isinstance(opt, dict) else opt.text
        word_counts[str(opt_id).upper()] = count_words(opt_text or "")

    counts = list(word_counts.values())
    min_w = min(counts) if counts else 0
    max_w = max(counts) if counts else 0
    mean_w = sum(counts) / len(counts) if counts else 0.0

    # Disparity ratio (max / min)
    disparity_ratio = round(max_w / max(1, min_w), 2) if min_w > 0 else (1.0 if max_w == 0 else 2.0)

    # Normalize correct answer keys
    correct_keys: list[str] = []
    if isinstance(correct_answer_id, list):
        correct_keys = [str(k).strip().upper() for k in correct_answer_id if str(k).strip()]
    elif isinstance(correct_answer_id, str) and correct_answer_id:
        correct_keys = [
            str(k).strip().upper() for k in correct_answer_id.split(",") if str(k).strip()
        ]

    # Check if any correct key is the longest choice
    correct_lengths = [word_counts[k] for k in correct_keys if k in word_counts]
    is_correct_longest = bool(correct_lengths and max(correct_lengths) == max_w and max_w > min_w)

    # Calculate 100-point symmetry score
    if disparity_ratio <= 1.15:
        symmetry_score = 100
    elif disparity_ratio <= 1.25:
        # Scale smoothly from 100 to 90
        symmetry_score = int(100 - ((disparity_ratio - 1.15) / 0.10) * 10)
    elif disparity_ratio <= 1.40:
        # Scale smoothly from 90 to 75
        symmetry_score = int(90 - ((disparity_ratio - 1.25) / 0.15) * 15)
    else:
        # Penalty scaling for wide disparities
        symmetry_score = max(30, int(75 - (disparity_ratio - 1.40) * 50))

    # Apply 8-point penalty if the correct answer is the longest, exceeds 2-4 word tolerance envelope, and disparity > 1.25
    word_diff = max_w - min_w
    if is_correct_longest and word_diff > 3 and disparity_ratio > 1.25:
        symmetry_score = max(20, symmetry_score - 8)

    # Status classification
    if disparity_ratio <= 1.25:
        status = "Balanced"
        is_balanced = True
    elif disparity_ratio <= 1.40:
        status = "Moderate Disparity"
        is_balanced = False
    else:
        status = "High Disparity"
        is_balanced = False

    return {
        "disparity_ratio": disparity_ratio,
        "symmetry_score": symmetry_score,
        "min_word_count": min_w,
        "max_word_count": max_w,
        "mean_word_count": round(mean_w, 1),
        "word_counts": word_counts,
        "is_balanced": is_balanced,
        "is_correct_longest": is_correct_longest,
        "status": status,
    }


_ROMAN_SET_RE = re.compile(
    r"^(?:none|neither)?\s*(?:[IV]{1,3}(?:\s*(?:,|and|or)\s*)?)+\s*(?:only)?$", re.IGNORECASE
)


def _are_options_ordered_set(options: list[OptionChoice]) -> bool:
    """True for Roman-numeral combination answers ("I only", "I and II only", "I, II, and III").

    Their order is meaningful (conventionally ascending), so shuffling would make them read oddly.
    """
    return len(options) >= 2 and all(bool(_ROMAN_SET_RE.match(o.text.strip())) for o in options)


def _stable_seed(draft: QuestionDraft) -> int:
    """Reproducible shuffle seed derived from the question content (same draft, same order)."""
    basis = draft.question_stem + "|" + "|".join(o.text for o in draft.options)
    return zlib.crc32(basis.encode("utf-8"))


def _are_options_purely_numeric(options: list[OptionChoice]) -> bool:
    """Detects if options are purely numerical values, currency, or units (e.g. in QR)."""
    num_pattern = re.compile(
        r"^[\$£€]?\s*-?\d+(?:\.\d+)?\s*(?:%|kg|g|mg|ml|l|m|cm|mm|min|s|hours|days|weeks)?$",
        re.IGNORECASE,
    )
    return len(options) >= 2 and all(bool(num_pattern.match(opt.text.strip())) for opt in options)


def _extract_numeric_value(text: str) -> float:
    """Extracts raw numeric float from text for sorting."""
    cleaned = re.sub(r"[^\d.-]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def remap_explanation_keys(explanation: str, old_to_new: dict[str, str]) -> str:
    """
    Safely substitutes option letter references in explanation text.

    Uses a 2-step token substitution to prevent collisions
    (e.g., preventing old 'B' -> new 'C' and old 'C' -> new 'B' from clobbering each other).
    """
    if not explanation or not old_to_new:
        return explanation

    # If identity mapping, return as-is
    if all(k == v for k, v in old_to_new.items()):
        return explanation

    result = explanation

    # 1. Regex replacements to placeholder tokens
    # Matches "Option B", "Choice C", "Key A", "Distractor D", and lists such as
    # "Options A and B", "choices B, C, and D", "answers A or C". Letters must be uppercase so the
    # article "a" in "choice a" style prose is never mistaken for an option.
    def repl_labeled(match: re.Match[str]) -> str:
        prefix = match.group(1)
        letters = re.sub(
            r"\b([A-E])\b",
            lambda m: f"__OPTTEMP_{m.group(1)}__" if m.group(1) in old_to_new else m.group(1),
            match.group(2),
        )
        return f"{prefix} {letters}"

    result = re.sub(
        r"\b((?i:Options?|Choices?|Answers?|Keys?|Distractors?|Statements?))\s+"
        r"([A-E](?:\s*(?:,\s*(?:and\s+|or\s+)?|\s+and\s+|\s+or\s+|&\s*)[A-E])*)\b",
        repl_labeled,
        result,
    )

    # Matches "B is correct", "C is incorrect", "A is the valid"
    def repl_predicate(match: re.Match[str]) -> str:
        letter = match.group(1).upper()
        rest = match.group(2)
        if letter in old_to_new:
            return f"__OPTTEMP_{letter}__ {rest}"
        return match.group(0)

    result = re.sub(
        r"\b([A-E])\s+((?i:is\s+(?:correct|incorrect|valid|invalid|the\s+right|the\s+wrong|true|false)))\b",
        repl_predicate,
        result,
    )

    # Matches bullet item start e.g. "- B: ", "* C - ", "D) "
    def repl_bullet(match: re.Match[str]) -> str:
        bullet = match.group(1)
        letter = match.group(2).upper()
        punct = match.group(3)
        if letter in old_to_new:
            return f"{bullet}__OPTTEMP_{letter}__{punct}"
        return match.group(0)

    result = re.sub(
        r"(^|\n)(\s*[-*•]?\s*)([A-E])(\s*[:\)\.-]\s+)",
        lambda m: (
            f"{m.group(1)}{m.group(2)}__OPTTEMP_{m.group(3)}__{m.group(4)}"
            if m.group(3) in old_to_new
            else m.group(0)
        ),
        result,
    )

    # Matches parentheses e.g. "(B)" or "(Option B)"
    result = re.sub(
        r"\(([A-E])\)",
        lambda m: (
            f"(__OPTTEMP_{m.group(1).upper()}__)"
            if m.group(1).upper() in old_to_new
            else m.group(0)
        ),
        result,
    )

    # 2. Swap placeholders to new letters
    for old_letter, new_letter in old_to_new.items():
        result = result.replace(f"__OPTTEMP_{old_letter}__", new_letter)

    return result


def balance_and_shuffle_options(
    draft: QuestionDraft,
    seed: int | None = None,
) -> tuple[QuestionDraft, dict[str, Any]]:
    """
    Reorders options and recalculates keys to eliminate position and letter bias.

    For numeric options (e.g. Quantitative Reasoning), sorts choices in standard
    ascending numerical order. For textual options, performs deterministic or seeded
    permutation to distribute correct answers uniformly across A, B, C, D (and E).
    """
    if len(draft.options) < 2:
        symmetry = calculate_option_symmetry(draft.options, draft.correct_answer_ids)
        symmetry["shuffled"] = False
        return draft, symmetry

    options_copy = list(draft.options)

    # Check if options are purely numerical
    if _are_options_purely_numeric(options_copy):
        # Order numerically ascending (official MCAT convention)
        options_copy.sort(key=lambda o: _extract_numeric_value(o.text))
    elif _are_options_ordered_set(options_copy):
        pass  # Roman-numeral combinations keep their conventional order
    else:
        # Textual choices: shuffle to break generator letter bias. The default seed comes from
        # the content, so a given draft always shuffles the same way (reproducible runs).
        rng = random.Random(_stable_seed(draft) if seed is None else seed)
        rng.shuffle(options_copy)

    # Assign sequential labels A, B, C, D, [E]
    alphabet = ["A", "B", "C", "D", "E"][: len(options_copy)]
    old_to_new: dict[str, str] = {}
    new_options: list[OptionChoice] = []

    for new_id, opt in zip(alphabet, options_copy, strict=False):
        old_id = opt.id.upper()
        old_to_new[old_id] = new_id
        new_options.append(OptionChoice(id=new_id, text=opt.text))

    # Remap correct answer keys
    old_keys = [str(k).strip().upper() for k in draft.correct_answer_ids if str(k).strip()]
    if not old_keys and draft.correct_answer_id:
        old_keys = [
            str(k).strip().upper() for k in draft.correct_answer_id.split(",") if str(k).strip()
        ]

    new_keys = sorted([old_to_new.get(k, k) for k in old_keys])
    new_correct_id_str = ", ".join(new_keys)

    # Remap explanation references
    new_explanation = remap_explanation_keys(draft.explanation, old_to_new)

    # Calculate symmetry
    symmetry = calculate_option_symmetry(new_options, new_keys)
    symmetry["shuffled"] = True
    symmetry["key_mapping"] = old_to_new

    balanced_draft = draft.model_copy(
        update={
            "options": new_options,
            "correct_answer_id": new_correct_id_str,
            "correct_answer_ids": new_keys,
            "explanation": new_explanation,
        }
    )

    return balanced_draft, symmetry
