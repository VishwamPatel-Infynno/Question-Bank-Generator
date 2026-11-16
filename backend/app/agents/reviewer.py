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
    mock_usage,
)
from app.agents.base import (
    LLMNotConfiguredError,
    QualityCheckUnavailableError,
    call_llm_validated,
    require_offline_mode,
    safe_json_loads,
)
from app.agents.mock_fixtures import evaluate_heuristically
from app.agents.prompt_builder import format_options
from app.agents.prompts import REVIEWER_SYSTEM_PROMPT
from app.agents.standards import is_cars, passage_words_text
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


_PILLARS = ("authenticity_score", "clarity_score", "distractor_score", "explanation_score")


def _parse_review(data: object) -> ReviewScore:
    """Strictly parses reviewer JSON: every pillar must be present and within 0-25.

    Missing or out-of-range scores raise ValueError instead of defaulting to a passing value.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Reviewer did not return a JSON object: {type(data).__name__}")
    scores: dict[str, int] = {}
    for key in _PILLARS:
        if key not in data:
            raise ValueError(f"Reviewer response is missing '{key}'")
        value = int(float(data[key]))
        if not 0 <= value <= 25:
            raise ValueError(f"Reviewer score '{key}'={value} is outside 0-25")
        scores[key] = value
    total = sum(scores.values())
    return ReviewScore(
        **scores,
        total_score=total,
        strengths=data.get("strengths") or [],
        weaknesses=data.get("weaknesses") or [],
        recommendations=data.get("recommendations") or [],
        passed=config.passes_quality_gate(total),
    )


async def review_question(
    draft: QuestionDraft, req: GenerationRequest, iteration: int = 1
) -> tuple[ReviewScore, TokenUsage]:
    """Invokes the Question Reviewer Agent to score a candidate draft against the 100-point rubric."""
    section_val = enum_value(req.section)
    section_name = MCAT_SECTION_LABELS.get(req.section, section_val)
    options_formatted = format_options(draft)

    target_trap = (
        req.primary_trap
        if (req.primary_trap and req.primary_trap != "Automatic")
        else (draft.primary_trap or "Author Diagnosed AAMC Trap")
    )

    has_shared_passage = bool(req.shared_stimulus and req.shared_stimulus.strip())
    has_passage = bool(draft.stimulus_text and draft.stimulus_text.strip())
    passage_words = len(draft.stimulus_text.split()) if draft.stimulus_text else 0
    if has_shared_passage:
        passage_note = (
            f"Shared Passage Set ({passage_words} words; pre-established shared passage across set — "
            "audit the question's passage linkage, NOT the shared passage's length or style)"
        )
        stimulus_label = "Background Reading Passage (Shared Across Set - REFERENCE ONLY; DO NOT score or deduct points for passage content, length, or style):"
    elif req.is_passage_active and has_passage:
        passage_note = (
            f"Yes ({passage_words_text(is_cars(req.section))}; evaluate linkage to question)"
        )
        stimulus_label = "Background Reading Passage (REFERENCE ONLY; evaluate question's data linkage, DO NOT deduct points for passage prose):"
    else:
        passage_note = "No (standalone question: no passage expected)"
        stimulus_label = "Stimulus (Discrete Question - No passage expected):"

    target_benchmark = int(req.passing_threshold or config.PASSING_SCORE_THRESHOLD)

    user_prompt = f"""Review the following candidate AAMC MCAT Multiple Choice Question:

Metadata:
- Subtest: {section_name}
- Subtopic: {req.subtopic or "General"}
- Target Difficulty: {req.difficulty.value}
- Interaction Format: {req.interaction_type or "single_choice"}
- Target Trap to Audit: {target_trap}
- Passage Status: {passage_note}
- Target Passing Benchmark: {target_benchmark}/100 (Aim: 100/100 Full Score on First Pass)
- Iteration Attempt: {iteration}

--- CANDIDATE QUESTION UNDER AUDIT ---
{stimulus_label}
{draft.stimulus_text if draft.stimulus_text else "(None - Standalone Question)"}

Question Stem:
{draft.question_stem}

Options:
{options_formatted}

Correct Answer Key(s):
{draft.correct_answer_id}

Explanation:
{draft.explanation}
--------------------------
AUDIT INSTRUCTIONS:
- The 4 scoring pillars evaluate SOLELY the question item: Question Stem, Options, Key, and Explanation.
- DO NOT critique or deduct points from any pillar for the background reading passage.
- If option word counts are within parity, Option Symmetry is satisfied; do NOT penalize options for minor stylistic phrasing.
- Award the full score of 25 points per pillar (100/100 total) when the item satisfies all requirements with no identifiable psychometric defects.
Evaluate the candidate question and return your 100-point rubric breakdown as JSON."""

    try:
        # One validated call: invalid JSON/scores get a single informed repair (both calls billed);
        # provider failures are already retried with backoff inside call_llm.
        review, usage = await call_llm_validated(
            prompt=user_prompt,
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            parse=lambda raw: _parse_review(safe_json_loads(raw)),
            model=req.model_name,
            api_key=req.api_key,
            temperature=config.REVIEWER_TEMPERATURE,
            max_tokens=config.REVIEWER_MAX_TOKENS,
        )
        return review, usage
    except LLMNotConfiguredError as e:
        require_offline_mode(e)
        # No credentials at all: offline demo/test mode keeps using the heuristic reviewer.
        logger.warning("Reviewer LLM not configured, using heuristic review: %s", e)
        fallback_usage = mock_usage(REVIEWER_MOCK_PROMPT_TOKENS, REVIEWER_MOCK_COMPLETION_TOKENS)
        return evaluate_heuristically(draft, req, iteration), fallback_usage
    except Exception as e:
        # Fail closed: an item must never pass because its reviewer broke.
        logger.error("Quality reviewer failed: %s", e)
        raise QualityCheckUnavailableError(f"Quality reviewer failed: {e}") from e
