"""Single source of truth for the numeric authoring standards.

Prompts, the deterministic validator and the reviewer all quote these numbers. They used to be
written out by hand in a dozen places and had drifted apart (option tolerance of 1-2, 1-3, 2-4
words or 15%; passage length of 250-400, 300-500, 320-450 words). Change them here only.
"""

from __future__ import annotations

import math

# Reading passage length in words
SCIENCE_PASSAGE_WORDS: tuple[int, int] = (300, 500)
CARS_PASSAGE_WORDS: tuple[int, int] = (500, 600)

# Option length parity: the spread (longest minus shortest option, in words) must stay within
# max(OPTION_SPREAD_MIN_WORDS, ceil(OPTION_SPREAD_FRACTION * mean option length)).
OPTION_SPREAD_MIN_WORDS = 3
OPTION_SPREAD_FRACTION = 0.20
# A spread above this multiple of the limit is a blocking defect (below it, a warning).
OPTION_SPREAD_BLOCKING_MULTIPLE = 2

OPTION_PARITY_TEXT = (
    f"within {OPTION_SPREAD_MIN_WORDS} words of each other "
    f"(or within {int(OPTION_SPREAD_FRACTION * 100)}% of the average length when options "
    "average more than 15 words)"
)


def is_cars(section: object) -> bool:
    """True for the CARS subtest (enum member or string, any case).

    Lives here (not in workflow/_section_utils) so agents can use it without importing the
    workflow package, which imports the agents back.
    """
    value = section.value if hasattr(section, "value") else section
    return str(value).strip().lower() in ("cars", "mcatsection.cars")


def passage_band(is_cars: bool) -> tuple[int, int]:
    """Word band for the section's reading passage."""
    return CARS_PASSAGE_WORDS if is_cars else SCIENCE_PASSAGE_WORDS


def passage_words_text(is_cars: bool) -> str:
    lo, hi = passage_band(is_cars)
    return f"{lo}-{hi} words"


def option_spread_limit(mean_words: float) -> int:
    """Maximum allowed word-count spread between the longest and shortest option."""
    return max(OPTION_SPREAD_MIN_WORDS, math.ceil(OPTION_SPREAD_FRACTION * mean_words))


def resolve_standards(text: str) -> str:
    """Fills the ``<<TOKEN>>`` placeholders used inside the static system prompts."""
    return (
        text.replace("<<OPTION_PARITY>>", OPTION_PARITY_TEXT)
        .replace("<<SCIENCE_WORDS>>", f"{SCIENCE_PASSAGE_WORDS[0]}-{SCIENCE_PASSAGE_WORDS[1]}")
        .replace("<<CARS_WORDS>>", f"{CARS_PASSAGE_WORDS[0]}-{CARS_PASSAGE_WORDS[1]}")
    )
