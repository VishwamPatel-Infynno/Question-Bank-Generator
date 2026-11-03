"""
_section_utils.py — Shared section-classification utilities for the workflow and batch layers.

Provides a single canonical helper for MCAT section checks so that the
``is_cars_section`` predicate is not duplicated across engine.py,
engine_helpers.py, and batch_runner.py.
"""

from __future__ import annotations

# All string representations that denote the CARS subtest
_CARS_VALUES: frozenset[str] = frozenset({"cars", "mcatsection.cars"})


def is_cars_section(section: object) -> bool:
    """Returns ``True`` if *section* represents the CARS (Critical Analysis and Reasoning Skills) subtest.

    Accepts both ``MCATSection`` enum members and raw string values, and is
    case-insensitive so that ``"CARS"``, ``"cars"``, and ``MCATSection.CARS``
    all return ``True``.

    Args:
        section: A ``MCATSection`` enum member, a string section code, or any
            object whose ``value`` attribute or ``str()`` representation can be
            compared to the known CARS identifiers.

    Returns:
        ``True`` if the section is CARS, ``False`` for all other sections.
    """
    val = section.value if hasattr(section, "value") else str(section)
    return val.strip().lower() in _CARS_VALUES
