"""Batch and job lifecycle statuses, and the groups of statuses the code reasons about.

``StrEnum`` members are real strings (``BatchStatus.FAILED == "failed"``, JSON and SQL see the
plain value), so these can replace string literals without changing behaviour. The database
CHECK constraint ``ck_generation_batches_status`` lists the same batch values.
"""

from __future__ import annotations

from enum import StrEnum


class BatchStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STOPPED = "stopped"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STOPPED = "stopped"


# Every value a batch row may hold (mirrors the database CHECK constraint)
BATCH_STATUSES: frozenset[str] = frozenset(s.value for s in BatchStatus)

# Work is (or may still be) going on
LIVE_STATES: frozenset[str] = frozenset(
    {BatchStatus.PENDING, BatchStatus.RUNNING, BatchStatus.IN_PROGRESS}
)

# A batch/job that delivered its questions (a short job is "completed" too)
COMPLETED_STATES: frozenset[str] = frozenset(
    {BatchStatus.COMPLETED, BatchStatus.PARTIALLY_COMPLETED}
)

# Nothing will run any more unless a user retries
TERMINAL_STATES: frozenset[str] = frozenset(
    {
        BatchStatus.COMPLETED,
        BatchStatus.PARTIALLY_COMPLETED,
        BatchStatus.FAILED,
        BatchStatus.CANCELLED,
        BatchStatus.STOPPED,
    }
)

# Jobs the runner should (re)execute when it picks a batch up
EXECUTABLE_JOB_STATES: frozenset[str] = frozenset(
    {
        JobStatus.PENDING,
        JobStatus.RUNNING,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        JobStatus.STOPPED,
    }
)

# Jobs a user-triggered retry may reset to pending
RETRYABLE_JOB_STATES: frozenset[str] = frozenset(
    {JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.PENDING}
)
