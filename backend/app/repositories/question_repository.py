"""
question_repository.py - Unified question data access interface (CQRS facade combining queries and mutations).

Decomposed into:
- `question_queries.py`: Query and aggregation operations.
- `question_mutations.py`: Write, update, deletion, and lifecycle operations.

Consolidates all DAL operations for MCAT questions into a single authoritative entrypoint.
"""

from __future__ import annotations

from app.repositories.question_mutations import (
    _VISIBLE_STATUSES,
    batch_update_question_status,
    delete_question,
    delete_questions_batch,
    hard_delete_question,
    hard_delete_questions_batch,
    override_question_duplicate,
    restore_question,
    save_question,
    save_questions_batch,
    update_question_status,
)
from app.repositories.question_queries import (
    QuestionHead,
    count_questions,
    get_active_batch_questions,
    get_active_job_question_heads,
    get_question_by_id,
    get_question_status_counts,
    get_questions,
    get_repository_metrics,
    get_subtopic_reference_questions,
)

__all__ = [
    "_VISIBLE_STATUSES",
    "QuestionHead",
    "batch_update_question_status",
    "count_questions",
    "delete_question",
    "delete_questions_batch",
    "get_active_batch_questions",
    "get_active_job_question_heads",
    "get_question_by_id",
    "get_question_status_counts",
    "get_questions",
    "get_repository_metrics",
    "get_subtopic_reference_questions",
    "hard_delete_question",
    "hard_delete_questions_batch",
    "override_question_duplicate",
    "restore_question",
    "save_question",
    "save_questions_batch",
    "update_question_status",
]
