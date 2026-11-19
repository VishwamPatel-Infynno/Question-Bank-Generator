# Infynno MCAT Question Bank Generator v2.0
> **An Infynno Solutions LLP Product • [Infinite Innovations](https://infynno.com/)**

[![CI Pipeline](https://github.com/VishwamPatel-Infynno/MCAT-Question-Bank-Generator/actions/workflows/ci.yml/badge.svg)](https://github.com/VishwamPatel-Infynno/MCAT-Question-Bank-Generator/actions/workflows/ci.yml)

An enterprise autonomous AI application for generating, quality-reviewing, and creating high-quality exam questions for the official **AAMC MCAT** (Medical College Admission Test).

Engineered by **[Infynno Solutions LLP](https://infynno.com/)**, powered by a **3-Step AI Pipeline**, **FastAPI**, **React 19**, and **PostgreSQL 16**, featuring a modern single-canvas studio, live team tracker, batch staging, AAMC SIRS reasoning skills, 100-point 4-pillar psychometric evaluation with First-Pass 100/100 calibration, and a unified 80/70 quality threshold.

---

## 📚 Comprehensive Documentation Suite

For deep-dive technical specifications, architecture diagrams, API schemas, and authoring guidelines, consult the dedicated guides in the [`docs/`](docs/) directory and repository root:

| Document | Description |
| :--- | :--- |
| **[Central Documentation Hub (docs/README.md)](docs/README.md)** | **Master Documentation Index**: Complete sitemap, role-based navigation paths, architectural overview, and cross-functional guide directory. |
| **[Client System & Workflow Guide (docs/CLIENT_SYSTEM_AND_WORKFLOW_GUIDE.md)](docs/CLIENT_SYSTEM_AND_WORKFLOW_GUIDE.md)** | **Primary Client Deliverable**: End-to-end operational walkthrough, 3-step wizard, 2 calibrated generation scopes (5 Questions [1 Job] and 50 Questions [10 Jobs]), Low/Medium/High difficulty tiers, AI Copilot Studio, Hero Landing & Quick-Start Presets, pgvector Semantic RAG shield, 6-format Export Studio, Blind-Solver safeguard, Deduplication & Editorial Override workflow, AAMC Split-Pane reading mode, canonical Editorial Cards Question Bank, mentor explanations, and token transparency. |
| **[UI/UX Design System (DESIGN.md)](DESIGN.md)** | Authoritative design tokens, dual obsidian/alabaster themes, streamlined 3-step wizard with decomposed summary/advanced drawers, decomposed QuestionCard components, `QuestionCopilotStrip`, `HeroLanding`, decomposed Export Studio panes (`ExportScopeSelector`, `ExportDataFormatPane`, `StudyGuideExportPane`), modular stylesheets (`study-guide-modal.css`, `question-copilot.css`, `stage-inspector.css`), accessible modal focus-trapping contracts (`Modal`, `ConfirmationModal`, `DeletePassageModal`), live batch retry telemetry (`AUTO-RETRYING X/3`), typography scale, component contracts, accessibility criteria (WCAG AA), and micro-animations. |
| **[Architecture & Multi-Agent Workflow](docs/ARCHITECTURE.md)** | Complete workflow diagrams, 3-step pipeline specifications, Blind-Solver Dual Validation, Deduplication & Anti-Collision Subsystem, AI Copilot Studio & in-flight tooling, pgvector Semantic RAG & HNSW vector indexing (`VECTOR(1536)`), 5-Slot Cognitive Blueprints with replenishment rotation, hard 36-call slot budget, Strict Quality Gate, single-threshold 80/70 quality model, global worker semaphores, background batch runner with 3-trial retries, SSE pipeline, and PostgreSQL 16 ERD. |
| **[REST & SSE API Reference](docs/API.md)** | Complete FastAPI endpoint documentation (48 endpoint operations across 42 unique paths including root `/metrics`), pgvector semantic search & RAG endpoints, deduplication, duplicate clustering, auto-resolve & refill endpoints, question restoration (`/restore`), permanent purges (`/permanent`, `/purge-batch`), batch generation schemas, 3-trial batch controls (`/stop`, `/retry`, `/cancel-all`), Prometheus `/metrics` exposition, AI Copilot suite (`/enhance-instructions`, `/refine-question`, `/audit-passage`, `/study-guide`), SSE event stream contracts, filter parameters, and cURL examples. |
| **[Testing & Quality Assurance Guide](docs/TESTING_AND_QA.md)** | Complete test specifications for the 501 passing deterministic unit/integration tests across 74 modules (511 total backend tests across 75 files), 140 frontend unit tests across 16 test files, 15 TestSprite-generated Playwright E2E scripts in `e2e/` (run manually, not in CI), Ruff & Oxlint code hygiene standards, and CI pipeline. |
| **[Token Usage & Cost Tracking](docs/TOKEN_TRACKING.md)** | Verified rate cards per model: DeepInfra DeepSeek ($0.20 in / $0.60 out per 1M tokens standard), Anthropic Claude Haiku 5.5 ($0.10 in / $0.50 out with tiers and prompt-cache rates), OpenAI gpt-4o-mini, text-embedding-3-small ($0.02 per 1M tokens), token-billed gpt-image-2.5-flare images, AI Copilot rate cards, hard 36-call slot budget, exact mathematical cost formulas, multi-agent accumulation, and UI observability. |
| **[Installation, Setup & Deployment](docs/SETUP_AND_CONFIG.md)** | Step-by-step setup, Docker PostgreSQL 16 guide with `pgvector/pgvector:pg16`, environment variables reference (73 Settings fields), modern `uv` workflow, database duplicate cleanup (`pnpm run db:clean-duplicates`), predev port cleanup, production deployment, linters, and troubleshooting. |
| **[MCAT Psychometric Rubric & Standards](docs/MCAT_RUBRIC.md)** | Official 4 AAMC sections standards, 100-point 4-pillar evaluation rubric (25 pts per pillar), First-Pass 100/100 Calibration Directive, 5-Slot Cognitive Blueprints for CARS and Science, domain and experimental condition rotation tables, Blind-Solver algorithmic verification, unified 80/70 quality thresholds, and cognitive distractor trap engineering. |
| **[Backend Developer Guide](backend/README.md)** | Layer separation, modular workflow engine (`engine.py`, `stream_emitter.py`, `slot_worker.py`, `engine_layout.py`, `review_loop.py`, `passage_prep.py`, `passage_blueprints.py`, `draft_parser.py`, `dedup_inflight.py`, `live_job_store.py`, `node_generator.py`, `node_reviewer.py`, `node_finalize.py`, `nodes.py`), AI Copilot in-flight services, pgvector Semantic RAG, Blind-Solver agent, CQRS repositories (`question_queries.py`, `question_mutations.py`, `mappers.py`, `query_builders.py`), schema migrations (`schema_migrations.py`), 3-trial retry engine, testing (501 deterministic tests across 74 modules, 511 total backend tests across 75 files), and seeding scripts. |
| **[Frontend Workstation Guide](frontend/README.md)** | Modern React 19 architecture, decomposed component directory (`wizard/`, `question/`, `copilot/`, `batch/`, `modals/`, `common/`), top-level views, modular stylesheets, 140 frontend unit tests across 16 test files, hooks, predev port cleaner, and local development instructions. |

---

## 🚀 Key System Capabilities

### 1. Fused Cognitive Architecture with Strict Quality Gate
```mermaid
graph LR
    FusedGen[Fused Draft & 100-pt Audit] -->|Score > 80 (High Quality)| ImageGen[Stimulus & Diagram]
    FusedGen -->|Score > 80 & Text Only| Finalize[Ready for Review Queue]
    FusedGen -->|Score <= 80| Regenerator[Remediation Engine]
    Regenerator --> Reviewer[Independent Auditor]
    Reviewer -->|Score <= 80 & Cycles < 3| Regenerator
    Reviewer -->|70 <= Score <= 80 & Cycles = 3| FinalizeBatch[Accept into Batch Only (Good Quality)]
    Reviewer -->|Score < 70 & Cycles = 3| Reject[Strict Quality Gate Reject]
    Reviewer -->|Score > 80| ImageGen
    Reviewer -->|Score > 80 & Text Only| Finalize
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
- **100-Point 4-Pillar Psychometric Audit & First-Pass 100/100 Directive**: Evaluates candidate questions across four rigorous 25-point pillars (*Authenticity & Tone*, *Clarity & Scientific Logic*, *Distractor Traps & Symmetry*, *Explanation Rigor*). The generator is explicitly mandated to aim for a perfect 100/100 on the initial draft, and the reviewer awards full points when all criteria are met without artificial dampening.
- **AAMC Scientific Inquiry & Reasoning Skills (SIRS)**: Integrates official AAMC SIRS skills (Skill 1: Knowledge of Scientific Concepts, Skill 2: Scientific Reasoning and Problem-solving, Skill 3: Reasoning About Design and Execution of Research, Skill 4: Data-based and Statistical Reasoning) and CARS Reasoning Skills (Foundations of Comprehension, Reasoning Within the Text, Reasoning Beyond the Text).
- **Independent Psychometric Auditor (`reviewer.py`)**: Independently audits candidate items whenever the initial draft scores $\le 80$ or after remediation across 4 equal 25-point pillars (*Authenticity & Tone*, *Clarity & Scientific Logic*, *Distractor Traps*, *Explanation & Key Accuracy*).
- **Remediation Engine Agent (`regenerator.py`)**: Automatically triggered when score $\le 80$. Digests the exact weaknesses and recommendations to repair borderline distractors and expand step-by-step proofs up to 3 iterations.
- **Strict Quality Gate**: If a question fails to reach the batch threshold ($70$ points) after maximum attempts (`MAX_REGENERATION_ATTEMPTS = 3`), the workflow halts immediately. Bypasses image generation and discards the candidate to protect repository integrity.
- **Reviewer-Regenerator Visual Preservation Boundary**: The Reviewer agent receives the complete Accompanying Visual Stimulus Specification and is governed by an anti-deduction audit boundary preventing it from penalizing references to "Figure 1" in standalone stems as unanswerable flaws. The Regenerator is mandated by Rule 12 to preserve `image_needed: True` and retain figure references, ensuring empirical scientific and clinical data are delivered via publication-grade figures.
- **Medical Imaging & Visual Stimulus Subsystem (`image_generator.py` & `medical_imaging.py`)**: Synthesizes publication-grade scientific figures and clinical diagnostic stimuli across 7 medical modalities (Radiology CT/MRI/X-Ray, Histopathology H&E, Gross Anatomy specimens, Cellular Electron Microscopy TEM/SEM, Physiology/ECG Traces, Clinical Pathology, and SVG Vector Diagrams) with active full-modality spectrum encouragement preventing 2D line plot clustering, autonomous AI visual discretion for standalone questions, and automated content safety retry fallback for educational textbook schematics (strictly disabled for CARS in compliance with official AAMC exam regulations).
- **Python Type Precision & Structured Contracts**: Fully typed backend runtime with mandatory `dict[str, Any]` annotations, `AgentUsageEntry` TypedDict, and strongly typed `SlotLedger` state.

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
- **Hero Landing Screen (`HeroLanding.jsx`)**: Minimalist welcome canvas presenting official AAMC MCAT sections and instant 1-click exam presets (`HERO_PRESETS` in `wizardConstants.js`) with dedicated icon mappings.
- **3-Step Guided Question Wizard (`GuidedWizard.jsx`)**: Streamlined step-by-step authoring workflow supporting 2 calibrated generation scopes (**5 Questions** [1 Single Job] and **50 Questions** [10-Job Batch]), 3 calibrated difficulty tiers (**Low**, **Medium**, **High**), interactive syllabus navigation, and a compact review summary table with collapsible advanced settings accordion.
- **Dedicated Generation & Review Workspace**: Clean, distraction-free full-width canvas (`maxWidth: 1040px`) hosting live multi-agent synthesis, telemetry, and batch staging without cramped column docks.
- **Editorial Question Presentation**: Scientific research passages and CARS essays formatted in serif typography with line-height `1.68` for fatigue-free reading; circular option badges (`A`, `B`, `C`, `D`), canonical Question Bank Editorial Cards view (legacy grid mode removed), top metadata strip with purple primary trap badge chips, AAMC Scaled Score and SIRS badges, 3-card structured mentor explanations (*Why Correct*, *Why Other Options Incorrect* with itemized distractor cards, and *Primary Cognitive Trap Spotlight*), and inline editing.
- **Instant Theme Switching**: Seamless toggle between Dark and Light themes with WCAG AA compliance via the `T` key shortcut.
- **Full Keyboard Navigation & WCAG AA Accessibility**: `⌘ + Enter` (Generate), `T` (Theme), `/` (Search Bank), `A` (Approve), `D` (Discard), `Escape` (Close Modals). All 5 primary workspace views feature native semantic `<button>` elements, dynamic `aria-pressed` on filter pills, `aria-current="step"` on steppers, `aria-expanded` on collapsible drawers, and explicit `aria-label`s on selection checkboxes and bulk actions.

### 5. Comprehensive 6-Format Publication & Export Studio (`ExportPrintModal.jsx`)
- **Official Exam Booklet (Standard PDF)**: Generates classroom and mock test papers with candidate metadata headers, section specifications, and `.page-break` rules preventing awkward splits across pages.
- **Exam Simulation Booklet (Split-Pane AAMC Layout PDF)**: Authentic full-length exam layout with passage left, questions right, and dedicated answer sheets.
- **Comprehensive Study Pack (Annotated Review PDF)**: Pairs every research or CARS stimulus with its question stem, correct key, cognitive trap analysis, and complete step-by-step cognitive proof rationales.
- **Anki Flashcard Deck (TSV with Cloze / QA Tags)**: Formatted TSV export ready for instant spaced-repetition import into Anki desktop and mobile apps.
- **Standardized CSV (`mcat_question_bank.csv`)**: Normalized tabular dataset of all questions, options, keys, rubrics, and token metrics for spreadsheet manipulation.
- **Normalized JSON (`mcat_question_bank.json`)**: Complete hierarchical schema export preserving full JSONB metadata, agent evolutions, and psychometric scores.
- **Decomposed Export Panes**: Modularized into specialized subcomponents:
  - `ExportScopeSelector.jsx`: Scope, section, and difficulty targeting.
  - `ExportDataFormatPane.jsx`: Format configurations for CSV, JSON, and Anki TSV.
  - `StudyGuideExportPane.jsx`: Custom study guide compilation parameters.

### 6. Question Deduplication, Collision Avoidance & Editorial Override
- **Multi-Metric Mathematical Similarity**: Hybrid algorithm combining Token Containment (35%), 1-Gram Jaccard (25%), 2-Gram Jaccard (20%), and SequenceMatcher Ratio (20%), elevated by an options set overlap penalty when distractor choices match ($\ge 75\%$).
- **Scoped Reference Pool**: Real-time evaluation scoped to the exact **Section** and **Subtopic** in PostgreSQL, plus sibling items drafted in the active batch session.
- **Autonomous Anti-Collision Loop**: If a candidate item triggers $\ge 0.80$ similarity, the engine re-prompts the generator with an explicit avoidance directive, steering generation toward alternative clinical presentations or distinct enzymatic mechanisms.
- **Autonomous Set-Preserving Duplicate Resolution (`batch_resolution.py`)**: Batches automatically detect pairwise duplicate clusters (>75% similarity), purge redundant drafts, and dispatch in-place replenishment trials while strictly preserving reading passages and target question quotas.
- **Permanent Audit Trail & Protected Shield**: Educators can **"Override & Approve"** legitimate edge cases (`is_duplicate_override = true`, `overridden_at = ISO_TIMESTAMP`), rendering a distinct blue shield badge (`🛡️ Overridden`) across question cards and bank tables. Alternatively, educators can choose **"Regenerate Fresh Angle"** or **"Discard"**.

### 7. AI Copilot Studio & In-Flight Assistance (`QuestionCopilotStrip.jsx` / `ai_copilot.py`)
- **Real-Time Educator Tooling**: Context-aware floating assistant strip providing 4 focused cognitive tools:
  - **Prompt Enhancement (`/enhance-instructions`)**: Refines authoring prompts with explicit AAMC phrasing, SIRS reasoning verbs, and distractor constraints.
  - **Question Refinement (`/refine-question`)**: Proposes targeted fixes for ambiguous wording, key clarity, distractor symmetry, or cognitive trap calibration.
  - **Passage Audit (`/audit-passage`)**: Reviews stimulus length (500-600 words for CARS, 200-400 for Science), reading grade level, vocabulary density, and empirical data validity.
  - **Study Guide Generator (`/study-guide`)**: Synthesizes high-yield clinical takeaway sheets and active recall summaries from passage sets.

### 8. Streamlined Hero Landing & Quick-Start Presets (`HeroLanding.jsx` / `wizard.css`)
- **Clean Two-Action Canvas**: Focuses the educator on two clear primary pathways: **"Create Questions"** (launching the Guided Wizard) and **"Question Bank"** (navigating to the verified repository).
- **Instant Section Quick-Start Presets**: 4 quick preset buttons configured with official AAMC parameters:
  - **Chemical and Physical Foundations (CP)**: Pacing 95s, Passage-Based, High difficulty.
  - **Critical Analysis and Reasoning Skills (CARS)**: Pacing 100s, Passage-Based, High difficulty.
  - **Biological and Biochemical Foundations (BB)**: Pacing 95s, Passage-Based, High difficulty.
  - **Psychological, Social, and Biological Foundations (PS)**: Pacing 95s, Passage-Based, Medium difficulty.
- **Accessible WCAG AA Semantics**: Implemented with native semantic `<button>` controls, explicit `aria-label`s on brand link and preset chips (`aria-label={"Start with " + preset.label + " preset"}`), and decorative icons hidden via `aria-hidden="true"`.

### 9. pgvector Semantic RAG & Anti-Collision Shield (`rag.py`, `embeddings.py`, `dedup_clustering.py`)
- **1536-Dimensional Neural Embeddings**: Generates real-time vector embeddings for questions and passages via OpenAI `text-embedding-3-small` stored in PostgreSQL `VECTOR(1536)`.
- **HNSW Vector Cosine Index**: High-speed indexing (`idx_questions_embedding_hnsw`) with `m=16`, `ef_construction=64`, and runtime `hnsw.ef_search = 40`.
- **Dual-Layer Anti-Collision Shield**: Combines pgvector semantic similarity distance ($1 - \text{cosine\_similarity}$) with n-gram lexical overlap ($>75\%$), eliminating conceptual repetition before items reach the bank.
- **Hierarchical Clustering**: Exposes `/api/v1/dedup/clusters` to group borderline items into conceptual families for batch resolution.

### 10. 5-Slot Cognitive Blueprints, Domain Rotation & Hard Slot Budget (`passage_blueprints.py`, `slot_worker.py`)
- **Pedagogical Passage Slot Specialization**: Standardized 5-slot cognitive blueprints ensuring every passage set contains an authentic distribution of reasoning skills:
  - **CARS**: Slot 1 (Foundations), Slot 2 (Within Text), Slot 3 (Within Text - Contrast), Slot 4 (Beyond Text - Novel Application), Slot 5 (Beyond Text - Challenge Assumption).
  - **Science**: Slot 1 (Foundational Knowledge), Slot 2 (Scientific Reasoning), Slot 3 (Research Design), Slot 4 (Data-based Reasoning), Slot 5 (Novel Hypothesis / Experimental Manipulation).
- **Modulo Attempt Rotation (`resolve_slot_domain_index`)**: When an item requires regeneration or replenishment, the worker rotates deterministically through 8 curated CARS application domains or 8 Science experimental conditions:
  $$\text{domain\_index} = (\text{base\_index} + \text{attempt} - 1) \pmod 8$$
- **Hard 36-Call LLM Slot Budget**: Enforces a strict ceiling of `MAX_LLM_CALLS_PER_SLOT = 36` (3 attempts $\times$ 12 calls) per slot to prevent runaway token costs and guarantee predictable batch execution.

---

## ⚡ Quickstart Guide

### 1. Start PostgreSQL with pgvector (Docker)
```bash
docker compose up -d
```
*Spins up PostgreSQL 16 with `pgvector` extension (`pgvector/pgvector:pg16`) on `localhost:5432` with database `mcat_db`.*

### 2. Backend Setup
```bash
# Option A: Modern uv workflow (recommended)
uv venv
source .venv/bin/activate
uv pip install -r backend/requirements-dev.txt

# Option B: Standard Python venv
python3 -m venv .venv
source .venv/bin/activate
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

Run the full backend test suite covering schemas, routing logic, strict quality gates, SVG & FLUX synthesis, pgvector operations, and token calculations:

```bash
# Run backend deterministic test suite (501 deterministic tests across 74 modules; 511 total backend tests across 75 files)
# Smart auto-skip: If PostgreSQL is offline, 394 pure unit tests pass and 99 DB tests skip cleanly
# conftest.py strips provider keys and enables OFFLINE_MODE: no test ever calls a live LLM
source .venv/bin/activate
pytest -v  # pyproject.toml sets the test path, PYTHONPATH and the "not live_e2e" marker

# Run backend linter and formatter check
ruff check .
ruff format --check .
```

Verify frontend code hygiene, unit tests, and production bundle:

```bash
# Run frontend unit tests (140 passed across 16 test files)
pnpm test:frontend

# Run frontend linter (oxlint: 0 warnings, 0 errors)
pnpm --dir frontend lint

# Verify optimized production build (compiles cleanly via Vite 8)
pnpm --dir frontend build
pnpm lint

# Build production bundle (vite build)
pnpm build
```

### Monorepo Orchestration Scripts Reference

| Command | Action |
| :--- | :--- |
| `pnpm dev` | Starts FastAPI backend (port 8000) and Vite frontend (port 5173) with automatic port cleanup |
| `pnpm run clean:ports` | Kills lingering processes on ports 8000 and 5173 (`scripts/clean-ports.mjs`) |
| `pnpm run sync:taxonomy` | Syncs `mcat_dependent_taxonomy.json` from backend to frontend constants |
| `pnpm run db:seed` | Seeds high-yield practice questions and reading passages into PostgreSQL |
| `pnpm run db:clean-duplicates` | Safely purges discarded duplicate drafts and archived slots from PostgreSQL |
| `pnpm run lint:all` | Runs full-stack linting (`uv run ruff check .` + `pnpm --dir frontend lint`) |
| `pnpm run test:all` | Runs full-stack test suites (501 backend tests + 140 frontend tests) |
| `pnpm run format` | Formats all Python files via Ruff |
| `pnpm --dir frontend run check:css` | Scans for unused or missing CSS classes across all JSX and CSS files |

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
│   ├── API.md                   # Complete REST & SSE API specification (48 operations across 42 unique paths including root /metrics)
│   ├── CLIENT_SYSTEM_AND_WORKFLOW_GUIDE.md # Client system & operational workflow guide
│   ├── TESTING_AND_QA.md        # Pytest test suite (501 deterministic tests across 74 modules; 511 total backend tests across 75 files) & TestSprite E2E specs
│   ├── TOKEN_TRACKING.md        # Dual-provider inference pricing & mathematical cost engine
│   ├── SETUP_AND_CONFIG.md      # Installation, deployment (73 Settings fields) & FAQs
│   └── MCAT_RUBRIC.md           # 100-point psychometric rubric & authoring standards
├── scripts/
│   └── clean_duplicate_artifacts.py # Database discarded duplicate cleanup utility (pnpm run db:clean-duplicates)
├── e2e/                         # Playwright E2E scenarios (TC001-TC015) and test plan
│   ├── TC0xx_*.py               # One script per scenario (run with python3 e2e/<file>)
│   ├── standard_prd.json        # Product requirements used to generate the scenarios
│   └── testsprite_frontend_test_plan.json # Test plan definition
├── backend/
│   ├── README.md                # Dedicated backend developer guide (74 deterministic modules / 501 tests; 511 total backend tests across 75 files)
│   ├── requirements.txt         # Runtime dependencies (requirements-dev.txt adds pytest, pytest-asyncio, pytest-cov, ruff)
│   ├── scripts/
│   │   └── seed_questions.py    # CLI database seeding script with authentic AAMC rubrics
│   ├── tests/                   # 75 test modules (501 passing deterministic unit/integration tests; 10 live_e2e tests)
│   │   ├── conftest.py                         # Pytest fixtures: offline DB socket probe, credential stripping, async client, patch_llm
│   │   ├── factories.py                        # Shared builders: make_draft/question/request/usage/completion/state, collect_events
│   │   ├── test_additional_instructions.py     # Educator custom instructions and prompt builder integration
│   │   ├── test_agents.py                      # Heuristics, agent mocking, blind solver & quality gates
│   │   ├── test_ai_native_planning.py          # Dynamic batch brainstorming, AI slot blueprinting, and passage claim extraction
│   │   ├── test_anthropic.py                   # Multi-provider switching, Anthropic models, prompt cache pricing & API keys
│   │   ├── test_api_ai.py                      # AI Copilot endpoints: prompt enhancement, question refinement & study guides
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
│   │   ├── test_dedup_decomposition.py         # Unit tests for decomposed dedup modules (clustering, metrics)
│   │   ├── test_deterministic_gate.py          # Tests that the deterministic validator gate runs before LLM review in the review loop
│   │   ├── test_draft_parser.py                # Strict JSON repair, markdown stripping and schema validation
│   │   ├── test_e2e_live.py                    # Live end-to-end integration tests (10 tests marked live_e2e)
│   │   ├── test_engine_cleanup.py              # The workflow stream must not leak worker tasks when its consumer stops reading
│   │   ├── test_engine_slices.py               # Unit tests for the pure, closure-free pieces sliced out of ``workflow.engine``
│   │   ├── test_extractors.py                  # Polymorphic question extractors (field, options, keys, answer text)
│   │   ├── test_http_caching.py                # HTTP Cache-Control, ETag headers & 304 conditional revalidation
│   │   ├── test_image_calls.py                 # Retry behaviour and response handling of the provider image calls (HTTP mocked)
│   │   ├── test_in_flight_pool_and_dedup.py    # Regression tests for in-flight deduplication pool and batch finalization
│   │   ├── test_index_migration.py             # The redundant single-column question indexes are dropped, covering composites stay
│   │   ├── test_job_stream_consumer.py         # The shared stream reader and request builder behind job runs and refills
│   │   ├── test_live_job_finalization.py       # Standalone /generate runs must always finalize their job and batch rows
│   │   ├── test_llm_budget.py                  # Hard per-slot LLM call budget and the free duplicate re-check after rewrites
│   │   ├── test_llm_call.py                    # Tests for call_llm request construction and retry behavior (provider mocked)
│   │   ├── test_logging_context.py             # Correlation ids bound with bind_log_context appear on log records, including in child tasks
│   │   ├── test_medical_imaging.py             # All 7 medical modalities detection, safety sanitization & prompt synthesis
│   │   ├── test_mock_fixture_table.py          # The seven canned mock drafts must stay byte-identical when their source representation changes
│   │   ├── test_modular_cleanup.py             # Regression checks for modular service extractions
│   │   ├── test_multi_batch_concurrency.py     # Multi-batch semaphore stress tests and rate-limit backoff
│   │   ├── test_offline_mode.py                # Mocks are an explicit opt-in: no credentials without OFFLINE_MODE must fail loudly
│   │   ├── test_openai.py                      # OpenAI text and image provider wiring (HTTP mocked)
│   │   ├── test_ops_and_resolution.py          # Request ids, body limits, error sanitising, liveness, batch resolution helpers
│   │   ├── test_passage_blueprints_decomposition.py # Unit tests for decomposed 5-slot passage blueprint structures
│   │   ├── test_passage_set_blueprints_and_dedup.py # Integrated passage set blueprints and anti-collision checks
│   │   ├── test_pedagogy.py                    # Pedagogical format & 3-card explanation tests
│   │   ├── test_pgvector_rag.py                # pgvector RAG, normalized embeddings, cosine metrics & hybrid search
│   │   ├── test_pricing_table.py               # Verified provider prices, model-based rate resolution, cache billing and image costs
│   │   ├── test_projected_reads.py             # Lightweight repository reads used by the batch worker
│   │   ├── test_prometheus_metrics.py          # Prometheus /metrics exposition & telemetry middleware tracking
│   │   ├── test_prompt_builder_blocks.py       # Decomposed generator user prompt sub-blocks (pedagogy, traps, stimulus)
│   │   ├── test_question_repository_decomposition.py # DAL split unit tests (question_queries & question_mutations)
│   │   ├── test_question_status_refill.py      # Status enums, active question helpers and deficit calculations
│   │   ├── test_recovery.py                    # Startup recovery: orphaned running jobs must not stay 'running' forever
│   │   ├── test_repository_mappers.py          # Pure mapping functions between SQLAlchemy models & Pydantic schemas
│   │   ├── test_request_secrets.py             # Client-supplied API keys must never be persisted or returned
│   │   ├── test_schema_migrations_decomposition.py # Schema migrations & vector index creation tests
│   │   ├── test_schemas.py                     # Pydantic schema validation tests
│   │   ├── test_shared_helpers.py              # Shared helpers extracted during cleanup keep their exact semantics
│   │   ├── test_slot_worker.py                 # 5-slot cognitive blueprint worker & attempt rotation tests
│   │   ├── test_soft_delete_batch_integrity.py # Soft-delete batch cascade integrity tests
│   │   ├── test_sse_keepalive.py               # SSE keep-alive comments while the engine is quiet
│   │   ├── test_stream_emitter.py              # Workflow SSE queue draining, timeout polling & terminal event assembly
│   │   ├── test_structured_output.py           # Model output is validated strictly, repaired once, and never silently defaulted
│   │   ├── test_target_count_guarantee.py      # Dynamic job allocation, slot replenishment and target count guarantees
│   │   ├── test_taxonomy_sync.py               # Byte-for-byte AAMC taxonomy synchronization between backend and frontend
│   │   ├── test_tokens.py                      # Token cost accumulation across providers and config cascade
│   │   ├── test_validators.py                  # Unit tests for the deterministic question validators (no LLM, no database)
│   │   ├── test_visuals.py                     # AI image generation, visual stimulus routing and cost accumulation
│   │   ├── test_workflow.py                    # Streaming workflow execution and event metadata
│   │   └── test_workflow_nodes_decomposition.py # Node execution unit tests (generator, reviewer, finalize)
│   └── app/
│       ├── main.py              # FastAPI app with modern lifespan context & security headers
│       ├── core/                # Core configurations & Pydantic V2 settings
│       │   ├── config.py        # Settings and model configuration
│       │   ├── pricing.py       # Price fallback tables & LiteLLM registry lookup
│       │   ├── concurrency.py   # Process-wide pipeline semaphore
│       │   ├── logging.py       # Structured logging configuration
│       │   ├── errors.py        # Standardized domain exceptions & error codes
│       │   └── __init__.py
│       ├── data/                # Static taxonomy data
│       │   ├── mcat_dependent_taxonomy.json # AAMC-aligned foundational concepts and skills
│       │   └── thematic_angles.py # Curated science and CARS thematic angle distributions
│       ├── middleware/          # ASGI middlewares
│       │   ├── telemetry.py     # Prometheus HTTP request timing & status tracking
│       │   └── __init__.py
│       ├── db/                  # Database connectivity & session lifecycle
│       │   ├── base.py          # SQLAlchemy declarative base
│       │   ├── session.py       # Async engine, connection pool & auto-migrations
│       │   ├── init_db.py       # Schema initialization, pgvector extension & FTS indexes
│       │   ├── schema_migrations.py # Non-destructive DDL migrations & HNSW vector index
│       │   └── __init__.py
│       ├── models/              # SQLAlchemy ORM models
│       │   ├── batch.py         # GenerationBatchModel for multi-question generation runs
│       │   ├── job.py           # GenerationJobModel for background worker jobs
│       │   ├── passage.py       # PassageModel for shared reading stimuli
│       │   ├── question.py      # QuestionModel with JSONB columns, VECTOR(1536) embedding & HNSW index
│       │   └── __init__.py
│       ├── repositories/        # Data Access Layer (DAL)
│       │   ├── _filters.py            # Shared soft-delete clauses
│       │   ├── batch_repository.py    # Staged batch run queries & persistence
│       │   ├── job_repository.py      # Background worker job state tracking
│       │   ├── passage_repository.py  # Shared stimulus reading passage queries
│       │   ├── question_repository.py # Facade combining queries and mutations
│       │   ├── question_queries.py    # Decomposed question read queries, filtering & FTS
│       │   ├── question_mutations.py  # Decomposed question write, update & soft-delete operations
│       │   ├── mappers.py             # Pure model mapping functions for Questions & Passages
│       │   ├── query_builders.py      # Shared SQLAlchemy query filters & difficulty aliases
│       │   └── __init__.py
│       ├── schemas/             # Domain Pydantic V2 schemas
│       │   ├── extractors.py    # Polymorphic question model extraction helpers
│       │   ├── mcat.py          # Official AAMC MCAT sections & subtopic taxonomy
│       │   ├── question.py      # QuestionOption, QuestionDraft, Question, status helper
│       │   ├── status.py        # QuestionStatus enum & lifecycle transitions
│       │   ├── token.py         # TokenUsage & TokenCostAccumulator schemas
│       │   ├── workflow.py      # GenerationRequest, ReviewScore, WorkflowEvent
│       │   └── __init__.py
│       ├── services/            # Background Worker Services & AI Pipelines
│       │   ├── ai_copilot.py    # In-flight educator copilot tools (enhance instructions, refine, audit, study guide)
│       │   ├── rag.py           # Semantic RAG retrieval & exemplar extraction
│       │   ├── embeddings.py    # Real-time OpenAI text-embedding-3-small generation
│       │   ├── dedup_clustering.py # Hierarchical duplicate clustering & cluster queries
│       │   ├── dedup_metrics.py # Multi-metric mathematical similarity calculation
│       │   ├── batch_runner.py  # High-level pool managing 5-question (1-job) & 50-question (10-job) batches
│       │   ├── batch_worker.py  # Dedicated background worker executing parallel job attempts & trials
│       │   ├── batch_concurrency.py # Process-wide worker semaphores & rate throttles
│       │   ├── batch_resolution.py  # Duplicate cluster resolution & deficit replenishment
│       │   ├── csv_export.py    # Tabular CSV streaming serialization
│       │   ├── deduplication.py # Real-time multi-metric similarity & anti-collision service
│       │   ├── metrics.py       # Prometheus text exposition metric collection
│       │   ├── readability.py   # Flesch-Kincaid & vocabulary density heuristics
│       │   └── __init__.py
│       ├── agents/              # Multi-agent decision logic & prompts
│       │   ├── _mock_tokens.py  # Mock token cost fixtures
│       │   ├── base.py          # LiteLLM client & calculate_token_cost()
│       │   ├── batch_planner.py # AI native batch planner & claim extraction
│       │   ├── blind_solver.py  # Independent key validation & agreement agent
│       │   ├── draft_parser.py  # Strict draft JSON parsing & trap classification
│       │   ├── generator.py     # Fused question generator & self-critique agent
│       │   ├── image_generator.py # Programmatic SVG & FLUX-2-klein-4b visual generator
│       │   ├── medical_imaging.py # High-fidelity anatomical & diagnostic clinical prompt synthesis
│       │   ├── mock_fixtures.py # Mock fallback questions & heuristic rubrics
│       │   ├── mock_drafts.py   # Table of the seven canned mock drafts
│       │   ├── option_balancer.py # Mathematical option length balancing (±15%)
│       │   ├── prompt_builder.py# User prompt assembly & cross-item calibration
│       │   ├── prompts.py       # Centralized system prompts & rubrics
│       │   ├── regenerator.py   # Autonomous remediation engine agent (<= 80 trigger)
│       │   ├── reviewer.py      # Question Reviewer Agent (100-pt rubric)
│       │   ├── standards.py     # Shared option-length and passage-length authoring standards
│       │   ├── validators.py    # Deterministic structural validators & dash repair (free, pre-review)
│       │   └── __init__.py
│       ├── workflow/            # Multi-agent workflow engine
│       │   ├── engine.py        # Core asynchronous workflow runner & event emitters
│       │   ├── engine_layout.py # Run layout, SlotLedger & SSE event formatting
│       │   ├── stream_emitter.py# Dedicated SSE lifecycle and status event emitter
│       │   ├── slot_worker.py   # 5-slot cognitive blueprint execution & attempt rotation
│       │   ├── draft_parser.py  # Strict JSON parsing, markdown stripping & draft validation
│       │   ├── passage_blueprints.py # CARS & Science 5-slot cognitive blueprint definitions
│       │   ├── review_loop.py   # Deterministic gate, reviewer, Blind-Solver & remediation loop
│       │   ├── passage_prep.py  # Per-item requests & shared passage/visual drafting
│       │   ├── dedup_inflight.py# Duplicate detection vs. DB, siblings & in-flight drafts
│       │   ├── live_job_store.py# Question & job/batch persistence for live runs
│       │   ├── node_generator.py# Generator worker node execution
│       │   ├── node_reviewer.py # Reviewer & Blind-Solver worker node execution
│       │   ├── node_finalize.py # Item staging & repository finalization node execution
│       │   ├── nodes.py         # Unified node exports
│       │   ├── routes.py        # route_after_review: Quality Gate routing used by the review loop
│       │   ├── sse.py           # SSE event formatting & keepalive pings
│       │   ├── state.py         # AgentWorkflowState typed dictionary
│       │   └── __init__.py
│       └── api/                 # Modular API Routers
│           ├── admin.py         # Admin authorization dependencies & protected gates
│           ├── router.py        # Central API router aggregator (/api prefix)
│           ├── security.py      # API access key verification & request rate limiters
│           ├── utils.py         # Shared API response helpers & serialization utilities
│           └── v1/
│               ├── ai.py        # AI Copilot studio endpoints (prompt enhancement, refine, audit, study guide)
│               ├── batches.py   # Batch execution runs & staged item retrieval
│               ├── config.py    # Read-only engine configuration & model settings
│               ├── generation.py# SSE streaming question generator endpoint
│               ├── health.py    # Database connectivity & system health checks
│               ├── metrics.py   # Prometheus text exposition endpoint
│               ├── passages.py  # Shared passage stimuli listing & retrieval
│               ├── questions.py # Question Bank CRUD, pgvector semantic search & JSON/CSV exports
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
        ├── styles/              # Modular domain stylesheets (tokens, base, layout, wizard, question, batch, bank, passage, modals, print, study-guide-modal, question-copilot, stage-inspector, accessibility)
        ├── views/               # Top-level screen views (Code-split with React.lazy)
        │   ├── index.js         # Centralized views index
        │   ├── AiValidatedQuestionsView.jsx # Dedicated AI Validated (>80) quality bank
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
        │   ├── copilot/         # AI Copilot Studio components
        │   │   ├── QuestionCopilotStrip.jsx # In-flight educator assistance strip
        │   │   └── index.js
        │   ├── layout/          # Layout components (Navbar, Footer)
        │   │   ├── Footer.jsx           # Infynno Solutions LLP attribution & resource footer
        │   │   ├── Navbar.jsx           # Header with branding, navigation tabs, and theme toggle
        │   │   └── index.js
        │   ├── modals/          # Dialog modals (WCAG AA Focus Trapped)
        │   │   ├── ConfirmationModal.jsx # Accessible confirmation modal replacing window.confirm
        │   │   ├── DeletePassageModal.jsx# Dedicated passage deletion and cascade warning dialog (Hoisted)
        │   │   ├── ExportPaperPreview.jsx # Live print layout previewer
        │   │   ├── ExportPrintModal.jsx   # 6-format Export Studio modal
        │   │   ├── ExportScopeSelector.jsx# Decomposed export scope & filter selector
        │   │   ├── ExportDataFormatPane.jsx# Decomposed CSV / JSON / Anki TSV format pane
        │   │   ├── StudyGuideExportPane.jsx# Decomposed study guide settings pane
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
        │   ├── api.js           # SSE event reader & REST API client (32 methods)
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
