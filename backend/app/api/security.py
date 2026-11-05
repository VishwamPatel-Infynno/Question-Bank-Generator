"""Optional shared-secret protection for mutating API routes."""

from __future__ import annotations

import hmac

from fastapi import HTTPException, Request, status

from app.core.config import config

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
