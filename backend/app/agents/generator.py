"""
generator.py - Question Generator Agent for MCAT Question Bank.

Provides three public entry-points:
- ``generate_passage_stimulus``: Drafts a reading passage stimulus for a passage set.
- ``generate_question``: Single-pass generator that produces a question draft.
- ``generate_question_with_self_critique``: Fused draft-and-critique generator that
  produces a question draft AND a self-scored rubric in a single LLM round-trip.

Internal helpers ``_parse_option_choices`` and ``_parse_correct_keys`` are shared
with ``regenerator.py`` to avoid duplication.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.agents._mock_tokens import (
    PASSAGE_GENERATOR_MOCK_COMPLETION_TOKENS,
    PASSAGE_GENERATOR_MOCK_PROMPT_TOKENS,
    QUESTION_GENERATOR_MOCK_COMPLETION_TOKENS,
    QUESTION_GENERATOR_MOCK_PROMPT_TOKENS,
)
from app.agents.base import (
    LLMNotConfiguredError,
    calculate_token_cost,
    call_llm,
    call_llm_validated,
    require_offline_mode,
    safe_json_loads,
)
from app.agents.mock_fixtures import evaluate_heuristically, get_mock_draft
from app.agents.option_balancer import balance_and_shuffle_options
from app.agents.prompt_builder import _build_generator_user_prompt
from app.agents.prompts import FUSED_GENERATOR_SYSTEM_PROMPT, GENERATOR_SYSTEM_PROMPT
from app.agents.standards import passage_words_text
from app.core.config import config
from app.schemas import (
    KNOWN_VISUAL_TYPES,
    MCAT_SECTION_LABELS,
    GenerationRequest,
    MCATSection,
    OptionChoice,
    QuestionDraft,
    ReviewScore,
    TokenUsage,
    normalize_mistake_pattern,
    normalize_primary_trap,
)

logger = logging.getLogger(__name__)


def _parse_option_choices(raw_options: Any, data: dict | None = None) -> list[OptionChoice]:
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


def _parse_correct_keys(
    data: dict, options: list[OptionChoice], fallback_keys: list[str] | None = None
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


def _detect_primary_trap(data: dict, req: GenerationRequest) -> str:
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


def _detect_mistake_pattern(data: dict, req: GenerationRequest) -> str | None:
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
        r"(?:misconception|mistake\s*pattern|common\s*error)[:\s]+([^\n.,;]+)",
        expl,
        re.IGNORECASE,
    )
    if m_match:
        return m_match.group(1).strip()
    return "Confuses closely related concepts or misreads reference baseline"


def _resolve_effective_stimulus(data: dict, req: GenerationRequest) -> str:
    """Resolves reading passage vs direct independent question stimulus."""
    if not req.is_passage_active:
        return ""
    if req.shared_stimulus:
        return req.shared_stimulus.strip()
    return str(data.get("stimulus_text") or "").strip()


def _require_text(data: dict, field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Model output is missing a non-empty '{field}'")
    return value


def _parse_question_draft_data(data: dict, req: GenerationRequest) -> QuestionDraft:
    if not isinstance(data, dict):
        raise ValueError(f"Model output must be a JSON object, got {type(data).__name__}")
    question_stem = _require_text(data, "question_stem")
    explanation = _require_text(data, "explanation")
    options = _parse_option_choices(data.get("options", []), data)
    correct_id_str, keys_list = _parse_correct_keys(data, options)
    primary_trap = _detect_primary_trap(data, req)
    effective_mistake = _detect_mistake_pattern(data, req)
    effective_stimulus = _resolve_effective_stimulus(data, req)

    aamc_skill = (
        data.get("aamc_skill")
        or req.aamc_skill
        or ("CARS_Skill_1" if req.section in (MCATSection.CARS, "CARS", "cars") else "Skill_2")
    )

    return QuestionDraft(
        stimulus_text=effective_stimulus,
        question_stem=question_stem,
        options=options,
        correct_answer_id=correct_id_str,
        correct_answer_ids=keys_list,
        explanation=explanation,
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
                req.section in (MCATSection.CARS, "CARS", "cars")
                or not (req.allow_ai_images or req.require_image)
            )
            else bool(data.get("image_needed", False))
        ),
        image_prompt_or_type=data.get("image_prompt_or_type"),
    )


async def generate_passage_stimulus(
    req: GenerationRequest,
) -> tuple[str, TokenUsage, bool, str | None]:
    """Generates a standalone, publication-caliber AAMC MCAT academic/experimental reading passage."""
    section_val = req.section.value if hasattr(req.section, "value") else str(req.section)
    section_name = MCAT_SECTION_LABELS.get(req.section, section_val)
    domain = req.content_domain or (
        "Humanities & Social Sciences"
        if req.section in (MCATSection.CARS, "CARS", "cars")
        else "Biomedical & Physical Sciences"
    )
    topic = req.subtopic or "Foundational Concepts & Research Design"

    is_cars = req.section in (MCATSection.CARS, "CARS", "cars")
    target_length = passage_words_text(is_cars)
    allow_visuals = (
        req.allow_ai_images
        or req.require_image
        or req.require_passage_image
        or req.visual_type in KNOWN_VISUAL_TYPES
    ) and not is_cars

    angle_instruction = (
        f"\nPedagogical / Experimental Angle: {req.thematic_angle}\n"
        f"CRITICAL DIVERSITY MANDATE: You MUST anchor this passage study and experimental context around this distinct thematic angle "
        f"so it does not duplicate other reading passages on {topic}."
        if req.thematic_angle
        else ""
    )

    author_instructions = req.additional_instructions or req.custom_prompt
    author_instruction_block = (
        f"\nCRITICAL EDUCATOR INSTRUCTION (PASSAGE MANDATE):\n"
        f"You MUST strictly adhere to and incorporate these author instructions into the passage study, experimental methodology, or analytical focus:\n"
        f'"""\n{author_instructions.strip()}\n"""'
        if author_instructions and author_instructions.strip()
        else ""
    )

    if allow_visuals:
        prompt = f"""Generate a high-yield, authentic AAMC MCAT Reading Passage for {section_name}.
Content Domain: {domain}
Topic Focus: {topic}{angle_instruction}{author_instruction_block}
Difficulty Calibration: {req.difficulty.value}
Target Length: {target_length}.

STANDARDS FOR AAMC MCAT PASSAGES:
1. Formal, intellectual scholarly register using precise American English scientific or academic vocabulary.
2. Structured in 3 to 5 coherent paragraphs.
3. Substantive experimental or biomedical study detailing a research hypothesis, experimental methods (e.g. assays, Western blots, kinetic measurements, reaction vessels), observed quantitative data or findings, and conclusions.
4. Provides rich material for multiple distinct reasoning questions evaluating AAMC skills.
5. EXPERIMENTAL & SCHOLARLY VISUAL STIMULUS REQUIREMENT (FIGURE 1):
   - Because visual stimuli are enabled for this passage, the study MUST describe and reference a central figure, chart, experimental setup, or diagram labeled as "Figure 1" (e.g., Figure 1: Experimental apparatus schematic, anatomical diagram, Western blot / gel electrophoresis, Lineweaver-Burk kinetic plot, reaction mechanism, or metabolic pathway).
   - In the text of the passage, explicitly mention "Figure 1" so questions can test visual data interpretation.
   - Strictly set "image_needed": true and provide a comprehensive, vivid description in "image_prompt" for generating this figure.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this exact structure:
{{
  "passage_text": "The full 3 to 5 paragraph reading passage text explicitly incorporating and describing Figure 1...",
  "image_needed": true,
  "image_prompt": "Detailed description of Figure 1: high-contrast experimental figure, chart, illustration, or diagram on a clean white background with clearly labeled axes, legends, or structures..."
}}"""
    else:
        prompt = f"""Generate a high-yield, authentic AAMC MCAT Reading Passage for {section_name}.
Content Domain: {domain}
Topic Focus: {topic}{angle_instruction}{author_instruction_block}
Difficulty Calibration: {req.difficulty.value}
Target Length: {target_length}.

STANDARDS FOR AAMC MCAT PASSAGES:
1. Formal, intellectual scholarly register using precise American English scientific or academic vocabulary.
2. Structured in 3 to 5 coherent paragraphs.
3. {"For CARS: Dense scholarly argument in philosophy, ethics, cultural theory, or social sciences. Expresses a distinct thesis, contrasting critical viewpoints, and authorial attitude. Strictly avoid scientific jargon." if is_cars else "For Sciences: Substantive experimental or biomedical study detailing a research hypothesis, experimental methods (e.g. assays, Western blots, kinetic measurements), observed quantitative data or findings, and conclusions."}
4. Provides rich material for multiple distinct reasoning questions evaluating AAMC skills.
5. DO NOT include questions, choices, or answers in this output. Output ONLY the pure reading passage text."""

    system_prompt = (
        "You are a Senior AAMC MCAT Lead Passage Author for official medical college admissions. "
        "Write authoritative, dense, publication-grade reading passages suitable for competitive premed candidates."
    )

    try:
        # Elevated temperature for passage diversity across jobs
        passage_temp = max(config.GENERATOR_TEMPERATURE, config.PASSAGE_TEMPERATURE)
        raw_output, usage = await call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            model=req.model_name,
            api_key=req.api_key,
            temperature=passage_temp,
            max_tokens=config.DEFAULT_MAX_TOKENS,
        )
        cleaned = raw_output.strip()
        # Clean any accidental markdown or quotes
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:])
        cleaned = cleaned.strip('" \n')

        passage_text = cleaned
        image_needed = False
        image_prompt = None

        if allow_visuals:
            try:
                data = safe_json_loads(cleaned)
                if isinstance(data, dict) and "passage_text" in data:
                    passage_text = str(data["passage_text"]).strip()
                    image_needed = bool(data.get("image_needed", True))
                    image_prompt = data.get("image_prompt")
                elif isinstance(data, dict) and "text" in data:
                    passage_text = str(data["text"]).strip()
                    image_needed = bool(data.get("image_needed", True))
                    image_prompt = data.get("image_prompt")
            except Exception as parse_err:
                # Plain-text passages are valid; fall back to the cleaned raw output.
                logger.debug("Passage output was not JSON, using raw text: %s", parse_err)

            # Guarantee that science passages have a diagram when visuals are permitted
            image_needed = True
            if not image_prompt:
                image_prompt = f"Official AAMC MCAT scientific experimental diagram and data figure for {section_name} study on {topic}: {passage_text[:180]}"

        return passage_text, usage, image_needed, image_prompt
    except LLMNotConfiguredError as e:
        require_offline_mode(e)
        logger.warning(
            f"Passage generation LLM not configured, using offline fallback passage: {e}"
        )
        if is_cars:
            fallback_passage = (
                "The philosophical justification of aesthetic value has long struggled to reconcile subjective sensory experience "
                "with the demand for objective critical consensus. In his Critique of Judgment, Immanuel Kant attempted to bridge this chasm "
                "by positing the 'sensus communis' - a shared subjective capacity that enables individuals to expect universal agreement "
                "for their aesthetic appraisals without relying on empirical concepts. To Kant, an authentic judgment of beauty must remain "
                "disinterested, detached from both sensory gratification and practical utility. When one declares a cathedral or a sonata beautiful, "
                "one speaks with a 'universal voice,' imputing the same contemplative satisfaction to all rational observers.\n\n"
                "However, contemporary sociological critique, most notably articulated by Pierre Bourdieu, dismisses this Kantian autonomy as "
                "a bourgeois illusion. Bourdieu argues that aesthetic dispositions do not reflect pure, disinterested cognition; rather, they are "
                "socially conditioned markers of class distinction, or 'cultural capital.' The ability to appreciate abstract painting or avant-garde "
                "composition presupposes prolonged exposure and educational privilege, subtly legitimizing social hierarchies under the guise of "
                "natural refined taste. In this view, disinterested aesthetic contemplation serves primarily to demarcate elite status from "
                "the necessity-driven preferences of the working classes.\n\n"
                "Yet to reduce all aesthetic appraisal to socio-economic positioning is to ignore the transformative phenomenology of art itself. "
                "If aesthetic appreciation were merely an arbitrary exercise in social signaling, it would fail to explain the profound emotional "
                "resonance and cognitive disequilibrium that art frequently elicits across diverse cultural strata. Genuine aesthetic encounters "
                "routinely disrupt habitual perception, unsettling entrenched beliefs rather than reinforcing social complacency. The enduring power "
                "of artistic expression lies neither in absolute Kantian universality nor in reductive sociological determinism, but in its capacity "
                "to stage an open-ended dialogue between individual subjectivity and the collective imagination."
            )
        else:
            fallback_passage = (
                "Phosphofructokinase-1 (PFK-1) functions as the primary committed and rate-limiting regulatory enzyme of glycolysis, "
                "catalyzing the ATP-dependent phosphorylation of fructose-6-phosphate (F6P) to fructose-1,6-bisphosphate (F1,6BP). "
                "Under physiological conditions, PFK-1 exists in an equilibrium between a low-affinity T (tense) state and a high-affinity "
                "R (relaxed) state. To elucidate the metabolic impact of allosteric modulators on glycolytic flux during acute ischemia, "
                "researchers isolated recombinant human hepatic PFK-1 and performed in vitro kinetic assays across varying substrate and "
                "effector concentrations at pH 7.4.\n\n"
                "In the presence of physiological levels of ATP (5.0 mM), PFK-1 activity was markedly inhibited, shifting the substrate saturation "
                "curve for F6P to a sigmoidal profile with a fivefold increase in the apparent Michaelis constant (Km). This cooperative inhibition "
                "stems from ATP binding to an allosteric regulatory site distinct from the catalytic pocket, stabilizing the low-affinity T conformation. "
                "Conversely, addition of 2.0 μM fructose-2,6-bisphosphate (F2,6BP) completely abrogated ATP-mediated allosteric inhibition, restoring "
                "hyperbolic Michaelis-Menten kinetics, decreasing the Km for F6P to 0.12 mM, and increasing Vmax by 40%.\n\n"
                "Further investigation demonstrated that intracellular acidosis (pH 6.8), mirroring the microenvironment of ischemic myocardium, "
                "potentiated ATP binding to the allosteric inhibitory site, resulting in a 75% reduction in catalytic efficiency (kcat/Km). "
                "However, elevated AMP concentrations (0.8 mM) competitive with ATP at the allosteric site partially restored glycolytic turnover. "
                "These findings demonstrate that cellular energy charge (AMP/ATP ratio) coupled with local proton concentration precisely regulates "
                "glycolytic flux through coordinated conformational switching of PFK-1."
            )
        mock_usage = TokenUsage(
            prompt_tokens=PASSAGE_GENERATOR_MOCK_PROMPT_TOKENS,
            completion_tokens=PASSAGE_GENERATOR_MOCK_COMPLETION_TOKENS,
            total_tokens=PASSAGE_GENERATOR_MOCK_PROMPT_TOKENS
            + PASSAGE_GENERATOR_MOCK_COMPLETION_TOKENS,
            cost_usd=calculate_token_cost(
                PASSAGE_GENERATOR_MOCK_PROMPT_TOKENS,
                PASSAGE_GENERATOR_MOCK_COMPLETION_TOKENS,
            ),
        )
        fallback_image_needed = bool(allow_visuals and not is_cars)
        fallback_image_prompt = (
            "Lineweaver-Burk and Michaelis-Menten plot of PFK-1 allosteric regulation by ATP and F2,6BP"
            if fallback_image_needed
            else None
        )
        return fallback_passage, mock_usage, fallback_image_needed, fallback_image_prompt


async def generate_question(
    req: GenerationRequest,
    diversity_context: str | None = None,
) -> tuple[QuestionDraft, TokenUsage]:
    """Invokes the Question Generator Agent to draft a publication-grade AAMC MCAT question."""
    user_prompt = _build_generator_user_prompt(
        req, fused=False, diversity_context=diversity_context
    )

    try:
        draft, usage = await call_llm_validated(
            prompt=user_prompt,
            system_prompt=GENERATOR_SYSTEM_PROMPT,
            parse=lambda raw: _parse_question_draft_data(safe_json_loads(raw), req),
            model=req.model_name,
            api_key=req.api_key,
            temperature=config.GENERATOR_TEMPERATURE,
            max_tokens=config.DEFAULT_MAX_TOKENS,
        )
        draft, _ = balance_and_shuffle_options(draft)
        return draft, usage
    except LLMNotConfiguredError as e:
        require_offline_mode(e)
        logger.warning(f"Generator LLM not configured, using offline mock draft: {e}")
        mock_usage = TokenUsage(
            prompt_tokens=QUESTION_GENERATOR_MOCK_PROMPT_TOKENS,
            completion_tokens=QUESTION_GENERATOR_MOCK_COMPLETION_TOKENS,
            total_tokens=QUESTION_GENERATOR_MOCK_PROMPT_TOKENS
            + QUESTION_GENERATOR_MOCK_COMPLETION_TOKENS,
            cost_usd=calculate_token_cost(
                QUESTION_GENERATOR_MOCK_PROMPT_TOKENS,
                QUESTION_GENERATOR_MOCK_COMPLETION_TOKENS,
            ),
        )
        mock_draft = get_mock_draft(req)
        if req.shared_stimulus:
            mock_draft.stimulus_text = req.shared_stimulus.strip()
        elif req.passage_required and str(req.passage_required).lower() in ("no", "false"):
            mock_draft.stimulus_text = ""
        return mock_draft, mock_usage


async def generate_question_with_self_critique(
    req: GenerationRequest,
    diversity_context: str | None = None,
) -> tuple[QuestionDraft, ReviewScore | None, TokenUsage]:
    """
    Fused Draft-and-Critique generator:
    Generates the candidate question AND scores it with the 100-point rubric
    in a single LLM round-trip.
    """
    user_prompt = _build_generator_user_prompt(req, fused=True, diversity_context=diversity_context)

    try:

        def _parse_fused(raw: str) -> tuple[dict, QuestionDraft]:
            parsed = safe_json_loads(raw)
            return parsed, _parse_question_draft_data(parsed, req)

        (data, draft), usage = await call_llm_validated(
            prompt=user_prompt,
            system_prompt=FUSED_GENERATOR_SYSTEM_PROMPT,
            parse=_parse_fused,
            model=req.model_name,
            api_key=req.api_key,
            temperature=config.GENERATOR_TEMPERATURE,
            max_tokens=config.DEFAULT_MAX_TOKENS,
        )
        draft, _ = balance_and_shuffle_options(draft)

        self_review = None
        critique = data.get("self_critique")
        if isinstance(critique, dict):
            try:
                auth = int(float(critique.get("authenticity_score", 0)))
                clarity = int(float(critique.get("clarity_score", 0)))
                distractor = int(float(critique.get("distractor_score", 0)))
                explanation = int(float(critique.get("explanation_score", 0)))
                total = auth + clarity + distractor + explanation
                self_review = ReviewScore(
                    authenticity_score=auth,
                    clarity_score=clarity,
                    distractor_score=distractor,
                    explanation_score=explanation,
                    total_score=total,
                    strengths=critique.get("strengths", []),
                    weaknesses=critique.get("weaknesses", []),
                    recommendations=critique.get("recommendations", []),
                    passed=config.passes_quality_gate(total),
                )
            except Exception as parse_err:
                logger.warning(f"Failed to parse self_critique object: {parse_err}")

        return draft, self_review, usage
    except LLMNotConfiguredError as e:
        require_offline_mode(e)
        logger.warning(f"Fused Generator LLM not configured, using offline mock draft: {e}")
        mock_usage = TokenUsage(
            prompt_tokens=QUESTION_GENERATOR_MOCK_PROMPT_TOKENS,
            completion_tokens=QUESTION_GENERATOR_MOCK_COMPLETION_TOKENS,
            total_tokens=QUESTION_GENERATOR_MOCK_PROMPT_TOKENS
            + QUESTION_GENERATOR_MOCK_COMPLETION_TOKENS,
            cost_usd=calculate_token_cost(
                QUESTION_GENERATOR_MOCK_PROMPT_TOKENS,
                QUESTION_GENERATOR_MOCK_COMPLETION_TOKENS,
            ),
        )
        mock_draft = get_mock_draft(req)
        if req.shared_stimulus:
            mock_draft.stimulus_text = req.shared_stimulus.strip()
        elif req.passage_required and str(req.passage_required).lower() in ("no", "false"):
            mock_draft.stimulus_text = ""
        mock_review = evaluate_heuristically(mock_draft, req, 1)
        return mock_draft, mock_review, mock_usage
