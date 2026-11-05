"""Optional shared-secret protection for mutating API routes."""

from __future__ import annotations

import hmac
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import config
from app.services.batch_concurrency import get_active_batch_metrics

_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# Read-only checks that happen to use POST must stay open
_OPEN_PATHS = frozenset({"/api/questions/check-duplicate"})


async def require_api_access(request: Request) -> None:
    """FastAPI dependency: enforces ``X-API-Key`` on mutating routes when API_ACCESS_KEY is set.

    With no key configured (local development, demos) every route stays open, exactly as
    before. Comparison is constant-time. This is a shared-secret gate for deployments behind
    a gateway or reverse proxy, not a replacement for per-user authentication.
    """
    expected = config.API_ACCESS_KEY
    if not expected or request.method not in _MUTATING_METHODS:
        return
    if request.url.path in _OPEN_PATHS:
        return
    supplied = request.headers.get("x-api-key", "")
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid X-API-Key header is required for this operation.",
        )


_RATE_WINDOW_SECONDS = 60.0
_request_times: dict[str, deque[float]] = defaultdict(deque)


async def limit_generation_requests(request: Request) -> None:
    """FastAPI dependency: per-client sliding-window limit for routes that spend LLM tokens."""
    limit = config.GENERATION_RATE_LIMIT_PER_MINUTE
    if limit <= 0:
        return
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _request_times[client]
    while window and now - window[0] > _RATE_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= limit:
        retry_after = max(1, int(_RATE_WINDOW_SECONDS - (now - window[0])))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many generation requests. Please slow down.",
            headers={"Retry-After": str(retry_after)},
        )
    window.append(now)
    if len(_request_times) > 1024:  # forget clients with no recent requests
        for key in [k for k, v in _request_times.items() if not v or now - v[-1] > 60.0]:
            del _request_times[key]


async def limit_active_batches() -> None:
    """FastAPI dependency: refuses to start more background batches than MAX_ACTIVE_BATCHES."""
    cap = config.MAX_ACTIVE_BATCHES
    if cap > 0 and get_active_batch_metrics()["active_running_batches"] >= cap:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{cap} batches are already running. Wait for one to finish or stop one.",
        )
