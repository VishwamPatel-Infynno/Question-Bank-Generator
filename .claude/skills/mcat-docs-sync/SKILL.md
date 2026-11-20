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
| Pipeline, thresholds, agents | `docs/ARCHITECTURE.md`, `docs/MCAT_RUBRIC.md`, `CONTRIBUTING.md` principles, `docs/GLOSSARY.md` (terms, defaults, statuses) |
| Pricing or token logic | `docs/TOKEN_TRACKING.md`, CONTRIBUTING principle 7 |
| Tests added/removed | `docs/TESTING_AND_QA.md` (per-module list and counts), `CONTRIBUTING.md`, `README.md`, `docs/README.md`, `docs/SETUP_AND_CONFIG.md`, `docs/CLIENT_SYSTEM_AND_WORKFLOW_GUIDE.md`, `backend/README.md`, `frontend/README.md` (test, file and module counts) |
| Frontend component, token, layout, shortcut | `DESIGN.md` (component specs, classes, section 6 shortcuts), `docs/ARCHITECTURE.md` (component tree, section 9.2.1), `frontend/README.md` (tree, api.js export count, test table, oxlint file counts), `docs/CLIENT_SYSTEM_AND_WORKFLOW_GUIDE.md` (flows, shortcuts) |
| Backend layer or module | `backend/README.md`, `docs/ARCHITECTURE.md` |

New `Settings` fields must be added to `.env.example` and `docs/SETUP_AND_CONFIG.md` in the same change: `backend/tests/test_config_docs.py` fails otherwise. Edit `.env.example` with exact-line edits (a substring replace once turned `REGENERATOR_TEMPERATURE` into garbage because it contained `GENERATOR_TEMPERATURE`).

## Method
1. Grep the docs for the thing you changed (`grep -rn "<name or number>" README.md DESIGN.md CONTRIBUTING.md docs backend/README.md frontend/README.md`).
2. Recompute counts from the code rather than guessing: test count via `PYTHONPATH=backend pytest backend/tests --collect-only -q -m "not live_e2e"` (and `-m requires_db` for DB-only tests), operations/paths via `app.openapi()["paths"]` (`PYTHONPATH=backend python -c ...`), the oxlint file and rule counts from `pnpm --dir frontend exec oxlint -f default` (the "Finished ... on N files with M rules" line; plain `pnpm lint` can print nothing when its output is piped, and oxlint also lints files outside `frontend/src`, so a `git ls-files` count will not match), and the frontend test file and test counts from `pnpm --dir frontend test` ("Test Files" and "Tests" lines; per-file counts via `vitest run --reporter=json --outputFile=<file>`). `backend/tests/test_config_docs.py::test_testing_guide_states_the_real_test_counts` fails until `docs/TESTING_AND_QA.md` says `<N> deterministic` and `<M> backend tests` with the numbers pytest collects (`N/M tests collected (K deselected)`); the other count mentions (README, CONTRIBUTING, docs/README.md, SETUP_AND_CONFIG, the client guide, backend/README, frontend/README) are not tested, so grep for the old numbers. Test trees appear in `README.md`, `docs/TESTING_AND_QA.md` and the numbered module list there; update all three when adding a test module.
3. Edit every occurrence so docs do not contradict each other.
4. Match the existing tone; keep single hyphens (no em or en dashes) per project rule.

Always write links relative to the file they live in (e.g. `../docs/API.md`), never absolute `file://` links or `/Users/...` paths, so they work on other machines.
