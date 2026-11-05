from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.admin import is_admin_request
from app.core.config import config
from app.db.session import check_db_health
from app.services.batch_concurrency import get_active_batch_metrics

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe: 503 until the database answers, so orchestrators hold traffic back."""
    db_status = await check_db_health()
    metrics = get_active_batch_metrics()
    ready = bool(db_status.get("connected"))
    body = {
        "status": "ready" if ready else "not_ready",
        "database_connected": ready,
        "ai_engine_ready": bool(
            config.DEEPINFRA_API_KEY or config.OPENAI_API_KEY or config.ANTHROPIC_API_KEY
        ),
        "active_running_batches": metrics["active_running_batches"],
    }
    return JSONResponse(body, status_code=200 if ready else 503)


@router.get("/health")
async def health_check(request: Request = None):
    """Health check reporting database status, exam standard, and active pricing."""
    db_status = await check_db_health()
    in_rate, out_rate = config.get_default_pricing_rates()

    # Masked payload for external HTTP requests (protecting competitive IP from competitors)
    status = "healthy" if db_status.get("connected") else "degraded"
    if not is_admin_request(request):
        return {
            "status": status,
            "exam": "AAMC MCAT",
            "database": "connected" if db_status.get("connected") else "disconnected",
            "database_connected": db_status.get("connected", False),
            "database_status": db_status.get(
                "status", "ready" if db_status.get("connected") else "unavailable"
            ),
            "engine": "Infynno Cognitive Architecture v2.0",
            "visual_engine": "Infynno Visual Studio v2.0",
            "ai_engine_ready": bool(
                config.DEEPINFRA_API_KEY or config.OPENAI_API_KEY or config.ANTHROPIC_API_KEY
            ),
            "offline_mode": config.OFFLINE_MODE,
            "max_regenerations": config.MAX_REGENERATION_ATTEMPTS,
            "passing_threshold": config.PASSING_SCORE_THRESHOLD,
            "cost_per_million_input": in_rate,
            "cost_per_million_output": out_rate,
            "image_width": config.IMAGE_WIDTH,
            "image_height": config.IMAGE_HEIGHT,
            "image_iters": config.IMAGE_ITERS,
            "current_image_cost_usd": config.calculate_image_cost(),
        }

    # Internal configuration when called directly by internal tests
    return {
        "status": status,
        "exam": "AAMC MCAT",
        "database": "connected" if db_status.get("connected") else "disconnected",
        "database_connected": db_status.get("connected", False),
        "database_status": db_status.get(
            "status", "ready" if db_status.get("connected") else "unavailable"
        ),
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
        "max_regenerations": config.MAX_REGENERATION_ATTEMPTS,
        "passing_threshold": config.PASSING_SCORE_THRESHOLD,
        "cost_per_million_input": in_rate,
        "cost_per_million_output": out_rate,
        "image_width": config.IMAGE_WIDTH,
        "image_height": config.IMAGE_HEIGHT,
        "image_iters": config.IMAGE_ITERS,
        "current_image_cost_usd": config.calculate_image_cost(),
    }
