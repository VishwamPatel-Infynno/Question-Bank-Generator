"""
Blind-Solver Dual Validation Agent.

Simulates an independent, top-percentile MCAT test-taker solving the drafted question
WITHOUT seeing the intended correct key or explanation. Verifies that the correct answer
is incontrovertible and that no ambiguous interpretations or flawed distractors exist.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

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

7. If a figure is described rather than shown, reason only from the description and treat missing numeric detail as a source of ambiguity.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object. Write your reasoning FIRST so the answer follows from it:
{
  "solver_rationale": "<step-by-step reasoning that rules each choice in or out>",
  "ambiguity_notes": "<any alternative defensible reading, or empty string>",
  "is_ambiguous": false,
  "confidence": <integer 0-100>,
  "selected_key": "<A, B, C, or D>"
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


_KEY_RE = re.compile(r"\b([A-D])\b")
_LETTER_REFERENCE_RE = re.compile(
    r"\b(?:options?|choices?|answers?|statements?)\s+[A-D]\b|\b[A-D]\s+(?:and|or|&)\s+[A-D]\b|\bboth\s+[A-D]\b",
    re.IGNORECASE,
)
# Display orders (indices into the draft's options) used to sample the solver on different layouts
_DISPLAY_ORDERS = ((0, 1, 2, 3), (3, 2, 1, 0), (2, 3, 0, 1))


@dataclass
class _Sample:
    key: str  # mapped back to the draft's original option id
    confidence: int
    is_ambiguous: bool
    notes: str
    rationale: str
    usage: TokenUsage


def _options_reference_letters(draft: QuestionDraft) -> bool:
    """True if any option mentions another option by letter, so relabeling would corrupt it."""
    return any(_LETTER_REFERENCE_RE.search(o.text or "") for o in draft.options)


def _display_order(draft: QuestionDraft, variant: int) -> list[int]:
    """Option order shown to the solver. Layout variation is skipped when it is unsafe."""
    if variant == 0 or _options_reference_letters(draft) or len(draft.options) != 4:
        return list(range(len(draft.options)))
    return list(_DISPLAY_ORDERS[variant % len(_DISPLAY_ORDERS)])


def _extract_key(raw: object) -> str:
    """Pulls a standalone A-D letter from model output ("B", "Option C", "THE ANSWER IS D")."""
    match = _KEY_RE.search(str(raw).strip().upper())
    if not match:
        raise ValueError(f"Blind solver returned an invalid key: {str(raw)!r}")
    return match.group(1)


def _format_blind_solver_prompt(
    draft: QuestionDraft, req: GenerationRequest, order: list[int] | None = None
) -> str:
    prompt_lines = [
        f"Section: {req.section.value if hasattr(req.section, 'value') else str(req.section)}"
    ]
    if req.topic:
        prompt_lines.append(f"Topic: {req.topic}")

    if draft.stimulus_text and draft.stimulus_text.strip():
        prompt_lines.append(
            f"\n[READING PASSAGE / EXPERIMENTAL STIMULUS]:\n{draft.stimulus_text.strip()}"
        )
    if draft.image_needed and draft.image_prompt_or_type:
        prompt_lines.append(
            f"\n[FIGURE - described, not shown]:\n{str(draft.image_prompt_or_type).strip()}"
        )

    prompt_lines.append(f"\n[QUESTION STEM]:\n{draft.question_stem.strip()}\n")
    prompt_lines.append("[ANSWER CHOICES]:")
    shown = order if order is not None else list(range(len(draft.options)))
    for letter, idx in zip("ABCD", shown, strict=False):
        prompt_lines.append(f"{letter}. {draft.options[idx].text}")

    prompt_lines.append(
        "\nDetermine the single best answer. Output your reasoning, ambiguity evaluation, "
        "confidence percentage (0-100) and selected key in the required JSON format."
    )
    return "\n".join(prompt_lines)


async def _solve_once(
    draft: QuestionDraft, req: GenerationRequest, variant: int, temperature: float
) -> _Sample:
    """One independent solve with retry; raises QualityCheckUnavailableError if both attempts fail."""
    order = _display_order(draft, variant)
    prompt = _format_blind_solver_prompt(draft, req, order)
    override = config.BLIND_SOLVER_MODEL
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            raw_output, usage = await call_llm(
                prompt=prompt,
                system_prompt=BLIND_SOLVER_SYSTEM_PROMPT,
                # A dedicated solver model must not receive a client key meant for the primary
                model=override or req.model_name,
                api_key=None if override else req.api_key,
                temperature=temperature,
                max_tokens=config.BLIND_SOLVER_MAX_TOKENS,
            )
            data = safe_json_loads(raw_output)
            if not isinstance(data, dict):
                raise ValueError(f"Blind solver did not return a JSON object: {data}")
            shown_key = _extract_key(data.get("selected_key", ""))
            shown_index = "ABCD".index(shown_key)
            if shown_index >= len(order):
                raise ValueError(f"Blind solver selected a nonexistent option: {shown_key}")
            if "confidence" not in data:
                raise ValueError("Blind solver response is missing 'confidence'")
            return _Sample(
                key=draft.options[order[shown_index]].id.strip().upper(),
                confidence=int(float(data["confidence"])),
                is_ambiguous=bool(data.get("is_ambiguous", False)),
                notes=str(data.get("ambiguity_notes", "")).strip(),
                rationale=str(data.get("solver_rationale", "")).strip(),
                usage=usage,
            )
        except LLMNotConfiguredError:
            raise
        except Exception as e:
            last_error = e
            logger.warning(f"Blind solver sample {variant} attempt {attempt}/2 failed: {e}")
    raise QualityCheckUnavailableError(f"Blind solver failed after 2 attempts: {last_error}")


def _sum_usage(samples: list[_Sample]) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=sum(s.usage.prompt_tokens for s in samples),
        completion_tokens=sum(s.usage.completion_tokens for s in samples),
        total_tokens=sum(s.usage.total_tokens for s in samples),
        cost_usd=round(sum(s.usage.cost_usd for s in samples), 7),
        duration_ms=max((s.usage.duration_ms or 0) for s in samples) or None,
    )


def aggregate_samples(samples: list[_Sample], expected_key: str) -> BlindSolverResult:
    """Combines independent solves into one verdict by majority vote.

    Verified requires a strict majority to pick the author's key, the agreeing samples' mean
    confidence to reach the threshold, and a majority of samples to see no ambiguity. A split vote
    is never verified: the stem or options are not unambiguous.
    """
    expected = expected_key.strip().upper()
    votes = Counter(s.key for s in samples)
    top_key, top_count = votes.most_common(1)[0]
    needed = math.floor(len(samples) / 2) + 1
    majority_key = top_key if top_count >= needed else None
    agreeing = [s for s in samples if s.key == expected]
    mean_conf = round(sum(s.confidence for s in agreeing) / len(agreeing)) if agreeing else 0
    ambiguous = sum(1 for s in samples if s.is_ambiguous) >= needed
    dissent = next((s for s in samples if s.key != expected), samples[0])
    is_verified = (
        majority_key == expected
        and mean_conf >= config.BLIND_SOLVER_CONFIDENCE_THRESHOLD
        and not ambiguous
    )
    shown = dissent if majority_key != expected else samples[0]
    return BlindSolverResult(
        selected_key=majority_key or dissent.key,
        confidence=mean_conf if agreeing else min(s.confidence for s in samples),
        is_ambiguous=ambiguous or majority_key is None,
        ambiguity_notes=(
            "Solver samples disagreed on the answer." if majority_key is None else shown.notes
        ),
        solver_rationale=shown.rationale,
        agrees_with_key=majority_key == expected,
        is_verified=is_verified,
        usage=_sum_usage(samples),
    )


async def blind_solve_question(
    draft: QuestionDraft,
    req: GenerationRequest,
) -> tuple[BlindSolverResult, TokenUsage]:
    """
    Submits candidate question to independent solver samples without key or explanation.

    Samples run on different option layouts (reversed, rotated) so position bias cannot confirm
    a flawed key: two concurrent samples, plus a tie-breaker only if they disagree
    (``BLIND_SOLVER_SAMPLES=1`` restores the single-sample behavior). Fails closed: if a sample
    cannot produce a valid answer, ``QualityCheckUnavailableError`` is raised instead of
    certifying the key unchecked. The only bypass is offline mode (no credentials, OFFLINE_MODE).
    """
    expected_key = (draft.correct_answer_id or "A").strip().upper()
    base_temp = config.BLIND_SOLVER_TEMPERATURE
    n = max(1, config.BLIND_SOLVER_SAMPLES)

    try:
        if n == 1:
            samples = [await _solve_once(draft, req, 0, base_temp)]
        else:
            diversified = min(1.0, base_temp + 0.2)
            samples = list(
                await asyncio.gather(
                    _solve_once(draft, req, 0, base_temp),
                    *(_solve_once(draft, req, v, diversified) for v in range(1, 2)),
                )
            )
            if n >= 3 and samples[0].key != samples[1].key:
                samples.append(await _solve_once(draft, req, 2, diversified))
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

    result = aggregate_samples(samples, expected_key)
    logger.info(
        f"Blind Solver: votes={[s.key for s in samples]}, intended='{expected_key}', "
        f"confidence={result.confidence}%, verified={result.is_verified}"
    )
    return result, result.usage
