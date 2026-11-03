import json
from pathlib import Path


def test_taxonomy_files_are_synchronized():
    """Guarantees backend and frontend taxonomy JSON definitions remain identical."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    backend_path = repo_root / "backend" / "app" / "data" / "mcat_dependent_taxonomy.json"
    frontend_path = repo_root / "frontend" / "src" / "constants" / "mcat_dependent_taxonomy.json"

    assert backend_path.exists(), f"Backend taxonomy not found at {backend_path}"
    assert frontend_path.exists(), f"Frontend taxonomy not found at {frontend_path}"

    with open(backend_path, encoding="utf-8") as f:
        backend_data = json.load(f)

    with open(frontend_path, encoding="utf-8") as f:
        frontend_data = json.load(f)

    assert backend_data == frontend_data, "Backend and frontend taxonomy JSON files have drifted!"
