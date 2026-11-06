"""
regenerator.py - Question Re-Generator Agent for MCAT Question Bank.

Invoked when a candidate draft scores ≤ 90 on the 100-point psychometric rubric.
Uses the Reviewer's detailed critique (weaknesses and recommendations) to produce
a refined, publication-grade replacement draft in a single LLM round-trip.

Option parsing is shared with ``generator.py`` via ``_parse_option_choices`` and
``_parse_correct_keys`` to ensure consistent, DRY response handling.
"""

from __future__ import annotations

import logging

from app.agents._mock_tokens import (
    REGENERATOR_MOCK_COMPLETION_TOKENS,
    REGENERATOR_MOCK_PROMPT_TOKENS,
    mock_usage,
)
from app.agents.base import (
    LLMNotConfiguredError,
    call_llm_validated,
    require_offline_mode,
    safe_json_loads,
)
from app.agents.generator import _parse_correct_keys, _parse_option_choices, _require_text
from app.agents.mock_fixtures import improve_draft_heuristically
from app.agents.prompts import REGENERATOR_SYSTEM_PROMPT
from app.agents.standards import OPTION_PARITY_TEXT, is_cars
from app.core.config import config
from app.schemas import (
    MCAT_SECTION_LABELS,
    GenerationRequest,
    QuestionDraft,
    ReviewScore,
    TokenUsage,
    enum_value,
)

logger = logging.getLogger(__name__)


async def regenerate_question(
    draft: QuestionDraft, review: ReviewScore, req: GenerationRequest, iteration: int = 2
) -> tuple[QuestionDraft, TokenUsage]:
    """Invokes the Question Re-Generator Agent to refine a draft that scored <= 90."""
    section_val = enum_value(req.section)
    section_name = MCAT_SECTION_LABELS.get(req.section, section_val)
    options_formatted = "\n".join([f"{opt.id}: {opt.text}" for opt in draft.options])

    is_passage_active = req.is_passage_active

    weaknesses_text = (
        "\n".join([f"- {w}" for w in review.weaknesses]) or "General refinement needed"
    )
    recommendations_text = (
        "\n".join([f"- {r}" for r in review.recommendations])
        or "Elevate distractor quality and explanation depth"
    )

    passage_instruction = (
        "Passage Required: Yes"
        if is_passage_active
        else 'Passage Required: No - Direct question ONLY. Do NOT generate any reading passage, vignette, or scenario. Leave stimulus_text strictly as an empty string (""). Pose the question directly in question_stem.'
    )

    instructions = req.additional_instructions or req.custom_prompt
    instruction_block = (
        f"\nCRITICAL EDUCATOR INSTRUCTION (HIGH FIDELITY MANDATE):\n"
        f"You MUST continue to strictly adhere to and incorporate these author instructions in the regenerated question:\n"
        f'"""\n{instructions.strip()}\n"""\n'
        if instructions and instructions.strip()
        else ""
    )

    user_prompt = f"""The following candidate MCAT question received a score of {review.total_score}/100 and needs to be re-generated to score > 90.

Section: {section_name}
Subtopic: {req.subtopic or "General"}
Target Difficulty: {req.difficulty.value}
{passage_instruction}{instruction_block}
Iteration: {iteration}

--- ORIGINAL CANDIDATE DRAFT ---
Stimulus:
{draft.stimulus_text if is_passage_active else ""}

Stem:
{draft.question_stem}

Options:
{options_formatted}

Key: {draft.correct_answer_id}

Explanation:
{draft.explanation}

--- REVIEWER CRITIQUE & DEFICIENCIES ---
Current Total Score: {review.total_score}/100
Weaknesses identified:
{weaknesses_text}

Actionable Recommendations:
{recommendations_text}
---------------------------------------
CRITICAL REMEDIATION MANDATE:
1. Equalize option lengths: Count the words in every option. All 4 options MUST be {OPTION_PARITY_TEXT}. Do NOT make the correct key longer or more hedged than the distractors.
2. Output format: "options" MUST be a JSON list of 4 objects with "id" and "text" string fields.

Please re-generate and refine this question to resolve all weaknesses and produce a publication-grade AAMC MCAT question. Output valid JSON only."""

    def _parse_regenerated(raw: str) -> QuestionDraft:
        data = safe_json_loads(raw)
        if not isinstance(data, dict):
            raise ValueError(f"Model output must be a JSON object, got {type(data).__name__}")

        # Reuse shared parsers from generator.py - single source of truth for option handling
        options = _parse_option_choices(data.get("options", []), data)
        # Keep the draft's key only when the model omits one (never guess a new key)
        correct_id_str, keys_list = _parse_correct_keys(
            data, options, fallback_keys=draft.correct_answer_ids or None
        )

        stimulus = (
            (
                req.shared_stimulus.strip()
                if req.shared_stimulus
                else str(data.get("stimulus_text") or draft.stimulus_text or "").strip()
            )
            if is_passage_active
            else ""
        )

        # Same visual gating as the generator: never request a figure it would not allow
        image_allowed = not is_cars(req.section) and bool(req.allow_ai_images or req.require_image)
        return QuestionDraft(
            stimulus_text=stimulus,
            question_stem=_require_text(data, "question_stem"),
            options=options,
            correct_answer_id=correct_id_str,
            correct_answer_ids=keys_list,
            explanation=_require_text(data, "explanation"),
            image_needed=image_allowed and bool(data.get("image_needed", draft.image_needed)),
            image_prompt_or_type=data.get("image_prompt_or_type") or draft.image_prompt_or_type,
            # Metadata describes the question's design, not this rewrite: carry it over
            primary_trap=draft.primary_trap,
            aamc_skill=draft.aamc_skill,
            subject=draft.subject,
            unit=draft.unit,
            topic=draft.topic,
            subskill=draft.subskill,
            likely_mistake_pattern=draft.likely_mistake_pattern,
        )

    try:
        re_draft, usage = await call_llm_validated(
            prompt=user_prompt,
            system_prompt=REGENERATOR_SYSTEM_PROMPT,
            parse=_parse_regenerated,
            model=req.model_name,
            api_key=req.api_key,
            temperature=config.REGENERATOR_TEMPERATURE,
            max_tokens=config.DEFAULT_MAX_TOKENS,
        )
        return re_draft, usage
    except LLMNotConfiguredError as e:
        require_offline_mode(e)
        logger.warning(
            "Re-Generator LLM not configured, using offline heuristic remediation: %s", e
        )
        fallback_usage = mock_usage(
            REGENERATOR_MOCK_PROMPT_TOKENS, REGENERATOR_MOCK_COMPLETION_TOKENS
        )
        fallback_draft = improve_draft_heuristically(draft, review, iteration)
        if not is_passage_active:
            fallback_draft.stimulus_text = ""
        return fallback_draft, fallback_usage
