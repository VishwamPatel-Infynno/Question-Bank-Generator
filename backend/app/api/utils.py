"""Shared FastAPI route helpers."""

from __future__ import annotations

from typing import TypeVar

from fastapi import HTTPException

T = TypeVar("T")


def or_404(value: T | None, detail: str = "Not found") -> T:
    """Raise HTTP 404 when *value* is falsy, otherwise return it unchanged with preserved type."""
    if not value:
        raise HTTPException(status_code=404, detail=detail)
    return value
