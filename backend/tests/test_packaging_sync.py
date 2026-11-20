"""pyproject.toml must mirror backend/requirements*.txt (the canonical dependency lists)."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _requirements(path: Path) -> set[str]:
    deps: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line and not line.startswith("-r"):
            deps.add(re.sub(r"\s+", "", line))
    return deps


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_runtime_dependencies_match_requirements_txt():
    declared = {re.sub(r"\s+", "", d) for d in _pyproject()["project"]["dependencies"]}
    assert declared == _requirements(ROOT / "backend" / "requirements.txt")


def test_dev_group_matches_requirements_dev_txt():
    declared = {re.sub(r"\s+", "", d) for d in _pyproject()["dependency-groups"]["dev"]}
    assert declared == _requirements(ROOT / "backend" / "requirements-dev.txt")
