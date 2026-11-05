# Installation, Setup & Configuration Guide

Engineered by **[Infynno Solutions LLP](https://infynno.com/)** (*"Infinite Innovations"*).

This guide provides complete instructions for provisioning, configuring, and operating the **Infynno MCAT Question Bank Generator v2.0** in both local development and production environments.

---

## 1. System Prerequisites

Before starting, ensure your system meets the following requirements:

| Tool | Minimum Version | Purpose |
| :--- | :--- | :--- |
| **Python** | `3.11+` | Backend runtime & FastAPI application |
| **Node.js** | `18.0+` (LTS) | Frontend runtime & Vite build engine |
| **pnpm** | `9.0+` | Fast, disk space efficient package manager |
| **Docker & Docker Compose** | `20.10+` / `v2+` | Containerized PostgreSQL 16 database |
| **Git** | `2.30+` | Version control |

---

## 2. Environment Variables Configuration

Create a `.env` file in the project root directory by copying `.env.example`:

```bash
cp .env.example .env
```

### Configuration Variables Reference

The system defines 53 configuration fields in `backend/app/core/config.py` (`Settings`). Key environment variables are configured via `.env`:

| Variable | Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `ACTIVE_LLM_PROVIDER` | `string` | `deepinfra` | Active inference provider: `deepinfra` or `anthropic` |
| `ANTHROPIC_MODEL` | `string` | `claude-haiku-5-5` | Primary Anthropic model identifier |
| `ANTHROPIC_COST_PER_MILLION_INPUT_TOKENS` | `float` | `0.10` | Input token price for Anthropic model ($0.10 / 1M) |
| `ANTHROPIC_COST_PER_MILLION_OUTPUT_TOKENS` | `float` | `0.50` | Output token price for Anthropic model ($0.50 / 1M) |
| `ANTHROPIC_API_KEY` | `string` | `""` | Anthropic API authorization key |
| `DEEPINFRA_MODEL` | `string` | `deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017` | Primary DeepInfra model identifier |
| `DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS` | `float` | `0.098` | Input token price for DeepInfra ($0.098 / 1M) |
| `DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS` | `float` | `0.294` | Output token price for DeepInfra ($0.294 / 1M) |
| `DATABASE_URL` | `string` | `postgresql+asyncpg://mcat_user:mcat_password@localhost:5432/mcat_db` | Async SQLAlchemy PostgreSQL connection string |
| `ACTIVE_IMAGE_PROVIDER` | `string` | `openai` | Image engine: `openai` or `deepinfra`. Note: the code default is `openai` while `.env.example` ships `deepinfra`; set it explicitly |
| `DEEPINFRA_IMAGE_MODEL` | `string` | `black-forest-labs/FLUX-2-klein-4b` | DeepInfra image model for visual stimuli |
| `DEEPINFRA_IMAGE_COST_PER_UNIT` | `float` | `0.014` | DeepInfra image price per 1024x1024 base unit |
| `OPENAI_API_KEY` | `string` | `""` | OpenAI API authorization key |
| `OPENAI_MODEL` | `string` | `gpt-4o-mini` | OpenAI text model |
| `OPENAI_COST_PER_MILLION_INPUT_TOKENS` | `float` | `0.15` | OpenAI input price per 1M tokens |
| `OPENAI_COST_PER_MILLION_OUTPUT_TOKENS` | `float` | `0.60` | OpenAI output price per 1M tokens |
| `OPENAI_IMAGE_MODEL` | `string` | `gpt-image-2.5-flare` | OpenAI image model |
| `OPENAI_IMAGE_COST_PER_UNIT` | `float` | `0.02` | OpenAI image price per 1024x1024 base unit |
| `DEEPINFRA_API_KEY` | `string` | `""` | DeepInfra API authorization key |
| `MAX_REGENERATION_ATTEMPTS`| `integer`| `3` | Maximum remediation loops before Quality Gate reject |
| `PASSING_SCORE_THRESHOLD` | `integer`| `90` | Minimum score required to pass individual psychometric gate (Tier 1) |
| `ALWAYS_INDEPENDENT_REVIEW` | `boolean` | `true` | Always run the independent Reviewer, even when the generator's own self-critique passes |
| `MAX_LLM_CALLS_PER_SLOT` | `integer` | `16` | Hard cap on LLM calls spent on one question slot across all attempts (drafts, duplicate rewrites, regenerations, review and solve samples). When reached the slot stops with a rejection instead of spending more; `0` disables the cap |
| `BLIND_SOLVER_MODEL` | `string` | `""` | Optional dedicated model for the Blind Solver so it is independent of the generator (empty = the request's model); the client's `api_key` is never sent to it |
| `BLIND_SOLVER_SAMPLES` | `integer` | `2` | Independent solver samples shown in different option layouts (reversed, rotated); a strict majority must pick the author's key, a split vote is never verified. `1` restores single-sample behavior |
| `OFFLINE_MODE` | `boolean` | `false` | Allow mock/heuristic fixtures when no LLM credentials are configured (demos, tests). When `false`, a missing key raises a clear configuration error and the run fails fast; mock-produced questions carry `stage_outcomes.offline_mode = true` |
| `PARALLEL_REVIEW_AND_SOLVE` | `boolean` | `false` | `false` (default): the Blind Solver runs only for drafts the Reviewer passes, so weak drafts cost no solver tokens. `true`: review and solve run concurrently, one LLM round trip faster per question but solver tokens are spent on drafts that then fail review |
| `ENABLE_PROMPT_CACHING` | `boolean` | `true` | Mark static system prompts cacheable for providers that need an explicit marker (Anthropic) |
| `ADMIN_API_KEY` | `string` | `""` | Optional secret for the full `/api/health` and `/api/config` payloads: the `x-admin-key` header must match it. When empty, nobody gets the full payload over HTTP (the masked one is always returned) |
| `API_ACCESS_KEY` | `string` | `""` | Optional shared secret for mutating API routes (`POST`/`PUT`/`PATCH`/`DELETE` need `X-API-Key`; reads and the duplicate pre-check stay open). Intended for deployments behind a gateway; a key built into the frontend via `VITE_API_ACCESS_KEY` is visible to browsers, so it is not a substitute for user authentication |
| `GENERATION_RATE_LIMIT_PER_MINUTE` | `integer` | `30` | Per-client-IP request budget per minute for the LLM-spending routes (`POST /api/generate`, `/batches/start`, `/batches/{id}/retry`, `/batches/{id}/refill`); `0` disables. In-process, which is correct for the single-worker deployment. Behind a proxy, run Uvicorn with `--proxy-headers` so the real client IP is used |
| `MAX_ACTIVE_BATCHES` | `integer` | `5` | Background batches allowed to run at once; further start/retry/refill requests get HTTP 429. `0` disables |
| `LOG_FORMAT` | `string` | `text` | `text` or `json`; lines carry batch, job, run and slot ids for correlation |
| `LLM_MAX_TOKENS_CEILING` | `integer` | `8000` | Upper bound when a truncated completion is retried with a larger token budget |
| `BATCH_PASSING_SCORE_THRESHOLD` | `integer`| `85` | Benchmark score required for batch activity run acceptance (Tier 2) |
| `DEFAULT_MAX_TOKENS` | `integer`| `3000` | Default maximum completion token budget for generator nodes |
| `REVIEWER_MAX_TOKENS` | `integer`| `1800` | Maximum completion token budget for 100-point psychometric reviewer |
| `COST_PER_MILLION_INPUT_TOKENS` | `float` | Dynamic | Dynamic property mapping to active provider input price ($0.098 DeepInfra / $0.10 Anthropic) |
| `COST_PER_MILLION_OUTPUT_TOKENS`| `float` | Dynamic | Dynamic property mapping to active provider output price ($0.294 DeepInfra / $0.50 Anthropic) |
| `DEFAULT_TEMPERATURE` | `float` | `0.2` | Global default sampling temperature for call_llm |
| `GENERATOR_TEMPERATURE` | `float` | `0.5` | Drafting temperature: enough variety that a batch on one subtopic does not converge on near-identical questions (invalid JSON is repaired once; low-temperature agents are unchanged) |
| `DUPLICATE_HARD_THRESHOLD` | `float` | `0.75` | Similarity at or above which a candidate counts as a duplicate (engine anti-collision, batch clustering and auto-resolve) |
| `DUPLICATE_SOFT_THRESHOLD` | `float` | `0.60` | Similarity at or above which a variety warning is emitted |
| `DUPLICATE_API_THRESHOLD` | `float` | `0.80` | Stricter threshold for the on-demand `POST /api/questions/check-duplicate` pre-check |
| `PASSAGE_TEMPERATURE` | `float` | `0.7` | Temperature for reading-passage generation (diversity across sets) |
| `REGENERATOR_TEMPERATURE` | `float` | `0.2` | Strict remediation temperature for Regenerator |
| `REVIEWER_TEMPERATURE` | `float` | `0.1` | Deterministic temperature for 100-pt Psychometric Reviewer |
| `BLIND_SOLVER_TEMPERATURE`| `float` | `0.1` | Ultra-deterministic temperature for Blind-Solver Agent |
| `FAST_MODEL_CASCADE` | `list[str]` | Dynamic | Dynamic property mapping to active provider fallback model list |
| `ENABLE_BLIND_SOLVER` | `boolean` | `true` | Enables dual-validation blind solver agent |
| `BLIND_SOLVER_CONFIDENCE_THRESHOLD` | `integer` | `88` | Minimum blind solver confidence percentage to pass without remediation |
| `BLIND_SOLVER_MAX_TOKENS` | `integer` | `1200` | Max completion tokens budget for blind-solver inference |
| `GLOBAL_MAX_CONCURRENT_PIPELINES` | `integer` | `8` | Process-wide cap on question pipelines in flight across all live runs and batches (replaces the old per-run limiter that multiplied concurrency) |
| `GLOBAL_MAX_CONCURRENT_JOBS` | `integer` | `4` | Global worker pool semaphore governing simultaneous batch jobs |
| `GLOBAL_MAX_CONCURRENT_LLM_CALLS` | `integer` | `10` | Global limiter for simultaneous outward inference calls |
| `LLM_MAX_RETRIES` | `integer` | `4` | Maximum exponential backoff retries on 429/503 errors |
| `LLM_BASE_BACKOFF_SECONDS` | `float` | `1.5` | Base backoff interval in seconds before retry |
| `WORKFLOW_MAX_WORKER_RETRIES` | `integer` | `2` | Per-worker retry attempts for individual question generation jobs within a batch |
| `DB_POOL_SIZE` | `integer` | `10` | Core persistent asyncpg database connections |
| `DB_MAX_OVERFLOW` | `integer` | `10` | Burst connection capacity beyond pool size. Keep `workers x (DB_POOL_SIZE + DB_MAX_OVERFLOW)` below Postgres `max_connections` (default 100) minus about 10 |
| `DB_POOL_TIMEOUT` | `integer` | `60` | Connection checkout timeout in seconds |
| `DB_POOL_RECYCLE` | `integer` | `1800` | Connection lifetime recycle in seconds (30 mins) |
| `ALLOWED_ORIGINS` | `list[str]` | `[]` | Additional CORS trusted origins (comma-separated in `.env`) |
| `IMAGE_WIDTH` | `integer` | `1024` | Default width for FLUX diagrams |
| `IMAGE_HEIGHT` | `integer` | `1024` | Default height for FLUX diagrams |
| `IMAGE_ITERS` | `integer` | `0` | Inference step iterations (0 for flat-rate models) |
| `IMAGE_COST_PER_BASE_UNIT` | `float` | `0.014` | Flat unit rate in USD ($0.014/img) |

> [!NOTE]
> `COST_PER_MILLION_INPUT_TOKENS`, `COST_PER_MILLION_OUTPUT_TOKENS`, and `FAST_MODEL_CASCADE` are dynamic `@property` getters and setters in `backend/app/core/config.py`. When unset, they automatically resolve to the active provider rates (`DEEPINFRA_*` or `ANTHROPIC_*`). Setters allow optional programmatic overrides during tests or custom runs.

---

## 3. Step-by-Step Installation

### Step 1: Start PostgreSQL Database (Docker)

Spin up the official PostgreSQL 16 container using the included `docker-compose.yml`:

```bash
docker compose up -d
```

Verify that the database container is healthy:
```bash
docker ps --filter "name=mcat_postgres"
```

*Expected output: Container `mcat_postgres` running on `0.0.0.0:5432->5432/tcp`.*

### Step 2: Backend Setup & Launch

```bash
# 1. Create a Python 3.11 virtual environment
python3 -m venv .venv

# 2. Activate the virtual environment
# macOS / Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# 3. Upgrade pip and install backend dependencies
pip install --upgrade pip
pip install -r backend/requirements-dev.txt

# 4. Launch the FastAPI server with hot-reload
PYTHONPATH=backend uvicorn app.main:app --port 8000 --reload
```

The backend initializes database tables automatically on startup (`init_db()`). Verify by opening:
- Health check: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- Interactive OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Step 3: Frontend Setup & Launch

In a new terminal window:

```bash
# 1. Install dependencies using pnpm
pnpm install

# 2. Start Vite development server
# Note: 'predev' hook automatically executes 'clean:ports' to kill any stale processes on ports 8000 and 5173
pnpm dev
```

Open **[http://localhost:5173](http://localhost:5173)** in your browser.

---

## 4. DeepInfra API Key Configuration

To enable live AI inference using DeepSeek V4.1 Flash 1017 on DeepInfra:

1. Sign up and obtain an API key from [deepinfra.com/dash/api_keys](https://deepinfra.com/dash/api_keys).
2. Set `DEEPINFRA_API_KEY=your_key_here` in your server `.env` file and restart the backend. API credentials are encrypted/isolated exclusively on the backend server for zero client-side credential exposure.

### Graceful Mock Fallback Mode
If no API key is provided, the backend automatically engages the **Authentic Mock Heuristic Engine**. This allows complete offline testing, local frontend development, and automated test execution without incurring token costs or requiring an internet connection.

---

## 5. Running Quality Verification & Automated Tests

The repository maintains an uncompromising **Zero-Defect Quality Policy** enforced across both backend and frontend layers.

### 5.1 Backend Verification Suite

Run the complete 229-test backend verification suite across 46 modules using `pytest` (see [`docs/TESTING_AND_QA.md`](TESTING_AND_QA.md) for full test specifications):

```bash
source .venv/bin/activate

# 1. Run all 219 deterministic unit and integration tests across 45 modules
# Smart auto-skip: If PostgreSQL is offline on localhost:5432, 159 pure unit tests pass and 60 DB tests skip cleanly
# The test suite is offline by default: tests/conftest.py strips API keys and enables
# OFFLINE_MODE, so no live LLM is ever called without `-m live_e2e`
PYTHONPATH=backend pytest backend/tests -v -m "not live_e2e"

# Or run via root package.json
pnpm run test

# 2. Run Python linting and code quality checks (enforces SIM, RET, B, C4, E, W, F, I, UP)
ruff check backend/
ruff format --check .
```

#### Dual Test Execution Modes
- **Offline Mode** (PostgreSQL offline): Executes all 55 algorithmic, schema, agent, taxonomy sync, and mathematical tests in ~12 seconds (`55 passed, 42 skipped, 10 deselected`).
- **Full Database Mode** (PostgreSQL online via Docker): Executes all 219 deterministic tests across 45 modules in ~23-28 seconds (10 live tests deselected).
- **Live E2E Mode** (Live LLM gateways active): Executes all 10 live integration tests in `test_e2e_live.py` (`10 passed`).
- **Total Backend Suite**: 229 tests across 46 test files.

This verifies:
- Multi-provider configuration switching (`ACTIVE_LLM_PROVIDER`), Anthropic Claude models, and prompt cache pricing.
- Autonomous 3-trials retry policy, trial count persistence, and HTTP 400 enforcement upon trial exhaustion.
- Set-preserving hard-delete duplicate resolution (`action="delete"`) and completion guards.
- Soft-deletion and restoration mechanics (`POST /api/questions/{id}/restore`) preserving batch review counts and integrity.
- Server-side question pagination (`limit`, `offset`) and lightweight projection (`slim=True`).
- Pydantic schema validation across all 4 official AAMC MCAT sections and custom authoring instructions.
- Reviewer 100-point rubric evaluation and remediation routing logic.
- Blind-Solver dual-validation agent agreement and discrepancy re-routing.
- Strict Quality Gate halt and rejection payload generation when score $\le 90$.
- Batch question withholding (`batch_only` during execution) and atomic promotion (`promote_completed_batch_questions`).
- Global worker pool semaphores, LLM rate-limiting backoff, and multi-batch concurrency.
- Programmatic SVG vector diagram rendering and XML validation.
- PostgreSQL 16 CRUD persistence, native JSONB columns, and B-Tree indexes.
- Dynamic job allocation in background batches and exact target count replenishment.
- Deterministic token cost calculation and multi-agent state accumulation.

#### Live Multi-Agent E2E Verification
To verify live inference, streaming SSE events, and manager matrix combinations with active LLM gateways:
```bash
PYTHONPATH=backend pytest backend/tests/test_e2e_live.py -v -m live_e2e
```

### 5.2 Browser End-to-End Automated Testing (TestSprite TC001–TC015)
The application includes 15 automated Playwright E2E browser tests covering guided wizard creation, SSE telemetry streaming, cancellation, staged approval, inline editing, batch approval, audit trail inspection, tab switching, and question bank management. All 15 tests pass with 100% success rate. See [`docs/TESTING_AND_QA.md`](TESTING_AND_QA.md) for the full test matrix and instructions.

### 5.3 Frontend Quality & Production Verification

```bash
# 1. High-speed Oxlint check across 90 frontend files (Zero warnings, zero errors required)
pnpm --dir frontend lint

# 2. Compile optimized production bundle with Vite (builds in ~218ms)
pnpm --dir frontend build
```

---

### 5.4 Database Maintenance & Seeding Utilities

#### 1. Clean Discarded Duplicate Question Artifacts
To permanently purge existing discarded duplicate questions and clean up test remnants from PostgreSQL:
```bash
# Run via root pnpm script
pnpm run db:clean-duplicates

# Or directly via Python
PYTHONPATH=backend ./.venv/bin/python scripts/clean_duplicate_artifacts.py
```

#### 2. Seed Mock Practice Questions
To ensure a clean, deterministic state upon initial development startup, auto-seeding mock questions on server launch is disabled by default.

To explicitly populate the database with authentic, high-quality MCAT practice questions across all 4 sections (complete with rubrics and evolution histories):

```bash
source .venv/bin/activate
python backend/scripts/seed_questions.py
```

---

## 6. Production Deployment Guidelines

### 6.1 Production Backend (single worker)
Run **one** Uvicorn worker. The batch task registry, in-flight draft pool, LLM semaphores and the startup reconcile of interrupted batches all live in process memory, so several workers would each run their own copy and disagree (duplicate collision checks, double-resumed batches). Scale by raising the per-process limits (`GLOBAL_MAX_CONCURRENT_LLM_CALLS`, `DB_POOL_SIZE`) rather than the worker count.

```bash
PYTHONPATH=backend uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 \
  --workers 1 \
  --timeout-graceful-shutdown 25
```
Keep the graceful timeout at 20 seconds or more so running batches can checkpoint on shutdown. Multi-worker support would need DB-backed batch ownership and heartbeats; it is not implemented.

### 6.1.1 Docker (backend + nginx web)
`docker-compose.yml` defines an optional `app` profile next to the default Postgres service:

```bash
docker compose --profile app up -d --build   # postgres + backend + web
# open http://127.0.0.1:8080
```
- `backend/Dockerfile`: multi-stage `python:3.11-slim`, non-root user, one Uvicorn worker, healthcheck on `/api/health/ready`. Build context is the repository root.
- `frontend/Dockerfile` + `frontend/nginx.conf`: Vite build served by nginx with SPA fallback, gzip, immutable caching for `/assets/`, and an `/api/` proxy with `proxy_buffering off` and a 1 hour read timeout so SSE generation streams arrive live.
- Settings come from `.env` (optional); `DATABASE_URL` is overridden to the compose `postgres` service. Postgres stays bound to loopback and the web port to `127.0.0.1:8080`; put a TLS-terminating proxy in front for anything shared.
- `docker compose up -d` (no profile) still starts only Postgres, which is what local development and CI tests use.

### 6.2 Production Frontend Build
Compile static production assets with Vite using pnpm:

```bash
pnpm build
```
This outputs optimized static bundles into `frontend/dist/`, which can be served via Nginx, Cloudflare Pages, AWS S3 / CloudFront, or Vercel.

### 6.3 Managed Cloud PostgreSQL
To connect to a managed cloud database (Neon, Supabase, AWS RDS, GCP Cloud SQL):
Update `DATABASE_URL` in `.env` to use the `postgresql+asyncpg://` protocol:

```env
DATABASE_URL=postgresql+asyncpg://<USER>:<PASSWORD>@<HOST>:<PORT>/<DATABASE>?ssl=require
```

---

## 7. Troubleshooting & FAQ

### Database connection error (`connection refused` on port 5432)
- **Check Docker status**: Run `docker ps` to verify container `mcat_postgres` is running.
- **Port Conflict**: If local PostgreSQL is already running on port 5432, stop local postgres (`brew services stop postgresql` or `sudo systemctl stop postgresql`) or edit `docker-compose.yml` to bind to port `5433:5432` and update `DATABASE_URL` accordingly.

### `ValueError: DeepInfra API Key is required`
- The system strictly validates API keys when sending live requests to `deepinfra/*` models. All credentials must be securely supplied in the server `.env` file (`DEEPINFRA_API_KEY="..."`). For security isolation, client-side runtime key entry has been deprecated.

### CORS Errors in Browser Console
- If hosting the backend and frontend on separate domains, ensure the FastAPI `CORSMiddleware` in [`backend/app/main.py`](../backend/app/main.py#L20-L28) includes your frontend domain in `allow_origins`.
