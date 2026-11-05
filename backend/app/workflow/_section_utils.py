"""
_section_utils.py — Shared section-classification utilities for the workflow and batch layers.

Provides a single canonical helper for MCAT section checks so that the
``is_cars_section`` predicate is not duplicated across engine.py,
engine_helpers.py, and batch_runner.py.
"""

from __future__ import annotations

from app.agents.standards import is_cars


def is_cars_section(section: object) -> bool:
    """Returns ``True`` if *section* is the CARS (Critical Analysis and Reasoning Skills) subtest.

    Kept for the workflow layer; the single implementation lives in ``agents.standards.is_cars``
    so the agents and the workflow can never disagree about what counts as CARS.
    """
    return is_cars(section)
