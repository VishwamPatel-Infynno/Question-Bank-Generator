"""Process-wide concurrency limits shared by every generation run."""

from __future__ import annotations

import asyncio

from app.core.config import config

_pipeline_semaphore: asyncio.Semaphore | None = None


def get_global_pipeline_semaphore() -> asyncio.Semaphore:
    """Singleton cap on question pipelines running at once across ALL runs and batches.

    Each run used to create its own semaphore, so concurrency multiplied with the number of
    runs (4 batch jobs x 4 workers = 16 pipelines). A single shared cap keeps load predictable;
    the separate LLM semaphore still bounds actual provider calls.
    """
    global _pipeline_semaphore
    if _pipeline_semaphore is None:
        _pipeline_semaphore = asyncio.Semaphore(config.GLOBAL_MAX_CONCURRENT_PIPELINES)
    return _pipeline_semaphore
