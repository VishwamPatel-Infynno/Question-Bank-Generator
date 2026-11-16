from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from fastapi import APIRouter, Request, Response

from app.api.admin import is_admin_request
from app.core.config import config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Configuration & Settings"])

_CONFIG_CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=60"
_ADMIN_CONFIG_CACHE_CONTROL = "private, no-cache"


def _matches_etag(client_etag: str | None, server_etag: str) -> bool:
    if not client_etag:
        return False
    if client_etag.strip() == "*":
        return True
    clean_server = server_etag.strip().removeprefix("W/").strip('"')
    tags = [t.strip().removeprefix("W/").strip('"') for t in client_etag.split(",")]
    return clean_server in tags


def _compute_etag(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return f'"{hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]}"'


def public_runtime_fields() -> dict[str, Any]:
    """The runtime facts every caller may see (shared by /config and /health)."""
    in_rate, out_rate = config.get_default_pricing_rates()
    return {
        "engine": "Infynno Cognitive Architecture v2.0",
        "visual_engine": "Infynno Visual Studio v2.0",
        "ai_engine_ready": bool(
            config.DEEPINFRA_API_KEY or config.OPENAI_API_KEY or config.ANTHROPIC_API_KEY
        ),
        "max_regenerations": config.MAX_REGENERATION_ATTEMPTS,
        "passing_threshold": config.PASSING_SCORE_THRESHOLD,
        "batch_passing_threshold": config.BATCH_PASSING_SCORE_THRESHOLD,
        "cost_per_million_input": in_rate,
        "cost_per_million_output": out_rate,
        "image_width": config.IMAGE_WIDTH,
        "image_height": config.IMAGE_HEIGHT,
        "image_iters": config.IMAGE_ITERS,
        "current_image_cost_usd": config.calculate_image_cost(),
    }


# Module-level defaults allowing direct test invocation without B008 function call defaults
_DEFAULT_REQUEST: Any = None
_DEFAULT_RESPONSE: Any = None


@router.get("/config", response_model=None)
async def get_runtime_settings(
    request: Request = _DEFAULT_REQUEST,
    response: Response = _DEFAULT_RESPONSE,
) -> Response | dict[str, Any]:
    # FastAPI only injects a bare ``Request`` annotation, hence the None default instead of ``| None``.
    """Retrieves current runtime configuration and pricing constants."""
    is_admin = is_admin_request(request)
    cache_control = _ADMIN_CONFIG_CACHE_CONTROL if is_admin else _CONFIG_CACHE_CONTROL

    # Masked payload for external HTTP requests (protecting competitive IP from competitors)
    if not is_admin:
        payload = {
            **public_runtime_fields(),
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
            "image_cost_base_rate": config.DEEPINFRA_IMAGE_COST_PER_UNIT,
        }
    else:
        # Internal configuration when called directly by internal tests
        payload = {
            **public_runtime_fields(),
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
            "fast_model_cascade": config.FAST_MODEL_CASCADE,
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
            "image_cost_base_rate": config.DEEPINFRA_IMAGE_COST_PER_UNIT,
        }

    etag = _compute_etag(payload)

    if request is not None and _matches_etag(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": cache_control})

    if response is not None:
        response.headers["Cache-Control"] = cache_control
        response.headers["ETag"] = etag

    return payload
