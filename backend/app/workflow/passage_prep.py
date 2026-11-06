"""Per-item request building, diagram requirement and shared passage/visual drafting."""

from __future__ import annotations

import uuid
from collections.abc import Callable
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
)
from app.workflow._section_utils import is_cars_section
from app.workflow.state import AgentWorkflowState


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
    usage_breakdown: list[dict[str, Any]] = field(default_factory=list)


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

    # For independent questions in science sections, when AI diagrams are permitted,
    # calibrate authentic AAMC frequency (~40%: items 0 and 2 in every 5 questions, or single question)
    sec_is_cars = is_cars_section(req.section)
    has_diagrams_enabled = (
        req.allow_ai_images or req.require_image or req.visual_type in KNOWN_VISUAL_TYPES
    )
    should_require_item_image = bool(
        not sec_is_cars
        and not is_passage_item
        and has_diagrams_enabled
        and (total_qty == 1 or (idx % 5 in (0, 2)))
    )

    item_req = req.model_copy(
        update={
            "run_id": item_run_id,
            "batch_id": batch_id,
            "questions_to_generate": 1,
            "interaction_type": item_interaction,
            "passage_required": item_passage,
            "passage_mode": item_passage_mode,
            "passage_id": item_passage_id,
            "shared_stimulus": item_stimulus,
            "require_image": should_require_item_image or req.require_image,
            "thematic_angle": req.thematic_angle or f"Question Item {idx + 1}",
            "visual_type": "AI_FLUX_Image"
            if (should_require_item_image or req.require_image)
            else req.visual_type,
        }
    )
    return item_req, item_run_id, is_passage_item, item_interaction


def _determine_item_diagram_requirement(
    state: AgentWorkflowState,
    idx: int,
    is_passage_item: bool,
) -> bool:
    """
    Evaluates whether a specific question item within a batch requires a visual stimulus diagram.

    Respects section type (CARS never has diagrams), passage attachment (passage-linked items
    share the passage diagram and never have their own), explicit image flags from the request,
    and the autonomous AI decision stored in the generated draft.

    Args:
        state: Current AgentWorkflowState for this question worker.
        idx: Zero-based index of this question (informational; not used in logic).
        is_passage_item: Whether this question is linked to the shared reading passage.

    Returns:
        True if a visual stimulus diagram should be generated for this question.
    """
    _ = idx  # Informational parameter reserved for item-index specific diagram rules
    req_data = state["request"]
    sec_raw = req_data.get("section", "")
    section_val = sec_raw.value if hasattr(sec_raw, "value") else str(sec_raw)
    allow_ai_images = req_data.get("allow_ai_images", False)
    explicit_image = req_data.get("require_image", False)
    visual_type = req_data.get("visual_type", "None")

    # CARS strictly has no figures, data tables or diagrams in official AAMC format
    if is_cars_section(section_val):
        return False
    if is_passage_item:
        # Passage question items share the passage diagram; they never have internal images
        return False

    # Check if visual generation is permitted at all
    visuals_permitted = allow_ai_images or explicit_image or visual_type in KNOWN_VISUAL_TYPES
    if not visuals_permitted:
        return False

    if explicit_image:
        return True

    # Autonomous AI determination for independent items
    return bool(state.get("current_draft", {}).get("image_needed", False))


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
) -> tuple[SharedPassageState, list[WorkflowEvent]]:
    """
    Drafts a shared reading passage and associated visual stimulus diagram when requested.

    Returns:
        Tuple of (SharedPassageState, events_to_emit).
    """
    events: list[WorkflowEvent] = []
    state = SharedPassageState(passage_text=shared_passage_text)

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
        events.append(passage_start_evt)

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

        state.usage_breakdown.append(
            {
                "agent": "Passage Writer",
                "iteration": 1,
                "prompt_tokens": passage_usage.prompt_tokens,
                "completion_tokens": passage_usage.completion_tokens,
                "total_tokens": passage_usage.total_tokens,
                "cost_usd": passage_usage.cost_usd,
            }
        )

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
        events.append(passage_done_evt)

    requires_passage_image = bool(
        not is_cars_section(req.section)
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
        events.append(p_img_start_evt)

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

        if p_img_usage and p_img_usage.get("cost_usd"):
            state.cost += p_img_usage["cost_usd"]

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
        events.append(p_img_done_evt)

    return state, events
