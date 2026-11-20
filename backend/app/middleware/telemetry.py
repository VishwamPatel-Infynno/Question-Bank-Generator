"""Plain ASGI telemetry middleware measuring request latencies and response statuses without SSE buffering."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from app.services.metrics import telemetry_store

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


def _route_template(scope: Scope, path: str) -> str | None:
    """Full path template of the matched route (``/api/batches/{batch_id}``), None if unmatched.

    Starlette stores the matched route in the shared scope. Routes included through an
    ``APIRouter`` prefix report only their own relative path, so the prefix is recovered by
    rendering the route with the concrete path params and stripping that tail from the real path.
    """
    route = scope.get("route")
    template = getattr(route, "path", None)
    if not isinstance(template, str):
        return None
    path_format = getattr(route, "path_format", None)
    params = scope.get("path_params") or {}
    if isinstance(path_format, str):
        try:
            tail = path_format.format(**{k: str(v) for k, v in params.items()})
        except (KeyError, IndexError, ValueError):
            return template
        if tail and path.endswith(tail):
            return path[: len(path) - len(tail)] + template
    return template


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
            route_template = _route_template(scope, path)
            telemetry_store.record_request(
                method=method,
                raw_path=path,
                status_code=status_code,
                duration_sec=duration,
                route_template=route_template if isinstance(route_template, str) else None,
            )
