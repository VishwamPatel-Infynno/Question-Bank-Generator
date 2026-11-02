import logging

from app.core.config import config
from app.schemas import GenerationRequest, MCATSection
from app.workflow.state import AgentWorkflowState

logger = logging.getLogger(__name__)


def _is_image_required(req: GenerationRequest, draft: dict) -> bool:
    """Evaluates whether an image is required based on section restrictions, autonomous AI discretion, or explicit flags."""
    sec_val = req.section.value if hasattr(req.section, "value") else str(req.section)
    if sec_val in (
        MCATSection.CARS.value,
        "CARS",
        "cars",
        "critical_analysis_and_reasoning_skills",
    ):
        return False
    if req.require_image or req.requires_visual_stimulus:
        return True
    return bool(draft.get("image_needed", False))


def route_after_fused_generation(state: AgentWorkflowState) -> str:
    """Routes to finalize (or image_generator) if fused self-score > 90; else to reviewer."""
    fused_passed = state.get("fused_self_passed", False)
    if not fused_passed:
        logger.info(
            "Fused self-critique <= threshold or unverified. Routing to Reviewer for standard audit."
        )
        return "reviewer"

    req_raw = state["request"]
    req = req_raw if isinstance(req_raw, GenerationRequest) else GenerationRequest(**req_raw)
    current_draft = state.get("current_draft") or {}
    requires_image = _is_image_required(req, current_draft)

    if requires_image:
        logger.info("Fused draft passed (> 90). Routing to Image Generator.")
        return "image_generator"

    logger.info("Fused draft passed (> 90). Routing directly to Finalize.")
    return "finalize"


def route_after_review(state: AgentWorkflowState) -> str:
    review = state.get("current_review")
    iteration = state.get("iteration_count", 1)

    score = review.get("total_score", 100) if review else 100
    threshold = state.get("passing_threshold") or config.PASSING_SCORE_THRESHOLD
    max_attempts = config.MAX_REGENERATION_ATTEMPTS

    # Strict Quality Gate check
    if score <= threshold:
        if iteration < max_attempts:
            logger.info(
                f"Score {score} <= {threshold} and iteration {iteration} < {max_attempts}. Routing to Re-Generator."
            )
            return "regenerator"
        logger.warning(
            f"Score {score} <= {threshold} after max attempts ({max_attempts}). Strict Quality Gate: Halting workflow."
        )
        return "reject"

    # Passing score (> 90): check if image generation is required
    req_raw = state["request"]
    req = req_raw if isinstance(req_raw, GenerationRequest) else GenerationRequest(**req_raw)
    current_draft = state.get("current_draft") or {}
    requires_image = _is_image_required(req, current_draft)

    if requires_image:
        logger.info(f"Score {score} > {threshold}. Routing to Image Generator.")
        return "image_generator"

    logger.info(f"Score {score} > {threshold}. Routing to Finalize.")
    return "finalize"
