"""Plain ASGI telemetry middleware measuring request latencies and response statuses without SSE buffering."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from app.services.metrics import telemetry_store

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class TelemetryMiddleware:
    """Records HTTP request counts and latencies without buffering or interfering with SSE streams."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        # Avoid recording scrapings of the metrics endpoints themselves to prevent self-inflation
        if path in ("/metrics", "/api/metrics"):
            await self._app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        start_time = time.perf_counter()
        status_code = 500  # Fallback if unhandled error occurs before response start

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        try:
            await self._app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start_time
            telemetry_store.record_request(
                method=method,
                raw_path=path,
                status_code=status_code,
                duration_sec=duration,
            )
