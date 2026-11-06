from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.admin import is_admin_request
from app.api.v1.config import public_runtime_fields
from app.core.config import config
from app.db.session import check_db_health
from app.services.batch_concurrency import get_active_batch_metrics

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health/live")
async def liveness_check() -> dict[str, Any]:
    """Liveness probe: the process is up and serving. Never touches the database."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe: 503 until the database answers, so orchestrators hold traffic back."""
    db_status = await check_db_health()
    metrics = get_active_batch_metrics()
    ready = bool(db_status.get("connected"))
    body = {
        "status": "ready" if ready else "not_ready",
        "database_connected": ready,
        "active_running_batches": metrics["active_running_batches"],
    }
    return JSONResponse(body, status_code=200 if ready else 503)


@router.get("/health")
async def health_check(request: Request = None) -> dict[str, Any]:
    """Health check reporting database status, exam standard, and active pricing."""
    db_status = await check_db_health()
    # Masked payload for external HTTP requests (protecting competitive IP from competitors)
    status = "healthy" if db_status.get("connected") else "degraded"
    if not is_admin_request(request):
        return {
            **public_runtime_fields(),
            "status": status,
            "exam": "AAMC MCAT",
            "database": "connected" if db_status.get("connected") else "disconnected",
            "database_connected": db_status.get("connected", False),
            "database_status": db_status.get(
                "status", "ready" if db_status.get("connected") else "unavailable"
            ),
            "offline_mode": config.OFFLINE_MODE,
        }

    # Internal configuration when called directly by internal tests
    return {
        **public_runtime_fields(),
        "status": status,
        "exam": "AAMC MCAT",
        "database": "connected" if db_status.get("connected") else "disconnected",
        "database_connected": db_status.get("connected", False),
        "database_status": db_status.get(
            "status", "ready" if db_status.get("connected") else "unavailable"
        ),
        "default_text_model": config.DEFAULT_TEXT_MODEL,
        "default_image_model": config.DEFAULT_IMAGE_MODEL,
        "active_provider": config.get_active_provider(),
        "active_image_provider": config.get_active_image_provider(),
        "has_anthropic_key": bool(config.ANTHROPIC_API_KEY),
        "has_deepinfra_key": bool(config.DEEPINFRA_API_KEY),
        "has_openai_key": bool(config.OPENAI_API_KEY),
    }
