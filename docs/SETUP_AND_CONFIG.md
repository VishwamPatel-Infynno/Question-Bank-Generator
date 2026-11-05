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
| `DEFAULT_IMAGE_MODEL` | `string` | `black-forest-labs/FLUX-2-klein-4b` | Image model for visual stimuli |
| `DEEPINFRA_API_KEY` | `string` | `""` | DeepInfra API authorization key |
| `MAX_REGENERATION_ATTEMPTS`| `integer`| `3` | Maximum remediation loops before Quality Gate reject |
| `PASSING_SCORE_THRESHOLD` | `integer`| `90` | Minimum score required to pass individual psychometric gate (Tier 1) |
| `ALWAYS_INDEPENDENT_REVIEW` | `boolean` | `true` | Always run the independent Reviewer, even when the generator's own self-critique passes |
| `PARALLEL_REVIEW_AND_SOLVE` | `boolean` | `true` | Run the Reviewer and Blind Solver concurrently, saving one LLM round trip per question |
| `ENABLE_PROMPT_CACHING` | `boolean` | `true` | Mark static system prompts cacheable for providers that need an explicit marker (Anthropic) |
| `ADMIN_API_KEY` | `string` | `""` | Optional secret for the full `/api/health` diagnostic payload; when set, the `x-admin-key` header must match it |
| `LOG_FORMAT` | `string` | `text` | `text` or `json`; lines carry batch, job, run and slot ids for correlation |
| `LLM_MAX_TOKENS_CEILING` | `integer` | `8000` | Upper bound when a truncated completion is retried with a larger token budget |
| `BATCH_PASSING_SCORE_THRESHOLD` | `integer`| `85` | Benchmark score required for batch activity run acceptance (Tier 2) |
| `DEFAULT_MAX_TOKENS` | `integer`| `3000` | Default maximum completion token budget for generator nodes |
| `REVIEWER_MAX_TOKENS` | `integer`| `1800` | Maximum completion token budget for 100-point psychometric reviewer |
| `COST_PER_MILLION_INPUT_TOKENS` | `float` | Dynamic | Dynamic property mapping to active provider input price ($0.098 DeepInfra / $0.10 Anthropic) |
| `COST_PER_MILLION_OUTPUT_TOKENS`| `float` | Dynamic | Dynamic property mapping to active provider output price ($0.294 DeepInfra / $0.50 Anthropic) |
| `DEFAULT_TEMPERATURE` | `float` | `0.2` | Global default sampling temperature for call_llm |
| `GENERATOR_TEMPERATURE` | `float` | `0.2` | Strict instruction-following temperature for Generator |
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
| `DB_POOL_SIZE` | `integer` | `20` | Core persistent asyncpg database connections |
| `DB_MAX_OVERFLOW` | `integer` | `30` | Burst connection capacity beyond pool size |
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

Run the complete 153-test backend verification suite across 28 modules using `pytest` (see [`docs/TESTING_AND_QA.md`](TESTING_AND_QA.md) for full test specifications):

```bash
source .venv/bin/activate

# 1. Run all 143 deterministic unit and integration tests across 28 modules
# Smart auto-skip: If PostgreSQL is offline on localhost:5432, 55 pure unit tests pass and 42 DB tests skip cleanly
# Note: ACTIVE_LLM_PROVIDER=deepinfra ensures deterministic offline mocking without calling live external LLMs
ACTIVE_LLM_PROVIDER=deepinfra pytest backend/tests -v -m "not live_e2e"

# Or run via root package.json
pnpm run test

# 2. Run Python linting and code quality checks (enforces SIM, RET, B, C4, E, W, F, I, UP)
ruff check backend/
ruff format --check .
```

#### Dual Test Execution Modes
- **Offline Mode** (PostgreSQL offline): Executes all 55 algorithmic, schema, agent, taxonomy sync, and mathematical tests in ~12 seconds (`55 passed, 42 skipped, 10 deselected`).
- **Full Database Mode** (PostgreSQL online via Docker): Executes all 143 deterministic tests across 28 modules in ~23-28 seconds (10 live tests deselected).
- **Live E2E Mode** (Live LLM gateways active): Executes all 10 live integration tests in `test_e2e_live.py` (`10 passed`).
- **Total Backend Suite**: 153 tests across 29 test files.

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

### 6.1 Production Backend (Gunicorn + Uvicorn)
In production, use `gunicorn` with multiple `uvicorn.workers.UvicornWorker` workers:

```bash
pip install gunicorn
PYTHONPATH=backend gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

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
