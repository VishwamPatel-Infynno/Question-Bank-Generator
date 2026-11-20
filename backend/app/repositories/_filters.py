"""Shared SQL filter clauses for the repositories.

Soft-deleted rows must be excluded the same way everywhere (the batch-integrity guarantees
depend on it), so the condition is defined once instead of being retyped in every query.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement

from app.models.passage import PassageModel
from app.models.question import QuestionModel


def active_question_clause() -> ColumnElement[bool]:
    """Matches questions that are not soft-deleted."""
    return QuestionModel.is_deleted.is_(False)


def active_passage_clause() -> ColumnElement[bool]:
    """Matches passages that are not soft-deleted."""
    return PassageModel.is_deleted.is_(False)


# Upper bound on rows a list query returns when the caller sets no (or a larger) limit.
MAX_LIST_LIMIT = 2000

LIKE_ESCAPE = "\\"


def clamp_list_limit(limit: int | None) -> int:
    """The effective LIMIT of a list query: the caller's positive limit, capped at MAX_LIST_LIMIT."""
    if limit and limit > 0:
        return min(limit, MAX_LIST_LIMIT)
    return MAX_LIST_LIMIT


def like_contains(text: str) -> str:
    """A ``%text%`` LIKE pattern with ``%``, ``_`` and the escape character taken literally.

    Use with ``column.ilike(pattern, escape=LIKE_ESCAPE)``.
    """
    escaped = (
        text.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", LIKE_ESCAPE + "%")
        .replace("_", LIKE_ESCAPE + "_")
    )
    return f"%{escaped}%"
