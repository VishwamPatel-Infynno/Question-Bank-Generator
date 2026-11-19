# Infynno MCAT Question Bank Generator - Backend

> **An Infynno Solutions LLP Product • [Infinite Innovations](https://infynno.com/)**  
> High-throughput asynchronous backend service powering the AAMC MCAT Question Studio v2.0.

Built with **Python 3.11+**, **FastAPI**, **LiteLLM**, **SQLAlchemy 2.0 (Async)**, and **PostgreSQL 16**.

---

## 1. Architecture & Modular Layer Separation

The backend is engineered with clear separation of concerns across presentation, orchestration, domain logic, persistence, and background worker services:

```
backend/
├── app/
│   ├── api/                 # Presentation Layer (HTTP & SSE Routers - 48 operations across 42 unique paths including root /metrics)
│   │   ├── admin.py         # Admin authorization dependencies & protected gates
│   │   ├── router.py        # Central API v1 router aggregator (applies the optional API_ACCESS_KEY gate)
│   │   ├── security.py      # Optional X-API-Key dependency & rate limiting for mutating routes
│   │   ├── utils.py         # Shared API response serialization & parameter validation helpers
│   │   └── v1/
│   │       ├── ai.py        # Real-time AI Copilot tools (/enhance-instructions, /refine-question, /audit-passage, /study-guide)
│   │       ├── generation.py # SSE streaming multi-agent orchestrator endpoint
│   │       ├── questions.py  # Question Bank CRUD, pgvector semantic search, approval, duplicate check & override, restoration, permanent purge & exports
│   │       ├── passages.py   # Shared clinical stimulus passages endpoints (list, retrieve, save, soft-delete)
│   │       ├── batches.py    # Multi-question batch execution run endpoints, clustering & refill
│   │       ├── taxonomy.py   # AAMC syllabus hierarchy & dependent taxonomy tree endpoints
│   │       ├── config.py     # Runtime engine configuration, dual-provider settings & pricing (runtime parameters)
│   │       ├── health.py     # Database connectivity & system health checks
│   │       └── metrics.py    # Prometheus text exposition endpoint serving application, database, batch concurrency, and HTTP telemetry
│   ├── workflow/            # Orchestration Layer (async workflow engine)
│   │   ├── engine.py        # Core streaming execution engine & event emitters
│   │   ├── stream_emitter.py # Asynchronous SSE queue consumer, backpressure polling & terminal event construction
│   │   ├── slot_worker.py   # Isolated single-slot worker lifecycle & attempt replenishment
│   │   ├── draft_parser.py  # Strict JSON parsing, markdown stripping, schema validation & deterministic repair
│   │   ├── passage_blueprints.py # CARS & Science 5-slot cognitive blueprint definitions, skill mapping & archetypes
│   │   ├── engine_layout.py # Run layout, SlotLedger & SSE event formatting
│   │   ├── review_loop.py   # Deterministic gate, reviewer, Blind-Solver and remediation loop for one draft
│   │   ├── passage_prep.py  # Per-item requests, cognitive blueprints (Slots 1-5), shared stimulus & visual drafting
│   │   ├── dedup_inflight.py # Duplicate detection vs. DB pool, staged siblings and in-flight drafts
│   │   ├── live_job_store.py # Question and job/batch persistence for standalone live runs
│   │   ├── node_generator.py # Fused Question Generator and agent usage accounting helpers
│   │   ├── node_reviewer.py # Quality audit, dual validation blind solver, and remediation nodes
│   │   ├── node_finalize.py # Visual stimulus, quality gate rejection, and final assembly nodes
│   │   ├── nodes.py         # Unified workflow nodes module with dynamic monkeypatch routing
│   │   ├── routes.py        # route_after_review: Quality Gate routing used by the review loop
│   │   ├── sse.py           # SSE event formatting, keepalive pings, and client-safe payload serialization
│   │   └── state.py         # AgentWorkflowState typed dictionary
│   ├── agents/              # Cognitive Reasoning & Synthesis Layer
│   │   ├── _mock_tokens.py  # Mock token cost fixtures
│   │   ├── base.py          # LiteLLM execution wrapper & sub-micro-cent token cost engine (DeepInfra + Anthropic)
│   │   ├── batch_planner.py # AI native batch thematic planning & blueprint claim extraction
│   │   ├── blind_solver.py  # Blind-solver dual-validation candidate verification agent (fail-closed)
│   │   ├── draft_parser.py  # Strict draft JSON parsing, markdown stripping & cognitive trap extraction
│   │   ├── generator.py     # Fused clinical question synthesis & self-critique agent
│   │   ├── image_generator.py # FLUX-2-klein-4b neural visual & SVG vector generator
│   │   ├── medical_imaging.py # High-fidelity anatomical & clinical diagnostic prompt synthesis (radiology, ECG, histology)
│   │   ├── mock_fixtures.py # Deterministic fallback fixtures for offline resilience
│   │   ├── mock_drafts.py   # Table of the seven canned mock drafts (section x passage/independent)
│   │   ├── option_balancer.py # Mathematical option length balancing (±15%) & anti-guessability
│   │   ├── prompt_builder.py # User prompt assembly & cross-item diversity calibration
│   │   ├── prompts.py       # Centralized system prompts, pacing rules & rubrics
│   │   ├── regenerator.py   # Autonomous remediation agent (<= 80 score trigger; Rule 12 visual retention)
│   │   ├── reviewer.py      # 100-point 4-pillar psychometric auditor agent (with Accompanying Visual Stimulus anti-deduction mandate)
│   │   ├── standards.py     # Shared option-length and passage-length authoring standards
│   │   └── validators.py    # Free deterministic structural validators & dash repair, run before LLM review
│   ├── services/            # Background Worker & AI Subsystems
│   │   ├── __init__.py          # Services facade re-exporting lifecycles, duplicate clustering & export builders
│   │   ├── ai_copilot.py    # Real-time educator copilot tooling (prompt enhancement, refine, audit, study guide)
│   │   ├── rag.py           # Semantic RAG retrieval & exemplar extraction via pgvector
│   │   ├── embeddings.py    # Real-time OpenAI text-embedding-3-small vector generation
│   │   ├── dedup_clustering.py # Hierarchical duplicate clustering & cluster querying
│   │   ├── dedup_metrics.py # Multi-metric similarity calculations (token containment, jaccard, sequence matcher)
│   │   ├── batch_runner.py  # High-level pool managing 5 Questions (1-job) and 50 Questions (10-job batch)
│   │   ├── batch_worker.py  # Dedicated background worker executing parallel job attempts, trial counts & recovery
│   │   ├── batch_concurrency.py # Process-wide worker semaphores, active run tracking & rate-limiting throttles
│   │   ├── batch_resolution.py  # Duplicate cluster leader selection & automated deficit replenishment calculation
│   │   ├── csv_export.py        # Tabular CSV streaming serialization
│   │   ├── deduplication.py # Multi-metric similarity scoring, pairwise clustering & anti-collision service
│   │   ├── metrics.py       # Real-time Prometheus metric collectors, counter updates & histogram exposition
│   │   └── readability.py   # Flesch-Kincaid & vocabulary density heuristics
│   ├── repositories/        # Data Access Layer (DAL)
│   │   ├── _filters.py            # Shared soft-delete clauses (active_question_clause, active_passage_clause)
│   │   ├── question_queries.py    # Query operations, paginated search, pgvector similarity, metrics, status counts & QuestionHead
│   │   ├── question_mutations.py  # Atomic writes, single/batch upserts, embeddings persistence, deletions, restorations & status updates
│   │   ├── question_repository.py # Unified CQRS facade re-exporting all DAL operations
│   │   ├── mappers.py             # Pure model mapping functions for Questions and Passages
│   │   ├── query_builders.py      # Shared SQLAlchemy query filters, difficulty aliases & deferred loading
│   │   ├── batch_repository.py    # Staged batch run queries & persistence
│   │   ├── job_repository.py      # Background worker job state tracking
│   │   └── passage_repository.py  # Shared stimulus reading passage queries, soft-deletion, and cascade question removal
│   ├── models/              # Persistence Layer (SQLAlchemy 2.0 ORM Entities)
│   │   ├── question.py      # QuestionModel with VECTOR(1536) embedding, JSONB duplicate_info, is_deleted, deleted_at & composite + HNSW indexes
│   │   ├── passage.py       # PassageModel for multi-item shared reading stimuli with is_deleted & deleted_at
│   │   ├── batch.py         # GenerationBatchModel for multi-question generation runs
│   │   └── job.py           # GenerationJobModel for background batch jobs with persisted trial_count
│   ├── schemas/             # Domain Transfer Layer (Pydantic V2)
│   │   ├── __init__.py          # Domain transfer facade re-exporting schemas, extractors & token accumulators
│   │   ├── mcat.py          # MCAT sections, difficulty tiers (low/medium/high) & subtopic taxonomy
│   │   ├── token.py         # TokenUsage & TokenCostAccumulator schemas
│   │   ├── question.py      # QuestionOption, QuestionDraft, Question, determine_question_status helper
│   │   ├── status.py        # QuestionStatus enum & lifecycle transitions
│   │   ├── extractors.py    # Polymorphic question extractors (field, options, keys, answer text)
│   │   └── workflow.py      # GenerationRequest, ReviewScore, WorkflowEvent
│   ├── core/                # Configuration & Settings
│   │   ├── config.py        # Pydantic SettingsConfigDict, dual-provider defaults & settings (73 fields)
│   │   ├── pricing.py       # Model price fallback tables and LiteLLM registry lookup
│   │   ├── concurrency.py   # Process-wide pipeline semaphore shared by all runs
│   │   ├── logging.py       # Centralized console logging handler & formatter
│   │   └── errors.py        # Standardized domain exceptions & error codes
│   ├── middleware/          # ASGI Middlewares
│   │   ├── telemetry.py     # Prometheus HTTP request timing, status code counters & latency histograms
│   │   └── __init__.py
│   ├── db/                  # Database Lifecycle & Migrations
│   │   ├── base.py          # Declarative Base
│   │   ├── init_db.py       # Ordered idempotent migration steps, pgvector extension, composite indexes & FTS
│   │   ├── schema_migrations.py # Schema migrations, HNSW cosine index (idx_questions_embedding_hnsw), foreign keys & column additions
│   │   └── session.py       # Async engine, connection pool & startup migrations
│   └── data/                # Static Taxonomy & Curricula
│       ├── mcat_dependent_taxonomy.json # AAMC official syllabus foundational concepts & skills
│       └── thematic_angles.py # Curated science and CARS thematic angle distributions
├── scripts/                 # Maintenance & Seeding Utilities
│   └── seed_questions.py    # Sample question bank seeder
└── tests/                   # Deterministic Automated Test Suite (76 deterministic modules / 512 tests + 1 live E2E module with 10 tests = 522 total backend tests across 77 files)
    ├── conftest.py                         # Pytest fixtures: offline DB socket probe, credential stripping, async client, patch_llm
    ├── factories.py                        # Shared builders: make_draft/question/request/usage/completion/state, collect_events
    ├── test_additional_instructions.py     # Educator custom authoring instructions and prompt builder integration
    ├── test_agents.py                      # Multi-agent worker nodes, heuristics, blind solver routing & quality gates
    ├── test_ai_native_planning.py          # Dynamic batch brainstorming, AI slot blueprinting, and passage claim extraction
    ├── test_anthropic.py                   # Multi-provider switching, Anthropic models, prompt cache pricing & API keys
    ├── test_api_ai.py                      # AI Copilot endpoints: prompt enhancement, question refinement & study guides
    ├── test_api_duplicates_passages_health.py # Duplicate detection, passage lifecycle, CORS and health endpoints
    ├── test_api_generation.py              # Generation flows through the API: batches, passage sets, visuals
    ├── test_api_hardening.py               # API hardening: admin gate, image safety, safe defaults, write validation
    ├── test_api_questions.py               # Question bank API: CRUD, approval, status lifecycle, pagination, slim projection
    ├── test_api_security.py                # Optional shared-secret gate and request input limits
    ├── test_authoring_standards.py         # One source of truth for authoring numbers; DDL helper that never locks migrated tables
    ├── test_batch_aggregate_lock.py        # Concurrent refreshes of one batch must serialize and stay consistent
    ├── test_batch_autonomous_retry.py      # Autonomous 3-trials policy, trial count persistence and in-flight retries
    ├── test_batch_dedup_hard_delete.py     # Hard-delete duplicate purge during batch deduplication and completion guards
    ├── test_batch_jobs_flow.py             # Background batch runner, job concurrency and refill preservation
    ├── test_batch_retry_resume.py          # Retry/resume must run the jobs it selected, and stuck jobs must never hang
    ├── test_batch_review_withholding.py    # Review queue withholding during batch execution and atomic promotion
    ├── test_batch_state.py                 # Batch correctness: terminal resolution, stop/refill guards, cost accounting
    ├── test_blind_solver_vote.py           # Blind solver: robust key parsing, layout-varied sampling and majority voting
    ├── test_config_and_pricing_polish.py   # Config defaults, pricing lookups & vendor-masked settings
    ├── test_config_docs.py                 # Settings fields, .env.example and the setup doc must not drift apart
    ├── test_cpu_async_hygiene.py           # Dedup pruning keeps verdicts, big pools leave the loop, litellm stays lazy
    ├── test_database_structure.py          # SQLAlchemy models, cascade deletion and constraint tests
    ├── test_deduplication.py               # Multi-metric similarity, token containment, options overlap and auto-resolve
    ├── test_dedup_decomposition.py         # Decomposed dedup clustering and multi-metric similarity unit tests
    ├── test_deterministic_gate.py          # Tests that the deterministic validator gate runs before LLM review in the review loop
    ├── test_draft_parser.py                # Strict JSON repair, markdown stripping, schema validation & deterministic repair
    ├── test_e2e_live.py                    # Live end-to-end integration tests (10 tests marked live_e2e)
    ├── test_engine_cleanup.py              # The workflow stream must not leak worker tasks when its consumer stops reading
    ├── test_engine_slices.py               # Unit tests for the pure, closure-free pieces sliced out of ``workflow.engine``
    ├── test_extractors.py                  # Polymorphic question extractors (field, options, keys, answer text)
    ├── test_http_caching.py                # HTTP Cache-Control, ETag headers & 304 conditional revalidation
    ├── test_image_calls.py                 # Retry behaviour and response handling of the provider image calls (HTTP mocked)
    ├── test_in_flight_pool_and_dedup.py    # Per-job in-flight dedup pool and cross-slot collision checks
    ├── test_index_migration.py             # The redundant single-column question indexes are dropped, covering composites stay
    ├── test_job_stream_consumer.py         # The shared stream reader and request builder behind job runs and refills
    ├── test_live_job_finalization.py       # Standalone /generate runs must always finalize their job and batch rows
    ├── test_llm_budget.py                  # Hard per-slot LLM call budget and the free duplicate re-check after rewrites
    ├── test_llm_call.py                    # Tests for call_llm request construction and retry behavior (provider mocked)
    ├── test_logging_context.py             # Correlation ids bound with bind_log_context appear on log records, including in child tasks
    ├── test_medical_imaging.py             # All 7 medical modalities detection, gross anatomy safety sanitization & OpenAI content moderation fallback retry
    ├── test_mock_fixture_table.py          # The seven canned mock drafts must stay byte-identical when their source representation changes
    ├── test_modular_cleanup.py             # Regression checks for modular service extractions
    ├── test_multi_batch_concurrency.py     # Multi-batch semaphore stress tests and rate-limit backoff
    ├── test_offline_mode.py                # Mocks are an explicit opt-in: no credentials without OFFLINE_MODE must fail loudly
    ├── test_openai.py                      # OpenAI text and image provider wiring (HTTP mocked)
    ├── test_ops_and_resolution.py          # Request ids, body limits, error sanitising, liveness, batch resolution helpers
    ├── test_optimizations_fullstack.py     # Session injection reusability, slim batch queries, and passage repository mutations
    ├── test_passage_blueprints_decomposition.py # Unit tests for decomposed 5-slot passage blueprint structures
    ├── test_passage_set_blueprints_and_dedup.py # CARS & Science slot blueprints, psychometric archetypes, and slot specialization directives
    ├── test_pedagogy.py                    # Pedagogical format & 3-card explanation tests
    ├── test_pgvector_rag.py                # pgvector RAG, normalized embeddings, cosine metrics & hybrid search
    ├── test_pricing_table.py               # Verified provider prices, model-based rate resolution, cache billing and image costs
    ├── test_projected_reads.py             # Lightweight repository reads used by the batch worker
    ├── test_prometheus_metrics.py          # Prometheus/OpenMetrics exposition and telemetry middleware tracking
    ├── test_prompt_builder_blocks.py       # Decomposed generator user prompt sub-blocks (pedagogy, traps, stimulus)
    ├── test_question_repository_decomposition.py # DAL CQRS decomposition, queries/mutations domain separation, and QuestionHead immutability
    ├── test_question_status_refill.py      # Status enums, active question helpers and deficit calculations
    ├── test_recovery.py                    # Startup recovery: orphaned running jobs must not stay 'running' forever
    ├── test_repository_mappers.py          # Pure mapping functions between SQLAlchemy models & Pydantic schemas
    ├── test_request_secrets.py             # Client-supplied API keys must never be persisted or returned
    ├── test_schemas.py                     # Pydantic schema validation tests
    ├── test_schema_migrations_decomposition.py # Schema migrations & HNSW vector index creation tests
    ├── test_shared_helpers.py              # Shared helpers extracted during cleanup keep their exact semantics
    ├── test_slot_worker.py                 # Isolated question slot execution, attempt replenishment, quality gate routing, and SlotWorkerContext
    ├── test_soft_delete_batch_integrity.py # Soft-delete & restore preserving batch progress metrics
    ├── test_sse_keepalive.py               # SSE keep-alive comments while the engine is quiet
    ├── test_stream_emitter.py              # Workflow SSE queue draining, timeout polling & terminal event assembly
    ├── test_structured_output.py           # Model output is validated strictly, repaired once, and never silently defaulted
    ├── test_target_count_guarantee.py      # Dynamic job allocation, slot replenishment and target count guarantees
    ├── test_taxonomy_sync.py               # Byte-for-byte AAMC taxonomy synchronization between backend and frontend
    ├── test_tokens.py                      # Token cost accumulation across providers and config cascade
    ├── test_validators.py                  # Unit tests for the deterministic question validators (no LLM, no database)
    ├── test_visuals.py                     # AI image generation, visual stimulus routing and cost accumulation
    ├── test_workflow.py                    # Streaming workflow execution and event metadata
    └── test_workflow_nodes_decomposition.py # Lifecycle node decomposition, facade re-exports, object identity, and monkeypatch synchronization
```

---

## 2. Multi-Agent Workflow Engine

The multi-agent workflow coordinates a 3-step autonomous pipeline through a strict psychometric contract:

```mermaid
graph TD
    Start([Generation Request]) --> NodeFused[Fused Draft & Self-Critique Node]
    
    NodeFused --> Gate[Deterministic Validator Gate]
    Gate -->|Blocking defect| NodeRegen[Remediation Node]
    Gate -->|Clean| NodeRev[Independent Reviewer Node]
    NodeRev --> Solver[Blind Solver Node]
    Solver --> ScoreCheck{Score > 80 & key confirmed?}
    ScoreCheck -->|Yes & Needs Diagram| NodeImg[AI Image Node]
    ScoreCheck -->|Yes & Text Only| NodeFin[Finalize & Persist Node]
    NodeImg --> NodeFin
    NodeRegen --> NodeRev
    ScoreCheck -->|Yes & Needs Diagram| NodeImg
    ScoreCheck -->|Yes & Text Only| NodeFin
    ScoreCheck -->|No & Cycles < 3| NodeRegen
    ScoreCheck -->|No & Cycles >= 3| NodeReject[Strict Quality Gate Reject]
    
    NodeReject --> Discard([Discard Candidate & Halt])
    NodeFin --> Success([Stream to Review Desk / Persist])
```

- **Fused Draft-and-Critique Entry Point**: Drafts question and generates immediate 100-point self-critique in a single pass (`fused_generator_node`), combining drafting and self-critique in one inference round-trip; the independent reviewer and blind solver still audit every draft by default (`ALWAYS_INDEPENDENT_REVIEW`).
- **Passing Threshold**: A question candidate must score **$> 80$** out of 100 on the standardized rubric to be approved for publication (`config.passes_quality_gate`, default `PASSING_SCORE_THRESHOLD=80`).
- **Deterministic Gate & Fail-Closed Checks**: Before any LLM review, `validators.py` checks structure and repairs forbidden dashes. The Reviewer runs first and the Blind Solver after it by default (`PARALLEL_REVIEW_AND_SOLVE=true` runs them concurrently); both raise `QualityCheckUnavailableError` rather than passing an item they could not check. Mock fixtures are used only when no credentials are configured.
- **Option Symmetry & Anti-Guessability**: Generator and Reviewer enforce word count parity (within 3 words, or 20% of the average for longer options) across all 4 options ($A, B, C, D$), parallel grammar, and balanced qualifiers to eliminate test-wiseness guessing cues.
- **Anti-AI Formatting Standard**: Strictly forbids em dashes, en dashes, or double hyphens; standard single hyphens (`-`) only.
- **3-Part Structured Mentor Explanations**: Renders pedagogical explanations across three specialized visual cards: Core Intuition & Proof, Itemized Distractor Analysis, and Primary Cognitive Trap Spotlight.
- **Autonomous Remediation**: If score $\le 80$, the Remediation node (`regenerator.py`) digests the exact weaknesses and distractor recommendations, attempting repairs for up to 3 cycles.
- **Strict Quality Gate**: If score remains $\le 80$ after 3 attempts (or $< 70$ in background batches), the candidate is discarded immediately, preserving question bank integrity.

### 2.1 Medical Imaging Subsystem (`medical_imaging.py` & `image_generator.py`)

The backend integrates an unrestricted medical and scientific imaging engine capable of synthesizing publication-grade visual stimuli across seven distinct clinical modalities:
- **Radiology (`radiology`)**: Axial, coronal, and sagittal CT scans, MRI (T1, T2, FLAIR sequences), standard chest and skeletal radiographs, ultrasound sonograms, and fluoroscopy.
- **Histopathology (`histopathology`)**: H&E light microscopy, cytological smears, and specialized immunohistochemical tissue sections (e.g., glomerular crescents, Reed-Sternberg cells).
- **Gross Anatomy (`gross_anatomy`)**: Clean medical atlas-style organ dissections and neurovascular pathways, with automated prompt sanitization to eliminate gore/trauma triggers.
- **Cellular Microscopy (`cellular_microscopy`)**: High-magnification TEM and SEM electron micrographs displaying organellar ultrastructure (mitochondria, rough ER, Golgi, ciliary axonemes).
- **Physiology & ECG Traces (`physiology_trace`)**: 12-lead ECG rhythm strips, cardiac action potential curves, ventricular pressure-volume (PV) loops, and spirometric flow-volume loops.
- **Clinical Pathology (`clinical_pathology`)**: Clinical diagnostic photographs, dermatological lesions (melanoma margins, erythema migrans), and ophthalmic fundoscopy.
- **Scientific Diagrams (`scientific_diagram`)**: Pure Python programmatic SVG vector graphics for enzyme kinetics, metabolic pathways, and optical schematics.

**Safety Moderation Fallback**: If an image generation provider (such as OpenAI DALL-E / GPT Image) rejects a raw clinical/anatomical prompt with an HTTP 400 content policy exception, the engine automatically reformulates the request into an educational textbook diagram style and retries transparently without interrupting the generation pipeline.

### 2.2 5-Slot Cognitive Blueprints & Modulo Replenishment Rotation (`passage_blueprints.py`, `slot_worker.py`)

To ensure passage sets reflect the multi-faceted cognitive demands of the authentic MCAT, the backend organizes 5-question passage sets into specialized cognitive slots:
- **CARS Archetypes**: Slot 1 (Foundations of Comprehension), Slot 2 (Within the Text - Inferential), Slot 3 (Within the Text - Contrasting Arguments), Slot 4 (Beyond the Text - Novel Application), Slot 5 (Beyond the Text - Challenge Assumption).
- **Science Archetypes**: Slot 1 (Foundational Scientific Knowledge), Slot 2 (Scientific Reasoning & Deduction), Slot 3 (Research Design & Methodology), Slot 4 (Data-based & Statistical Reasoning), Slot 5 (Novel Hypothesis / Experimental Manipulation).
- **Deterministic Domain Rotation**: When a candidate slot fails review or requires replenishment during batch execution, `resolve_slot_domain_index` rotates deterministically through 8 curated CARS application domains or 8 Science experimental conditions:
  $$\text{domain\_index} = (\text{base\_index} + \text{attempt} - 1) \pmod 8$$
- **Hard 36-Call LLM Slot Budget**: Enforces `MAX_LLM_CALLS_PER_SLOT = 36` (3 attempts $\times$ 12 calls) per slot to guarantee finite execution and prevent runaway inference expenses.

### 2.3 pgvector Semantic RAG & Anti-Collision Subsystem (`rag.py`, `embeddings.py`, `dedup_clustering.py`)

- **Vector Persistence**: Uses `pgvector/pgvector:pg16` Docker container with 1536-dimensional float vectors stored in `questions.embedding`.
- **HNSW Cosine Indexing**: Automatically builds `idx_questions_embedding_hnsw` on startup (`m=16`, `ef_construction=64`, distance metric `vector_cosine_ops`), configured with runtime `hnsw.ef_search = 40`.
- **Dual-Shield Anti-Collision Loop**: Combines pgvector semantic similarity distance ($1 - \text{cosine\_similarity}$) with n-gram lexical overlap ($>75\%$). If a collision is flagged, the generator is prompted with an explicit anti-collision directive to re-steer the item.
- **Hierarchical Clustering**: Groups repository items into semantic clusters for batch duplicate resolution and portfolio pruning.

### 2.4 AI Copilot Studio (`ai_copilot.py`)

- **AI Copilot Suite**: Powers real-time educator assistance across 4 specialized endpoints:
  - `/api/v1/ai/enhance-instructions`: Refines authoring prompts with explicit AAMC phrasing, SIRS reasoning verbs, and distractor constraints.
  - `/api/v1/ai/refine-question`: Proposes targeted fixes for ambiguous wording, key clarity, distractor symmetry, or cognitive trap calibration.
  - `/api/v1/ai/audit-passage`: Reviews stimulus length (500-600 words for CARS, 200-400 for Science), reading grade level, vocabulary density, and empirical data validity.
  - `/api/v1/ai/study-guide`: Synthesizes high-yield clinical takeaway sheets and active recall summaries from passage sets.

---

## 3. High-Throughput Pricing & Micro-Cost Engine

Token costs are calculated per request at the lowest execution layer ([`backend/app/agents/base.py`](app/agents/base.py)) and accumulated across all agent cycles:

- **DeepInfra DeepSeek-V4.1-Flash-1017** (standard price): $0.20 input / $0.60 output per 1,000,000 tokens (cached input $0.006); DeepInfra also lists a 51% promo ($0.098 / $0.294), selectable through the `DEEPINFRA_COST_PER_MILLION_*` settings.
- **Claude Haiku 5.5**: $0.10 / $0.50 up to 100K prompt tokens, $0.50 / $2.50 above (cache read $0.01 / write $0.125).
- **gpt-4o-mini**: $0.15 / $0.60 (cached $0.075).
- **FLUX-2-klein-4b**: $0.014 per 1024x1024 image, scaled by resolution. **gpt-image-2.5-flare** is billed per token from the returned usage ($5 text in / $8 image in / $30 out per 1M).
- Rates follow the model's own provider. Sources and verification dates live in `app/core/pricing.py` (`PRICE_SOURCES`); details in `docs/TOKEN_TRACKING.md`.

Calculations are rounded to **7 decimal places** to prevent IEEE 754 floating-point drift:
$$\text{Cost (USD)} = \left(\frac{\text{Prompt Tokens}}{1,000,000} \times R_{\text{in}}\right) + \left(\frac{\text{Completion Tokens}}{1,000,000} \times R_{\text{out}}\right)$$

with the per-model rates above (plus cache read/write terms where the provider bills them).

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
- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health) (overview, `degraded` without a database), [http://localhost:8000/api/health/live](http://localhost:8000/api/health/live) (liveness, no database access) and [http://localhost:8000/api/health/ready](http://localhost:8000/api/health/ready) (readiness, `503` when the database is down)

---

## 5. Automated Testing & Code Quality

### Running Tests
Run the deterministic backend test suite covering endpoints, schemas, database operations, workflow routing, and token cost formulas (see [`docs/TESTING_AND_QA.md`](../docs/TESTING_AND_QA.md) for full specs):

```bash
# Run all unit and integration tests (515 deterministic tests across 77 modules, 525 total backend tests)
# Smart auto-skip: pure unit tests pass offline, DB-dependent tests skip cleanly if PostgreSQL is offline
uv run pytest backend/tests -v
# or using activated virtual environment:
pytest -v

# Run database relational structure tests
uv run pytest backend/tests/test_database_structure.py -v
```

### Code Formatting, Zero-Suppression & Type Precision
Enforce Python code hygiene using **Ruff** (rules E, W, F, I, UP, B, C4, SIM, RET, G004, ASYNC, PT, RUF):

```bash
# Check code style and rules (0 errors policy)
uvx ruff check backend/app
# or using local venv:
ruff check .

# Verify formatting without modification across repository
ruff format --check .

# Automatically fix linting issues
ruff check --fix backend/
```

- **Native Zero-Suppression Standard**: The backend enforces a strict zero-suppression policy (**0 `# noqa` directives across the entire codebase**). Linter findings are resolved architecturally:
  - Mutable `ContextVar` defaults (`B039`) are resolved with immutable `default=None` and runtime fallback (`_log_context.get() or {}`).
  - Timeout argument shadowing (`ASYNC109`) is resolved by renaming to `timeout_seconds: float`.
  - Import registration in `init_db.py` (`F401`) is resolved through explicit `__all__` export manifests.
  - Unused arguments (`ARG001`) and dictionary key iterations (`PERF102`) are resolved by signature cleanup and `.values()` loops.
- **Python Type Precision & Typing Standards**: Bare `dict` type annotations are strictly prohibited across all modules in favor of `dict[str, Any]` and dedicated `TypedDict` schemas (`AgentUsageEntry`, `AgentWorkflowState`). All background coroutines declare explicit return types (`-> None`).

---

## 6. Database Seeding Script

To populate the Question Bank with realistic AAMC MCAT practice questions across all 4 sections:

```bash
source .venv/bin/activate
PYTHONPATH=backend python backend/scripts/seed_questions.py   # or: pnpm run db:seed
```
This generates authentic questions with complete psychometric rubrics, evolution histories, distractors, and token telemetry.

---

## 7. High-Performance Query Pipelining & Layer Facades

### Concurrent Database Query Pipelining (`asyncio.gather`)
To minimize round-trip latencies across high-volume endpoints, read queries are pipelined concurrently across available connections in the `asyncpg` connection pool:
- **`GET /api/questions`**: Concurrently gathers question entities (`get_questions`), matching total count (`count_questions`), and repository token/cost analytics (`get_repository_metrics`), reducing listing latency by 45–60%.
- **`GET /api/passages/{passage_id}`**: Concurrently loads the stimulus reading passage (`get_passage_by_id`) and all associated active questions (`get_questions(passage_id=...)`).
- **`GET /api/batches/{batch_id}`**: Concurrently loads the batch entity (`get_batch_by_id`), all associated job attempts (`get_jobs_by_batch_id`), and all generated question items (`get_questions(include_deleted=True)`).
- **`GET /api/batches/{batch_id}/duplicate-clusters`**: Concurrently loads the batch entity and question items before computing duplicate clusters.

### Native SQL Counting Aggregations
High-traffic counters bypass model hydration and memory-heavy allocations via native SQL aggregation functions:
- **`count_batches(section, status)`**: Executes `SELECT count(GenerationBatchModel.id)` directly in PostgreSQL.
- **`count_passages(section, subtopic, search)`**: Executes native `SELECT count(PassageModel.id)` to support bounded pagination (`limit`, `offset`) on reading passages.

### Single-Session `scoped_session` Dependency Injection Pattern
To eliminate connection thrashing, socket leakage, and uncoordinated transactions, all FastAPI endpoints inject database sessions through FastAPI dependencies (`session: AsyncSession = Depends(get_db_session)`). Data Access Layer (DAL) repository methods accept this single session reference (`session=session`) rather than independently acquiring or closing connections from the connection pool:
- **Zero Socket Thrashing**: Eliminates redundant checkout/checkin cycles within a single HTTP request lifecycle.
- **Atomic Operations**: Guarantees mutations execute within an explicit transactional boundary that rolls back cleanly upon unhandled exceptions.
- **Transparent Mocking & Testing**: Test fixtures inject test-scoped transaction sessions without requiring external network mock configurations.

### Slim Query Projections (`slim=true`)
For high-frequency polling and monitoring (such as background batch progress tracking), endpoints support slim payload projections:
- **`GET /api/batches/{id}?slim=true`**: Loads the batch entity and its job status records while omitting large embedded question JSON payloads, reducing payload sizes by up to 90% and response latencies to sub-5ms (yielding >200 req/s throughput under load).

### Canonical Facade Layer Architecture
Submodule reaching is eliminated through authoritative layer facades:
- **`backend/app/services/__init__.py`**: Re-exports all service operations (`launch_background_batch`, `stop_background_batch`, `cancel_all_background_batches`, `get_active_batch_metrics`, `forget_batch_request`, `find_cluster_duplicates`, `cluster_questions`, `evaluate_duplicate`, `embed_question`, `find_similar_questions`, `generate_questions_csv`, `build_csv_headers`, `build_csv_row`).
- **`backend/app/schemas/__init__.py`**: Re-exports domain transfer schemas (`Question`, `Passage`, `GenerationRequest`, `TokenUsage`), extractors (`extract_field`, `extract_correct_answer_text`), and token accumulators (`sum_usage`).

