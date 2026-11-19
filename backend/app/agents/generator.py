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
from typing import Any

from app.agents import base
from app.agents._mock_tokens import (
    PASSAGE_GENERATOR_MOCK_COMPLETION_TOKENS,
    PASSAGE_GENERATOR_MOCK_PROMPT_TOKENS,
    QUESTION_GENERATOR_MOCK_COMPLETION_TOKENS,
    QUESTION_GENERATOR_MOCK_PROMPT_TOKENS,
    mock_usage,
)
from app.agents.base import (
    LLMNotConfiguredError,
    call_llm_validated,
    require_offline_mode,
    safe_json_loads,
)
from app.agents.draft_parser import (
    _detect_mistake_pattern,
    _detect_primary_trap,
    _parse_correct_keys,
    _parse_option_choices,
    _parse_question_draft_data,
    _require_text,
    _resolve_effective_stimulus,
    detect_mistake_pattern,
    detect_primary_trap,
    parse_correct_keys,
    parse_option_choices,
    parse_question_draft_data,
    require_text,
    resolve_effective_stimulus,
)
from app.agents.mock_fixtures import evaluate_heuristically, get_mock_draft
from app.agents.option_balancer import balance_and_shuffle_options
from app.agents.prompt_builder import (
    build_generator_user_prompt,
    educator_instruction_block,
)
from app.agents.prompts import FUSED_GENERATOR_SYSTEM_PROMPT, GENERATOR_SYSTEM_PROMPT
from app.agents.standards import is_cars, passage_words_text
from app.core.config import config
from app.schemas import (
    KNOWN_VISUAL_TYPES,
    MCAT_SECTION_LABELS,
    GenerationRequest,
    QuestionDraft,
    ReviewScore,
    TokenUsage,
    enum_value,
)

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
_build_generator_user_prompt = build_generator_user_prompt

__all__ = [
    "_build_generator_user_prompt",
    "_detect_mistake_pattern",
    "_detect_primary_trap",
    "_parse_correct_keys",
    "_parse_option_choices",
    "_parse_question_draft_data",
    "_require_text",
    "_resolve_effective_stimulus",
    "build_generator_user_prompt",
    "detect_mistake_pattern",
    "detect_primary_trap",
    "generate_passage_stimulus",
    "generate_question",
    "generate_question_with_self_critique",
    "parse_correct_keys",
    "parse_option_choices",
    "parse_question_draft_data",
    "require_text",
    "resolve_effective_stimulus",
]


async def generate_passage_stimulus(
    req: GenerationRequest,
) -> tuple[str, TokenUsage, bool, str | None]:
    """Generates a standalone, publication-caliber AAMC MCAT academic/experimental reading passage."""
    section_val = enum_value(req.section)
    section_name = MCAT_SECTION_LABELS.get(req.section, section_val)
    domain = req.content_domain or (
        "Humanities & Social Sciences" if is_cars(req.section) else "Biomedical & Physical Sciences"
    )
    topic = req.subtopic or "Foundational Concepts & Research Design"

    cars = is_cars(req.section)
    target_length = passage_words_text(cars)
    allow_visuals = (
        req.allow_ai_images
        or req.require_image
        or req.require_passage_image
        or req.visual_type in KNOWN_VISUAL_TYPES
    ) and not cars

    angle_instruction = (
        f"\nPedagogical / Experimental Angle: {req.thematic_angle}\n"
        f"CRITICAL DIVERSITY MANDATE: You MUST anchor this passage study and experimental context around this distinct thematic angle "
        f"so it does not duplicate other reading passages on {topic}."
        if req.thematic_angle
        else ""
    )

    author_instruction_block = educator_instruction_block(
        req,
        "PASSAGE MANDATE",
        "You MUST strictly adhere to and incorporate these author instructions into the passage study, experimental methodology, or analytical focus:",
    )

    if allow_visuals:
        prompt = f"""Generate a high-yield, authentic AAMC MCAT Reading Passage for {section_name}.
Content Domain: {domain}
Topic Focus: {topic}{angle_instruction}{author_instruction_block}
Difficulty Calibration: {req.difficulty.value}
Target Length: {target_length}.

STANDARDS FOR AAMC MCAT PASSAGES:
1. Formal, intellectual scholarly register using precise American English scientific or academic vocabulary.
2. Structured in 4 to 5 coherent, well-developed paragraphs:
   - Paragraph 1: Foundational research context, biological system/disease model, and core scientific definitions.
   - Paragraph 2: Experimental methodology, assay protocol, and explicit reference to and description of "Figure 1".
   - Paragraph 3: Observed quantitative data, table/graph trends, baseline measurements, and statistical comparisons.
   - Paragraph 4: Molecular mechanism, biochemical pathway shifts, or enzymatic kinetics deductions.
   - Paragraph 5: Downstream physiological significance, pharmacological implications, or clinical relevance.
3. Substantive experimental, clinical, or biomedical study detailing a research premise, experimental or clinical methodologies (e.g. diagnostic imaging scans, biopsy histopathology, physiological traces, cellular electron microscopy, enzyme assays, or biochemical mechanisms), observed quantitative data, and observations. DO NOT state overarching final conclusions or test answers directly in the passage; present empirical observations and data clearly so questions can evaluate scientific reasoning.
4. Rich Conceptual Diversity: Provide distinct empirical and textual territory across all paragraphs so that 5 separate questions can each evaluate independent evidence without overlapping on the same sentence or concept.
5. EXPERIMENTAL, MEDICAL & SCHOLARLY VISUAL STIMULUS REQUIREMENT (FIGURE 1):
   - Because visual stimuli are enabled for this passage, the study MUST describe and reference a central figure, chart, experimental setup, or medical image labeled as "Figure 1".
   - UNRESTRICTED MODALITY FREEDOM: Figure 1 may be any authentic medical imaging scan or scientific schematic matching the study:
     * Diagnostic Radiology (chest/bone X-rays, axial/sagittal CT or MRI scans, ultrasound/echocardiograms)
     * Histopathology (H&E tissue biopsy, cytology smear, light micrograph)
     * Gross Anatomy (anatomical specimen, organ cross-section, vascular/neural atlas diagram)
     * Cellular Electron Microscopy (TEM/SEM subcellular organelles, mitochondrial cristae, membrane junctions)
     * Physiological Traces (12-lead ECG rhythm strip, cardiac action potential, Wiggers diagram, spirometry loop)
     * Clinical Pathology (dermatologic manifestation, retinal fundoscopy photograph)
     * Scientific Schematics (biochemical pathways, Western blot / gel, Lineweaver-Burk kinetic plot, reaction mechanism)
   - In the text of the passage, explicitly mention and describe "Figure 1" so questions can test visual data interpretation.
   - Strictly set "image_needed": true and provide a comprehensive, vivid description in "image_prompt" for generating this figure without restricting the image model.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this exact structure:
{{
  "passage_text": "The full 3 to 5 paragraph reading passage text explicitly incorporating and describing Figure 1...",
  "image_needed": true,
  "image_prompt": "Detailed description of Figure 1: clinical medical imaging scan, histopathology slide, physiological trace, or experimental diagram specifying tissue, modality, orientation, and diagnostic features..."
}}"""
    else:
        prompt = f"""Generate a high-yield, authentic AAMC MCAT Reading Passage for {section_name}.
Content Domain: {domain}
Topic Focus: {topic}{angle_instruction}{author_instruction_block}
Difficulty Calibration: {req.difficulty.value}
Target Length: {target_length}.

STANDARDS FOR AAMC MCAT PASSAGES:
1. Formal, intellectual scholarly register using precise American English scientific or academic vocabulary.
2. Structured in 4 to 5 coherent, well-developed paragraphs:
   - Paragraph 1: Central thesis, historical/philosophical framework, or foundational scientific premise.
   - Paragraph 2: Primary argument, textual evidence, or experimental methodology.
   - Paragraph 3: Counter-argument, contrasting critical viewpoint, or observed quantitative assay data.
   - Paragraph 4: Nuanced theoretical reconciliation, authorial critique, or biochemical mechanistic deduction.
   - Paragraph 5: Broader normative implications, future horizons, or physiological/clinical significance.
3. {"For CARS: Dense scholarly argument in philosophy, ethics, cultural theory, or social sciences. Expresses a distinct thesis, contrasting critical viewpoints, and authorial attitude. Strictly avoid scientific jargon." if cars else "For Sciences: Substantive experimental or biomedical study detailing a research premise, experimental methods (e.g. assays, Western blots, kinetic measurements), observed quantitative data, and observations without front-loading final conclusions."}
4. Rich Conceptual Diversity: Provides distinct conceptual depth across all paragraphs so that 5 separate reasoning questions can each evaluate independent evidence without overlapping on the same sentence or concept.
5. DO NOT include questions, choices, or answers in this output. Output ONLY the pure reading passage text."""

    system_prompt = (
        "You are a Senior AAMC MCAT Lead Passage Author for official medical college admissions. "
        "Write authoritative, dense, publication-grade reading passages suitable for competitive premed candidates."
    )

    try:
        # Elevated temperature for passage diversity across jobs
        passage_temp = max(config.GENERATOR_TEMPERATURE, config.PASSAGE_TEMPERATURE)
        raw_output, usage = await base.call_llm(
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
            except (ValueError, TypeError, KeyError, AttributeError) as parse_err:
                # Plain-text passages are valid; fall back to the cleaned raw output.
                logger.debug("Passage output was not JSON, using raw text: %s", parse_err)

            # Guarantee that science passages have a diagram when visuals are permitted
            image_needed = True
            if not image_prompt:
                image_prompt = f"Official AAMC MCAT scientific experimental diagram and data figure for {section_name} study on {topic}: {passage_text[:180]}"

    except LLMNotConfiguredError as e:
        require_offline_mode(e)
        logger.warning(
            "Passage generation LLM not configured, using offline fallback passage: %s", e
        )
        if cars:
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
        fallback_usage = mock_usage(
            PASSAGE_GENERATOR_MOCK_PROMPT_TOKENS, PASSAGE_GENERATOR_MOCK_COMPLETION_TOKENS
        )
        fallback_image_needed = bool(allow_visuals and not cars)
        fallback_image_prompt = (
            "Lineweaver-Burk and Michaelis-Menten plot of PFK-1 allosteric regulation by ATP and F2,6BP"
            if fallback_image_needed
            else None
        )
        return fallback_passage, fallback_usage, fallback_image_needed, fallback_image_prompt
    else:
        return passage_text, usage, image_needed, image_prompt


def _offline_mock_draft(req: GenerationRequest) -> QuestionDraft:
    """Offline fixture draft whose stimulus follows the request (shared passage or none)."""
    draft = get_mock_draft(req)
    if req.shared_stimulus:
        draft.stimulus_text = req.shared_stimulus.strip()
    elif req.passage_required and str(req.passage_required).lower() in ("no", "false"):
        draft.stimulus_text = ""
    return draft


async def generate_question(
    req: GenerationRequest,
    diversity_context: str | None = None,
) -> tuple[QuestionDraft, TokenUsage]:
    """Invokes the Question Generator Agent to draft a publication-grade AAMC MCAT question."""
    user_prompt = build_generator_user_prompt(req, fused=False, diversity_context=diversity_context)

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
    except LLMNotConfiguredError as e:
        require_offline_mode(e)
        logger.warning("Generator LLM not configured, using offline mock draft: %s", e)
        fallback_usage = mock_usage(
            QUESTION_GENERATOR_MOCK_PROMPT_TOKENS, QUESTION_GENERATOR_MOCK_COMPLETION_TOKENS
        )
        mock_draft = _offline_mock_draft(req)
        return mock_draft, fallback_usage
    else:
        return draft, usage


async def generate_question_with_self_critique(
    req: GenerationRequest,
    diversity_context: str | None = None,
) -> tuple[QuestionDraft, ReviewScore | None, TokenUsage]:
    """
    Fused Draft-and-Critique generator:
    Generates the candidate question AND scores it with the 100-point rubric
    in a single LLM round-trip.
    """
    user_prompt = build_generator_user_prompt(req, fused=True, diversity_context=diversity_context)

    try:

        def _parse_fused(raw: str) -> tuple[dict[str, Any], QuestionDraft]:
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
            except (ValueError, TypeError, KeyError, AttributeError) as parse_err:
                logger.warning("Failed to parse self_critique object: %s", parse_err)

    except LLMNotConfiguredError as e:
        require_offline_mode(e)
        logger.warning("Fused Generator LLM not configured, using offline mock draft: %s", e)
        fallback_usage = mock_usage(
            QUESTION_GENERATOR_MOCK_PROMPT_TOKENS, QUESTION_GENERATOR_MOCK_COMPLETION_TOKENS
        )
        mock_draft = _offline_mock_draft(req)
        mock_review = evaluate_heuristically(mock_draft, req, 1)
        return mock_draft, mock_review, fallback_usage
    else:
        return draft, self_review, usage
