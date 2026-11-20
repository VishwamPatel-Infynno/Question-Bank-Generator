"""Optional shared-secret protection for mutating API routes."""

from __future__ import annotations

import hmac
import ipaddress
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator

from fastapi import HTTPException, Request, status

from app.core.config import config
from app.services import get_active_batch_metrics

_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# Read-only checks that happen to use POST stay exempt from the API key (they are rate limited
# separately by their route dependency)
_OPEN_PATHS = frozenset({"/api/questions/check-duplicate"})


async def require_api_access(request: Request) -> None:
    """FastAPI dependency: enforces ``X-API-Key`` on mutating routes when API_ACCESS_KEY is set.

    With no key configured (local development, demos) every route stays open, exactly as
    before. Comparison is constant-time. This is a shared-secret gate for deployments behind
    a gateway or reverse proxy, not a replacement for per-user authentication.
    """
    if request.method == "POST" and request.url.path in _OPEN_PATHS:
        # Exempt from the key, but each call runs an embedding/similarity search: rate limit it
        # (own bucket, so duplicate checks never consume the generation allowance)
        _enforce_rate_limit(request, bucket="dup")
        return
    expected = config.API_ACCESS_KEY
    if not expected or request.method not in _MUTATING_METHODS:
        return
    supplied = request.headers.get("x-api-key", "")
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid X-API-Key header is required for this operation.",
        )


_RATE_WINDOW_SECONDS = 60.0
_request_times: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    """Rate-limit identity: the transport peer address as resolved by uvicorn.

    Only ``request.client`` is used, never a raw ``X-Forwarded-For`` header: uvicorn rewrites the
    client from that header only for peers listed in FORWARDED_ALLOW_IPS, so a forged header from
    anyone else is ignored. IPv6 clients are bucketed by /64 so one host cannot dodge the limit by
    rotating addresses inside its own prefix.
    """
    host = request.client.host if request.client else "unknown"
    try:
        addr = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return host
    if isinstance(addr, ipaddress.IPv6Address):
        if addr.ipv4_mapped is not None:
            return str(addr.ipv4_mapped)
        return str(ipaddress.ip_network(f"{addr}/64", strict=False).network_address)
    return str(addr)


async def limit_generation_requests(request: Request) -> None:
    """FastAPI dependency: per-client sliding-window limit for routes that spend LLM tokens."""
    _enforce_rate_limit(request, bucket="gen")


def _enforce_rate_limit(request: Request, bucket: str) -> None:
    limit = config.GENERATION_RATE_LIMIT_PER_MINUTE
    if limit <= 0:
        return
    client = f"{bucket}:{_client_key(request)}"
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


# Launches that passed the cap check but whose background task is not registered yet. The check
# and the reservation below run with no ``await`` in between, so concurrent requests cannot all
# observe the same free slot (the previous check-then-launch let a burst exceed the cap).
_pending_batch_launches = 0


async def limit_active_batches() -> AsyncIterator[None]:
    """FastAPI dependency: refuses to start more background batches than MAX_ACTIVE_BATCHES.

    Holds a reservation for the duration of the request handler, which registers the batch task
    before it returns; the slot is then counted by the active-batch registry instead.
    """
    global _pending_batch_launches
    cap = config.MAX_ACTIVE_BATCHES
    if cap <= 0:
        yield
        return
    active = get_active_batch_metrics()["active_running_batches"]
    if active + _pending_batch_launches >= cap:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{cap} batches are already running. Wait for one to finish or stop one.",
        )
    _pending_batch_launches += 1
    try:
        yield
    finally:
        _pending_batch_launches -= 1
