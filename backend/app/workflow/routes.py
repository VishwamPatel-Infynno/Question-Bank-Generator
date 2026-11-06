from __future__ import annotations

import logging

from app.core.config import config
from app.schemas import GenerationRequest, is_cars
from app.workflow.state import AgentWorkflowState

logger = logging.getLogger(__name__)


def _is_image_required(req: GenerationRequest, draft: dict) -> bool:
    """Evaluates whether an image is required based on section restrictions, autonomous AI discretion, or explicit flags."""
    if is_cars(req.section):
        return False
    if req.require_image or req.requires_visual_stimulus:
        return True
    return bool(draft.get("image_needed", False))


def route_after_review(state: AgentWorkflowState) -> str:
    review = state.get("current_review")
    iteration = state.get("iteration_count", 1)

    # No review means nothing vouched for this draft: fail closed instead of passing it
    score = review.get("total_score", 0) if review else 0
    threshold = state.get("passing_threshold") or config.PASSING_SCORE_THRESHOLD
    max_attempts = config.MAX_REGENERATION_ATTEMPTS

    # Strict Quality Gate check
    if score <= threshold:
        if iteration < max_attempts:
            logger.info(
                "Score %s <= %s and iteration %s < %s. Routing to Re-Generator.",
                score,
                threshold,
                iteration,
                max_attempts,
            )
            return "regenerator"
        logger.warning(
            "Score %s <= %s after max attempts (%s). Strict Quality Gate: Halting workflow.",
            score,
            threshold,
            max_attempts,
        )
        return "reject"

    # Passing score (> 90): check if image generation is required
    req_raw = state["request"]
    req = req_raw if isinstance(req_raw, GenerationRequest) else GenerationRequest(**req_raw)
    current_draft = state.get("current_draft") or {}
    requires_image = _is_image_required(req, current_draft)

    if requires_image:
        logger.info("Score %s > %s. Routing to Image Generator.", score, threshold)
        return "image_generator"

    logger.info("Score %s > %s. Routing to Finalize.", score, threshold)
    return "finalize"
