"""Shared admin-header check for diagnostic endpoints."""

from __future__ import annotations

import hmac

from fastapi import Request

from app.core.config import config


def is_admin_request(request: Request | None) -> bool:
    """True when the caller may see the full diagnostic/config payload.

    Direct (non-HTTP) calls pass ``None`` and are trusted. Over HTTP the ``x-admin-key`` header
    must match ``ADMIN_API_KEY`` (constant-time compare); with no key configured nobody is admin,
    so the full payload is never unlocked by an arbitrary header.
    """
    if request is None:
        return True
    supplied = request.headers.get("x-admin-key")
    if not supplied or not config.ADMIN_API_KEY:
        return False
    return hmac.compare_digest(supplied, config.ADMIN_API_KEY)
