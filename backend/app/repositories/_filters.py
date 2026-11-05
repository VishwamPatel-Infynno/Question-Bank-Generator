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
