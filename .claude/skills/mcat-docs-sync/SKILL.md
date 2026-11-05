---
name: mcat-docs-sync
description: Keep Question Bank Generator documentation in step with code: README.md, DESIGN.md, CONTRIBUTING.md, docs/*.md (API, ARCHITECTURE, TESTING_AND_QA, SETUP_AND_CONFIG, TOKEN_TRACKING, MCAT_RUBRIC), backend/README.md, frontend/README.md. Use after any change to endpoints, config keys, pipeline behavior, thresholds, pricing, UI components or tokens, test or file counts, or when the user asks to update, audit or fix docs.
---

# Docs sync

Recent history shows docs are updated in the same commit as refactors, and they quote many counts that go stale. Update docs as part of the change, not later.

## What to update for which change
| Change | Docs |
|---|---|
| New or changed endpoint | `docs/API.md` (also the operation/path counts quoted in `docs/README.md`) |
| New env/config key | `.env.example`, `docs/SETUP_AND_CONFIG.md` (it quotes a parameter count) |
| Pipeline, thresholds, agents | `docs/ARCHITECTURE.md`, `docs/MCAT_RUBRIC.md`, `CONTRIBUTING.md` principles |
| Pricing or token logic | `docs/TOKEN_TRACKING.md`, CONTRIBUTING principle 7 |
| Tests added/removed | `docs/TESTING_AND_QA.md`, `CONTRIBUTING.md`, `docs/README.md` (test and module counts) |
| Frontend component, token, layout | `DESIGN.md`, `frontend/README.md` (file counts for oxlint) |
| Backend layer or module | `backend/README.md`, `docs/ARCHITECTURE.md` |

New `Settings` fields must be added to `.env.example` and `docs/SETUP_AND_CONFIG.md` in the same change: `backend/tests/test_config_docs.py` fails otherwise. Edit `.env.example` with exact-line edits (a substring replace once turned `REGENERATOR_TEMPERATURE` into garbage because it contained `GENERATOR_TEMPERATURE`).

## Method
1. Grep the docs for the thing you changed (`grep -rn "<name or number>" README.md DESIGN.md CONTRIBUTING.md docs backend/README.md frontend/README.md`).
2. Recompute counts from the code rather than guessing: test count via `PYTHONPATH=backend pytest backend/tests --collect-only -q -m "not live_e2e"` (and `-m requires_db` for DB-only tests), operations/paths via `app.openapi()["paths"]` (`PYTHONPATH=backend python -c ...`), frontend files via `git ls-files frontend/src | wc -l`. Test trees appear in `README.md`, `docs/TESTING_AND_QA.md` and the numbered module list there; update all three when adding a test module.
3. Edit every occurrence so docs do not contradict each other.
4. Match the existing tone; keep single hyphens (no em or en dashes) per project rule.

Always write links relative to the file they live in (e.g. `../docs/API.md`), never absolute `file:///Users/...` paths, so they work on other machines.
