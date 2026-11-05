"""Settings fields, .env.example and the setup doc must not drift apart."""

import re
from pathlib import Path

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
# Fields that are internal and not meant to appear in .env.example (none today)
INTERNAL_FIELDS: set[str] = set()


def _env_example_keys() -> set[str]:
    keys = set()
    for line in (ROOT / ".env.example").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            assert re.match(r"^[A-Z0-9_]+=", line), f"Malformed .env.example line: {line!r}"
            keys.add(line.split("=", 1)[0])
    return keys


def test_every_setting_is_in_env_example_and_nothing_extra():
    fields = set(Settings.model_fields) - INTERNAL_FIELDS
    keys = _env_example_keys()
    assert fields - keys == set(), f"Missing from .env.example: {sorted(fields - keys)}"
    assert keys - set(Settings.model_fields) == set(), "Unknown keys in .env.example"


def test_every_setting_is_documented_in_the_setup_guide():
    doc = (ROOT / "docs" / "SETUP_AND_CONFIG.md").read_text()
    undocumented = sorted(
        f for f in set(Settings.model_fields) - INTERNAL_FIELDS if f"`{f}`" not in doc
    )
    assert undocumented == [], f"Missing from docs/SETUP_AND_CONFIG.md: {undocumented}"
