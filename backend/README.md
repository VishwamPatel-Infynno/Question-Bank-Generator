# Infynno MCAT Question Bank Generator - Backend

> **An Infynno Solutions LLP Product • [Infinite Innovations](https://infynno.com/)**  
> High-throughput asynchronous backend service powering the AAMC MCAT Question Studio v2.0.

Built with **Python 3.11+**, **FastAPI**, **LangGraph**, **LiteLLM**, **SQLAlchemy 2.0 (Async)**, and **PostgreSQL 16**.

---

## 1. Architecture & Modular Layer Separation

The backend is engineered with clear separation of concerns across presentation, orchestration, domain logic, persistence, and background worker services:

```
backend/
├── app/
│   ├── api/                 # Presentation Layer (HTTP & SSE Routers - 38 Z paths)
│   │   ├── router.py        # Central API v1 router aggregator
│   │   └── v1/
│   │       ├── generation.py # SSE streaming multi-agent orchestrator endpoint
│   │       ├── questions.py  # Question Bank CRUD, review approval, duplicate check & override, restoration, permanent purge & exports
│   │       ├── passages.py   # Shared clinical stimulus passages endpoints (list, retrieve, save, soft-delete)
│   │       ├── batches.py    # Multi-question batch execution run endpoints, clustering & refill
│   │       ├── taxonomy.py   # AAMC syllabus hierarchy & dependent taxonomy tree endpoints
│   │       ├── config.py     # Runtime engine configuration, dual-provider settings & pricing (28 fields)
│   │       └── health.py     # Database connectivity & system health checks
│   ├── workflow/            # Orchestration Layer (LangGraph Engine)
│   │   ├── engine.py        # Core streaming execution engine & event emitters
│   │   ├── engine_helpers.py # Review loop, passage preparation & live persistence helpers
│   │   ├── nodes.py         # Discrete agent worker nodes (Generator, Reviewer, etc.)
│   │   ├── routes.py        # Deterministic conditional routing logic (Quality Gate)
│   │   ├── graph.py         # StateGraph builder and compilation pipeline
│   │   └── state.py         # AgentWorkflowState typed dictionary
│   ├── agents/              # Cognitive Reasoning & Synthesis Layer
│   │   ├── generator.py     # Fused clinical question synthesis & self-critique agent
│   │   ├── blind_solver.py  # Blind-solver dual-validation candidate verification agent (fail-closed)
│   │   ├── validators.py    # Free deterministic structural validators & dash repair, run before LLM review
│   │   ├── reviewer.py      # 100-point 4-pillar psychometric auditor agent
│   │   ├── regenerator.py   # Autonomous remediation agent (<= 90 score trigger)
│   │   ├── option_balancer.py # Mathematical option length balancing (±15%) & anti-guessability
│   │   ├── image_generator.py # FLUX-2-klein-4b neural visual & SVG vector generator
│   │   ├── prompt_builder.py # User prompt assembly & cross-item diversity calibration
│   │   ├── prompts.py       # Centralized system prompts, pacing rules & rubrics
│   │   ├── mock_fixtures.py # Deterministic fallback fixtures for offline resilience
│   │   └── base.py          # LiteLLM execution wrapper & sub-micro-cent token cost engine (DeepInfra + Anthropic)
│   ├── services/            # Background Worker & Asynchronous Services
│   │   ├── batch_runner.py  # Background pool managing Practice Sets (1-job, 5 Qs) and Full Exams (10-job, 50 Qs)
│   │   └── deduplication.py # Multi-metric similarity scoring & anti-collision service
│   ├── repositories/        # Data Access Layer (DAL)
│   │   ├── question_repository.py # Clean CRUD, soft-deletion, restoration, duplicate overrides, reference queries, hybrid FTS & token analytics
│   │   ├── batch_repository.py    # Staged batch run queries & persistence
│   │   ├── job_repository.py      # Background worker job state tracking
│   │   └── passage_repository.py  # Shared stimulus reading passage queries, soft-deletion, and cascade question removal
│   ├── models/              # Persistence Layer (SQLAlchemy 2.0 ORM Entities)
│   │   ├── question.py      # QuestionModel with JSONB duplicate_info, is_deleted, deleted_at & 7 composite indexes
│   │   ├── passage.py       # PassageModel for multi-item shared reading stimuli with is_deleted & deleted_at
│   │   ├── batch.py         # BatchModel for multi-question generation runs
│   │   └── job.py           # JobModel for tracking individual background batch jobs with persisted trial_count
│   ├── schemas/             # Domain Transfer Layer (Pydantic V2)
│   │   ├── mcat.py          # MCAT sections, difficulty tiers (low/medium/high) & subtopic taxonomy
│   │   ├── token.py         # TokenUsage & TokenCostAccumulator schemas
│   │   ├── question.py      # QuestionOption, QuestionDraft, Question, determine_question_status helper
│   │   └── workflow.py      # GenerationRequest, ReviewScore, WorkflowEvent
│   ├── core/                # Configuration & Settings
│   │   ├── config.py        # Pydantic SettingsConfigDict, dual-provider defaults, cache rates & pricing (39 model fields)
│   │   └── logging.py       # Centralized console logging handler & formatter
│   ├── db/                  # Database Lifecycle
│   │   ├── base.py          # Declarative Base
│   │   ├── init_db.py       # Schema verification, column backfills, FTS & FK constraints
│   │   └── session.py       # Async engine, connection pool & startup migrations
│   └── data/                # Static Taxonomy & Curricula
│       └── mcat_dependent_taxonomy.json # AAMC official syllabus foundational concepts & skills
├── scripts/                 # Maintenance & Seeding Utilities
│   └── seed_questions.py    # Sample question bank seeder
└── tests/                   # Deterministic Automated Test Suite (21 deterministic modules / 110 tests + 1 live E2E module = 153 total)
    ├── conftest.py          # Pytest fixtures, offline DB socket probe & async test client
    ├── test_additional_instructions.py # Educator custom instructions and prompt builder integration
    ├── test_agents.py       # Cognitive agent unit tests
    ├── test_anthropic.py    # Multi-provider switching, Anthropic models, prompt cache pricing & API keys
    ├── test_api.py          # REST & SSE endpoint integration tests, CRUD, batch staging, pagination & duplicate overrides
    ├── test_batch_autonomous_retry.py # Autonomous 3-trials policy, trial count persistence, HTTP 400 rejection, and in-flight retries
    ├── test_batch_dedup_hard_delete.py # Hard-delete duplicate purge during batch deduplication and completion guards
    ├── test_batch_jobs_flow.py # Background batch runner, job concurrency, and refill preservation
    ├── test_batch_review_withholding.py # Review queue withholding during batch execution and atomic promotion
    ├── test_database_structure.py # SQLAlchemy models, cascade deletion, and constraint tests
    ├── test_deduplication.py# Multi-metric similarity, token containment & options overlap tests
    ├── test_e2e_live.py     # Live end-to-end integration tests (10 tests marked live_e2e)
    ├── test_multi_batch_concurrency.py # Multi-batch semaphore stress tests
    ├── test_pedagogy.py     # Pedagogical format & 3-card explanation tests
    ├── test_question_status_refill.py # Status enums, active question helpers, and deficit calculations
    ├── test_schemas.py      # Pydantic schema validation tests
    ├── test_soft_delete_batch_integrity.py # Soft deletion & restoration preserving batch progress integrity
    ├── test_target_count_guarantee.py # Dynamic job allocation, slot replenishment, and target count guarantees
    ├── test_taxonomy_sync.py # Byte-for-byte AAMC taxonomy synchronization between backend and frontend
    ├── test_tokens.py       # Mathematical token cost accumulation tests across providers
    ├── test_visuals.py      # SVG & neural image generation tests
    └── test_workflow.py     # LangGraph StateGraph execution tests
```

---

## 2. Multi-Agent Workflow Engine

The multi-agent workflow coordinates a 3-step autonomous pipeline through a strict psychometric contract:

```mermaid
graph TD
    Start([Generation Request]) --> NodeFused[Fused Draft & Self-Critique Node]
    
    NodeFused --> FusedScoreCheck{Self-Score > 90?}
    FusedScoreCheck -->|Yes & Needs Diagram| NodeImg[FLUX-2-klein-4b / SVG Node]
    FusedScoreCheck -->|Yes & Text Only| NodeFin[Finalize & Persist Node]
    NodeImg --> NodeFin
    
    FusedScoreCheck -->|No| NodeRegen[Remediation Node]
    NodeRegen --> NodeRev[Independent Reviewer Node]
    
    NodeRev --> ScoreCheck{Score > 90?}
    ScoreCheck -->|Yes & Needs Diagram| NodeImg
    ScoreCheck -->|Yes & Text Only| NodeFin
    ScoreCheck -->|No & Cycles < 3| NodeRegen
    ScoreCheck -->|No & Cycles >= 3| NodeReject[Strict Quality Gate Reject]
    
    NodeReject --> Discard([Discard Candidate & Halt])
    NodeFin --> Success([Stream to Review Desk / Persist])
```

- **Fused Draft-and-Critique Entry Point**: Drafts question and generates immediate 100-point self-critique in a single pass (`fused_generator_node`), combining drafting and self-critique in one inference round-trip; the independent reviewer and blind solver still audit every draft by default (`ALWAYS_INDEPENDENT_REVIEW`).
- **Passing Threshold**: A question candidate must score **$> 90$** out of 100 on the standardized rubric to be approved for publication (`config.passes_quality_gate`).
- **Deterministic Gate & Fail-Closed Checks**: Before any LLM review, `validators.py` checks structure and repairs forbidden dashes. The Reviewer and Blind Solver run concurrently (`PARALLEL_REVIEW_AND_SOLVE`) and raise `QualityCheckUnavailableError` rather than passing an item they could not check. Mock fixtures are used only when no credentials are configured.
- **Option Symmetry & Anti-Guessability**: Generator and Reviewer enforce word count parity (within 3 words, or 20% of the average for longer options) across all 4 options ($A, B, C, D$), parallel grammar, and balanced qualifiers to eliminate test-wiseness guessing cues.
- **Anti-AI Formatting Standard**: Strictly forbids em dashes, en dashes, or double hyphens; standard single hyphens (`-`) only.
- **3-Part Structured Mentor Explanations**: Renders pedagogical explanations across three specialized visual cards: Core Intuition & Proof, Itemized Distractor Analysis, and Primary Cognitive Trap Spotlight.
- **Autonomous Remediation**: If score $\le 90$, the Remediation node (`regenerator.py`) digests the exact weaknesses and distractor recommendations, attempting repairs for up to 3 cycles.
- **Strict Quality Gate**: If score remains $\le 90$ after 3 attempts, the candidate is discarded immediately, preserving question bank integrity.

---

## 3. High-Throughput Pricing & Micro-Cost Engine

Token costs are calculated per request at the lowest execution layer ([`backend/app/agents/base.py`](app/agents/base.py)) and accumulated across all agent cycles:

- **Input Tokens**: $0.098 per 1,000,000 tokens
- **Output Tokens**: $0.294 per 1,000,000 tokens
- **FLUX-2-klein-4b Image Generation**: Flat unit rate of $0.014 per image, scaled dynamically by resolution.

Calculations are rounded to **7 decimal places** to prevent IEEE 754 floating-point drift:
$$\text{Cost (USD)} = \left(\frac{\text{Prompt Tokens}}{1,000,000} \times 0.098\right) + \left(\frac{\text{Completion Tokens}}{1,000,000} \times 0.294\right)$$

---

## 4. Local Setup & Execution

### Prerequisites
- Python 3.11+
- PostgreSQL 16 (running via Docker Compose or native)

### Step 1: Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install requirements
pip install --upgrade pip
pip install -r backend/requirements-dev.txt
```

### Step 2: Database Initialization
Ensure PostgreSQL 16 is running on port `5432`:
```bash
docker compose up -d
```
The database connection string in `.env` defaults to:
`DATABASE_URL=postgresql+asyncpg://mcat_user:mcat_password@localhost:5432/mcat_db`

### Step 3: Run FastAPI Application
```bash
PYTHONPATH=backend uvicorn app.main:app --port 8000 --reload
```
- **Service Root**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health) (liveness, `degraded` without a database) and [http://localhost:8000/api/health/ready](http://localhost:8000/api/health/ready) (readiness, `503` when the database is down)

---

## 5. Automated Testing & Code Quality

### Running Tests
Run the deterministic backend test suite covering endpoints, schemas, database operations, workflow routing, and token cost formulas (see [`docs/TESTING_AND_QA.md`](../docs/TESTING_AND_QA.md) for full specs):

```bash
# Run all unit and integration tests (143 deterministic tests across 28 modules)
# Smart auto-skip: 55 pure unit tests pass offline, 42 DB-dependent tests skip cleanly if PostgreSQL is offline
source .venv/bin/activate
ACTIVE_LLM_PROVIDER=deepinfra pytest backend/tests -v -m "not live_e2e"

# Run database relational structure tests
PYTHONPATH=backend pytest backend/tests/test_database_structure.py -v
```

### Code Formatting & Linting
Enforce Python code hygiene using **Ruff** (enforces SIM, RET, B, C4, E, W, F, I, UP):

```bash
# Check code style and rules (0 errors policy)
ruff check backend/

# Verify formatting without modification across repository
ruff format --check .

# Automatically fix linting issues
ruff check --fix backend/
```

---

## 6. Database Seeding Script

To populate the Question Bank with realistic AAMC MCAT practice questions across all 4 sections:

```bash
source .venv/bin/activate
python backend/scripts/seed_questions.py
```
This generates authentic questions with complete psychometric rubrics, evolution histories, distractors, and token telemetry.
