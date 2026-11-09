# Infynno MCAT Question Bank Generator v2.0
> **An Infynno Solutions LLP Product • [Infinite Innovations](https://infynno.com/)**

[![CI Pipeline](https://github.com/VishwamPatel-Infynno/MCAT-Question-Bank-Generator/actions/workflows/ci.yml/badge.svg)](https://github.com/VishwamPatel-Infynno/MCAT-Question-Bank-Generator/actions/workflows/ci.yml)

An enterprise autonomous AI application for generating, quality-reviewing, and creating high-quality exam questions for the official **AAMC MCAT** (Medical College Admission Test).

Engineered by **[Infynno Solutions LLP](https://infynno.com/)**, powered by a **3-Step AI Pipeline**, **FastAPI**, **React 19**, and **PostgreSQL 16**, featuring a modern single-canvas studio, live team tracker, batch staging, AAMC SIRS reasoning skills, calibrated scaled scoring (118–132 per section / 472–528 composite), and strict 90+ score quality standard.

---

## 📚 Comprehensive Documentation Suite

For deep-dive technical specifications, architecture diagrams, API schemas, and authoring guidelines, consult the dedicated guides in the [`docs/`](docs/) directory and repository root:

| Document | Description |
| :--- | :--- |
| **[Central Documentation Hub (docs/README.md)](docs/README.md)** | **Master Documentation Index**: Complete sitemap, role-based navigation paths, architectural overview, and cross-functional guide directory. |
| **[Client System & Workflow Guide (docs/CLIENT_SYSTEM_AND_WORKFLOW_GUIDE.md)](docs/CLIENT_SYSTEM_AND_WORKFLOW_GUIDE.md)** | **Primary Client Deliverable**: End-to-end operational walkthrough, 3-step wizard, 2 calibrated generation scopes (5 Questions [1 Job] and 50 Questions [10 Jobs]), Low/Medium/High difficulty tiers, Blind-Solver safeguard, Deduplication & Editorial Override workflow, AAMC Split-Pane reading mode, canonical Editorial Cards Question Bank, mentor explanations, and token transparency. |
| **[UI/UX Design System (DESIGN.md)](DESIGN.md)** | Authoritative design tokens, dual obsidian/alabaster themes, streamlined 3-step wizard with decomposed summary/advanced drawers, decomposed QuestionCard components, Duplicate Comparison Modal, AAMC Dual Split-Pane reading mode, accessible modal focus-trapping contracts (`Modal`, `ConfirmationModal`, `DeletePassageModal`), live batch retry telemetry (`AUTO-RETRYING X/3`), typography scale, component contracts, accessibility criteria (WCAG AA), and micro-animations. |
| **[Architecture & Multi-Agent Workflow](docs/ARCHITECTURE.md)** | Complete workflow diagrams, 3-step pipeline specifications, Blind-Solver Dual Validation, Deduplication & Anti-Collision Subsystem, Strict Quality Gate, Two-Tier quality threshold model, global worker semaphores, background batch runner with 3-trial retries, SSE pipeline, and PostgreSQL 16 ERD. |
| **[REST & SSE API Reference](docs/API.md)** | Complete FastAPI endpoint documentation (39 endpoint operations), deduplication, duplicate clustering, auto-resolve & refill endpoints, question restoration (`/restore`), permanent purges (`/permanent`, `/purge-batch`), batch generation schemas, 3-trial batch controls (`/stop`, `/retry`, `/cancel-all`), SSE event stream contracts, filter parameters, and cURL examples. |
| **[Testing & Quality Assurance Guide](docs/TESTING_AND_QA.md)** | Complete test specifications for the 353 passing deterministic unit/integration tests across 55 modules (363 total backend tests), 15 TestSprite-generated Playwright E2E scripts in `e2e/` (run manually, not in CI), Ruff & Oxlint code hygiene standards, and CI pipeline. |
| **[Token Usage & Cost Tracking](docs/TOKEN_TRACKING.md)** | Verified rate cards per model: DeepInfra DeepSeek ($0.20 in / $0.60 out per 1M tokens standard), Anthropic Claude Haiku 5.5 ($0.10 in / $0.50 out with tiers and prompt-cache rates), OpenAI gpt-4o-mini, and token-billed gpt-image-2.5-flare images, exact mathematical cost formulas, multi-agent accumulation, and UI observability. |
| **[Installation, Setup & Deployment](docs/SETUP_AND_CONFIG.md)** | Step-by-step setup, Docker PostgreSQL 16 guide, environment variables reference (67 Settings fields), database duplicate cleanup (`pnpm run db:clean-duplicates`), predev port cleanup, production deployment, linters, and troubleshooting. |
| **[MCAT Psychometric Rubric & Standards](docs/MCAT_RUBRIC.md)** | Official 4 AAMC sections standards, 100-point 4-pillar evaluation rubric, Blind-Solver algorithmic verification, $> 90$ quality benchmark, calibrated scaled score (118-132), and cognitive distractor trap engineering. |
| **[Backend Developer Guide](backend/README.md)** | Layer separation, modular workflow engine (`engine.py`, `review_loop.py`, `passage_prep.py`, `dedup_inflight.py`, `live_job_store.py`, `nodes.py`), Blind-Solver agent, services, repositories, 3-trial retry engine, testing (363 tests across 56 modules: 353 offline-capable, 10 live), and seeding scripts. |
| **[Frontend Workstation Guide](frontend/README.md)** | Modern React 19 architecture, decomposed component directory (`wizard/`, `question/`, `batch/`, `modals/`, `common/`), top-level views, hooks, predev port cleaner, and local development instructions. |

---

## 🚀 Key System Capabilities

### 1. Fused Cognitive Architecture with Strict Quality Gate
```mermaid
graph LR
    FusedGen[Fused Draft & Self-Critique] -->|Score > 90 (~40% Faster)| ImageGen[Stimulus & Diagram]
    FusedGen -->|Score > 90 & Text Only| Finalize[Admin Review Desk]
    FusedGen -->|Score <= 90| Regenerator[Remediation Engine]
    Regenerator --> Reviewer[Independent Auditor]
    Reviewer -->|Score <= 90 & Cycles < 3| Regenerator
    Reviewer -->|Score <= 90 & Cycles = 3| Reject[Strict Quality Gate Reject]
    Reviewer -->|Score > 90| ImageGen
    Reviewer -->|Score > 90 & Text Only| Finalize
    ImageGen --> Finalize
```
- **Fused Draft-and-Critique Cognitive Engine (`generator.py` / `fused_generator_node`)**: Merges item authoring and 100-point psychometric self-critique into a single unified inference round-trip, combining drafting and self-critique in one inference round-trip; the independent reviewer and blind solver still audit every draft by default (`ALWAYS_INDEPENDENT_REVIEW`).
- **Option Symmetry & Anti-Guessability Engine**: Mathematically balances option lengths (within 3 words of each other, or 20% of the average for longer options (`agents/standards.py`)) and enforces parallel grammatical syntax so students cannot guess the answer using "longest option" cues.
- **Anti-AI Formatting Standard**: Strictly forbids em dashes (`—`), en dashes (`–`), or double hyphens (`--`); enforces standard single hyphens (`-`) for human editorial authenticity.
- **3-Part Structured Mentor Explanations (`MentorExplanationView.jsx`)**: Renders pedagogical explanations across three specialized visual cards:
  - **Card 1: Why Option [Key] is Correct** (Emerald / Success styling): Establishes the core intuition and step-by-step deductive or mathematical proof confirming why the correct key is incontrovertible.
  - **Card 2: Why Other Options are Incorrect** (Amber / Warning styling): Features individual itemized sub-cards for every incorrect distractor, dissecting the exact flaw, tempting misconception, and disqualifying factor.
  - **Card 3: Primary Cognitive Trap Spotlight** (Purple / Violet styling): Highlights the dominant cognitive failure mode, explaining the precise psychological error mechanism and providing a student defense strategy to neutralize the trap under real exam conditions.
- **Automatic (Smart AI Choice) Cognitive Trap Engine**: Supports 8 curated AAMC MCAT cognitive trap categories (`Out_of_Scope`, `Distortion_Opposite`, `Outside_Knowledge_in_CARS`, `Extreme_Language`, `Correlation_vs_Causation`, `Calculation_Formula_Trap`, `Half_Right_False_Premise`, `Scope_Shift`) alongside a default `"Automatic"` mode. In Smart AI mode, the generator agent analyzes the scientific research study or CARS passage, options, and distractors to intelligently select the most fitting trap, which is tracked in `primary_trap`, saved to PostgreSQL, and displayed as a top-strip purple badge chip on candidate cards and repository views.
- **AAMC Scaled Score Calibration Engine**: Automatically calibrates internal 100-point psychometric audit scores into official AAMC scaled scores (`118–132` section scale, `472–528` composite scale) and percentile ranks (`99th+ Percentile (Elite)` down to `50th Percentile`).
- **AAMC Scientific Inquiry & Reasoning Skills (SIRS)**: Integrates official AAMC SIRS skills (Skill 1: Knowledge of Scientific Concepts, Skill 2: Scientific Reasoning and Problem-solving, Skill 3: Reasoning About Design and Execution of Research, Skill 4: Data-based and Statistical Reasoning) and CARS Reasoning Skills (Foundations of Comprehension, Reasoning Within the Text, Reasoning Beyond the Text).
- **Independent Psychometric Auditor (`reviewer.py`)**: Independently audits candidate items whenever the initial draft scores $\le 90$ or after remediation across 4 equal 25-point pillars (*Authenticity & Tone*, *Clarity & Scientific Logic*, *Distractor Traps*, *Explanation & Key Accuracy*).
- **Remediation Engine Agent (`regenerator.py`)**: Automatically triggered when score $\le 90$. Digests the exact weaknesses and recommendations to repair borderline distractors and expand step-by-step proofs up to 3 iterations.
- **Strict Quality Gate**: If a question fails to score $> 90$ after reaching maximum attempts (`MAX_REGENERATION_ATTEMPTS = 3`), the workflow halts immediately. Bypasses image generation and discards the candidate to protect repository integrity.
- **Stimulus & Diagram Agent (`image_generator.py`)**: Renders clean programmatic SVG vector diagrams for metabolic pathways, reaction mechanisms, optics, and experimental charts, with fallback support for AI visual generators (strictly disabled for CARS).

### 2. Dual First-Class AI Inference & Precision Cost Accounting
- **Inference Engines**: Multi-provider support switchable via `ACTIVE_LLM_PROVIDER`:
  - **DeepInfra**: DeepSeek-V4.1-Flash-1017 High-Throughput Reasoning Engine ($0.20 input / $0.60 output per 1M tokens, standard price) + FLUX-2-klein-4b visual stimuli ($0.014/unit).
  - **Anthropic**: Claude Haiku 5.5 ($0.10 input / $0.50 output per 1M tokens), Claude 3.5 Sonnet, and Claude 3 Opus with native prompt cache read/write rates.
- **Micro-Dollar Tracking**: Every request computes exact USD costs rounded to 7 decimal places:
  $$\text{Cost (USD)} = \left(\frac{\text{Prompt Tokens}}{1,000,000} \times R_{\text{in}}\right) + \left(\frac{\text{Completion Tokens}}{1,000,000} \times R_{\text{out}}\right) + \text{Cache Costs}$$
- **Granular Observability**:
  - Live 4-milestone pipeline visualizer with active stopwatch, everyday status indicators (*Passed quality check*, *No figure needed*), and collapsible event log tray.
  - QuestionCard badges displaying total tokens and cost.
  - Psychometric Review Audit Modal itemized table showing prompt tokens, completion tokens, and cost per agent cycle.
  - Question Bank metrics strip tracking accumulated repository-wide tokens and total expenditure.

### 3. Production PostgreSQL 16 Tier (SQLAlchemy Async + asyncpg)
- **Native JSONB Columns**: Stores options, review rubrics, evolution histories, and granular per-agent token tracking.
- **UUID4 Traceability**: Automatic UUID4 generation for every question (`id`), execution run (`run_id`), batch set (`batch_id`), and combination matrix (`combination_id`).
- **Docker Compose Setup**: Instant container initialization on port `5432` with pre-ping connection pooling.
- **Zero-Downtime Auto-Migration**: Automatically runs non-destructive schema migrations and full-text search indexing on startup.

### 4. Modern Enterprise Minimalist UI (Dual Theme: Dark & Light)
- **Linear/Vercel-Inspired Aesthetic**: Hairline borders (`rgba(255, 255, 255, 0.06)` dark / `#e8ecf2` light), quiet obsidian and alabaster surfaces, and zero multi-card clutter.
- **Hero Landing Screen (`HeroLanding.jsx`)**: Minimalist welcome canvas presenting official AAMC MCAT sections and instant practice presets.
- **3-Step Guided Question Wizard (`GuidedWizard.jsx`)**: Streamlined step-by-step authoring workflow supporting 2 calibrated generation scopes (**5 Questions** [1 Single Job] and **50 Questions** [10-Job Batch]), 3 calibrated difficulty tiers (**Low**, **Medium**, **High**), interactive syllabus navigation, and a compact review summary table with collapsible advanced settings accordion.
- **Dedicated Generation & Review Workspace**: Clean, distraction-free full-width canvas (`maxWidth: 1040px`) hosting live multi-agent synthesis, telemetry, and batch staging without cramped column docks.
- **Editorial Question Presentation**: Scientific research passages and CARS essays formatted in serif typography with line-height `1.68` for fatigue-free reading; circular option badges (`A`, `B`, `C`, `D`), canonical Question Bank Editorial Cards view (legacy grid mode removed), top metadata strip with purple primary trap badge chips, AAMC Scaled Score and SIRS badges, 3-card structured mentor explanations (*Why Correct*, *Why Other Options Incorrect* with itemized distractor cards, and *Primary Cognitive Trap Spotlight*), and inline editing.
- **Instant Theme Switching**: Seamless toggle between Dark and Light themes with WCAG AA compliance via the `T` key shortcut.
- **Full Keyboard Navigation**: `⌘ + Enter` (Generate), `T` (Theme), `/` (Search Bank), `A` (Approve), `D` (Discard), `Escape` (Close Modals).

### 5. Professional Export & Print Studio (`ExportPrintModal.jsx`)
- **Official Exam Booklet (PDF / Print)**: Generates classroom and mock test papers with candidate metadata headers, section specifications, and `.page-break` rules preventing awkward splits across pages.
- **Comprehensive Study Pack**: Pairs every research or CARS stimulus with its question stem, correct key, and complete step-by-step cognitive proof rationales.
- **Direct Data Exports**: Download the entire repository or filtered subsets as standardized CSV files (`mcat_question_bank.csv`) or normalized JSON bundles (`mcat_question_bank.json`).

### 6. Question Deduplication, Collision Avoidance & Editorial Override
- **Multi-Metric Mathematical Similarity**: Hybrid algorithm combining Token Containment (35%), 1-Gram Jaccard (25%), 2-Gram Jaccard (20%), and SequenceMatcher Ratio (20%), elevated by an options set overlap penalty when distractor choices match ($\ge 75\%$).
- **Scoped Reference Pool**: Real-time evaluation scoped to the exact **Section** and **Subtopic** in PostgreSQL, plus sibling items drafted in the active batch session.
- **Autonomous Anti-Collision Loop**: If a candidate item triggers $\ge 0.80$ similarity, the engine re-prompts the generator with an explicit avoidance directive, steering generation toward alternative clinical presentations or distinct enzymatic mechanisms.
- **Autonomous Set-Preserving Duplicate Resolution (`batch_resolution.py`)**: Batches automatically detect pairwise duplicate clusters (>75% similarity), purge redundant drafts, and dispatch in-place replenishment trials while strictly preserving reading passages and target question quotas.
- **Permanent Audit Trail & Protected Shield**: Educators can **"Override & Approve"** legitimate edge cases (`is_duplicate_override = true`, `overridden_at = ISO_TIMESTAMP`), rendering a distinct blue shield badge (`🛡️ Overridden`) across question cards and bank tables. Alternatively, educators can choose **"Regenerate Fresh Angle"** or **"Discard"**.

---

## ⚡ Quickstart Guide

### 1. Start PostgreSQL (Docker)
```bash
docker compose up -d
```
*Spins up PostgreSQL 16 on `localhost:5432` with database `mcat_db`.*

### 2. Backend Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements-dev.txt

# Start FastAPI server
PYTHONPATH=backend uvicorn app.main:app --port 8000 --reload
```
*Backend runs on **[http://localhost:8000](http://localhost:8000)** (OpenAPI docs at `/docs`).*

### 3. Frontend Setup
```bash
# Install dependencies using pnpm
pnpm install

# Start development server
pnpm dev
```
*Frontend runs on **[http://localhost:5173](http://localhost:5173)**.*

---

## 🧪 Automated Testing & Linters

Run the full backend test suite covering schemas, routing logic, strict quality gates, SVG & FLUX synthesis, database operations, and token calculations:

```bash
# Run backend deterministic test suite (353 deterministic tests across 55 modules)
# Smart auto-skip: If PostgreSQL is offline, 275 pure unit tests pass and 78 DB tests skip cleanly
# conftest.py strips provider keys and enables OFFLINE_MODE: no test ever calls a live LLM
source .venv/bin/activate
pytest -v  # pyproject.toml sets the test path, PYTHONPATH and the "not live_e2e" marker

# Run backend linter and formatter check
ruff check .
ruff format --check .
```

Verify frontend code hygiene and production bundle:

```bash
# Run frontend linter (oxlint: 0 warnings, 0 errors)
pnpm --dir frontend lint

# Verify optimized production build (compiles cleanly via Vite 8)
pnpm --dir frontend build
pnpm lint

# Build production bundle (vite build)
pnpm build
```

For complete test specifications and the 15 TestSprite Playwright E2E browser scenarios, consult [`docs/TESTING_AND_QA.md`](docs/TESTING_AND_QA.md).

---

## 📁 Repository Structure

```
Question Bank Generator/
├── README.md                    # Project overview & documentation index
├── DESIGN.md                    # Authoritative UI/UX Design System Guide (tokens, dual themes, split-pane)
├── CONTRIBUTING.md              # Engineering workflows, code conventions & quality policies
├── LICENSE                      # MIT / Corporate License
├── docker-compose.yml           # PostgreSQL 16 (default) + optional backend/web `app` profile
├── .dockerignore                # Keeps secrets, tests and node_modules out of image builds
├── pyproject.toml               # Python build configuration (pytest, ruff, asyncio)
├── package.json                 # Monorepo pnpm orchestration scripts (with predev port cleaner)
├── pnpm-workspace.yaml          # Pnpm workspace definition
├── pnpm-lock.yaml               # Deterministic package lockfile
├── .env.example                 # Environment variables template (active configuration template)
├── docs/                        # Comprehensive Documentation Suite
│   ├── README.md                # Master Documentation Index & role-based sitemap
│   ├── ARCHITECTURE.md          # Multi-agent architecture, quality gate & Blind-Solver
│   ├── API.md                   # Complete REST & SSE API specification (39 operations / 33 paths)
│   ├── CLIENT_SYSTEM_AND_WORKFLOW_GUIDE.md # Client system & operational workflow guide
│   ├── TESTING_AND_QA.md        # Pytest test suite (363 tests across 56 modules: 353 offline-capable, 10 live) & TestSprite E2E specs
│   ├── TOKEN_TRACKING.md        # Dual-provider inference pricing & mathematical cost engine
│   ├── SETUP_AND_CONFIG.md      # Installation, deployment (67 Settings fields) & FAQs
│   └── MCAT_RUBRIC.md           # 100-point psychometric rubric & authoring standards
├── scripts/
│   └── clean_duplicate_artifacts.py # Database discarded duplicate cleanup utility (pnpm run db:clean-duplicates)
├── e2e/                         # Playwright E2E scenarios (TC001-TC015) and test plan
│   ├── TC0xx_*.py               # One script per scenario (run with python3 e2e/<file>)
│   ├── standard_prd.json        # Product requirements used to generate the scenarios
│   └── testsprite_frontend_test_plan.json # Test plan definition
├── backend/
│   ├── README.md                # Dedicated backend developer guide (55 test modules)
│   ├── requirements.txt         # Runtime dependencies (requirements-dev.txt adds pytest, pytest-asyncio, pytest-cov, ruff)
│   ├── scripts/
│   │   └── seed_questions.py    # CLI database seeding script with authentic AAMC rubrics
│   ├── tests/
│   │   ├── conftest.py                         # Pytest fixtures: offline DB socket probe, credential stripping, async client, patch_llm
│   │   ├── factories.py                        # Shared builders: make_draft/question/request/usage/completion/state, collect_events
│   │   ├── test_additional_instructions.py     # Educator custom instructions and prompt builder integration
│   │   ├── test_agents.py                      # Heuristics, agent mocking, blind solver & quality gates
│   │   ├── test_anthropic.py                   # Multi-provider switching, Anthropic models, prompt cache pricing & API keys
│   │   ├── test_api_duplicates_passages_health.py # Duplicate detection, passage lifecycle, CORS and health endpoints
│   │   ├── test_api_generation.py              # Generation flows through the API: batches, passage sets, visuals
│   │   ├── test_api_hardening.py               # API hardening: admin gate, image safety, safe defaults, write validation
│   │   ├── test_api_questions.py               # Question bank API: CRUD, approval, status lifecycle, pagination
│   │   ├── test_api_security.py                # Optional shared-secret gate and request input limits
│   │   ├── test_authoring_standards.py         # One source of truth for authoring numbers; DDL helper that never locks migrated tables
│   │   ├── test_config_and_pricing_polish.py   # Difficulty alias filtering, OpenAPI generation and the narrowed JSON parsing
│   │   ├── test_batch_aggregate_lock.py        # Concurrent refreshes of one batch must serialize and stay consistent
│   │   ├── test_batch_autonomous_retry.py      # Autonomous 3-trials policy, trial count persistence and in-flight retries
│   │   ├── test_batch_dedup_hard_delete.py     # Hard-delete duplicate purge during batch deduplication and completion guards
│   │   ├── test_batch_jobs_flow.py             # Background batch runner, job concurrency and refill preservation
│   │   ├── test_batch_retry_resume.py          # Retry/resume must run the jobs it selected, and stuck jobs must never hang
│   │   ├── test_batch_review_withholding.py    # Review queue withholding during batch execution and atomic promotion
│   │   ├── test_batch_state.py                 # Batch correctness: terminal resolution, stop/refill guards, cost accounting
│   │   ├── test_blind_solver_vote.py           # Blind solver: robust key parsing, layout-varied sampling and majority voting
│   │   ├── test_config_docs.py                 # Settings fields, .env.example and the setup doc must not drift apart
│   │   ├── test_cpu_async_hygiene.py           # Dedup pruning keeps verdicts, big pools leave the loop, litellm stays lazy
│   │   ├── test_database_structure.py          # SQLAlchemy models, cascade deletion and constraint tests
│   │   ├── test_deduplication.py               # Multi-metric similarity, token containment, options overlap and auto-resolve
│   │   ├── test_deterministic_gate.py          # Tests that the deterministic validator gate runs before LLM review in the review loop
│   │   ├── test_e2e_live.py                    # Live end-to-end integration tests (10 tests marked live_e2e)
│   │   ├── test_engine_cleanup.py              # The workflow stream must not leak worker tasks when its consumer stops reading
│   │   ├── test_engine_slices.py               # Unit tests for the pure, closure-free pieces sliced out of ``workflow.engine``
│   │   ├── test_image_calls.py                 # Retry behaviour and response handling of the provider image calls (HTTP mocked)
│   │   ├── test_index_migration.py             # The redundant single-column question indexes are dropped, covering composites stay
│   │   ├── test_job_stream_consumer.py         # The shared stream reader and request builder behind job runs and refills
│   │   ├── test_live_job_finalization.py       # Standalone /generate runs must always finalize their job and batch rows
│   │   ├── test_llm_budget.py                  # Hard per-slot LLM call budget and the free duplicate re-check after rewrites
│   │   ├── test_llm_call.py                    # Tests for call_llm request construction and retry behavior (provider mocked)
│   │   ├── test_logging_context.py             # Correlation ids bound with bind_log_context appear on log records, including in child tasks
│   │   ├── test_mock_fixture_table.py          # The seven canned mock drafts must stay byte-identical when their source representation changes
│   │   ├── test_multi_batch_concurrency.py     # Multi-batch semaphore stress tests and rate-limit backoff
│   │   ├── test_offline_mode.py                # Mocks are an explicit opt-in: no credentials without OFFLINE_MODE must fail loudly
│   │   ├── test_openai.py                      # OpenAI text and image provider wiring (HTTP mocked)
│   │   ├── test_ops_and_resolution.py          # Request ids, body limits, error sanitising, liveness, batch resolution helpers
│   │   ├── test_pedagogy.py                    # Pedagogical format & 3-card explanation tests
│   │   ├── test_pricing_table.py               # Verified provider prices, model-based rate resolution, cache billing and image costs
│   │   ├── test_projected_reads.py             # Lightweight repository reads used by the batch worker
│   │   ├── test_question_status_refill.py      # Status enums, active question helpers and deficit calculations
│   │   ├── test_recovery.py                    # Startup recovery: orphaned running jobs must not stay 'running' forever
│   │   ├── test_request_secrets.py             # Client-supplied API keys must never be persisted or returned
│   │   ├── test_in_flight_pool_and_dedup.py    # Regression tests for in-flight deduplication pool and batch finalization
│   │   ├── test_schemas.py                     # Pydantic schema validation tests
│   │   ├── test_shared_helpers.py              # Shared helpers extracted during cleanup keep their exact semantics
│   │   ├── test_soft_delete_batch_integrity.py # Tests
│   │   ├── test_sse_keepalive.py               # SSE keep-alive comments while the engine is quiet
│   │   ├── test_structured_output.py           # Model output is validated strictly, repaired once, and never silently defaulted
│   │   ├── test_target_count_guarantee.py      # Dynamic job allocation, slot replenishment and target count guarantees
│   │   ├── test_taxonomy_sync.py               # Byte-for-byte AAMC taxonomy synchronization between backend and frontend
│   │   ├── test_tokens.py                      # Token cost accumulation across providers and config cascade
│   │   ├── test_validators.py                  # Unit tests for the deterministic question validators (no LLM, no database)
│   │   ├── test_visuals.py                     # AI image generation, visual stimulus routing and cost accumulation
│   │   └── test_workflow.py                    # Streaming workflow execution and event metadata
│   └── app/
│       ├── main.py              # FastAPI app with modern lifespan context & security headers
│       ├── core/                # Core configurations & Pydantic V2 settings
│       │   ├── config.py        # Settings and model configuration
│       │   ├── pricing.py       # Price fallback tables & LiteLLM registry lookup
│       │   ├── concurrency.py   # Process-wide pipeline semaphore
│       │   ├── logging.py       # Structured logging configuration
│       │   └── __init__.py
│       ├── data/                # Static taxonomy data
│       │   └── mcat_dependent_taxonomy.json # AAMC-aligned foundational concepts and skills
│       ├── db/                  # Database connectivity & session lifecycle
│       │   ├── base.py          # SQLAlchemy declarative base
│       │   ├── session.py       # Async engine, connection pool & auto-migrations
│       │   ├── init_db.py       # Schema initialization, DDL migrations & FTS indexes
│       │   └── __init__.py
│       ├── models/              # SQLAlchemy ORM models
│       │   ├── batch.py         # GenerationBatchModel for multi-question generation runs
│       │   ├── job.py           # GenerationJobModel for background worker jobs
│       │   ├── passage.py       # PassageModel for shared reading stimuli
│       │   ├── question.py      # QuestionModel with JSONB columns & B-tree indexes
│       │   └── __init__.py
│       ├── repositories/        # Data Access Layer (DAL)
│       │   ├── _filters.py            # Shared soft-delete clauses
│       │   ├── batch_repository.py    # Staged batch run queries & persistence
│       │   ├── job_repository.py      # Background worker job state tracking
│       │   ├── passage_repository.py  # Shared stimulus reading passage queries
│       │   ├── question_repository.py # Clean CRUD, hybrid FTS & aggregate token usage queries
│       │   └── __init__.py
│       ├── schemas/             # Domain Pydantic V2 schemas
│       │   ├── mcat.py          # Official AAMC MCAT sections & subtopic taxonomy
│       │   ├── question.py      # QuestionOption, QuestionDraft, Question, status helper
│       │   ├── token.py         # TokenUsage & TokenCostAccumulator schemas
│       │   ├── workflow.py      # GenerationRequest, ReviewScore, WorkflowEvent
│       │   └── __init__.py
│       ├── services/            # Background Worker Services
│       │   ├── batch_runner.py  # Asynchronous worker pool (5 Q single job / 50 Q 10 jobs)
│       │   ├── deduplication.py # Real-time multi-metric similarity & anti-collision service
│       │   └── __init__.py
│       ├── agents/              # Multi-agent decision logic & prompts
│       │   ├── base.py          # LiteLLM client & calculate_token_cost()
│       │   ├── blind_solver.py  # Independent key validation & agreement agent
│       │   ├── validators.py    # Deterministic structural validators & dash repair (free, pre-review)
│       │   ├── standards.py     # Shared option-length and passage-length authoring standards
│       │   ├── generator.py     # Fused question generator & self-critique agent
│       │   ├── image_generator.py # Programmatic SVG & FLUX-2-klein-4b visual generator
│       │   ├── mock_fixtures.py # Mock fallback questions & heuristic rubrics
│       │   ├── mock_drafts.py   # Table of the seven canned mock drafts
│       │   ├── option_balancer.py # Mathematical option length balancing (±15%)
│       │   ├── prompt_builder.py# User prompt assembly & cross-item calibration
│       │   ├── prompts.py       # Centralized system prompts & rubrics
│       │   ├── regenerator.py   # Autonomous remediation engine agent (<= 90 trigger)
│       │   ├── reviewer.py      # Question Reviewer Agent (100-pt rubric)
│       │   └── __init__.py
│       ├── workflow/            # Multi-agent workflow engine
│       │   ├── engine.py        # Core asynchronous workflow runner & event emitters
│       │   ├── review_loop.py   # Deterministic gate, reviewer, Blind-Solver & remediation loop
│       │   ├── passage_prep.py  # Per-item requests & shared passage/visual drafting
│       │   ├── dedup_inflight.py# Duplicate detection vs. DB, siblings & in-flight drafts
│       │   ├── live_job_store.py# Question & job/batch persistence for live runs
│       │   ├── nodes.py         # Discrete agent worker nodes (Generator, Reviewer, etc.)
│       │   ├── routes.py        # route_after_review: Quality Gate routing used by the review loop
│       │   ├── state.py         # AgentWorkflowState typed dictionary
│       │   └── __init__.py
│       └── api/                 # Modular API Routers
│           ├── router.py        # Central API v1 router aggregator
│           └── v1/
│               ├── batches.py   # Batch execution runs & staged item retrieval
│               ├── config.py    # Read-only engine configuration & model settings
│               ├── generation.py# SSE streaming question generator endpoint
│               ├── health.py    # Database connectivity & system health checks
│               ├── passages.py  # Shared passage stimuli listing & retrieval
│               ├── questions.py # Question Bank CRUD & JSON/CSV exports
│               ├── taxonomy.py  # AAMC syllabus hierarchy & dependent taxonomy
│               └── __init__.py
└── frontend/
    ├── README.md                # Modern React 19 architecture & component guide
    ├── package.json             # React 19 dependencies & scripts (pnpm workspace)
    ├── vite.config.js           # Vite build configuration with chunk splitting
    ├── index.html               # Main HTML entry document
    ├── public/                  # Static assets
    │   ├── favicon.svg          # SVG brand favicon
    │   └── icons.svg            # UI SVG sprite icons
    └── src/
        ├── App.jsx              # Main application shell & router
        ├── main.jsx             # React 19 application entry point
        ├── index.css            # Precision Design System aggregator hub (imports styles/*)
        ├── styles/              # Modular domain stylesheets (tokens, base, layout, wizard, question, batch, bank, passage, modals, print)
        ├── views/               # Top-level screen views (Code-split with React.lazy)
        │   ├── index.js         # Centralized views index
        │   ├── AiValidatedQuestionsView.jsx # Dedicated AI Validated (>90) quality bank
        │   ├── BatchActivityView.jsx      # Batch job lifecycle monitor
        │   ├── PassageBankView.jsx        # Passage stimuli repository & editorial desk
        │   └── QuestionBankView.jsx       # Question Bank search, filter, and export
        ├── constants/           # Centralized application constants
        │   ├── index.js         # Constants barrel export
        │   ├── mcat.js          # MCAT sections, pacing targets, and skills
        │   ├── mcatTraps.js     # AAMC cognitive trap definitions and defense strategies
        │   └── mcat_dependent_taxonomy.json # AAMC-aligned foundational concepts and skills
        ├── hooks/               # Custom stateful React hooks
        │   ├── index.js                 # Barrel export for custom hooks
        │   ├── useAppState.js           # Centralized view routing & global event broker
        │   ├── useFocusTrap.js          # Accessible WCAG AA keyboard focus-trapping hook
        │   ├── useGeneratorForm.js      # Form state, validation & preset handlers
        │   ├── useKeyboardShortcuts.js  # Global hotkeys (⌘↵, T, A, D, /, Esc)
        │   ├── usePagination.js         # Pagination state & range calculations
        │   ├── useQuestionBank.js       # Debounced search, sorting, and bank fetching
        │   └── useTheme.js              # Theme manager (Dark/Light with localStorage)
        ├── components/          # Domain-organized UI components
        │   ├── index.js         # Barrel exports for clean component imports
        │   ├── bank/            # Question repository filters & table
        │   │   ├── QuestionBankFilters.jsx # Section, difficulty & search filters
        │   │   ├── QuestionBankTable.jsx   # Canonical Editorial Cards view & actions
        │   │   └── index.js
        │   ├── batch/           # Batch Activity cards & job monitors
        │   │   ├── ActiveMultiBatchMonitor.jsx # Global concurrency metrics & live monitor
        │   │   ├── BatchCard.jsx               # Summary status card for generation batches
        │   │   ├── BatchFiltersBar.jsx         # Section, status, and search filters
        │   │   ├── BatchJobCard.jsx            # Per-question job card with lifecycle status
        │   │   ├── BatchQuestionItem.jsx       # Staged question item with review modal trigger
        │   │   ├── BatchStatsHeader.jsx        # High-level aggregate batch statistics
        │   │   └── index.js
        │   ├── common/          # Common primitives
        │   │   ├── CustomSelect.jsx     # Accessible custom dropdown select primitive
        │   │   ├── ErrorBoundary.jsx    # Production React error boundary with fallback UI
        │   │   ├── FormattedText.jsx    # Inline markdown & cognitive trap chip highlighter
        │   │   ├── InfynnoLogo.jsx      # Official corporate vector logo primitive
        │   │   ├── LiveStopwatch.jsx    # High-precision live stopwatch timer
        │   │   ├── PaginationBar.jsx    # Accessible pagination bar with page range counter
        │   │   ├── Toast.jsx            # Floating toast notification system
        │   │   └── index.js
        │   ├── layout/          # Layout components (Navbar, Footer)
        │   │   ├── Footer.jsx           # Infynno Solutions LLP attribution & resource footer
        │   │   ├── Navbar.jsx           # Header with branding, navigation tabs, and theme toggle
        │   │   └── index.js
        │   ├── modals/          # Dialog modals (WCAG AA Focus Trapped)
        │   │   ├── ConfirmationModal.jsx # Accessible confirmation modal replacing window.confirm
        │   │   ├── DeletePassageModal.jsx# Dedicated passage deletion and cascade warning dialog (Hoisted)
        │   │   ├── ExportPaperPreview.jsx # Live print layout previewer
        │   │   ├── ExportPrintModal.jsx   # Exam Paper (PDF), Study Pack, CSV/JSON export modal
        │   │   └── index.js
        │   ├── passage/         # Reading passage bank components
        │   │   ├── PassageBankFilters.jsx # Passage search & section filters
        │   │   ├── PassageBankTable.jsx   # Passage repository table & question sets
        │   │   ├── PassageEditorialDesk.jsx # Reading passage editor & preview desk
        │   │   ├── PassageLinkedQuestionCard.jsx # Linked question card within passage desk
        │   │   ├── PassageVisualStimulusEditor.jsx # Passage diagram & figure attachment editor
        │   │   └── index.js
        │   ├── question/        # Single Question Review Desk
        │   │   ├── MentorExplanationView.jsx # 3-card mentor explanation view
        │   │   ├── QuestionCard.jsx     # Interactive student practice & review card
        │   │   ├── QuestionInlineEditor.jsx # In-place authoring & remediation editor
        │   │   ├── QuestionScorecardTab.jsx # 100-point rubric breakdown accordion
        │   │   ├── ReviewAuditView.jsx  # 100-point rubric breakdown & token cost modal (Focus Trapped)
        │   │   ├── SharedPassageCard.jsx# Shared reading passage stimulus display card
        │   │   ├── StageJsonInspector.jsx# Deep stage outcome JSON inspector accordion
        │   │   ├── VisualStimulusViewer.jsx # SVG & neural visual diagram renderer
        │   │   └── index.js
        │   ├── validated/       # Dedicated AI Validated quality cards & filters
        │   │   ├── AiValidatedFiltersBar.jsx   # Filters for AI-validated questions
        │   │   ├── AiValidatedQuestionCard.jsx # Card with direct bank approval actions
        │   │   ├── AiValidatedStatsBar.jsx     # Quick-action statistics header
        │   │   └── index.js
        │   └── wizard/          # Progressive 3-step Guided Wizard
        │       ├── GuidedWizard.jsx     # Streamlined 3-step guided exam generation wizard
        │       ├── HeroLanding.jsx      # Welcome landing hero header
        │       ├── steps/               # Wizard step components
        │       │   ├── WizardStep1SectionFocus.jsx   # Step 1: Section, pacing & focus
        │       │   ├── WizardStep2LevelFormat.jsx    # Step 2: Level, format & scope (5/50)
        │       │   ├── WizardStep3ReviewAdvanced.jsx # Step 3: Compact review table & advanced
        │       │   └── index.js
        │       └── index.js
        ├── services/
        │   ├── api.js           # SSE event reader & REST API client (24 methods)
        │   └── index.js
        └── utils/               # Pure utility helpers
            ├── explanationHelpers.js # Distractor line & cognitive trap parser
            ├── exportUtils.js   # Re-export shim for the export/ modules
            ├── export/          # csv.js, json.js, htmlDoc.js (A4 print builder), printPaperCss.js
            ├── formatters.js    # Time, word count, token & currency formatters
            ├── optionHelpers.js # Option length parity & calculateOptionSymmetry engine
            ├── trapHelpers.js   # Cognitive trap resolution & text detectors
            └── index.js
```

---

## 📄 License & Attribution
Proprietary - Infynno MCAT Question Bank Generator is engineered and maintained by **[Infynno Solutions LLP](https://infynno.com/)**. All rights reserved.
