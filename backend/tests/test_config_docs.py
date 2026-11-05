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
    # VITE_* variables are read by the frontend dev server, not by the backend Settings
    unknown = {k for k in keys - set(Settings.model_fields) if not k.startswith("VITE_")}
    assert unknown == set(), f"Unknown keys in .env.example: {sorted(unknown)}"


def test_every_setting_is_documented_in_the_setup_guide():
    doc = (ROOT / "docs" / "SETUP_AND_CONFIG.md").read_text()
    undocumented = sorted(
        f for f in set(Settings.model_fields) - INTERNAL_FIELDS if f"`{f}`" not in doc
    )
    assert undocumented == [], f"Missing from docs/SETUP_AND_CONFIG.md: {undocumented}"


# .env.example deliberately recommends a different value than the code default for these
INTENTIONAL_ENV_OVERRIDES = {"ACTIVE_IMAGE_PROVIDER"}


def _same_value(a: str, b: str) -> bool:
    a, b = a.strip().strip('"'), b.strip().strip('"')
    if a == b:
        return True
    try:
        return float(a) == float(b)
    except ValueError:
        return False


def test_documented_defaults_match_the_code():
    """Catches docs that promise a default the code does not use (e.g. LLM_MAX_RETRIES 4 vs 3)."""
    doc = (ROOT / "docs" / "SETUP_AND_CONFIG.md").read_text()
    doc_defaults = {
        m.group(1): m.group(2)
        for m in re.finditer(r"^\| `([A-Z0-9_]+)` \| `[^`]*`\s*\| `([^`]*)`", doc, re.M)
    }
    env = {}
    for line in (ROOT / ".env.example").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            key, value = line.split("=", 1)
            env[key] = value
    problems = []
    for name, field in Settings.model_fields.items():
        default = field.default
        if default is None or isinstance(default, (list, dict)) or field.default_factory:
            continue
        expected = str(default).lower() if isinstance(default, bool) else str(default)
        shown = doc_defaults.get(name)
        if shown is not None and not _same_value(shown, expected):
            problems.append(f"docs {name}: {shown!r} != code {expected!r}")
        example = env.get(name)
        if (
            example is not None
            and name not in INTENTIONAL_ENV_OVERRIDES
            and not example.startswith("your_")
            and not _same_value(example, expected)
        ):
            problems.append(f".env.example {name}: {example!r} != code {expected!r}")
    assert problems == [], problems


def test_testing_guide_states_the_real_test_counts():
    """The one authoritative count in docs/TESTING_AND_QA.md must match what pytest collects."""
    import subprocess
    import sys

    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "backend/tests",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "backend")},
    ).stdout
    match = re.search(r"(\d+)/(\d+) tests collected \((\d+) deselected\)", out)
    assert match, out[-300:]
    deterministic, total = match.group(1), match.group(2)
    guide = (ROOT / "docs" / "TESTING_AND_QA.md").read_text()
    assert f"{deterministic} deterministic" in guide, (
        f"update the deterministic count to {deterministic}"
    )
    assert f"{total} backend tests" in guide or f"{total} Total Backend Tests" in guide, (
        f"update the total test count to {total}"
    )
