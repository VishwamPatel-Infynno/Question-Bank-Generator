from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response

from app.api.admin import is_admin_request
from app.core.config import config
from app.services.metrics import render_prometheus_metrics

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Observability & Telemetry"])

PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"


_DEFAULT_REQUEST: Any = None


@router.get("/metrics", response_model=None)
async def get_metrics(request: Request = _DEFAULT_REQUEST) -> Response:
    """Prometheus exposition endpoint serving application, database, batch concurrency, and HTTP telemetry.

    Public by default for standard Prometheus/Grafana scrapers. When an invalid admin key is
    explicitly provided, the call is rejected with HTTP 403.
    """
    if config.ADMIN_API_KEY and request is not None and not is_admin_request(request):
        admin_header = request.headers.get("x-admin-key") or request.headers.get("authorization")
        if admin_header:
            raise HTTPException(status_code=403, detail="Invalid admin credentials for metrics.")

    metrics_text = await render_prometheus_metrics()
    return Response(
        content=metrics_text,
        media_type=PROMETHEUS_MEDIA_TYPE,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
