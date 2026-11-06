---
name: mcat-verify
description: Run the full quality gate for the Question Bank Generator before declaring work done, committing, or opening a PR: ruff lint and format, pytest, oxlint, Vite build. Also use to run or write tests, diagnose failing tests, or interpret skipped DB tests. Trigger on "test this", "does it pass", "check everything", "ready to commit", or whenever you finish a code change here.
---

# Verification gate

This mirrors `.github/workflows/ci.yml`. Run only what the change touches while iterating, and everything before finishing.

```bash
ruff check .
ruff format --check .
PYTHONPATH=backend pytest backend/tests -m "not live_e2e"
pnpm lint
pnpm test:frontend
pnpm --dir frontend run check:css
pnpm build
```
Shortcuts: `pnpm lint:backend`, `pnpm format`, `pnpm test`. Single test: `PYTHONPATH=backend pytest backend/tests/test_x.py -k name -x`.

## Reading results
- Tests marked `requires_db` (see docs/TESTING_AND_QA.md for the current counts) skip when Postgres is down. Start it (`docker compose up -d`, see mcat-dev-env) to run them; otherwise say plainly that those tests were skipped, not passed.
- `live_e2e` tests need a running backend and paid LLM credentials; excluded by default (`addopts`). Do not run them unasked.
- pytest is async (`asyncio_mode = "auto"`, session-scoped loop), so write tests as plain `async def` with no decorator (older files still carry a redundant `@pytest.mark.asyncio`; it is harmless).
- CI sets `DATABASE_URL` for its PostgreSQL service; locally `.env` supplies it. `conftest.py` strips provider keys and enables `OFFLINE_MODE`, so no env var is needed for determinism.

## Writing tests
Put them in `backend/tests/test_<area>.py`, reuse `conftest.py` fixtures and the builders in `tests/factories.py` (`make_draft`, `make_question`, `make_request`, `make_usage`, `make_completion`, `make_state`, `make_json_response`, `collect_events`; import with `from factories import ...`) instead of writing another `_draft`/`_question` helper, and prefer mocks from `agents/mock_fixtures.py` over network. Bug fixes get a regression test. Counts of tests and files quoted in docs drift; see mcat-docs-sync.

Fake the LLM with the `patch_llm` fixture from `tests/conftest.py` (it patches `app.agents.base.call_llm`, which every agent including the passage writer resolves at call time). Tests that simulate an offline/no-credentials run must make it raise `LLMNotConfiguredError`; a generic exception now means a real provider failure and fails closed. Install dev tools with `pip install -r backend/requirements-dev.txt` (CI does the same).

Report failures with the actual output. Fix root causes rather than loosening assertions or adding ruff ignores.
