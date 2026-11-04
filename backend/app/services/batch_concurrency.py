"""
batch_concurrency.py - Concurrency controls and task registries for background generation batches.

Governs the global worker pool semaphore, active batch asyncio task tracking,
and graceful cancellation/stopping routines.
"""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

from app.core.config import config
from app.repositories.batch_repository import (
    get_batch_by_id,
    refresh_batch_aggregates,
    save_batch,
)
from app.repositories.job_repository import (
    get_jobs_by_batch_id,
    update_job_progress,
)
from app.schemas import GenerationRequest

logger = logging.getLogger(__name__)

# Module-level dicts for tracking running tasks and generation requests.
# NOTE: Process-local. For multi-process/distributed setups, back with Redis.
_active_batch_tasks: dict[str, asyncio.Task[Any]] = {}
_batch_requests: dict[str, GenerationRequest] = {}

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
    _batch_requests[batch_id] = req


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
    if task and not task.done():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task

    # Mark remaining pending/running jobs as cancelled
    jobs = await get_jobs_by_batch_id(batch_id)
    now_iso = datetime.now(UTC).isoformat()
    for j in jobs:
        if j.status in ("pending", "running"):
            await update_job_progress(j.id, status="cancelled", completed_at=now_iso)

    b = await get_batch_by_id(batch_id)
    if b:
        b.status = "cancelled" if (b.completed_jobs or 0) == 0 else "partially_completed"
        await save_batch(b)
    await refresh_batch_aggregates(batch_id)
    return True


async def cancel_background_batch(batch_id: str) -> bool:
    """Cancels an active background batch runner task if running."""
    return await stop_background_batch(batch_id)


async def cancel_all_background_batches() -> int:
    """Gracefully halts all active background batches, preserving generated questions."""
    batch_ids = list(_active_batch_tasks.keys())
    count = 0
    for b_id in batch_ids:
        stopped = await stop_background_batch(b_id)
        if stopped:
            count += 1
    return count
