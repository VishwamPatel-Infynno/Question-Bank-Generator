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

    # Quality Gate check:
    # Try to get the score strictly greater than threshold on iterations < max_attempts
    if score <= threshold:
        if iteration < max_attempts:
            logger.info(
                "Score %s <= %s and iteration %s < %s. Routing to Re-Generator to try for > %s.",
                score,
                threshold,
                iteration,
                max_attempts,
                threshold,
            )
            return "regenerator"

        # After max_attempts (3 trials):
        # If score >= (threshold - 10), accept it into the Good Quality batch retention window (batch_only)
        # Otherwise, if score < (threshold - 10), halt and reject.
        batch_hold_threshold = threshold - 10
        if score >= batch_hold_threshold:
            logger.info(
                "Score %s <= %s but >= %s after %s attempts. Accepted as Good Quality.",
                score,
                threshold,
                batch_hold_threshold,
                iteration,
            )
        else:
            logger.warning(
                "Score %s < %s after max attempts (%s). Strict Quality Gate: Halting workflow.",
                score,
                batch_hold_threshold,
                max_attempts,
            )
            return "reject"

    # Passing score (> threshold or accepted Good Quality at max attempts): check if image generation is required
    req_raw = state["request"]
    req = req_raw if isinstance(req_raw, GenerationRequest) else GenerationRequest(**req_raw)
    current_draft = state.get("current_draft") or {}
    requires_image = _is_image_required(req, current_draft)

    if requires_image:
        logger.info("Score %s. Routing to Image Generator.", score)
        return "image_generator"

    logger.info("Score %s. Routing to Finalize.", score)
    return "finalize"
