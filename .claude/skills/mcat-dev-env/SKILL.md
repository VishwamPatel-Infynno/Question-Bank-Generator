---
name: mcat-dev-env
description: Start, stop, set up or debug the local Question Bank Generator environment (FastAPI backend on :8000, Vite frontend on :5173, PostgreSQL 16 via Docker, .venv, pnpm, .env). Use whenever the user wants to run the app, see a change working, fix "port already in use", DB connection errors, missing env vars, install dependencies, switch LLM provider (deepinfra/anthropic/openai), or clean duplicate DB artifacts, even if they just say "run it" or "it won't start".
---

# Local environment

Monorepo: `backend/` (FastAPI, Python 3.11+, async SQLAlchemy + asyncpg), `frontend/` (React 19 + Vite 8, pnpm workspace), PostgreSQL 16 in Docker.

## Start everything
```bash
docker compose up -d     # Postgres on :5432 (mcat_user / mcat_password / mcat_db)
pnpm dev                 # predev frees :8000 and :5173, then runs backend + frontend together
```
`pnpm dev:backend` / `pnpm dev:frontend` run each side alone. The backend command is `PYTHONPATH=backend ./.venv/bin/uvicorn app.main:app --port 8000 --reload`; `PYTHONPATH=backend` is required because imports are `from app...`.

## First-time setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp .env.example .env     # then fill provider keys
pnpm install
```

## Config
- All settings live in `backend/app/core/config.py` (pydantic settings read from `.env`); `.env.example` documents every key. Add new settings in both places.
- `ACTIVE_LLM_PROVIDER` selects `deepinfra` (default), `anthropic` or `openai`; model names and per-million-token prices resolve from it via properties on `config`. Never hardcode prices or model ids in feature code.
- Never print or commit `.env` contents or API keys.

## Troubleshooting
- Port busy: `pnpm run clean:ports`.
- DB refused or auth failure: `docker compose ps`; confirm `DATABASE_URL` is `postgresql+asyncpg://...`. DB-backed tests skip themselves when Postgres is unreachable, so a "passing" run without Docker does not exercise them.
- Duplicate questions or passages in the DB: `pnpm run db:clean-duplicates` (script `scripts/clean_duplicate_artifacts.py`). This mutates data, so confirm with the user first.
- Seed data: `backend/scripts/seed_questions.py`.
- Frontend calls `/api/...`, so check the Vite proxy rather than hardcoding a backend host.

To verify a UI change in the running app, use the built-in browser against http://localhost:5173 after `pnpm dev`.
