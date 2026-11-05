"""Centralized logging configuration for the Infynno MCAT Question Bank Generator backend."""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Per-task correlation ids (run, batch, job, question slot). asyncio tasks copy the current
# context when created, so values bound in a parent flow into the workers it spawns.
_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})  # noqa: B039


@contextmanager
def bind_log_context(**fields: Any) -> Iterator[None]:
    """Binds correlation ids (e.g. batch_id, job_id, run_id) to every log line in this scope."""
    token = _log_context.set({**_log_context.get(), **{k: v for k, v in fields.items() if v}})
    try:
        yield
    finally:
        _log_context.reset(token)


def _install_record_factory() -> None:
    """Adds ``ctx`` (dict) and ``ctx_str`` (text) to every record, whatever handler formats it."""
    previous = logging.getLogRecordFactory()
    if getattr(previous, "_mcat_ctx", False):
        return

    def factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = previous(*args, **kwargs)
        ctx = _log_context.get()
        record.ctx = ctx
        record.ctx_str = (
            "[" + " ".join(f"{k}={str(v)[:8]}" for k, v in ctx.items()) + "] " if ctx else ""
        )
        return record

    factory._mcat_ctx = True  # type: ignore[attr-defined]
    logging.setLogRecordFactory(factory)


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with correlation ids as top-level fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **getattr(record, "ctx", {}),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO, json_format: bool | None = None) -> None:
    """
    Configures the root logger with a structured console handler.

    Sets a consistent log format across all backend modules so that
    every module-level ``logging.getLogger(__name__)`` logger inherits
    the same format and level without any per-module setup. Lines carry the correlation ids
    bound with :func:`bind_log_context`; set ``LOG_FORMAT=json`` for machine-readable output.

    Args:
        level: The logging level to apply globally (default: INFO).
        json_format: Force JSON output; defaults to the ``LOG_FORMAT`` setting.
    """
    from app.core.config import config

    _install_record_factory()
    use_json = json_format if json_format is not None else config.LOG_FORMAT.lower() == "json"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter()
        if use_json
        else logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(ctx_str)s%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    # Avoid adding duplicate handlers if configure_logging is called multiple times
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(level)
