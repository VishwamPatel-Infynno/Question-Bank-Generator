from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.config import config
from app.db.session import check_db_health

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health")
async def health_check():
    """Health check reporting database status, exam standard, and active pricing."""
    db_status = await check_db_health()
    in_rate, out_rate = config.get_default_pricing_rates()
    return {
        "status": "healthy",
        "exam": "AAMC MCAT",
        "database": "connected" if db_status.get("connected") else "disconnected",
        "database_connected": db_status.get("connected", False),
        "database_status": db_status.get(
            "status", "ready" if db_status.get("connected") else "unavailable"
        ),
        "default_text_model": config.DEFAULT_TEXT_MODEL,
        "default_image_model": config.DEFAULT_IMAGE_MODEL,
        "active_provider": config.get_active_provider(),
        "has_anthropic_key": bool(config.ANTHROPIC_API_KEY),
        "has_deepinfra_key": bool(config.DEEPINFRA_API_KEY),
        "max_regenerations": config.MAX_REGENERATION_ATTEMPTS,
        "passing_threshold": config.PASSING_SCORE_THRESHOLD,
        "cost_per_million_input": in_rate,
        "cost_per_million_output": out_rate,
        "image_width": config.IMAGE_WIDTH,
        "image_height": config.IMAGE_HEIGHT,
        "image_iters": config.IMAGE_ITERS,
        "current_image_cost_usd": config.calculate_flux_image_cost(),
    }
