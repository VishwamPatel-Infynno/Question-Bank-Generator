"""
ai_copilot.py - AI-Native interactive editorial, onboarding, and study copilot.

Provides dynamic LLM assistance across the entire product lifecycle:
1. Magic Setup: Natural language prompt -> structured GenerationRequest form state.
2. Prompt Enhancer: Rough educator notes -> AAMC-calibrated pedagogical mandate.
3. Question Copilot: In-place distractor polishing, explanation simplifying, sibling variant generation.
4. Passage Intelligence: Readability grade level, empirical data density, and AAMC stylistic audit.
5. Study Guide Synthesis: Automatic cheat sheet, trap checklist, and flashcard generation.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.agents.base import call_llm, safe_json_loads
from app.core.config import config
from app.schemas import enum_value
from app.services.readability import audit_passage_text, count_syllables

logger = logging.getLogger(__name__)

# Backward-compatible alias
_count_syllables = count_syllables


# ---------------------------------------------------------------------------
# 1. Magic Setup: Natural Language -> Wizard Form State
# ---------------------------------------------------------------------------


def _heuristic_magic_setup(prompt: str) -> dict[str, Any]:
    """Fallback deterministic parser for magic setup queries."""
    p_lower = prompt.lower()

    # Section detection
    if any(
        k in p_lower
        for k in ["cars", "humanities", "philosophy", "ethics", "literature", "history", "art"]
    ):
        section = "cars"
        subject = "Humanities"
        topic = "Philosophy & Critical Analysis"
        subtopic = "Epistemology & Rhetoric"
    elif any(
        k in p_lower
        for k in [
            "physics",
            "circuit",
            "thermo",
            "optics",
            "fluid",
            "chemical",
            "reaction",
            "acid-base",
            "titration",
        ]
    ):
        section = "chem_phys"
        subject = "Chemistry & Physics"
        topic = "Chemical Principles & Physical Foundations"
        subtopic = "Thermodynamics & Kinetics"
    elif any(
        k in p_lower
        for k in [
            "psych",
            "socio",
            "behavior",
            "conditioning",
            "memory",
            "conformity",
            "dissonance",
            "stratification",
        ]
    ):
        section = "psych_soc"
        subject = "Psychology & Sociology"
        topic = "Psychological Foundations"
        subtopic = "Cognitive Processes & Social Structure"
    else:
        section = "bio_biochem"
        subject = "Biological Sciences"
        topic = "Biochemistry & Cellular Physiology"
        subtopic = "Enzymology & Metabolism"

    # Difficulty detection
    if any(k in p_lower for k in ["hard", "difficult", "elite", "high", "top percentile"]):
        difficulty = "high"
    elif any(k in p_lower for k in ["easy", "foundational", "low"]):
        difficulty = "low"
    else:
        difficulty = "medium"

    # Question count detection (e.g. "10 questions", "10 hard passage questions", "10 sets")
    count_match = re.search(
        r"\b(\d{1,2})\s*(?:[a-z\-_]+\s+){0,4}(?:questions?|items?|sets?|qs?)\b", p_lower
    )
    if not count_match:
        # Check for bare number followed by Q (e.g. "10q", "5qs")
        count_match = re.search(r"\b(\d{1,2})\s*q[s]?\b", p_lower)
    qty = max(1, min(50, int(count_match.group(1)))) if count_match else 5

    # Visual type detection
    if any(k in p_lower for k in ["trace", "ecg", "action potential"]):
        visual_type = "physiology_trace"
    elif any(k in p_lower for k in ["radiology", "ct", "x-ray", "mri", "pet", "fmri"]):
        visual_type = "diagnostic_radiology"
    elif any(k in p_lower for k in ["pathology", "histology", "biopsy", "smear"]):
        visual_type = "histopathology"
    elif any(k in p_lower for k in ["microscopy", "tem", "sem", "micrograph"]):
        visual_type = "cellular_microscopy"
    elif any(
        k in p_lower for k in ["diagram", "graph", "plot", "gel", "blot", "pathway", "circuit"]
    ):
        visual_type = "scientific_diagram"
    else:
        visual_type = "None"

    # Primary trap detection
    if any(k in p_lower for k in ["calc", "math", "inversion", "fraction"]):
        primary_trap = "calculation_trap"
    elif any(k in p_lower for k in ["scope", "out of scope"]):
        primary_trap = "out_of_scope"
    elif any(k in p_lower for k in ["opposite", "reversal", "distortion"]):
        primary_trap = "distortion_opposite"
    elif any(k in p_lower for k in ["extreme", "absolute", "unwarranted"]):
        primary_trap = "extreme_extrapolation"
    else:
        primary_trap = "none"

    # Passage mode
    passage_mode = (
        "single_passage"
        if section == "cars" or "passage" in p_lower
        else (
            "independent" if "discrete" in p_lower or "standalone" in p_lower else "single_passage"
        )
    )

    # Extract clean topic snippet from prompt
    clean_prompt = prompt.strip()
    return {
        "section": section,
        "subject": subject,
        "unit": topic,
        "topic": topic,
        "subtopic": subtopic,
        "difficulty": difficulty,
        "passage_mode": passage_mode,
        "questions_to_generate": qty,
        "visual_type": visual_type,
        "primary_trap": primary_trap,
        "additional_instructions": f"Focus: {clean_prompt}",
    }


async def parse_magic_setup(prompt: str) -> dict[str, Any]:
    """Parses a natural language educator prompt into pre-filled wizard configuration."""
    if not prompt or not prompt.strip():
        return _heuristic_magic_setup("5 MCAT questions")

    if config.OFFLINE_MODE:
        return _heuristic_magic_setup(prompt)

    system_prompt = (
        "You are an expert MCAT platform coordinator. Convert the user's natural language request "
        "into structured generator parameters matching official AAMC specifications.\n"
        "Supported sections: 'bio_biochem', 'chem_phys', 'cars', 'psych_soc'.\n"
        "Supported difficulties: 'low', 'medium', 'high'.\n"
        "Supported visual_types: 'None', 'scientific_diagram', 'histopathology', 'gross_anatomy', "
        "'cellular_microscopy', 'physiology_trace', 'diagnostic_radiology'.\n"
        "Supported passage_modes: 'single_passage', 'independent'.\n"
        "Return ONLY a JSON object."
    )

    user_prompt = (
        f"User Request: {prompt}\n\n"
        "Extract the following fields:\n"
        "{\n"
        '  "section": "bio_biochem" | "chem_phys" | "cars" | "psych_soc",\n'
        '  "subject": string,\n'
        '  "unit": string,\n'
        '  "topic": string,\n'
        '  "subtopic": string,\n'
        '  "difficulty": "low" | "medium" | "high",\n'
        '  "passage_mode": "single_passage" | "independent",\n'
        '  "questions_to_generate": number (1-50),\n'
        '  "visual_type": string,\n'
        '  "primary_trap": string,\n'
        '  "additional_instructions": string\n'
        "}"
    )

    try:
        raw, _ = await call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.DEFAULT_TEXT_MODEL,
            temperature=0.2,
            max_tokens=2048,
        )
        data = safe_json_loads(raw)
        if isinstance(data, dict) and "section" in data:
            # Validate numeric bounds
            if "questions_to_generate" in data:
                data["questions_to_generate"] = max(1, min(50, int(data["questions_to_generate"])))
            return data
    except Exception as exc:
        logger.warning(
            "Magic setup LLM parsing failed (%s); falling back to heuristic parsing.", exc
        )

    return _heuristic_magic_setup(prompt)


# ---------------------------------------------------------------------------
# 2. Prompt Enhancer: Educator Notes -> AAMC Calibrated Mandate
# ---------------------------------------------------------------------------


async def enhance_instructions(
    instructions: str,
    section: str,
    topic: str | None = None,
    difficulty: str | None = None,
) -> str:
    """Enhances raw educator notes into a professional AAMC prompt mandate."""
    cleaned = (instructions or "").strip()
    sec_str = enum_value(section).replace("_", " ").upper()
    topic_str = (topic or "Core Curriculum").strip()
    diff_str = (difficulty or "medium").strip().lower()

    if config.OFFLINE_MODE or not cleaned:
        return (
            f"AAMC CALIBRATED MANDATE [{sec_str} • {topic_str} • {diff_str.upper()}]:\n"
            f"- Primary Pedagogical Target: {cleaned or 'Foundational conceptual and empirical mastery'}.\n"
            "- Distractor Trap Rigor: Enforce authentic multi-step reasoning traps (e.g. calculation inversion, "
            "faulty premise extrapolation) while ensuring all 4 options maintain length parity within 3 words.\n"
            "- Scientific Accuracy: All distractors must represent plausible misconceptions rather than nonsense."
        )

    system_prompt = (
        "You are an elite AAMC test development lead. Expand the educator's brief instructions into "
        "a rigorous, highly specific prompt mandate that guides AI question generation.\n"
        "Enforce official AAMC principles: single-choice (A-D), length parity, high-yield clinical/empirical "
        "grounding, and precise distractor trap calibration."
    )

    user_prompt = (
        f"MCAT Section: {sec_str}\n"
        f"Topic Focus: {topic_str}\n"
        f"Target Difficulty: {diff_str}\n"
        f"Educator's Raw Notes: {cleaned}\n\n"
        "Transform these notes into a structured 3-bullet prompt mandate specifying:\n"
        "1. Precise scientific or passage-reasoning constraint\n"
        "2. Exact distractor trap architecture to embed\n"
        "3. Quantitative or empirical baseline to require"
    )

    try:
        raw, _ = await call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.DEFAULT_TEXT_MODEL,
            temperature=0.4,
            max_tokens=800,
        )
        return raw.strip()
    except Exception as exc:
        logger.warning(
            "Enhance instructions LLM call failed (%s); returning structured fallback.", exc
        )
        return (
            f"AAMC MANDATE [{sec_str}]: {cleaned}\n"
            "- Ensure 100% scientific plausibility with strict length parity across all 4 options.\n"
            "- Target authentic clinical reasoning and empirical data interpretation."
        )


# ---------------------------------------------------------------------------
# 3. Question Copilot: Interactive Refinements
# ---------------------------------------------------------------------------


async def refine_question(
    question_data: dict[str, Any],
    instruction: str,
    action: str = "custom",
) -> dict[str, Any]:
    """Applies interactive AI refinement to a question (polish distractor, simplify explanation, invert)."""
    copied = dict(question_data)

    if config.OFFLINE_MODE:
        if action == "simplify_explanation":
            copied["explanation"] = (
                f"SIMPLIFIED EXPLANATION:\n"
                f"Correct Answer ({copied.get('correct_answer_id', 'A')}): "
                f"This choice is correct because it directly matches the foundational principle.\n\n"
                f"Distractor Breakdown:\n"
                f"Other options are incorrect because they represent common test-day misconceptions."
            )
        elif action == "polish_distractor":
            # Polish option texts
            opts = copied.get("options", [])
            if opts and len(opts) >= 4:
                # Append refined suffix
                opts[-1]["text"] = opts[-1]["text"] + " (Refined for Trap Symmetry)"
                copied["options"] = opts
        else:
            copied["explanation"] = (
                f"{copied.get('explanation', '')}\n\n[AI Refined: {instruction}]"
            )
        return copied

    system_prompt = (
        "You are an expert MCAT psychometric editor. Your task is to refine or revise an existing MCAT question "
        "according to the educator's request. Maintain single-choice format (A-D), strict option length symmetry, "
        "and accurate scientific reasoning.\n"
        "Return ONLY a JSON object representing the updated question."
    )

    user_prompt = (
        f"Original Question:\n{json.dumps(question_data, indent=2)}\n\n"
        f"Editorial Action: {action}\n"
        f"Educator Instruction: {instruction}\n\n"
        "Return the complete updated question JSON with keys: "
        "'question_stem', 'options' (array of {id, text}), 'correct_answer_id', 'explanation'."
    )

    try:
        raw, _ = await call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.DEFAULT_TEXT_MODEL,
            temperature=0.3,
            max_tokens=4096,
        )
        data = safe_json_loads(raw)
        if isinstance(data, dict) and "question_stem" in data and "options" in data:
            for k in ["question_stem", "options", "correct_answer_id", "explanation"]:
                if k in data:
                    copied[k] = data[k]
            return copied
    except Exception as exc:
        logger.warning(
            "Question refinement LLM call failed (%s); returning original with note.", exc
        )
        copied["explanation"] = (
            f"{copied.get('explanation', '')}\n\n[Editorial note: {instruction}]"
        )

    return copied


# ---------------------------------------------------------------------------
# 4. Passage Intelligence: Readability & Diagnostics
# ---------------------------------------------------------------------------

audit_passage = audit_passage_text


# ---------------------------------------------------------------------------
# 5. Study Guide Synthesis: Selected Questions -> High-Yield Cheat Sheet
# ---------------------------------------------------------------------------


async def synthesize_study_guide(questions: list[dict[str, Any]]) -> dict[str, Any]:
    """Synthesizes a collection of questions into an integrated high-yield study guide and flashcards."""
    if not questions:
        return {
            "title": "MCAT Study Guide",
            "summary": "No questions provided.",
            "top_traps": [],
            "flashcards": [],
            "markdown_guide": "# MCAT Study Guide\nNo questions provided.",
        }

    stems = [q.get("question_stem", "") for q in questions[:10]]
    topics = list(
        {q.get("subtopic") or q.get("topic") or q.get("section", "MCAT") for q in questions}
    )
    primary_topic = topics[0] if topics else "General MCAT Concepts"

    def _build_deterministic() -> dict[str, Any]:
        flashcards: list[dict[str, str]] = []
        for i, q in enumerate(questions[:8]):
            stem = q.get("question_stem", f"Concept #{i + 1}")
            corr_id = q.get("correct_answer_id", "A")
            corr_opt = next(
                (opt["text"] for opt in q.get("options", []) if opt.get("id") == corr_id),
                "Key Concept",
            )
            flashcards.append(
                {
                    "front": stem[:180],
                    "back": f"Correct ({corr_id}): {corr_opt}",
                }
            )

        top_traps = [
            "Conflating thermodynamic spontaneity (Delta G) with reaction velocity (Kinetics)",
            "Reciprocal / Fraction Inversion in physiological clearance equations",
            "Extrapolating in vitro biochemical affinity directly to in vivo physiological efficacy",
        ]

        md_content = (
            f"# High-Yield MCAT Study Guide: {primary_topic}\n\n"
            f"**Total Questions Analyzed:** {len(questions)}\n\n"
            "## 1. Executive Summary of Core Principles\n"
            f"This question set evaluates core competencies in {primary_topic}. Examinees must master "
            "foundational definitions, multi-step mechanistic deductions, and empirical data interpretation.\n\n"
            "## 2. Top Misconceptions & Distractor Traps Tested\n"
            + "\n".join(f"- {trap}" for trap in top_traps)
            + "\n\n## 3. High-Yield Flashcard Review\n"
            + "\n\n".join(
                f"**Q{i + 1}:** {fc['front']}\n*Answer:* {fc['back']}"
                for i, fc in enumerate(flashcards)
            )
        )

        return {
            "title": f"High-Yield Study Guide: {primary_topic}",
            "summary": f"Comprehensive synthesis of {len(questions)} questions on {primary_topic}.",
            "top_traps": top_traps,
            "flashcards": flashcards,
            "markdown_guide": md_content,
        }

    if config.OFFLINE_MODE:
        return _build_deterministic()

    system_prompt = (
        "You are a master MCAT medical educator. Synthesize the provided set of questions into a high-yield "
        "study guide, common trap checklist, and student flashcard deck.\n"
        "Return ONLY a JSON object."
    )

    user_prompt = (
        f"Topic Focus: {primary_topic}\n"
        f"Sample Questions:\n{json.dumps(stems, indent=2)}\n\n"
        "Generate a structured JSON study guide with keys:\n"
        "{\n"
        '  "title": string,\n'
        '  "summary": string,\n'
        '  "top_traps": string[],\n'
        '  "flashcards": [{"front": string, "back": string}],\n'
        '  "markdown_guide": string (rich markdown with headers, bullet points, and key takeaways)\n'
        "}"
    )

    try:
        raw, _ = await call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.DEFAULT_TEXT_MODEL,
            temperature=0.3,
            max_tokens=4096,
        )
        data = safe_json_loads(raw)
        if isinstance(data, dict) and "flashcards" in data and "markdown_guide" in data:
            return data
    except Exception as exc:
        logger.warning(
            "Study guide synthesis LLM call failed (%s); falling back to deterministic guide.", exc
        )

    return _build_deterministic()
