"""
Blind-Solver Dual Validation Agent.

Simulates an independent, top-percentile MCAT test-taker solving the drafted question
WITHOUT seeing the intended correct key or explanation. Verifies that the correct answer
is incontrovertible and that no ambiguous interpretations or flawed distractors exist.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.agents.base import (
    LLMNotConfiguredError,
    QualityCheckUnavailableError,
    call_llm,
    require_offline_mode,
    safe_json_loads,
)
from app.core.config import config
from app.schemas import GenerationRequest, QuestionDraft, TokenUsage

logger = logging.getLogger(__name__)

BLIND_SOLVER_SYSTEM_PROMPT = """You are an elite MD/PhD Physician-Scientist and Perfect-Score MCAT Test Taker (528/528).
Your task is to independently solve candidate AAMC MCAT Multiple Choice Questions strictly based on the provided stimulus and question stem.

CRITICAL INSTRUCTIONS:
1. You are solving this problem BLIND. You are not given the intended answer key or the author's explanation.
2. Carefully analyze the stimulus (if present) and the question stem.
3. Evaluate each of the 4 answer choices (A, B, C, D) with uncompromising scientific, mathematical, and textual rigor.
4. Select the SINGLE BEST ANSWER that is indisputably supported by the passage or scientific principles.
5. Provide your confidence score as a percentage from 0 to 100:
   - 90-100%: Completely clear, indisputable key with zero ambiguity.
   - 70-89%: Likely correct, but minor ambiguity in phrasing or one distractor is uncomfortably close.
   - <70%: Highly ambiguous question, flawed stem, or multiple defensible answers.
6. Evaluate Ambiguity: Set "is_ambiguous" to true if there is ANY reasonable interpretation under which another choice could be argued as correct, or if the question stem lacks crucial information.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this exact structure:
{
  "selected_key": "B",
  "confidence": 95,
  "is_ambiguous": false,
  "ambiguity_notes": "",
  "solver_rationale": "Option B is incontrovertibly supported by paragraph 3 kinetic data..."
}"""


class BlindSolverResult(BaseModel):
    selected_key: str = Field(
        description="The option letter chosen by the blind solver (A, B, C, or D)"
    )
    confidence: int = Field(default=95, description="Confidence score 0-100")
    is_ambiguous: bool = Field(
        default=False, description="Whether the question suffers from ambiguity"
    )
    ambiguity_notes: str = Field(
        default="", description="Critique of any stem or distractor ambiguities"
    )
    solver_rationale: str = Field(
        default="", description="Brief proof explaining why the selected key was chosen"
    )
    agrees_with_key: bool = Field(
        default=True, description="Whether selected_key matches the draft key"
    )
    is_verified: bool = Field(
        default=True, description="Whether the question passed blind validation"
    )
    usage: TokenUsage | None = None


def _format_blind_solver_prompt(draft: QuestionDraft, req: GenerationRequest) -> str:
    prompt_lines = [
        f"Section: {req.section.value if hasattr(req.section, 'value') else str(req.section)}"
    ]
    if req.topic:
        prompt_lines.append(f"Topic: {req.topic}")

    if draft.stimulus_text and draft.stimulus_text.strip():
        prompt_lines.append(
            f"\n[READING PASSAGE / EXPERIMENTAL STIMULUS]:\n{draft.stimulus_text.strip()}"
        )

    prompt_lines.append(f"\n[QUESTION STEM]:\n{draft.question_stem.strip()}\n")
    prompt_lines.append("[ANSWER CHOICES]:")
    for opt in draft.options:
        prompt_lines.append(f"{opt.id}. {opt.text}")

    prompt_lines.append(
        "\nDetermine the single best answer. Output your selected key, confidence percentage (0-100), "
        "ambiguity evaluation, and solver rationale in the required JSON format."
    )
    return "\n".join(prompt_lines)


async def blind_solve_question(
    draft: QuestionDraft,
    req: GenerationRequest,
) -> tuple[BlindSolverResult, TokenUsage]:
    """
    Submits candidate question to an independent solver model without key or explanation.
    Evaluates key alignment, confidence, and absence of ambiguity.

    Fails closed: if the solver cannot produce a valid answer after two attempts, a
    ``QualityCheckUnavailableError`` is raised instead of certifying the key unchecked.
    The only bypass is offline mode (no LLM credentials configured at all).
    """
    user_prompt = _format_blind_solver_prompt(draft, req)
    expected_key = (draft.correct_answer_id or "A").strip().upper()

    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            raw_output, usage = await call_llm(
                prompt=user_prompt,
                system_prompt=BLIND_SOLVER_SYSTEM_PROMPT,
                model=req.model_name,
                api_key=req.api_key,
                temperature=config.BLIND_SOLVER_TEMPERATURE,
                max_tokens=config.BLIND_SOLVER_MAX_TOKENS,
            )
            result = _parse_solver_result(safe_json_loads(raw_output), expected_key, usage)
            logger.info(
                f"Blind Solver: selected='{result.selected_key}', intended='{expected_key}', "
                f"confidence={result.confidence}%, verified={result.is_verified}"
            )
            return result, usage
        except LLMNotConfiguredError as e:
            require_offline_mode(e)
            logger.warning(f"Blind solver LLM not configured, offline bypass: {e}")
            usage = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0, cost_usd=0.0)
            return BlindSolverResult(
                selected_key=expected_key,
                confidence=95,
                is_ambiguous=False,
                ambiguity_notes="",
                solver_rationale="Blind solver bypassed: no LLM credentials configured (offline mode).",
                agrees_with_key=True,
                is_verified=True,
                usage=usage,
            ), usage
        except Exception as e:
            last_error = e
            logger.warning(f"Blind solver attempt {attempt}/2 failed: {e}")

    raise QualityCheckUnavailableError(f"Blind solver failed after 2 attempts: {last_error}")


def _parse_solver_result(data: object, expected_key: str, usage: TokenUsage) -> BlindSolverResult:
    """Strictly parses the solver JSON; missing or invalid fields raise ValueError."""
    if not isinstance(data, dict):
        raise ValueError(f"Blind solver did not return a JSON object: {data}")

    selected_key = str(data.get("selected_key", "")).strip().upper()
    # Extract single letter if model returned e.g. "Option B" or "B."
    if len(selected_key) > 1:
        for char in selected_key:
            if char in ("A", "B", "C", "D"):
                selected_key = char
                break
    if selected_key not in ("A", "B", "C", "D"):
        raise ValueError(f"Blind solver returned an invalid key: {selected_key!r}")
    if "confidence" not in data:
        raise ValueError("Blind solver response is missing 'confidence'")

    confidence = int(float(data["confidence"]))
    is_ambiguous = bool(data.get("is_ambiguous", False))
    agrees = selected_key == expected_key
    is_verified = (
        agrees and confidence >= config.BLIND_SOLVER_CONFIDENCE_THRESHOLD and not is_ambiguous
    )
    return BlindSolverResult(
        selected_key=selected_key,
        confidence=confidence,
        is_ambiguous=is_ambiguous,
        ambiguity_notes=str(data.get("ambiguity_notes", "")).strip(),
        solver_rationale=str(data.get("solver_rationale", "")).strip(),
        agrees_with_key=agrees,
        is_verified=is_verified,
        usage=usage,
    )
