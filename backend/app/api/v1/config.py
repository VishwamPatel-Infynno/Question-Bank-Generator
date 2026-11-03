from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.config import config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Configuration & Settings"])


@router.get("/config")
async def get_settings():
    """Retrieves current runtime configuration and pricing constants."""
    in_rate, out_rate = config.get_default_pricing_rates()
    return {
        "default_text_model": config.DEFAULT_TEXT_MODEL,
        "default_image_model": config.DEFAULT_IMAGE_MODEL,
        "active_provider": config.get_active_provider(),
        "has_anthropic_key": bool(config.ANTHROPIC_API_KEY),
        "has_deepinfra_key": bool(config.DEEPINFRA_API_KEY),
        "fast_model_cascade": config.FAST_MODEL_CASCADE
        if isinstance(config.FAST_MODEL_CASCADE, list)
        else [config.FAST_MODEL_CASCADE],
        "max_regenerations": config.MAX_REGENERATION_ATTEMPTS,
        "passing_threshold": config.PASSING_SCORE_THRESHOLD,
        "batch_passing_threshold": config.BATCH_PASSING_SCORE_THRESHOLD,
        "default_max_tokens": config.DEFAULT_MAX_TOKENS,
        "reviewer_max_tokens": config.REVIEWER_MAX_TOKENS,
        "default_temperature": config.DEFAULT_TEMPERATURE,
        "generator_temperature": config.GENERATOR_TEMPERATURE,
        "regenerator_temperature": config.REGENERATOR_TEMPERATURE,
        "reviewer_temperature": config.REVIEWER_TEMPERATURE,
        "blind_solver_temperature": config.BLIND_SOLVER_TEMPERATURE,
        "enable_blind_solver": config.ENABLE_BLIND_SOLVER,
        "blind_solver_confidence_threshold": config.BLIND_SOLVER_CONFIDENCE_THRESHOLD,
        "global_max_concurrent_jobs": config.GLOBAL_MAX_CONCURRENT_JOBS,
        "global_max_concurrent_llm_calls": config.GLOBAL_MAX_CONCURRENT_LLM_CALLS,
        "workflow_max_worker_retries": config.WORKFLOW_MAX_WORKER_RETRIES,
        "cost_per_million_input": in_rate,
        "cost_per_million_output": out_rate,
        "image_width": config.IMAGE_WIDTH,
        "image_height": config.IMAGE_HEIGHT,
        "image_iters": config.IMAGE_ITERS,
        "image_cost_base_rate": config.IMAGE_COST_PER_BASE_UNIT,
        "current_image_cost_usd": config.calculate_flux_image_cost(),
    }
