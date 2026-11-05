---
name: mcat-verify
description: Run the full quality gate for the Question Bank Generator before declaring work done, committing, or opening a PR: ruff lint and format, pytest, oxlint, Vite build. Also use to run or write tests, diagnose failing tests, or interpret skipped DB tests. Trigger on "test this", "does it pass", "check everything", "ready to commit", or whenever you finish a code change here.
---

# Verification gate

This mirrors `.github/workflows/ci.yml`. Run only what the change touches while iterating, and everything before finishing.

```bash
ruff check backend/
ruff format --check .
PYTHONPATH=backend pytest backend/tests -m "not live_e2e"
pnpm lint
pnpm build
```
Shortcuts: `pnpm lint:backend`, `pnpm format`, `pnpm test`. Single test: `PYTHONPATH=backend pytest backend/tests/test_x.py -k name -x`.

## Reading results
- Tests marked `requires_db` (about 48 of the 143 offline-capable tests) skip when Postgres is down. Start it (`docker compose up -d`, see mcat-dev-env) to run them; otherwise say plainly that those tests were skipped, not passed.
- `live_e2e` tests need a running backend and paid LLM credentials; excluded by default (`addopts`). Do not run them unasked.
- pytest is async (`asyncio_mode = "auto"`, session-scoped loop), so write tests as plain `async def` with no decorator.
- CI sets DB env vars and provider defaults; locally `.env` supplies them, and `ACTIVE_LLM_PROVIDER=deepinfra` matches CI.

## Writing tests
Put them in `backend/tests/test_<area>.py`, reuse `conftest.py` fixtures, and prefer mocks from `agents/mock_fixtures.py` over network. Bug fixes get a regression test. Counts of tests and files quoted in docs drift; see mcat-docs-sync.

Fake the LLM with the `patch_llm` fixture from `tests/conftest.py` (it patches `app.agents.base.call_llm`). Tests that simulate an offline/no-credentials run must make it raise `LLMNotConfiguredError`; a generic exception now means a real provider failure and fails closed. Install dev tools with `pip install -r backend/requirements-dev.txt` (CI does the same).

Report failures with the actual output. Fix root causes rather than loosening assertions or adding ruff ignores.
