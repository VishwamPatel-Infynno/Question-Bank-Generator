"""Centralized logging configuration for the Infynno MCAT Question Bank Generator backend."""

from __future__ import annotations

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configures the root logger with a structured console handler.

    Sets a consistent log format across all backend modules so that
    every module-level ``logging.getLogger(__name__)`` logger inherits
    the same format and level without any per-module setup.

    Args:
        level: The logging level to apply globally (default: INFO).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    # Avoid adding duplicate handlers if configure_logging is called multiple times
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(level)
