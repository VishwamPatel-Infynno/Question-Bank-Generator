"""
draft_parser.py - Question Draft Parsing, Validation & Cognitive Trap Extraction.

Decoupled parser for LLM-generated question draft payloads:
- Validates and shuffles option choices into typed OptionChoice models.
- Validates single/multiple correct answer keys against available options.
- Classifies primary cognitive traps across 20+ AAMC distractor taxonomies.
- Extracts student mistake patterns and reading passage stimuli.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.standards import is_cars
from app.agents.validators import order_distractors_in_explanation
from app.schemas import (
    KNOWN_VISUAL_TYPES,
    GenerationRequest,
    OptionChoice,
    QuestionDraft,
    normalize_mistake_pattern,
    normalize_primary_trap,
)

__all__ = [
    "_detect_mistake_pattern",
    "_detect_primary_trap",
    "_parse_correct_keys",
    "_parse_option_choices",
    "_parse_question_draft_data",
    "_require_text",
    "_resolve_effective_stimulus",
    "detect_mistake_pattern",
    "detect_primary_trap",
    "parse_correct_keys",
    "parse_option_choices",
    "parse_question_draft_data",
    "require_text",
    "resolve_effective_stimulus",
]


def parse_option_choices(
    raw_options: Any, data: dict[str, Any] | None = None
) -> list[OptionChoice]:
    """Parses raw options list or dict into validated OptionChoice instances."""
    if not raw_options and data and isinstance(data, dict):
        for candidate_key in ("options", "choices", "answer_choices"):
            if data.get(candidate_key):
                raw_options = data[candidate_key]
                break
        if not raw_options and "question" in data and isinstance(data["question"], dict):
            raw_options = data["question"].get("options") or data["question"].get("choices")

    if isinstance(raw_options, dict):
        options = []
        for i, (k, v) in enumerate(raw_options.items()):
            opt_id = chr(65 + i)
            clean_k = str(k).strip().strip('"').strip("'")
            val_text = str(v).strip()
            if not val_text and (":" in clean_k or len(clean_k) > 3):
                parts = clean_k.split(":", 1)
                if len(parts) == 2 and len(parts[0].strip()) <= 2:
                    opt_id = parts[0].strip().upper()
                    val_text = parts[1].strip().strip('"').strip("'")
                else:
                    val_text = clean_k
            elif len(clean_k) == 1 and clean_k.isalpha():
                opt_id = clean_k.upper()
            options.append(OptionChoice(id=opt_id, text=val_text))
    elif isinstance(raw_options, list):
        options = []
        for i, opt in enumerate(raw_options):
            opt_id = chr(65 + i)
            if isinstance(opt, dict):
                raw_id_str = str(opt.get("id", chr(65 + i))).strip().upper()
                opt_id = raw_id_str[0] if raw_id_str and raw_id_str[0].isalpha() else chr(65 + i)
                text_val = str(opt.get("text", "")).strip()
            else:
                opt_str = str(opt).strip()
                if len(opt_str) > 2 and opt_str[1] in (":", ".", ")") and opt_str[0].isalpha():
                    opt_id = opt_str[0].upper()
                    text_val = opt_str[2:].strip()
                else:
                    text_val = opt_str
            options.append(OptionChoice(id=opt_id, text=text_val))
    else:
        options = []

    if len(options) != 4:
        raise ValueError(f"Expected exactly 4 options for AAMC MCAT, got {len(options)}")
    return options


def parse_correct_keys(
    data: dict[str, Any], options: list[OptionChoice], fallback_keys: list[str] | None = None
) -> tuple[str, list[str]]:
    """Extracts the string key representation and list of correct answer keys."""
    raw_id = data.get("correct_answer_id")
    raw_ids = data.get("correct_answer_ids")
    if isinstance(raw_ids, list) and raw_ids:
        keys_list = [str(k).strip().upper() for k in raw_ids if str(k).strip()]
    elif isinstance(raw_id, str) and raw_id:
        keys_list = [str(k).strip().upper() for k in raw_id.split(",") if str(k).strip()]
    elif fallback_keys:
        keys_list = list(fallback_keys)
    else:
        # Never guess: silently defaulting to option A would certify an arbitrary key.
        raise ValueError("Model output has no correct_answer_id")
    valid_ids = {o.id.strip().upper() for o in options}
    unknown = [k for k in keys_list if k not in valid_ids]
    if unknown:
        raise ValueError(
            f"correct_answer_id {unknown} is not among the options {sorted(valid_ids)}"
        )
    return ", ".join(keys_list), keys_list


def detect_primary_trap(data: dict[str, Any], req: GenerationRequest) -> str:
    """Determines the primary cognitive trap from payload, request override, or explanation regex."""
    raw_trap = data.get("primary_trap")
    normalized_trap = normalize_primary_trap(raw_trap)
    if normalized_trap and normalized_trap != "Automatic":
        return normalized_trap

    if req.primary_trap and req.primary_trap != "Automatic":
        return normalize_primary_trap(req.primary_trap) or req.primary_trap

    expl = data.get("explanation", "")
    taxonomies = [
        ("CONCEPT_CONFUSION", r"Concept\s*Confusion"),
        ("WRONG_BASE", r"Wrong\s*Base|Reference\s*Value"),
        ("UNIT_CONVERSION", r"Unit\s*Conversion"),
        ("FORMULA_MISAPPLICATION", r"Formula\s*Misapplication"),
        ("SIGN_CONVENTION", r"Sign\s*Convention|Direction"),
        ("PROPORTIONALITY_ERROR", r"Proportionality\s*Error"),
        ("ASSUMPTION_MISSED", r"Missed\s*Assumption|Assumption\s*Missed"),
        ("CAUSE_EFFECT_CONFUSION", r"Cause[- ]Effect|Causality"),
        (
            "CORRELATION_CAUSATION",
            r"Correlation\s*(?:vs\.?|and|mistaken\s*for)\s*Causation",
        ),
        ("CONTROL_GROUP_CONFUSION", r"Control[- ]Group"),
        ("VARIABLE_CONFUSION", r"Variable\s*Confusion|Independent\s*and\s*Dependent"),
        ("SAMPLE_SIZE_BIAS", r"Sample\s*Size|Sampling\s*Bias"),
        ("STATISTICAL_SIGNIFICANCE", r"Statistical\s*Significance|p-value"),
        ("GRAPH_AXIS_MISREADING", r"Axis\s*Misread|Graph\s*Axis"),
        ("TABLE_COMPARISON_ERROR", r"Table\s*Comparison"),
        ("TREND_EXTRAPOLATION", r"Trend\s*Extrapolation"),
        ("MECHANISM_CONFUSION", r"Mechanism\s*Confusion"),
        ("EXCEPTION_OVERLOOKED", r"Exception\s*Overlooked|Qualifier"),
        ("NEGATION_MISREAD", r"Negation|NOT/EXCEPT|LEAST\s*likely"),
        ("SCOPE_SHIFT", r"Scope\s*Shift"),
        ("UNSUPPORTED_INFERENCE", r"Unsupported\s*Inference"),
        ("PASSAGE_CONTRADICTION", r"Passage\s*Contradiction|Directly\s*contradicts"),
        ("OVERGENERALIZATION", r"Overgeneralization|Extreme\s*(?:Language|Quantifier)"),
        ("DISTRACTOR_OVERINTERPRETATION", r"Distractor\s*Overinterpretation"),
        ("ANSWER_CHOICE_CONFLATION", r"Answer\s*Choice\s*Conflation"),
    ]

    for trap_key, pattern in taxonomies:
        if re.search(pattern, expl, re.IGNORECASE):
            return trap_key
    return "SCOPE_SHIFT"


def detect_mistake_pattern(data: dict[str, Any], req: GenerationRequest) -> str | None:
    """Determines target student misconception / likely mistake pattern."""
    raw_mistake = data.get("likely_mistake_pattern")
    if req.likely_mistake_pattern and req.likely_mistake_pattern not in ("Automatic", ""):
        if req.likely_mistake_pattern == "None":
            return None
        return normalize_mistake_pattern(req.likely_mistake_pattern) or req.likely_mistake_pattern

    normalized_mistake = normalize_mistake_pattern(raw_mistake)
    effective_mistake = normalized_mistake or (str(raw_mistake).strip() if raw_mistake else None)
    if effective_mistake:
        return effective_mistake

    expl = data.get("explanation", "")
    m_match = re.search(
        r"(?:misconception|mistake\s*pattern|common\s*error|common\s*mistake)[:\s]+([^\n.,;]+)",
        expl,
        re.IGNORECASE,
    )
    if m_match:
        return m_match.group(1).strip()
    return "Confuses closely related concepts or misreads reference baseline"


def resolve_effective_stimulus(data: dict[str, Any], req: GenerationRequest) -> str:
    """Resolves reading passage vs direct independent question stimulus."""
    if not req.is_passage_active:
        return ""
    if req.shared_stimulus:
        return req.shared_stimulus.strip()
    return str(data.get("stimulus_text") or "").strip()


def require_text(data: dict[str, Any], field: str) -> str:
    """Validates that a required string field is present and non-empty."""
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Model output is missing a non-empty '{field}'")
    return value


def parse_question_draft_data(data: dict[str, Any], req: GenerationRequest) -> QuestionDraft:
    """Transforms raw LLM dictionary payload into a validated QuestionDraft model."""
    if not isinstance(data, dict):
        raise ValueError(f"Model output must be a JSON object, got {type(data).__name__}")
    question_stem = require_text(data, "question_stem")
    explanation = require_text(data, "explanation")
    options = parse_option_choices(data.get("options", []), data)
    correct_id_str, keys_list = parse_correct_keys(data, options)
    primary_trap = detect_primary_trap(data, req)
    effective_mistake = detect_mistake_pattern(data, req)
    effective_stimulus = resolve_effective_stimulus(data, req)

    if req.aamc_skill and req.aamc_skill.lower() not in ("automatic", "all", "none"):
        aamc_skill = req.aamc_skill
    else:
        aamc_skill = data.get("aamc_skill") or ("CARS1" if is_cars(req.section) else "Skill_2")

    return QuestionDraft(
        stimulus_text=effective_stimulus,
        question_stem=question_stem,
        options=options,
        correct_answer_id=correct_id_str,
        correct_answer_ids=keys_list,
        explanation=order_distractors_in_explanation(explanation),
        primary_trap=primary_trap,
        aamc_skill=aamc_skill,
        subject=req.subject,
        unit=req.unit,
        topic=req.topic,
        subskill=req.subskill,
        likely_mistake_pattern=effective_mistake,
        image_needed=(
            False
            if (
                is_cars(req.section)
                or not (
                    req.allow_ai_images
                    or req.require_image
                    or req.require_passage_image
                    or req.visual_type in KNOWN_VISUAL_TYPES
                )
            )
            else bool(data.get("image_needed", False))
        ),
        image_prompt_or_type=data.get("image_prompt_or_type"),
    )


# Backward-compat aliases: public names that pre-decomposition callers and test suites import.
# These are intentional and tested; do not remove without updating test_draft_parser.py.
_parse_option_choices = parse_option_choices
_parse_correct_keys = parse_correct_keys
_detect_primary_trap = detect_primary_trap
_detect_mistake_pattern = detect_mistake_pattern
_resolve_effective_stimulus = resolve_effective_stimulus
_require_text = require_text
_parse_question_draft_data = parse_question_draft_data
