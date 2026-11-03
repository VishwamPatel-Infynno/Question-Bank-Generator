"""
base.py - SQLAlchemy declarative base and datetime utility helpers.

Provides the common Base declarative class for all SQLAlchemy ORM models,
along with timezone-safe conversions between Python datetimes and ISO-8601 strings.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def to_datetime(val: Any) -> datetime:
    """Converts a string ISO timestamp, datetime, or None to a timezone-aware UTC datetime."""
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=UTC)
        return val
    if isinstance(val, str) and val.strip():
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt
        except Exception:
            pass
    return datetime.now(UTC)


def to_iso_str(val: Any) -> str:
    """Safely converts a datetime object or string to an ISO-8601 string."""
    if val is None:
        return ""
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)
