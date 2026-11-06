"""
batch_concurrency.py - Concurrency controls and task registries for background generation batches.

Governs the global worker pool semaphore, active batch asyncio task tracking,
and graceful cancellation/stopping routines.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any

from app.core.config import config
from app.repositories import (
    get_batch_by_id,
    get_jobs_by_batch_id,
    refresh_batch_aggregates,
    save_batch,
    update_job_progress,
)
from app.schemas import TERMINAL_STATES, BatchStatus, GenerationRequest, JobStatus

logger = logging.getLogger(__name__)

# Module-level dicts for tracking running tasks and generation requests.
# NOTE: Process-local. For multi-process/distributed setups, back with Redis.
_active_batch_tasks: dict[str, asyncio.Task[Any]] = {}
# Most-recently stored last. Bounded: a request holds the client's API key, which must not
# accumulate for the lifetime of the process (the DB copy is deliberately scrubbed of it).
_batch_requests: OrderedDict[str, GenerationRequest] = OrderedDict()
MAX_STORED_BATCH_REQUESTS = 256

# Global worker pool semaphore governing concurrent jobs across ALL running batches
_GLOBAL_JOB_SEMAPHORE: asyncio.Semaphore | None = None


def get_global_job_semaphore() -> asyncio.Semaphore:
    """Returns the singleton global worker pool semaphore, lazily initialized."""
    global _GLOBAL_JOB_SEMAPHORE
    if _GLOBAL_JOB_SEMAPHORE is None:
        _GLOBAL_JOB_SEMAPHORE = asyncio.Semaphore(config.GLOBAL_MAX_CONCURRENT_JOBS)
    return _GLOBAL_JOB_SEMAPHORE


def register_batch_task(batch_id: str, task: asyncio.Task[Any]) -> None:
    """Registers an active asyncio task for a batch."""
    _active_batch_tasks[batch_id] = task


def unregister_batch_task(batch_id: str, task: asyncio.Task[Any] | None = None) -> None:
    """Unregisters a batch task if current or if task matches."""
    if task is None or _active_batch_tasks.get(batch_id) is task:
        _active_batch_tasks.pop(batch_id, None)


def store_batch_request(batch_id: str, req: GenerationRequest) -> None:
    """Stores the original GenerationRequest in memory to support 1-click retries."""
    _batch_requests.pop(batch_id, None)
    _batch_requests[batch_id] = req
    while len(_batch_requests) > MAX_STORED_BATCH_REQUESTS:
        _batch_requests.popitem(last=False)


def forget_batch_request(batch_id: str) -> None:
    """Drops a batch's cached request (the batch is gone, so nothing can retry it)."""
    _batch_requests.pop(batch_id, None)


def get_stored_batch_request(batch_id: str) -> GenerationRequest | None:
    """Retrieves the cached GenerationRequest for a batch if present."""
    return _batch_requests.get(batch_id)


def get_active_batch_metrics() -> dict[str, Any]:
    """Returns real-time concurrency metrics for background batches."""
    return {
        "active_running_batches": len(_active_batch_tasks),
        "global_max_concurrent_jobs": config.GLOBAL_MAX_CONCURRENT_JOBS,
        "global_max_concurrent_llm_calls": config.GLOBAL_MAX_CONCURRENT_LLM_CALLS,
        "active_batch_ids": list(_active_batch_tasks.keys()),
    }


async def stop_background_batch(batch_id: str) -> bool:
    """Gracefully stops an active batch, halts running tasks, and preserves generated questions."""
    task = _active_batch_tasks.pop(batch_id, None)
    batch = await get_batch_by_id(batch_id)
    if batch is None:
        return False
    # Nothing is running and the batch already reached a terminal status: stopping must not
    # rewrite its history (e.g. downgrade a completed batch to partially_completed).
    if (task is None or task.done()) and batch.status in TERMINAL_STATES:
        return False
    if task and not task.done():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task

    # Mark remaining pending/running jobs as cancelled
    jobs = await get_jobs_by_batch_id(batch_id)
    now_iso = datetime.now(UTC).isoformat()
    for j in jobs:
        if j.status in (JobStatus.PENDING, JobStatus.RUNNING):
            await update_job_progress(j.id, status=JobStatus.CANCELLED, completed_at=now_iso)

    b = await get_batch_by_id(batch_id)
    if b:
        b.status = (
            BatchStatus.CANCELLED
            if (b.completed_jobs or 0) == 0
            else BatchStatus.PARTIALLY_COMPLETED
        )
        await save_batch(b)
    await refresh_batch_aggregates(batch_id)
    return True


def is_batch_running(batch_id: str) -> bool:
    """True while a background task is executing this batch in this process."""
    task = _active_batch_tasks.get(batch_id)
    return task is not None and not task.done()


async def cancel_all_background_batches() -> int:
    """Gracefully halts all active background batches, preserving generated questions."""
    batch_ids = list(_active_batch_tasks.keys())
    count = 0
    for b_id in batch_ids:
        stopped = await stop_background_batch(b_id)
        if stopped:
            count += 1
    return count
