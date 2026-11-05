"""
reviewer.py - Question Reviewer Agent for MCAT Question Bank.

Scores a candidate question draft against the 100-point psychometric rubric,
breaking down Authenticity (0-25), Clarity (0-25), Distractors (0-25), and
Explanation (0-25) into a ``ReviewScore``. A score above 90 signals publication-grade quality.
"""

from __future__ import annotations

import logging

from app.agents._mock_tokens import (
    REVIEWER_MOCK_COMPLETION_TOKENS,
    REVIEWER_MOCK_PROMPT_TOKENS,
)
from app.agents.base import calculate_token_cost, call_llm, safe_json_loads
from app.agents.mock_fixtures import evaluate_heuristically
from app.agents.prompts import REVIEWER_SYSTEM_PROMPT
from app.core.config import config
from app.schemas import (
    MCAT_SECTION_LABELS,
    GenerationRequest,
    QuestionDraft,
    ReviewScore,
    TokenUsage,
)

logger = logging.getLogger(__name__)


async def review_question(
    draft: QuestionDraft, req: GenerationRequest, iteration: int = 1
) -> tuple[ReviewScore, TokenUsage]:
    """Invokes the Question Reviewer Agent to score a candidate draft against the 100-point rubric."""
    section_val = req.section.value if hasattr(req.section, "value") else str(req.section)
    section_name = MCAT_SECTION_LABELS.get(req.section, section_val)
    options_formatted = "\n".join([f"{opt.id}: {opt.text}" for opt in draft.options])

    target_trap = (
        req.primary_trap
        if (req.primary_trap and req.primary_trap != "Automatic")
        else (draft.primary_trap or "Author Diagnosed AAMC Trap")
    )

    user_prompt = f"""Review the following candidate AAMC MCAT Multiple Choice Question:

Metadata:
- Subtest: {section_name}
- Subtopic: {req.subtopic or "General"}
- Target Difficulty: {req.difficulty.value}
- Interaction Format: {req.interaction_type or "single_choice"}
- Target Trap to Audit: {target_trap}
- Passage Type: {"Yes (250-400 words)" if req.passage_required and str(req.passage_required).lower() in ("yes", "true") else "No"}
- Iteration Attempt: {iteration}

--- CANDIDATE QUESTION ---
Stimulus:
{draft.stimulus_text}

Question Stem:
{draft.question_stem}

Options:
{options_formatted}

Correct Answer Key(s):
{draft.correct_answer_id}

Explanation:
{draft.explanation}
--------------------------
Evaluate this question thoroughly and return your 100-point rubric breakdown as JSON."""

    try:
        raw_output, usage = await call_llm(
            prompt=user_prompt,
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            model=req.model_name,
            api_key=req.api_key,
            temperature=config.REVIEWER_TEMPERATURE,
            max_tokens=config.REVIEWER_MAX_TOKENS,
        )
        data = safe_json_loads(raw_output)

        auth = int(float(data.get("authenticity_score", 23)))
        clarity = int(float(data.get("clarity_score", 23)))
        distractor = int(float(data.get("distractor_score", 23)))
        explanation = int(float(data.get("explanation_score", 23)))
        total = auth + clarity + distractor + explanation

        passed = config.passes_quality_gate(total)

        review = ReviewScore(
            authenticity_score=auth,
            clarity_score=clarity,
            distractor_score=distractor,
            explanation_score=explanation,
            total_score=total,
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            recommendations=data.get("recommendations", []),
            passed=passed,
        )
        return review, usage
    except Exception as e:
        logger.warning(f"Reviewer LLM failed or not configured, using heuristic review: {e}")
        mock_usage = TokenUsage(
            prompt_tokens=REVIEWER_MOCK_PROMPT_TOKENS,
            completion_tokens=REVIEWER_MOCK_COMPLETION_TOKENS,
            total_tokens=REVIEWER_MOCK_PROMPT_TOKENS + REVIEWER_MOCK_COMPLETION_TOKENS,
            cost_usd=calculate_token_cost(
                REVIEWER_MOCK_PROMPT_TOKENS,
                REVIEWER_MOCK_COMPLETION_TOKENS,
            ),
        )
        return evaluate_heuristically(draft, req, iteration), mock_usage
