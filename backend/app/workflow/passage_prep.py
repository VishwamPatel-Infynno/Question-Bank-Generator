"""Per-item request building, diagram requirement and shared passage/visual drafting."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any

from app.agents.generator import generate_passage_stimulus
from app.agents.image_generator import generate_image_stimulus
from app.schemas import (
    KNOWN_VISUAL_TYPES,
    GenerationRequest,
    OptionChoice,
    QuestionDraft,
    WorkflowEvent,
    enum_value,
    is_cars,
)
from app.workflow.nodes import agent_usage_entry
from app.workflow.state import AgentUsageEntry, AgentWorkflowState


@dataclass
class SharedPassageState:
    """Encapsulates the generated state, tokens, and cost of a shared reading passage and diagram."""

    passage_text: str | None = None
    image_url: str | None = None
    image_svg: str | None = None
    image_desc: str | None = None
    tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    usage_breakdown: list[AgentUsageEntry] = field(default_factory=list)


MODALITY_ROTATION_BY_SECTION: dict[str, list[str]] = {
    "bio_biochem": [
        "histopathology (e.g. H&E tissue biopsy, cellular histology, blood smear)",
        "scientific_diagram (e.g. enzyme kinetics plot, SDS-PAGE gel, metabolic pathway)",
        "gross_anatomy (e.g. organ cross-section, cardiac chambers, renal architecture)",
        "cellular_microscopy (e.g. TEM micrograph of mitochondrial cristae, sarcomere ultrastructure)",
        "physiology_trace (e.g. 12-lead ECG strip, cardiac action potential, PV loop)",
    ],
    "chem_phys": [
        "scientific_diagram (e.g. reaction mechanism, titration curve, optics diagram, circuit)",
        "diagnostic_radiology (e.g. plain radiograph X-ray, CT attenuation, ultrasound, MRI)",
        "physiology_trace (e.g. cardiac electrical trace, respiratory pressure-volume curve)",
        "cellular_microscopy (e.g. membrane channel ultrastructure, electron micrograph)",
    ],
    "psych_soc": [
        "scientific_diagram (e.g. experimental scatter plot with regression line, psychophysics curve)",
        "diagnostic_radiology (e.g. fMRI BOLD cortical activation scan, PET neuroimaging)",
        "gross_anatomy (e.g. neuroanatomical structures: limbic system, hippocampus, amygdala)",
        "clinical_pathology (e.g. neurological examination findings, emotion processing stimuli)",
    ],
}

# Standard AAMC CARS 5-Question Set Blueprint
CARS_PASSAGE_SET_BLUEPRINTS: list[dict[str, str]] = [
    {
        "skill": "CARS1",
        "archetype": "Central Claim / Main Thesis",
        "directive": (
            "SLOT 1 FOCUS: Test the author's overarching thesis, central argument, or primary communicative purpose across the entire passage. "
            "Formulate an unambiguous stem asking for the author's core claim or purpose."
        ),
    },
    {
        "skill": "CARS1",
        "archetype": "Local Detail & Passage Evidence",
        "directive": (
            "SLOT 2 FOCUS: Test direct textual comprehension of a specific concept, term, or relationship discussed in the early paragraphs (Paragraph 1 or 2). "
            "Do NOT ask about the overarching thesis; test local textual evidence."
        ),
    },
    {
        "skill": "CARS2",
        "archetype": "Rhetorical Function / Author's Stance",
        "directive": (
            "SLOT 3 FOCUS: Test the logical or rhetorical function of a specific phrase, metaphor, or cited example in the middle of the passage "
            "(e.g., why the author mentions X, or how Paragraph 3 functions relative to Paragraph 2). Do NOT repeat the main claim."
        ),
    },
    {
        "skill": "CARS3",
        "archetype": "Reasoning Beyond the Text: Novel Scenario Application",
        "directive": (
            "SLOT 4 FOCUS: Extrapolate the author's reasoning to a NEW, hypothetical real-world scenario, historical event, or modern policy NOT described in the text. "
            "Ask how the author's philosophy or framework would apply to this new situation."
        ),
    },
    {
        "skill": "CARS3",
        "archetype": "Reasoning Beyond the Text: Challenge / Weaken Assumptions",
        "directive": (
            "SLOT 5 FOCUS: Present a new piece of hypothetical evidence or counter-argument and ask which finding or observation would most directly weaken, challenge, or invalidate the author's argument."
        ),
    },
]

# Standard AAMC Science 5-Question Set Blueprint (CPBS, BBLS, PSBB)
SCIENCE_PASSAGE_SET_BLUEPRINTS: list[dict[str, str]] = [
    {
        "skill": "Skill_1",
        "archetype": "Scientific Concept & Principle Foundation",
        "directive": (
            "SLOT 1 FOCUS: Test foundational biochemical, physical, or physiological concepts referenced in the passage (Knowledge of Scientific Concepts and Principles). "
            "Focus on the underlying scientific definitions and laws."
        ),
    },
    {
        "skill": "Skill_4",
        "archetype": "Data, Figure & Graph Interpretation",
        "directive": (
            "SLOT 2 FOCUS: Test data-based and statistical reasoning (Skill 4). "
            "Require the examinee to analyze a quantitative trend, data relationship, experimental baseline, or table/figure described in the passage."
        ),
    },
    {
        "skill": "Skill_3",
        "archetype": "Experimental Design & Methodological Rationale",
        "directive": (
            "SLOT 3 FOCUS: Test reasoning about research design and execution (Skill 3). "
            "Evaluate why a specific control was chosen, how a variable was isolated, or the rationale for a specific experimental assay."
        ),
    },
    {
        "skill": "Skill_2",
        "archetype": "Scientific Reasoning & Problem Solving / Mechanism",
        "directive": (
            "SLOT 4 FOCUS: Test multi-step mechanistic deduction or problem solving (Skill 2). "
            "Require combining a passage observation with outside foundational knowledge to deduce a mechanism."
        ),
    },
    {
        "skill": "Skill_2",
        "archetype": "Novel Experimental Condition / Hypothesis Testing",
        "directive": (
            "SLOT 5 FOCUS: Predict the outcome of a hypothetical follow-up experiment or modification to the experimental protocol (Reasoning Beyond the Passage). "
            "Ask what would happen if a novel inhibitor, gene knockout, or condition were introduced."
        ),
    },
]


def _build_batch_worker_request(
    req: GenerationRequest,
    idx: int,
    total_qty: int,
    batch_id: str | None,
    effective_passage_count: int,
    shared_passage_id: str | None,
    shared_passage_text: str | None,
) -> tuple[GenerationRequest, str, bool, str]:
    """
    Builds an isolated GenerationRequest for an individual question worker within a batch,
    resolving whether the question is passage-linked or independent (strictly single-choice MCAT format).

    For independent/standalone question batches (total_qty > 1 and passage_mode == 'independent'),
    items are guaranteed autonomous AI visual discretion (allow_ai_images=True, require_image=False)
    so that visual generation is determined solely by the AI draft's clinical/scientific assessment
    rather than inheriting forced parent batch flags.

    Args:
        req: The parent GenerationRequest for the batch.
        idx: Zero-based index of this question within the batch.
        total_qty: Total number of questions in the batch.
        batch_id: UUID of the parent batch record.
        effective_passage_count: Number of questions that are passage-linked (0 = all independent).
        shared_passage_id: UUID shared by all passage-linked items in this batch.
        shared_passage_text: Pre-generated passage text, or None if not yet generated.

    Returns:
        Tuple of (item_req, item_run_id, is_passage_item, item_interaction) where:
        - item_req: Cloned GenerationRequest scoped to a single question.
        - item_run_id: Unique UUID for this question's run.
        - is_passage_item: True if this question is linked to the shared passage.
        - item_interaction: Always "single_choice" (official MCAT format).
    """
    item_run_id = str(uuid.uuid4()) if total_qty > 1 else req.run_id
    is_passage_item = idx < effective_passage_count
    item_interaction = "single_choice"

    if is_passage_item:
        item_passage = "Yes"
        item_passage_mode = "single_passage"
        item_passage_id = shared_passage_id
        item_stimulus = shared_passage_text
    else:
        item_passage = "No"
        item_passage_mode = "independent"
        item_passage_id = None
        item_stimulus = None

    # Visual stimulus generation for science sections:
    # Autonomous AI validation: items inherit allow_ai_images so the AI dynamically evaluates
    # visual necessity for each question item. require_image is only True if explicitly mandated
    # by the user on the parent request.
    sec_is_cars = is_cars(req.section)
    has_diagrams_enabled = (
        req.allow_ai_images or req.require_image or req.visual_type in KNOWN_VISUAL_TYPES
    ) and not sec_is_cars
    should_require_item_image = bool(req.require_image and not sec_is_cars)

    # Resolve AAMC Reasoning Skill & Slot Blueprint:
    # If this is a passage set, assign deterministic slot archetypes so sibling questions
    # test distinct aspects (Main Idea, Detail, Function, Novel Application, Weaken).
    user_skill = (req.aamc_skill or "").strip()
    is_automatic_skill = not user_skill or user_skill.lower() in (
        "automatic",
        "all",
        "all skills",
        "none",
    )

    item_question_type = req.question_type
    if is_passage_item and effective_passage_count > 1:
        blueprints = CARS_PASSAGE_SET_BLUEPRINTS if sec_is_cars else SCIENCE_PASSAGE_SET_BLUEPRINTS
        blueprint = blueprints[idx % len(blueprints)]
        item_skill = blueprint["skill"] if is_automatic_skill else user_skill
        item_question_type = blueprint["archetype"]
        slot_directive = blueprint["directive"]
        if req.thematic_angle:
            item_thematic_angle = f"{req.thematic_angle} • {slot_directive}"
        else:
            item_thematic_angle = slot_directive
    else:
        if not is_automatic_skill:
            item_skill = user_skill
        elif sec_is_cars:
            cars_skills = ["CARS1", "CARS2", "CARS3"]
            item_skill = cars_skills[idx % len(cars_skills)]
        else:
            science_skills = ["Skill_1", "Skill_2", "Skill_3", "Skill_4", "Skill_2"]
            item_skill = science_skills[idx % len(science_skills)]
        item_thematic_angle = req.thematic_angle or f"Question Item {idx + 1}"

    item_req = req.model_copy(
        update={
            "run_id": item_run_id,
            "batch_id": batch_id,
            "questions_to_generate": 1,
            "interaction_type": item_interaction,
            "question_type": item_question_type,
            "passage_required": item_passage,
            "passage_mode": item_passage_mode,
            "passage_id": item_passage_id,
            "shared_stimulus": item_stimulus,
            "aamc_skill": item_skill,
            "allow_ai_images": bool(has_diagrams_enabled and not sec_is_cars),
            "require_image": should_require_item_image,
            "thematic_angle": item_thematic_angle,
            "visual_type": "None"
            if sec_is_cars
            else (
                "AI_FLUX_Image"
                if (should_require_item_image or has_diagrams_enabled)
                else req.visual_type
            ),
        }
    )
    return item_req, item_run_id, is_passage_item, item_interaction


def _determine_item_diagram_requirement(
    state: AgentWorkflowState, _is_passage_item: bool = False, **_kwargs: Any
) -> bool:
    """
    Evaluates whether a specific question item within a batch requires a visual stimulus diagram.

    Respects section type (CARS never has diagrams), explicit image flags from the request,
    and autonomous AI decisions stored in the generated draft.

    Args:
        state: Current AgentWorkflowState for this question worker.
        is_passage_item: Whether this question is linked to the shared reading passage.

    Returns:
        True if a visual stimulus diagram should be generated for this question.
    """
    req_data = state["request"]
    sec_raw = req_data.get("section", "")
    section_val = enum_value(sec_raw)
    allow_ai_images = req_data.get("allow_ai_images", False)
    explicit_image = req_data.get("require_image", False)
    visual_type = req_data.get("visual_type", "None")

    # CARS strictly has no figures, data tables or diagrams in official AAMC format
    if is_cars(section_val):
        return False

    # Check if visual generation is permitted at all
    visuals_permitted = allow_ai_images or explicit_image or visual_type in KNOWN_VISUAL_TYPES
    if not visuals_permitted:
        return False

    if explicit_image:
        return True

    draft = state.get("current_draft") or {}

    # Autonomous AI validation: only generate a diagram if the draft explicitly validated
    # that an accompanying visual stimulus is needed for this question item.
    return bool(draft.get("image_needed", False))


async def _prepare_shared_passage_and_visual(
    req: GenerationRequest,
    batch_id: str,
    shared_passage_id: str | None,
    shared_passage_text: str | None,
    is_single_passage_set: bool,
    effective_passage_count: int,
    independent_count: int,
    total_qty: int,
    make_event: Callable[..., WorkflowEvent],
    passage_generator_fn: Callable[..., Any] | None = None,
    image_generator_fn: Callable[..., Any] | None = None,
    *,
    state: SharedPassageState,
) -> AsyncIterator[WorkflowEvent]:
    """Drafts the shared reading passage and its visual stimulus diagram when requested.

    Yields each progress event as it happens (so "writing passage" reaches the client before
    the passage call, not after the diagram is done) and fills ``state`` in place.
    """
    state.passage_text = shared_passage_text

    actual_passage_gen = passage_generator_fn or generate_passage_stimulus
    actual_image_gen = image_generator_fn or generate_image_stimulus

    passage_image_needed = False
    passage_image_prompt = None

    if is_single_passage_set and not shared_passage_text:
        passage_start_evt = make_event(
            event_type="agent_start",
            agent_name="Passage Writer",
            message=f"Writing shared reading passage for {effective_passage_count} linked questions ({req.section.value})...",
            data={
                "stage": "passage_drafting",
                "total_questions": total_qty,
                "passage_question_count": effective_passage_count,
                "independent_question_count": independent_count,
                "batch_id": batch_id,
                "passage_id": shared_passage_id,
            },
        )
        yield passage_start_evt

        (
            shared_passage_text,
            passage_usage,
            passage_image_needed,
            passage_image_prompt,
        ) = await actual_passage_gen(req)

        state.passage_text = shared_passage_text
        state.tokens = passage_usage.total_tokens
        state.prompt_tokens = passage_usage.prompt_tokens
        state.completion_tokens = passage_usage.completion_tokens
        state.cost = passage_usage.cost_usd

        state.usage_breakdown.append(agent_usage_entry("Passage Writer", passage_usage))

        word_count = len(shared_passage_text.split())
        passage_done_evt = make_event(
            event_type="agent_complete",
            agent_name="Passage Writer",
            message=f"Shared reading passage completed ({word_count} words). Now drafting questions ({effective_passage_count} linked, {independent_count} independent)...",
            data={
                "stage": "passage_drafting",
                "passage_text": shared_passage_text,
                "passage_id": shared_passage_id,
                "word_count": word_count,
                "latest_usage": passage_usage.model_dump(),
            },
        )
        yield passage_done_evt

    requires_passage_image = bool(
        not is_cars(req.section)
        and (
            req.allow_ai_images
            or passage_image_needed
            or req.require_passage_image
            or req.require_image
            or req.visual_type in KNOWN_VISUAL_TYPES
        )
    )

    # Generate shared visual stimulus diagram for the passage if required
    if is_single_passage_set and requires_passage_image and state.passage_text:
        p_img_start_evt = make_event(
            event_type="agent_start",
            agent_name="Diagram & Chart Maker",
            message="Drawing shared visual stimulus diagram for reading passage...",
            data={
                "stage": "passage_image",
                "passage_id": shared_passage_id,
                "batch_id": batch_id,
            },
        )
        yield p_img_start_evt

        p_draft = QuestionDraft(
            stimulus_text=state.passage_text,
            question_stem=f"Visual stimulus diagram for {req.section.value} passage",
            options=[
                OptionChoice(id="A", text="Option A"),
                OptionChoice(id="B", text="Option B"),
                OptionChoice(id="C", text="Option C"),
                OptionChoice(id="D", text="Option D"),
            ],
            correct_answer_id="A",
            explanation="Shared passage visual stimulus reference",
            image_needed=True,
            image_prompt_or_type=passage_image_prompt
            or req.custom_prompt
            or f"Scientific clinical diagram for: {state.passage_text[:120]}",
        )

        (
            img_url,
            img_svg,
            img_desc,
            p_img_usage,
        ) = await actual_image_gen(p_draft, req)

        state.image_url = img_url
        state.image_svg = img_svg
        state.image_desc = img_desc

        if p_img_usage:
            # The diagram's spend belongs in the breakdown as well as the total
            state.cost += p_img_usage.get("cost_usd", 0.0) or 0.0
            state.usage_breakdown.append({"iteration": 1, **p_img_usage})

        p_img_done_evt = make_event(
            event_type="agent_complete",
            agent_name="Diagram & Chart Maker",
            message="Shared visual stimulus diagram ready for reading passage.",
            data={
                "stage": "passage_image",
                "passage_id": shared_passage_id,
                "image_url": img_url,
                "image_svg": img_svg,
                "image_description": img_desc,
                "batch_id": batch_id,
            },
        )
        yield p_img_done_evt
