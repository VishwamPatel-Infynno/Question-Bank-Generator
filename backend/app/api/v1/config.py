from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from app.api.admin import is_admin_request
from app.core.config import config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Configuration & Settings"])


@router.get("/config")
async def get_runtime_settings(request: Request = None) -> dict[str, Any]:  # type: ignore[assignment]
    # FastAPI only injects a bare ``Request`` annotation, hence the None default instead of ``| None``.
    """Retrieves current runtime configuration and pricing constants."""
    in_rate, out_rate = config.get_default_pricing_rates()

    # Masked payload for external HTTP requests (protecting competitive IP from competitors)
    if not is_admin_request(request):
        return {
            "engine": "Infynno Cognitive Architecture v2.0",
            "visual_engine": "Infynno Visual Studio v2.0",
            "ai_engine_ready": bool(
                config.DEEPINFRA_API_KEY or config.OPENAI_API_KEY or config.ANTHROPIC_API_KEY
            ),
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
            "current_image_cost_usd": config.calculate_image_cost(),
        }

    # Internal configuration when called directly by internal tests
    return {
        "engine": "Infynno Cognitive Architecture v2.0",
        "visual_engine": "Infynno Visual Studio v2.0",
        "ai_engine_ready": bool(
            config.DEEPINFRA_API_KEY or config.OPENAI_API_KEY or config.ANTHROPIC_API_KEY
        ),
        "default_text_model": config.DEFAULT_TEXT_MODEL,
        "default_image_model": config.DEFAULT_IMAGE_MODEL,
        "active_provider": config.get_active_provider(),
        "active_image_provider": config.get_active_image_provider(),
        "has_anthropic_key": bool(config.ANTHROPIC_API_KEY),
        "has_deepinfra_key": bool(config.DEEPINFRA_API_KEY),
        "has_openai_key": bool(config.OPENAI_API_KEY),
        "openai_model": config.OPENAI_MODEL,
        "openai_image_model": config.OPENAI_IMAGE_MODEL,
        "deepinfra_image_model": config.DEEPINFRA_IMAGE_MODEL,
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
        "current_image_cost_usd": config.calculate_image_cost(),
    }
