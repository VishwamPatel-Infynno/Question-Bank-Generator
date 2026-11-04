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
)
from app.agents.base import calculate_token_cost, call_llm, safe_json_loads
from app.agents.generator import _parse_correct_keys, _parse_option_choices
from app.agents.mock_fixtures import improve_draft_heuristically
from app.agents.prompts import REGENERATOR_SYSTEM_PROMPT
from app.core.config import config
from app.schemas.mcat import MCAT_SECTION_LABELS
from app.schemas.question import QuestionDraft, ReviewScore
from app.schemas.token import TokenUsage
from app.schemas.workflow import GenerationRequest

logger = logging.getLogger(__name__)


async def regenerate_question(
    draft: QuestionDraft, review: ReviewScore, req: GenerationRequest, iteration: int = 2
) -> tuple[QuestionDraft, TokenUsage]:
    """Invokes the Question Re-Generator Agent to refine a draft that scored <= 90."""
    section_val = req.section.value if hasattr(req.section, "value") else str(req.section)
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
1. Equalize option lengths: Count the words in every option. All 4 options MUST be within 1-2 words of each other in length (e.g. 11-13 words each). Do NOT make the correct key longer or more hedged than the distractors.
2. Output format: "options" MUST be a JSON list of 4 objects with "id" and "text" string fields.

Please re-generate and refine this question to resolve all weaknesses and produce a publication-grade AAMC MCAT question. Output valid JSON only."""

    try:
        raw_output, usage = await call_llm(
            prompt=user_prompt,
            system_prompt=REGENERATOR_SYSTEM_PROMPT,
            model=req.model_name,
            api_key=req.api_key,
            temperature=config.REGENERATOR_TEMPERATURE,
            max_tokens=config.DEFAULT_MAX_TOKENS,
        )
        data = safe_json_loads(raw_output)

        # Reuse shared parsers from generator.py — single source of truth for option handling
        options = _parse_option_choices(data.get("options", []), data)
        correct_id_str, keys_list = _parse_correct_keys(data, options)

        # Fall back to the draft's existing answer keys when none are returned
        if not keys_list:
            keys_list = draft.correct_answer_ids or [options[0].id]
            correct_id_str = ", ".join(keys_list)

        effective_stimulus = (
            (
                req.shared_stimulus.strip()
                if req.shared_stimulus
                else data.get("stimulus_text", draft.stimulus_text).strip()
            )
            if is_passage_active
            else ""
        )

        re_draft = QuestionDraft(
            stimulus_text=effective_stimulus,
            question_stem=data["question_stem"],
            options=options,
            correct_answer_id=correct_id_str,
            correct_answer_ids=keys_list,
            explanation=data["explanation"],
            image_needed=data.get("image_needed", draft.image_needed),
            image_prompt_or_type=data.get("image_prompt_or_type", draft.image_prompt_or_type),
        )
        return re_draft, usage
    except Exception as e:
        logger.warning(
            f"Re-Generator LLM failed or not configured, using heuristic remediation: {e}"
        )
        mock_usage = TokenUsage(
            prompt_tokens=REGENERATOR_MOCK_PROMPT_TOKENS,
            completion_tokens=REGENERATOR_MOCK_COMPLETION_TOKENS,
            total_tokens=REGENERATOR_MOCK_PROMPT_TOKENS + REGENERATOR_MOCK_COMPLETION_TOKENS,
            cost_usd=calculate_token_cost(
                REGENERATOR_MOCK_PROMPT_TOKENS,
                REGENERATOR_MOCK_COMPLETION_TOKENS,
            ),
        )
        fallback_draft = improve_draft_heuristically(draft, review, iteration)
        if not is_passage_active:
            fallback_draft.stimulus_text = ""
        return fallback_draft, mock_usage
