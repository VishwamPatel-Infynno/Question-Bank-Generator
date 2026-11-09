"""Shared FastAPI route helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def or_404(value: Any, detail: str = "Not found") -> Any:
    """Raise HTTP 404 when *value* is falsy, otherwise return it unchanged."""
    if not value:
        raise HTTPException(status_code=404, detail=detail)
    return value

