"""
prompt_builder.py - User-prompt construction for the MCAT question generator agent.

Extracted from generator.py to separate pure string-building logic from LLM call
and response-parsing logic. This module has no side-effects and does not call any
external services.
"""

from app.schemas.mcat import (
    MCAT_SECTION_LABELS,
    MCATSection,
)
from app.schemas.workflow import GenerationRequest


def _build_generator_user_prompt(
    req: GenerationRequest,
    fused: bool = False,
    diversity_context: str | None = None,
) -> str:
    """
    Constructs the user-turn prompt sent to the MCAT question generator LLM.

    Assembles all relevant request parameters - section, difficulty, passage mode,
    distractor traps, mistake patterns, visual stimulus flags, and cross-item diversity
    calibration - into a single structured prompt string.

    Args:
        req: The GenerationRequest containing all question generation parameters.
        fused: If True, appends the self-critique instruction required by the
            fused generator (which outputs both a question draft and a rubric score
            in one LLM call).
        diversity_context: Optional string injected to guide trap/misconception
            variety across multi-question batches (e.g. "Previously used: X, Y").

    Returns:
        A fully assembled prompt string ready to be sent as the ``user`` turn
        to ``call_llm``.
    """
    section_val = req.section.value if hasattr(req.section, "value") else str(req.section)
    section_name = MCAT_SECTION_LABELS.get(req.section, section_val)

    user_prompt = f"""Generate an official-caliber AAMC MCAT Multiple Choice Question with 4 options (A, B, C, D) and exactly ONE correct answer.

Section: {section_name}"""
    if req.subject:
        user_prompt += f"\nSubject: {req.subject}"
    if req.unit:
        user_prompt += f"\nUnit: {req.unit}"
    if req.topic:
        user_prompt += f"\nTopic: {req.topic}"
    user_prompt += f"\nSubtopic: {req.subtopic or 'Foundational Syllabus Focus'}"
    user_prompt += f"\nTarget Difficulty: {req.difficulty.value}"
    user_prompt += "\nInteraction Format: Single Choice (4 options: A, B, C, D)"
    user_prompt += (
        "\nCRITICAL OPTION LENGTH MANDATE: All 4 options (A, B, C, D) MUST have virtually identical word counts "
        "(within 1 to 3 words of each other, e.g., exactly 12-14 words each). The correct answer MUST NOT be "
        "longer, more qualified, or more detailed than any distractor."
    )

    if req.aamc_skill:
        user_prompt += f"\nAAMC Reasoning Skill: {req.aamc_skill}"
    if req.subskill:
        user_prompt += f"\nGranular Subskill Focus: {req.subskill}"
    if req.combination_id:
        user_prompt += f"\nCombination ID: {req.combination_id}"
    if req.content_domains:
        user_prompt += f"\nContent Domains: {', '.join(req.content_domains)}"
    elif req.content_domain:
        user_prompt += f"\nContent Domain: {req.content_domain}"
    if req.question_type:
        user_prompt += f"\nQuestion Type Format: {req.question_type}"

    # Target Student Misconception / Likely Mistake Pattern Calibration
    if req.likely_mistake_pattern and req.likely_mistake_pattern not in ("Automatic", "None", ""):
        user_prompt += (
            f"\nTarget Student Misconception / Mistake Pattern: {req.likely_mistake_pattern}\n"
            "CRITICAL DISTRACTOR DESIGN: Engineer at least one distractor option specifically designed "
            "to attract students who commit this exact mistake, and explain this in the distractor breakdown. "
            "Set 'likely_mistake_pattern' to this targeted pattern."
        )
    elif req.likely_mistake_pattern == "None":
        user_prompt += (
            "\nTarget Student Misconception: Standard item format (no specific single misconception targeted). "
            "Set 'likely_mistake_pattern': null in output JSON."
        )
    else:
        # Default or "Automatic" → Smart AI Choice
        user_prompt += (
            "\nTarget Student Misconception / Mistake Pattern: Automatic (Smart AI Choice)\n"
            "Analyze the scientific passage, concepts, equations, and question stem to diagnose the most authentic "
            "student misconception or calculation/conceptual error for this problem (e.g. from official MCAT patterns "
            "such as USES_WRONG_REFERENCE_VALUE, INVERTS_FRACTION, FORGETS_SQUARE_ROOT, CONFUSES_ENANTIOMERS_DIASTEREOMERS, "
            "MISREADS_GRAPH_AXES, FAILS_TO_SUBTRACT_BASELINE, CONFUSES_KM_VMAX, DROPS_NEGATIVE_SIGN, etc., or tailored to the concept). "
            "Engineer at least one distractor specifically targeting this misconception, explain it in the distractor breakdown, "
            "and populate the 'likely_mistake_pattern' JSON field with your diagnosed pattern."
        )

    # Primary Cognitive Distractor Trap
    if req.primary_trap and req.primary_trap != "Automatic":
        user_prompt += f"\nPrimary Distractor Trap to Emphasize: {req.primary_trap}"
    else:
        user_prompt += (
            "\nPrimary Distractor Trap: Automatic (Smart AI Choice)\n"
            "Analyze the section, passage/stimulus, and question stem to intelligently choose the most realistic "
            "AAMC cognitive distractor trap from the official 25 traps (e.g. CONCEPT_CONFUSION, WRONG_BASE, "
            "UNIT_CONVERSION, FORMULA_MISAPPLICATION, SIGN_CONVENTION, PROPORTIONALITY_ERROR, ASSUMPTION_MISSED, "
            "CAUSE_EFFECT_CONFUSION, CORRELATION_CAUSATION, CONTROL_GROUP_CONFUSION, VARIABLE_CONFUSION, "
            "SAMPLE_SIZE_BIAS, STATISTICAL_SIGNIFICANCE, GRAPH_AXIS_MISREADING, TABLE_COMPARISON_ERROR, "
            "TREND_EXTRAPOLATION, MECHANISM_CONFUSION, EXCEPTION_OVERLOOKED, NEGATION_MISREAD, SCOPE_SHIFT, "
            "UNSUPPORTED_INFERENCE, PASSAGE_CONTRADICTION, OVERGENERALIZATION, DISTRACTOR_OVERINTERPRETATION, "
            "ANSWER_CHOICE_CONFLATION) and populate the 'primary_trap' JSON field with your selected trap."
        )

    # Cross-Item Diversity Calibration for multi-question sets / batches
    if diversity_context:
        user_prompt += f"\nCROSS-ITEM VARIETY CALIBRATION: {diversity_context}"

    # Section-specific CARS warning
    if req.section in (MCATSection.CARS, "CARS", "cars"):
        user_prompt += (
            "\nCRITICAL CARS RULE: Strictly test ONLY what is justified directly by the passage text. "
            "Do NOT test or permit any outside scientific, clinical, or unmentioned real-world knowledge. "
            "Assess Foundations of Comprehension, Reasoning Within the Text, or Reasoning Beyond the Text."
        )

    # Handle pre-existing shared passage (Single Passage Set) vs new passage
    if req.shared_stimulus and req.shared_stimulus.strip():
        user_prompt += f"""\nCRITICAL PASSAGE INSTRUCTION:
You MUST formulate this question strictly and exclusively based on the following PRE-EXISTING READING PASSAGE.
Do NOT write a new passage. Formulate your question stem, options, correct key, and explanation directly against this text:
---
{req.shared_stimulus.strip()}
---"""
    elif req.is_passage_active:
        user_prompt += (
            "\nPassage Required: Yes - Provide a rigorous, substantive 300-500 word experimental/biomedical study "
            "(or 500-600 word humanities/social sciences essay for CARS) with clear paragraphing and empirical data descriptions."
        )
    else:
        user_prompt += (
            "\nPassage Required: No - Standalone discrete question ONLY. Do NOT write any reading passage, scenario, or vignette in stimulus_text. "
            'Leave stimulus_text strictly as an empty string (""). Pose the complete problem directly in question_stem.'
        )

    if req.visual_type and req.visual_type != "None":
        user_prompt += f"\nVisual Stimulus Type: {req.visual_type}"
    instructions = req.additional_instructions or req.custom_prompt
    if instructions and instructions.strip():
        user_prompt += (
            "\nCRITICAL EDUCATOR INSTRUCTION (HIGH FIDELITY MANDATE):\n"
            "The author has specified the following mandatory custom instructions for this question. "
            "You MUST strictly adhere to and incorporate these requirements into the question stem, answer choices, and rationale:\n"
            f'"""\n{instructions.strip()}\n"""'
        )

    # Visual stimulus discretion instruction
    allow_visuals = (req.allow_ai_images or req.require_image) and req.section not in (
        MCATSection.CARS,
        "CARS",
        "cars",
    )
    if allow_visuals:
        if req.require_image:
            user_prompt += (
                "\nMANDATORY VISUAL STIMULUS REQUIREMENT:\n"
                "- This question MUST incorporate and directly test an accompanying visual stimulus, figure, or illustration as required by the context "
                "(e.g. anatomical/organ system illustration, cellular pathway, laboratory experimental apparatus, data plot, biochemical mechanism, "
                "reaction coordinate, electrical circuit, ray optics setup, or behavioral/psychological test paradigm).\n"
                "- In your question stem, directly refer to the visual figure (e.g., 'As shown in the diagram...', 'Based on the figure below...', 'In the experiment depicted...').\n"
                "- Strictly set 'image_needed': true and write a vivid, detailed description of the visual in 'image_prompt_or_type'.\n"
            )
        else:
            user_prompt += (
                "\nVISUAL STIMULUS DISCRETION:\n"
                "- Visual stimuli are ENABLED. If this question benefits from any accompanying visual stimulus (such as an experimental apparatus, "
                "biological or anatomical diagram, physiological process, optical ray diagram, electrical circuit, metabolic pathway, Lineweaver-Burk or kinetic plot, "
                "gel electrophoresis blot, molecular structure, reaction mechanism, or psychological test stimulus) to solve, "
                "set 'image_needed': true and provide a detailed visual description in 'image_prompt_or_type'.\n"
                "- If the question is purely conceptual, numerical, or fully solvable from text alone, set 'image_needed': false and 'image_prompt_or_type': null."
            )
    else:
        user_prompt += (
            "\nVISUAL STIMULUS RESTRICTION:\n"
            "- Visual stimuli are DISABLED. Strictly set 'image_needed': false and 'image_prompt_or_type': null."
        )

    user_prompt += (
        "\nANTI-GUESSABILITY & OPTION SYMMETRY MANDATE:\n"
        "- All options MUST have roughly equal length and word count (strictly within ±15% or 2-4 words of each other).\n"
        "- The correct option MUST NOT be the longest choice or the most qualified/hedged statement.\n"
        "- Use parallel grammatical syntax across all choices (identical part of speech and structural format).\n"
        "- Ensure distractors represent authentic, highly plausible cognitive reasoning traps."
    )

    if fused:
        user_prompt += (
            "\nCRITICAL SELF-CRITIQUE CERTIFICATION INSTRUCTION:\n"
            "After composing the question, options, and explanation, perform an objective psychometric self-critique.\n"
            "Verify option lengths: when all 4 choices are balanced within 1-3 words of each other and follow parallel syntax, "
            "Option Symmetry is 100% satisfied. When your draft fulfills publication standards, certify your completed draft "
            "at passing standard (authenticity_score: 24, clarity_score: 24, distractor_score: 23, explanation_score: 24, total: 95/100).\n"
            "Output ONLY valid JSON matching the specified fused schema."
        )
    else:
        user_prompt += "\nOutput ONLY valid JSON matching the specified schema."

    return user_prompt
