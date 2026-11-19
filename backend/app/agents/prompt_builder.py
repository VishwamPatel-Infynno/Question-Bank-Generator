"""
prompt_builder.py - User-prompt construction for the MCAT question generator agent.

Extracted from generator.py to separate pure string-building logic from LLM call
and response-parsing logic. This module has no side-effects and does not call any
external services.
"""

from __future__ import annotations

from app.agents.standards import (
    CARS_PASSAGE_WORDS,
    OPTION_PARITY_TEXT,
    SCIENCE_PASSAGE_WORDS,
    is_cars,
)
from app.schemas import (
    AAMC_REASONING_SKILLS,
    KNOWN_VISUAL_TYPES,
    MCAT_SECTION_LABELS,
    GenerationRequest,
    QuestionDraft,
    enum_value,
)

__all__ = [
    "_build_generator_user_prompt",
    "_build_mandates_and_critique_block",
    "_build_mistake_pattern_directive",
    "_build_pedagogy_and_trap_block",
    "_build_primary_trap_directive",
    "_build_skill_and_domain_metadata",
    "_build_stimulus_context_block",
    "_build_syllabus_metadata_lines",
    "_build_topic_coordinates",
    "_build_visual_stimulus_block",
    "build_generator_user_prompt",
    "educator_instruction_block",
    "format_options",
]


def educator_instruction_block(req: GenerationRequest, mandate: str, directive: str) -> str:
    """The author's custom instructions as a prompt block, or "" when there are none."""
    instructions = req.additional_instructions
    if not instructions or not instructions.strip():
        return ""
    return (
        f"\nCRITICAL EDUCATOR INSTRUCTION ({mandate}):\n{directive}\n"
        f'"""\n{instructions.strip()}\n"""'
    )


def format_options(draft: QuestionDraft) -> str:
    """Answer options as the one-per-line "A: text" list the reviewer and improver prompts use."""
    return "\n".join(f"{opt.id}: {opt.text}" for opt in draft.options)


def _build_mistake_pattern_directive(req: GenerationRequest) -> str:
    """Formulates the target misconception / mistake pattern prompt directive."""
    if req.likely_mistake_pattern and req.likely_mistake_pattern not in ("Automatic", "None", ""):
        return (
            f"Target Student Misconception / Mistake Pattern: {req.likely_mistake_pattern}\n"
            "CRITICAL DISTRACTOR DESIGN: Engineer at least one distractor option specifically designed "
            "to attract students who commit this exact mistake, and explain this in the distractor breakdown. "
            "Set 'likely_mistake_pattern' to this targeted pattern."
        )
    if req.likely_mistake_pattern == "None":
        return (
            "Target Student Misconception: Standard item format (no specific single misconception targeted). "
            "Set 'likely_mistake_pattern': null in output JSON."
        )
    return (
        "Target Student Misconception / Mistake Pattern: Automatic (Smart AI Choice)\n"
        "Analyze the scientific passage, concepts, equations, and question stem to diagnose the most authentic "
        "student misconception or calculation/conceptual error for this problem (e.g. from official MCAT patterns "
        "such as USES_WRONG_REFERENCE_VALUE, INVERTS_FRACTION, FORGETS_SQUARE_ROOT, CONFUSES_ENANTIOMERS_DIASTEREOMERS, "
        "MISREADS_GRAPH_AXES, FAILS_TO_SUBTRACT_BASELINE, CONFUSES_KM_VMAX, DROPS_NEGATIVE_SIGN, etc., or tailored to the concept). "
        "Engineer at least one distractor specifically targeting this misconception, explain it in the distractor breakdown, "
        "and populate the 'likely_mistake_pattern' JSON field with your diagnosed pattern."
    )


def _build_primary_trap_directive(req: GenerationRequest) -> str:
    """Formulates the primary cognitive distractor trap prompt directive."""
    if req.primary_trap and req.primary_trap != "Automatic":
        return f"Primary Distractor Trap to Emphasize: {req.primary_trap}"
    return (
        "Primary Distractor Trap: Automatic (Smart AI Choice)\n"
        "Analyze the section, passage/stimulus, and question stem to intelligently choose the most realistic "
        "AAMC cognitive distractor trap from the official 25 traps (e.g. CONCEPT_CONFUSION, WRONG_BASE, "
        "UNIT_CONVERSION, FORMULA_MISAPPLICATION, SIGN_CONVENTION, PROPORTIONALITY_ERROR, ASSUMPTION_MISSED, "
        "CAUSE_EFFECT_CONFUSION, CORRELATION_CAUSATION, CONTROL_GROUP_CONFUSION, VARIABLE_CONFUSION, "
        "SAMPLE_SIZE_BIAS, STATISTICAL_SIGNIFICANCE, GRAPH_AXIS_MISREADING, TABLE_COMPARISON_ERROR, "
        "TREND_EXTRAPOLATION, MECHANISM_CONFUSION, EXCEPTION_OVERLOOKED, NEGATION_MISREAD, SCOPE_SHIFT, "
        "UNSUPPORTED_INFERENCE, PASSAGE_CONTRADICTION, OVERGENERALIZATION, DISTRACTOR_OVERINTERPRETATION, "
        "ANSWER_CHOICE_CONFLATION) and populate the 'primary_trap' JSON field with your selected trap."
    )


def _build_topic_coordinates(req: GenerationRequest) -> list[str]:
    """Builds subject, unit, topic, subtopic, and difficulty lines."""
    lines: list[str] = []
    if req.subject:
        lines.append(f"Subject: {req.subject}")
    if req.unit:
        lines.append(f"Unit: {req.unit}")
    if req.topic:
        lines.append(f"Topic: {req.topic}")
    lines.append(f"Subtopic: {req.subtopic or 'Foundational Syllabus Focus'}")
    lines.append(f"Target Difficulty: {req.difficulty.value}")
    lines.append("Interaction Format: Single Choice (4 options: A, B, C, D)")
    lines.append(
        "CRITICAL OPTION LENGTH MANDATE: All 4 options (A, B, C, D) MUST have virtually identical word counts "
        f"({OPTION_PARITY_TEXT}). The correct answer MUST NOT be "
        "longer, more qualified, or more detailed than any distractor."
    )
    return lines


def _build_skill_and_domain_metadata(req: GenerationRequest) -> list[str]:
    """Builds AAMC reasoning skill, subskill, combination ID, domain, and directive lines."""
    lines: list[str] = []
    if req.aamc_skill and req.aamc_skill.lower() not in ("automatic", "all", "none"):
        skill_desc = AAMC_REASONING_SKILLS.get(req.aamc_skill)
        if skill_desc:
            lines.append(f"AAMC Reasoning Skill: {req.aamc_skill} ({skill_desc})")
        else:
            lines.append(f"AAMC Reasoning Skill: {req.aamc_skill}")
    if req.subskill:
        lines.append(f"Granular Subskill Focus: {req.subskill}")
    if req.combination_id:
        lines.append(f"Combination ID: {req.combination_id}")
    if req.content_domains:
        lines.append(f"Content Domains: {', '.join(req.content_domains)}")
    elif req.content_domain:
        lines.append(f"Content Domain: {req.content_domain}")
    if req.question_type:
        lines.append(f"Question Type Format: {req.question_type}")
    if req.thematic_angle:
        lines.append(f"Pedagogical & Slot Directive: {req.thematic_angle}")
    return lines


def _build_syllabus_metadata_lines(req: GenerationRequest) -> list[str]:
    """Extracts curriculum coordinates, skills, and formats into ordered prompt lines."""
    return _build_topic_coordinates(req) + _build_skill_and_domain_metadata(req)


def _build_pedagogy_and_trap_block(
    req: GenerationRequest,
    diversity_context: str | None = None,
) -> str:
    """Assembles syllabus coordinates, AAMC skills, student misconception targets, and cognitive traps."""
    section_val = enum_value(req.section)
    section_name = MCAT_SECTION_LABELS.get(req.section, section_val)

    header = f"""Generate an official-caliber AAMC MCAT Multiple Choice Question with 4 options (A, B, C, D) and exactly ONE correct answer.

MANDATE FOR FIRST-PASS EXCELLENCE (AIM FOR FULL SCORE 100/100):
Construct this question to achieve a perfect 100 out of 100 on the official 100-point AAMC evaluation rubric on this initial attempt:
- Authenticity & Scientific Register: 25/25 (Indistinguishable from official AAMC medical exams)
- Clarity & Scientific Soundness: 25/25 (Unambiguous stem, completely sound premises)
- Distractor Quality & Option Symmetry: 25/25 (All 4 options strictly within length parity, parallel grammar, sophisticated cognitive traps, zero giveaways)
- Explanation & Solution Rigor: 25/25 (Irrefutable step-by-step proof for key, all 3 distractors individually refuted with trap explanations in alphabetical order)
Ensure the draft is publication-ready immediately so it earns a top passing score on the very first pass.

Section: {section_name}"""

    metadata_lines = _build_syllabus_metadata_lines(req)
    prompt = header + "\n" + "\n".join(metadata_lines)
    prompt += f"\n{_build_mistake_pattern_directive(req)}"
    prompt += f"\n{_build_primary_trap_directive(req)}"

    if diversity_context:
        prompt += f"\nCROSS-ITEM VARIETY CALIBRATION: {diversity_context}"

    return prompt


def _build_stimulus_context_block(req: GenerationRequest) -> str:
    """Assembles CARS guidelines, shared reading passage context, or discrete instructions."""
    prompt = ""
    if is_cars(req.section):
        prompt += (
            "\nCRITICAL CARS RULE: Strictly test ONLY what is justified directly by the passage text. "
            "Do NOT test or permit any outside scientific, clinical, or unmentioned real-world knowledge. "
            "Assess Foundations of Comprehension, Reasoning Within the Text, or Reasoning Beyond the Text."
        )

    if req.shared_stimulus and req.shared_stimulus.strip():
        slot_mandate = ""
        if req.thematic_angle:
            slot_mandate = (
                f"\n\nMANDATORY SLOT SPECIALIZATION:\n{req.thematic_angle}\n"
                "You MUST strictly adhere to this assigned slot role and archetype. "
                "Do NOT write a general main idea question if assigned a detail, function, or application question. "
                "Ensure your stem, choices, and key are distinct from typical sibling questions on this passage."
            )
        prompt += f"""\nCRITICAL PASSAGE INSTRUCTION:
You MUST formulate this question strictly and exclusively based on the following PRE-EXISTING READING PASSAGE.{slot_mandate}
Do NOT write a new passage. Formulate your question stem, options, correct key, and explanation directly against this text:
---
{req.shared_stimulus.strip()}
---"""
    elif req.is_passage_active:
        prompt += (
            f"\nPassage Required: Yes - Provide a rigorous, substantive {SCIENCE_PASSAGE_WORDS[0]}-{SCIENCE_PASSAGE_WORDS[1]} word "
            f"experimental/biomedical study (or {CARS_PASSAGE_WORDS[0]}-{CARS_PASSAGE_WORDS[1]} word humanities/social sciences "
            "essay for CARS) with clear paragraphing and empirical data descriptions."
        )
    else:
        prompt += (
            "\nPassage Required: No - Standalone discrete question ONLY. Do NOT write any reading passage, scenario, or vignette in stimulus_text. "
            'Leave stimulus_text strictly as an empty string (""). Pose the complete problem directly in question_stem.'
        )

    if req.visual_type and req.visual_type != "None":
        prompt += f"\nVisual Stimulus Type: {req.visual_type}"

    return prompt.strip()


def _build_visual_stimulus_block(req: GenerationRequest) -> str:
    """Assembles medical imaging and visual stimulus instructions based on request settings."""
    allow_visuals = (
        req.allow_ai_images
        or req.require_image
        or req.require_passage_image
        or req.visual_type in KNOWN_VISUAL_TYPES
    ) and not is_cars(req.section)

    if not allow_visuals:
        return (
            "VISUAL STIMULUS STATUS:\n"
            "- Visual stimuli are disabled for this item. Set 'image_needed': false and 'image_prompt_or_type': null."
        )

    if req.require_image:
        return (
            "MANDATORY VISUAL STIMULUS & MEDICAL IMAGING REQUIREMENT:\n"
            "- This question MUST incorporate and directly test an accompanying medical image, clinical figure, or scientific illustration. "
            "The visual stimulus should reflect realistic medical and scientific scenarios across supported modalities:\n"
            "  1. Diagnostic Radiology: Plain radiographs (chest/bone X-rays), contrast/non-contrast CT scans, MRI (T1, T2, FLAIR), ultrasound/echocardiograms, or nuclear scintigraphy.\n"
            "  2. Histopathology: High-magnification light microscopy of tissue biopsies stained with Hematoxylin & Eosin (H&E), cytology smears, or specialized histochemical/immunohistochemical stains.\n"
            "  3. Gross Anatomy & Dissections: True-to-life anatomical structures, master medical atlas illustrations, organ cross-sections (cardiac chambers, circle of Willis, organ systems, neuroanatomy, vasculature).\n"
            "  4. Cellular Electron Microscopy: Transmission or scanning electron micrographs (TEM/SEM) displaying subcellular organelles (mitochondrial cristae, rough ER, nuclear pores, sarcomeres, synaptic junctions).\n"
            "  5. Physiological Traces: Standard clinical 12-lead ECG rhythm strips on pink/red millimeter grid paper, cardiac action potential curves, Wiggers diagrams, or spirometry flow loops.\n"
            "  6. Clinical Pathology: Diagnostic clinical photography (dermatological manifestations, retinal fundoscopic exam findings, physical examination signs).\n"
            "  7. Scientific & Biochemical Diagrams: Reaction mechanisms, metabolic cycles, enzyme kinetics plots, titration curves, or circuit diagrams.\n"
            "- UNRESTRICTED MEDICAL IMAGING FREEDOM: Align with the thematic visual focus assigned to this question item if specified in thematic_angle (e.g. histopathology, scientific diagram, radiology, physiology trace). Do not artificially restrict the image type or modality.\n"
            "- DO NOT spoon-feed findings or numerical coordinates in the text stem—present the empirical data through the figure (e.g. 'As shown in Figure 1...', 'In the radiograph below...', 'Based on the histopathology slide below...') and require the examinee to interpret the visual stimulus to arrive at the answer.\n"
            "- Strictly set 'image_needed': true and write a vivid, clinically accurate description of the visual in 'image_prompt_or_type' specifying the exact modality, view/plane, staining, and parameters."
        )

    return (
        "AI VISUAL NECESSITY ASSESSMENT & PEDAGOGICAL VALIDATION (Include Images When Needed is ON):\n"
        "- Visual stimuli and medical imaging are ENABLED for this question bank session.\n"
        "- STEP 1: Critically evaluate the pedagogical requirement of the specific concept, problem, and subtopic being authored:\n"
        "  * REQUIRE AN IMAGE ('image_needed': true):\n"
        "    If this question item tests or benefits from empirical data interpretation, experimental graphs (Lineweaver-Burk, Michaelis-Menten, scatter plots, titration curves), molecular biology assays (SDS-PAGE/Western blots, PCR, chromatography), metabolic pathways, chemical reaction mechanisms, organ anatomy, tissue biopsy histology (H&E staining), cellular electron micrographs (TEM/SEM), diagnostic radiology (X-ray, CT, MRI, ultrasound), or physiological traces (12-lead ECG, action potentials, PV loops):\n"
        "    1. Set 'image_needed': true at the beginning of your JSON response.\n"
        "    2. Write a vivid, publication-grade figure description in 'image_prompt_or_type' specifying the exact modality, view/plane, staining, and parameters.\n"
        "    3. In 'question_stem', directly reference the visual figure (e.g. 'As shown in Figure 1...', 'In the radiograph below...', 'Based on the histopathology slide below...').\n"
        "    4. DO NOT spoon-feed graph axes, findings, or numerical coordinates in text sentences—present the empirical data through the figure so examinees must interpret the visual stimulus!\n"
        "    5. Modality Diversity: Draw naturally from across all 7 supported modalities (Radiology, Histology, Gross Anatomy, Cellular Electron Microscopy, Physiological Traces, Clinical Pathology, Scientific Diagrams) based on the subject matter.\n"
        "  * REMAIN TEXT-ONLY ('image_needed': false):\n"
        "    If this question item tests purely conceptual definitions, theoretical principles, terminology recall, or abstract reasoning that does not involve an empirical figure or data plot:\n"
        "    1. Set 'image_needed': false and 'image_prompt_or_type': null.\n"
        "    2. Formulate a crisp, high-yield text-focused question stem without decorative or unnecessary visual clutter."
    )


def _build_mandates_and_critique_block(fused: bool = False) -> str:
    """Assembles option parity, distractor order, explanation proof, and self-critique rubric."""
    mandates = (
        "ANTI-GUESSABILITY & OPTION SYMMETRY MANDATE:\n"
        f"- All options MUST have roughly equal length and word count ({OPTION_PARITY_TEXT}).\n"
        "- The correct option MUST NOT be the longest choice or the most qualified/hedged statement.\n"
        "- Use parallel grammatical syntax across all choices (identical part of speech and structural format).\n"
        "- Prohibit Polarity Outliers: NEVER create a 3-versus-1 pattern (e.g. 3 negative and 1 positive).\n"
        "- Ensure distractors represent authentic, highly plausible cognitive reasoning traps.\n\n"
        "EXPLANATION & DISTRACTOR MANDATE:\n"
        "- Exactly ONE option is the correct answer. Ambiguous or multiple keys are strictly prohibited.\n"
        "- Write in clear, accessible, student-friendly language so that any learner can easily understand the rationale without confusion.\n"
        "- Structure the explanation with:\n"
        "  1. 'Core Intuition & Big-Picture Takeaway': 2-3 sentences of accessible conceptual intuition.\n"
        "  2. 'Why Option [Key] is Correct': Direct step-by-step scientific/textual proof.\n"
        "  3. 'Why Other Options are Incorrect (Distractor & Trap Breakdown)': Dedicated separate bullets for ALL THREE other options strictly in alphabetical order (Option A, then Option B, then Option C, then Option D as applicable). Do not omit or combine any distractor."
    )
    if fused:
        mandates += (
            "\n\nSELF-CRITIQUE INSTRUCTION:\n"
            "After composing the question, options, and explanation, audit your own draft as a skeptical independent reviewer.\n"
            f"Check option lengths (all 4 choices {OPTION_PARITY_TEXT}, parallel syntax). Score each pillar from 0-25 "
            "by deducting points for every concrete flaw you can name, and list each flaw under weaknesses. "
            "Do not inflate scores: an independent reviewer and a blind solver will re-check this item.\n"
            "Output ONLY valid JSON matching the specified fused schema."
        )
    else:
        mandates += "\n\nOutput ONLY valid JSON matching the specified schema."
    return mandates


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
    """
    blocks = [
        _build_pedagogy_and_trap_block(req, diversity_context=diversity_context),
        _build_stimulus_context_block(req),
        educator_instruction_block(
            req,
            "HIGH FIDELITY MANDATE",
            "The author has specified the following mandatory custom instructions for this question. "
            "You MUST strictly adhere to and incorporate these requirements into the question stem, answer choices, and rationale:",
        ),
        _build_visual_stimulus_block(req),
        _build_mandates_and_critique_block(fused=fused),
    ]
    return "\n\n".join(b for b in blocks if b)


# Backward-compat alias: public canonical name and referenced by test_additional_instructions.py.
build_generator_user_prompt = _build_generator_user_prompt
