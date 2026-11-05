---
name: mcat-backend
description: Conventions and step-by-step recipes for changing the Python/FastAPI backend of the Question Bank Generator: adding or modifying API endpoints, Pydantic schemas, SQLAlchemy models, repositories, services, batch runner behavior, soft-delete, dedup, DB constraints. Use for any work under backend/app (api, models, repositories, schemas, services, db, core), even if the user only says "add an endpoint", "add a field to questions", or "fix the batch bug".
---

# Backend conventions

Layering is strict. Each layer only calls downward:

`api/v1/*` (HTTP only) -> `services/` and `workflow/` (orchestration) -> `agents/` (LLM calls) and `repositories/` (all DB access) -> `models/` (SQLAlchemy) ; `schemas/` (Pydantic) is shared.

Routers contain no SQL and no business logic. Repositories own every query and convert models to schemas (see `_batch_model_to_schema` in `repositories/batch_repository.py` for the pattern). This keeps tests and the batch runner reusing one data path.

## Style rules (enforced by ruff, config in pyproject.toml)
- Every module starts with `from __future__ import annotations`.
- Python 3.11 idioms (`UTC`, `X | None`), double quotes, line length 100, ruff rules E W F I UP B C4 SIM RET. Run `ruff check backend/` and `ruff format .`.
- Async everywhere for DB/LLM; use `async_session_factory` from `app.db.session`.
- Keep `(str, Enum)` style for pydantic-serialized enums (UP042 is intentionally ignored).
- Docstrings on public functions; use `logging.getLogger(__name__)`, not print.

## Recipe: add or change an endpoint
1. Schema in `schemas/` (request/response). Re-export in `schemas/__init__.py` if siblings do.
2. Repository function in `repositories/` (async, takes/creates a session, returns schemas).
3. Router in `api/v1/<area>.py`; if a new file, register it in `api/v1/__init__.py` (routes mount under `/api`).
4. Test in the matching `backend/tests/test_api_*.py` module (questions, generation, duplicates/passages/health, security) or a focused one; use the `httpx.AsyncClient` + `ASGITransport` fixtures in `conftest.py`.
5. Update `docs/API.md` (see mcat-docs-sync).

## Recipe: add or change a DB column / status
- Edit the model in `models/`; question `status` is guarded by a CHECK constraint `ck_questions_status` listing allowed values, so adding a status means updating that constraint and any migration path in `db/init_db.py`, plus `tests/test_database_structure.py`.
- There is no Alembic: `db/init_db.py` runs `Base.metadata.create_all` plus idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements for existing databases. Add a matching ALTER there for every new column, or existing DBs will break.
- Add indexes deliberately (see `ix_questions_status_*` examples).

## Behavioral invariants that tests protect
- Soft delete: delete sets `is_deleted = true` and must NOT decrement a batch's `actual_count`; restore via `POST /api/questions/{id}/restore`; soft-deleting a passage cascades to its questions.
- Batch questions stay `batch_only` until the batch completes, then items scoring above 90 are atomically promoted to `ai_validated`. Never let in-progress questions reach the review queue.
- Autonomous retry: at most 3 trials per set; manual retry returns HTTP 400 once exhausted.
- Global job concurrency is bounded by semaphores in `services/batch_concurrency.py`; do not spawn unbounded LLM tasks. The global LLM semaphore is held only during the API call in `agents/base.py`.
- Startup/shutdown: `main.py` lifespan stops batches gracefully and disposes the engine; `reconcile_interrupted_batches` stops orphaned batches and marks their `pending`/`running` jobs `stopped` (still retryable).
- `update_job_progress` treats `None` as "unchanged"; pass `clear=("error_message", ...)` to reset a field to NULL.
- Security: never persist or return `api_key` (`batch_repository._scrub_request_payload`); optional `API_ACCESS_KEY` gate lives in `api/security.py`; keep new text inputs length-limited in `schemas/workflow.py`.
- Repositories: use `repositories/_filters.py` (`active_question_clause`, `active_passage_clause`) for soft-delete filtering instead of retyping `is_deleted.is_(False)`. Model prices and fallbacks live in `core/pricing.py` (tables) with `Settings.get_default_pricing_rates` as the thin dispatcher.
- DB writes: batch aggregates refresh under a `FOR NO KEY UPDATE` row lock; do not use plain `FOR UPDATE` (deadlocks with the key-share lock of question inserts). New migrations are ordered steps in `db/init_db.py` (`_SCHEMA_STEPS` run through the lock-avoiding connection, `_DATA_STEPS` in a second transaction); add a `_step_*` function and register it in the tuple (DDL that already exists is skipped; never add unconditional DDL that locks tables on every start).
- Health: `/api/health` (liveness, `degraded` without DB) and `/api/health/ready` (503 without DB); `ADMIN_API_KEY` gates the full payload.
- Logging: bind correlation ids with `bind_log_context(batch_id=..., job_id=...)` from `app.core.logging`; set `LOG_FORMAT=json` for structured output.
- Dedup lives in `services/deduplication.py`; reuse it, do not re-implement similarity checks.

Before finishing, run the mcat-verify skill.
