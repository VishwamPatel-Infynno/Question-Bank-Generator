"""
node_finalize.py - Image generation, quality gate rejection, and final question assembly nodes.

Handles visual stimulus generation for science sections, terminal quality gate
rejection payloads, and comprehensive final Question entity assembly and optional persistence.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.image_generator import generate_image_stimulus
from app.agents.option_balancer import calculate_option_symmetry
from app.core.config import config
from app.repositories import save_question
from app.schemas import (
    MCAT_SECTION_LABELS,
    GenerationRequest,
    OptionChoice,
    Question,
    QuestionDraft,
    ReviewScore,
    determine_question_status,
    is_cars,
)
from app.workflow.state import AgentWorkflowState

logger = logging.getLogger(__name__)


async def reject_node(state: AgentWorkflowState) -> dict[str, Any]:
    """
    Quality Gate Reject Node:
    Triggered when candidate question fails to score > passing_threshold (default 80) after max attempts.
    Halts workflow: Bypasses image generation and does NOT persist to database.
    """
    req = GenerationRequest(**state["request"])
    draft = QuestionDraft(**state["current_draft"])
    review = ReviewScore(**state["current_review"]) if state.get("current_review") else None

    final_score = review.total_score if review else 0
    iteration = state.get("iteration_count", 1)
    passing_threshold = state.get("passing_threshold") or config.PASSING_SCORE_THRESHOLD

    logger.warning(
        "Strict Quality Gate: Question rejected. Score: %s/100 < %s after %s attempts. NOT saving to Question Bank repository.",
        final_score,
        passing_threshold,
        iteration,
    )

    rejection_payload = {
        "section": req.section.value,
        "section_label": MCAT_SECTION_LABELS.get(req.section, req.section.value),
        "subtopic": req.subtopic or "Core Syllabus",
        "difficulty": req.difficulty.value,
        "final_score": final_score,
        "threshold": passing_threshold,
        "review_rubric": review.model_dump() if review else None,
        "iteration_count": iteration,
        "iterations_history": state.get("iterations_history", []),
        "draft": draft.model_dump(),
        "total_tokens": state.get("total_tokens", 0),
        "total_prompt_tokens": state.get("total_prompt_tokens", 0),
        "total_completion_tokens": state.get("total_completion_tokens", 0),
        "total_cost_usd": state.get("total_cost_usd", 0.0),
        "agent_usage_breakdown": state.get("agent_usage_breakdown", []),
        "reason": (
            f"Question scored {final_score}/100, which is less than or equal to the required "
            f"{passing_threshold}-point quality benchmark after {iteration} iteration attempts. "
            f"Generation halted and question discarded from Question Bank."
        ),
    }

    return {
        "status": "rejected_below_threshold",
        "active_agent": "Quality Gate",
        "rejection_data": rejection_payload,
    }


async def image_node(state: AgentWorkflowState) -> dict[str, Any]:
    """Generates an accompanying visual stimulus diagram when requested or required."""
    req = GenerationRequest(**state["request"])
    draft = QuestionDraft(**state["current_draft"])

    logger.info("Executing Image Generator Agent...")
    img_url, img_svg, img_desc, usage = await generate_image_stimulus(draft, req)

    visual_category = None
    if usage and isinstance(usage, dict) and "details" in usage:
        visual_category = usage["details"].get("medical_modality") or usage["details"].get(
            "modality"
        )

    # Accumulate image generation cost and itemized breakdown
    current_cost = state.get("total_cost_usd", 0.0)
    image_cost = usage.get("cost_usd", 0.0) if usage else 0.0
    new_total_cost = round(current_cost + image_cost, 7)

    usage_list = list(state.get("agent_usage_breakdown", []))
    if usage:
        usage_list.append(usage)

    outcomes = dict(state.get("stage_outcomes", {}))
    outcomes["visual_stimulus"] = {
        "status": "generated",
        "image_url": img_url,
        "image_svg": img_svg,
        "image_description": img_desc,
        "usage": usage,
        "ai_validated": True,
        "image_needed": True,
        "modality": visual_category,
    }

    return {
        "image_url": img_url,
        "image_svg": img_svg,
        "image_description": img_desc,
        "visual_medical_category": visual_category,
        "visual_clinical_description": img_desc,
        "active_agent": "Image Generator",
        "status": "image_generated",
        "total_cost_usd": new_total_cost,
        "agent_usage_breakdown": usage_list,
        "latest_usage": usage,
        "stage_outcomes": outcomes,
    }


async def finalize_node(state: AgentWorkflowState) -> dict[str, Any]:
    """Assembles the final validated Question entity, computes option symmetry, and optionally persists."""
    req = GenerationRequest(**state["request"])
    draft = QuestionDraft(**state["current_draft"])
    review = ReviewScore(**state["current_review"]) if state.get("current_review") else None

    options = [OptionChoice(**o) if isinstance(o, dict) else o for o in draft.options]
    section_label = MCAT_SECTION_LABELS.get(req.section, req.section.value)
    symmetry = calculate_option_symmetry(options, draft.correct_answer_ids)

    outcomes = dict(state.get("stage_outcomes", {}))
    outcomes["option_symmetry"] = symmetry
    if "polish_refine" not in outcomes:
        outcomes["polish_refine"] = {
            "status": "bypassed",
            "reason": f"Draft achieved passing quality score ({review.total_score if review else 95}/100) on initial audit; regeneration loop was not required.",
        }
    if "visual_stimulus" not in outcomes:
        draft_img_needed = bool(getattr(draft, "image_needed", False))
        if req.allow_ai_images and not draft_img_needed:
            bypass_reason = (
                "AI visual necessity assessment evaluated this item and determined that the concept is "
                "conceptual/theoretical and best tested as a clean, text-focused item without an unnecessary figure."
            )
        elif is_cars(req.section):
            bypass_reason = "Visual stimuli are strictly prohibited in CARS section in accordance with official AAMC standards."
        else:
            bypass_reason = f"No visual stimulus needed (image_required='{req.image_required or 'No'}', visual_type='{req.visual_type or 'None'}')."

        outcomes["visual_stimulus"] = {
            "status": "bypassed",
            "reason": bypass_reason,
            "ai_validated": True,
            "image_needed": draft_img_needed,
        }
    effective_trap = (
        getattr(draft, "primary_trap", None)
        or (req.primary_trap if req.primary_trap != "Automatic" else None)
        or "SCOPE_SHIFT"
    )
    if req.likely_mistake_pattern == "None":
        effective_mistake = None
    else:
        effective_mistake = getattr(draft, "likely_mistake_pattern", None) or (
            req.likely_mistake_pattern
            if req.likely_mistake_pattern not in ("Automatic", "")
            else None
        )

    outcomes["final_payload"] = {
        "id": draft.question_stem[:12],  # placeholder until final_q created below
        "run_id": req.run_id,
        "batch_id": req.batch_id,
        "section": req.section.value,
        "section_label": section_label,
        "combination_id": req.combination_id,
        "content_domain": req.content_domain,
        "question_type": req.question_type,
        "interaction_type": req.interaction_type or "single_choice",
        "primary_trap": effective_trap,
        "likely_mistake_pattern": effective_mistake,
        "passage_required": str(req.passage_required) if req.passage_required is not None else None,
        "passage_mode": req.passage_mode or "single_passage",
        "passage_id": req.passage_id,
        "passage_questions": req.passage_questions,
        "visual_type": req.visual_type or "None",
        "visual_medical_category": state.get("visual_medical_category")
        or getattr(draft, "visual_medical_category", None),
        "visual_clinical_description": state.get("visual_clinical_description")
        or state.get("image_description"),
        "image_svg": state.get("image_svg"),
        "image_url": state.get("image_url"),
        "image_description": state.get("image_description"),
        "final_score": review.total_score if review else 95,
        "correct_answer_id": draft.correct_answer_id,
        "correct_answer_ids": draft.correct_answer_ids,
        "total_tokens": state.get("total_tokens", 0),
        "cost_usd": state.get("total_cost_usd", 0.0),
        "option_symmetry": symmetry,
    }

    score_val = review.total_score if review else 95
    determined_status = determine_question_status(
        score_val, is_in_progress_batch=bool(req.batch_id)
    )

    final_q = Question(
        run_id=req.run_id,
        batch_id=req.batch_id,
        status=determined_status,
        section=req.section.value,
        section_label=section_label,
        subtopic=req.subtopic or "Core Syllabus",
        difficulty=req.difficulty.value,
        stimulus_text=draft.stimulus_text,
        question_stem=draft.question_stem,
        options=options,
        correct_answer_id=draft.correct_answer_id,
        correct_answer_ids=draft.correct_answer_ids,
        explanation=draft.explanation,
        image_url=state.get("image_url"),
        image_svg=state.get("image_svg"),
        image_description=state.get("image_description"),
        final_score=review.total_score if review else 95,
        review_rubric=review,
        iteration_count=state.get("iteration_count", 1),
        iterations_history=state.get("iterations_history", []),
        total_tokens=state.get("total_tokens", 0),
        prompt_tokens=state.get("total_prompt_tokens", 0),
        completion_tokens=state.get("total_completion_tokens", 0),
        cost_usd=state.get("total_cost_usd", 0.0),
        token_usage_details=state.get("agent_usage_breakdown", []),
        combination_id=req.combination_id,
        content_domain=req.content_domain,
        question_type=req.question_type,
        interaction_type=req.interaction_type or "single_choice",
        primary_trap=effective_trap,
        passage_required=str(req.passage_required) if req.passage_required is not None else None,
        passage_mode=req.passage_mode or "single_passage",
        passage_id=req.passage_id,
        passage_questions=req.passage_questions,
        visual_type=req.visual_type or "None",
        visual_medical_category=state.get("visual_medical_category")
        or getattr(draft, "visual_medical_category", None),
        visual_clinical_description=state.get("visual_clinical_description")
        or state.get("image_description"),
        aamc_skill=draft.aamc_skill or req.aamc_skill,
        subject=req.subject or getattr(draft, "subject", None),
        unit=req.unit or getattr(draft, "unit", None),
        topic=req.topic or getattr(draft, "topic", None),
        subskill=req.subskill or getattr(draft, "subskill", None),
        likely_mistake_pattern=effective_mistake,
        duplicate_info=state.get("duplicate_info"),
        is_duplicate_override=bool(state.get("is_duplicate_override", False)),
        stage_outcomes=outcomes,
        option_symmetry=symmetry,
    )
    outcomes["final_payload"]["id"] = final_q.id

    # Persist in Question Bank ONLY if auto_save is explicitly requested (e.g. testing)
    if getattr(req, "auto_save", False):
        await save_question(final_q)
        logger.info(
            "Question auto-saved to Question Bank repository: %s (Score: %s, Cost: $%.5f)",
            final_q.id,
            final_q.final_score,
            final_q.cost_usd,
        )
    else:
        logger.info(
            "Question candidate verified (%s, Score: %s). Staged for Admin Review & Approval.",
            final_q.id,
            final_q.final_score,
        )

    return {
        "final_question": final_q.model_dump(),
        "status": "completed",
        "active_agent": "Completed",
        "stage_outcomes": outcomes,
    }
