"""Correlation ids bound with bind_log_context appear on log records, including in child tasks."""

import asyncio
import json
import logging

import pytest
from app.core.logging import JsonFormatter, _install_record_factory, bind_log_context


def _record(msg="hello"):
    _install_record_factory()
    return logging.getLogger("t").makeRecord("t", logging.INFO, __file__, 1, msg, (), None)


def test_ids_are_attached_and_removed_with_scope():
    with bind_log_context(batch_id="batch-1234567890", job_id="job-9"):
        rec = _record()
        assert rec.ctx == {"batch_id": "batch-1234567890", "job_id": "job-9"}
        assert rec.ctx_str.startswith("[batch_id=batch-12")
        assert json.loads(JsonFormatter().format(rec))["job_id"] == "job-9"
    assert _record().ctx == {}


@pytest.mark.asyncio
async def test_child_tasks_inherit_ids_without_leaking_back():
    seen = {}

    async def child():
        with bind_log_context(slot=3):
            seen["child"] = _record().ctx

    with bind_log_context(batch_id="b1"):
        await asyncio.create_task(child())
        seen["parent"] = _record().ctx

    assert seen["child"] == {"batch_id": "b1", "slot": 3}
    assert seen["parent"] == {"batch_id": "b1"}
