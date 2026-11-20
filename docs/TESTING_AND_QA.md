# Testing & Quality Assurance Specification

Engineered by **[Infynno Solutions LLP](https://infynno.com/)** (*"Infinite Innovations"*).

This document details the comprehensive testing architecture, automated quality gates, End-to-End Playwright test specifications, and code hygiene standards governing the **Infynno MCAT Question Bank Generator v2.0**.

---

## 1. Quality Engineering Overview

The system enforces a multi-tiered testing strategy ensuring psychometric integrity, deterministic execution, and seamless user interaction across the entire stack:

```mermaid
graph TD
    subgraph "Tier 1: Static Analysis & Hygiene"
        Ruff[Ruff Python Linter & Formatter]
        Oxlint[Oxlint Frontend Linter]
    end

    subgraph "Tier 2: Backend Pytest Engine"
        UnitTests[549 Deterministic Unit & Integration Tests across 79 Modules]
        LiveE2E[10 Live LLM API E2E Integration Tests - 559 Total Backend Tests across 80 Files]
    end

    subgraph "Tier 3: Browser E2E Automation"
        TestSprite[TestSprite Playwright E2E Suite: TC001-TC015]
    end

    subgraph "Tier 4: Runtime Quality Gate"
        StrictGate[Quality Gate Evaluation (80/70 Threshold)]
        BlindSolver[Blind-Solver Dual Validation Verification]
    end

    Ruff --> UnitTests
    Oxlint --> UnitTests
    UnitTests --> TestSprite
    TestSprite --> StrictGate
    StrictGate --> BlindSolver
```

| Testing Layer | Scope | Tooling | Coverage / Status |
| :--- | :--- | :--- | :--- |
| **Static Code Hygiene** | PEP 8, syntax correctness, modern JS/JSX idioms, zero debug artifacts | **Ruff** (Python 3.11; rules E, W, F, I, UP, B, C4, SIM, RET, G004, ASYNC, PT, RUF), **Oxlint** (React 19) | 0 errors, 0 warnings policy (oxlint last run: 184 files, 106 rules; `ruff check .` and `ruff format --check .` gate CI) |
| **Deterministic Unit & Integration** | Schemas, agents, DAL, API endpoints, tokens, batch runner, deduplication, withholding guards, multi-provider, soft-delete, 3-trial retries, hard-delete dedup, taxonomy sync, HTTP caching, Prometheus telemetry, pgvector RAG, query pipelining, and pagination limits, list/export bounds, packaging sync | **Pytest**, **pytest-asyncio**, PostgreSQL 16 (pgvector) for the 96 tests marked `requires_db` | **549 deterministic tests across 79 modules by default** (559 collected across 80 files, 10 `live_e2e` deselected); without a reachable PostgreSQL, 453 run and 96 skip |
| **Frontend Unit Tests** | Component visual helpers, explanation formatting, batch helpers, form state, export serializers, request guards | **Vitest** with jsdom (components are rendered with `react-dom/client` and `act`; Testing Library is not installed) | **203 passing tests across 25 test files** |
| **Live Multi-Agent Integration** | End-to-end LLM inference, DeepInfra & Anthropic gateways | **Pytest** (`-m live_e2e`) | 10 dedicated live tests in `test_e2e_live.py`; they call a running backend at `http://127.0.0.1:8000/api` (559 total backend tests across 80 modules: 79 deterministic + 1 live E2E) |
| **Automated Browser E2E** | Guided wizard, SSE streaming, UI modals, bank CRUD | **Playwright**, **TestSprite AI** | 15 generated scripts in `e2e/` (TC001-TC015) plus a TestSprite plan JSON with 35 cases; run manually, no CI job |
| **Runtime Psychometric Gate** | 100-point 4-pillar rubric, AAMC distractor traps | **Async workflow engine** | Threshold $> 80$ points (`PASSING_SCORE_THRESHOLD`) |

---

## 2. Backend Pytest Test Suite

The deterministic test suite verifies all backend logic without making live external API calls or incurring token costs.

### 2.1 Test Directory Structure

```
backend/tests/
├── conftest.py                       # DB probe (TCP + asyncpg auth) for requires_db auto-skipping, credential stripping + OFFLINE_MODE for non-live tests, async client & patch_llm fixtures
├── factories.py                      # Shared test object builders (make_draft, make_question, make_request, collect_events)
├── test_additional_instructions.py   # Educator custom authoring instructions and prompt builder integration
├── test_agents.py                    # Multi-agent worker nodes, heuristics, blind solver routing & quality gates
├── test_ai_native_planning.py        # Dynamic batch brainstorming, AI slot blueprinting, and passage claim extraction
├── test_anthropic.py                 # Multi-provider switching, Anthropic models, prompt cache pricing & API keys
├── test_api_ai.py                    # AI Copilot endpoints: prompt enhancement, question refinement & study guides
├── test_api_duplicates_passages_health.py # Duplicate detection, passage lifecycle, CORS and health endpoints
├── test_api_generation.py            # Batch generation, passage sets and visual stimuli through the API
├── test_api_hardening.py             # Admin auth, image safety MIME checks, rate limits & status validation
├── test_api_questions.py             # CRUD, approval, status lifecycle, pagination and slim projection
├── test_api_security.py              # Optional API_ACCESS_KEY gate, request/body size caps, rate-limit identity, proxy config & error sanitizing
├── test_authoring_standards.py       # Shared option spread & passage length standards; safe DDL helper
├── test_batch_aggregate_lock.py      # Concurrent refresh_batch_aggregates calls serialize via row locks
├── test_batch_autonomous_retry.py    # Autonomous 3-trials policy, trial counts, 400 rejection & in-flight retries
├── test_batch_dedup_hard_delete.py   # Hard-delete duplicate purge during batch deduplication
├── test_batch_jobs_flow.py           # Background batch execution lifecycle (10 jobs x 5 questions) and refills
├── test_batch_retry_resume.py        # Retry runs selected jobs despite stale status; stopped jobs do not hang
├── test_batch_review_withholding.py  # Review queue withholding during batch runs & atomic promotion
├── test_batch_state.py               # Terminal resolution, stop/refill guards & cost accounting
├── test_blind_solver_vote.py         # Key parsing, layout-varied sampling, majority voting & confidence gating
├── test_config_and_pricing_polish.py # Config defaults, pricing lookups & vendor-masked settings
├── test_config_docs.py               # 73 Settings fields vs .env.example vs docs drift verification
├── test_cpu_async_hygiene.py         # Dedup pruning, thread pool offloading & lazy litellm import
├── test_database_structure.py        # SQLAlchemy schema, hybrid FTS, cascade deletion & constraints
├── test_deduplication.py             # Multi-metric similarity scoring, clustering & auto-refill
├── test_dedup_decomposition.py       # CQRS & structural decomposition of the deduplication engine
├── test_deterministic_gate.py        # Pure-Python validator gate runs before LLM review; fail-closed
├── test_draft_parser.py              # Decoupled candidate question JSON drafting parser & fallback extractors
├── test_e2e_live.py                  # 10 live end-to-end multi-agent integration tests (marked as live_e2e)
├── test_engine_cleanup.py            # Event stream cleanup & worker task cancellation on client disconnect
├── test_engine_slices.py             # Pure engine pieces: run layout, slot ledger, diversity context & sibling collision
├── test_extractors.py                # Polymorphic question extractors across dicts, Pydantic & ORM models
├── test_gzip_compression.py          # GZipMiddleware: compresses payloads >= 1KB, skips small responses and requests without Accept-Encoding
├── test_http_caching.py              # HTTP Cache-Control, ETag headers & 304 conditional revalidation
├── test_image_calls.py               # Provider image generation retries & response parsing (HTTP mocked)
├── test_in_flight_pool_and_dedup.py  # Per-job in-flight dedup pool & cross-slot collision checks
├── test_index_migration.py           # Redundant single-column index cleanup & composite index verification
├── test_job_stream_consumer.py       # Shared stream reader & request builder for background jobs
├── test_live_job_finalization.py     # Standalone /generate runs finalize job and batch rows
├── test_llm_budget.py                # Hard per-slot LLM call budget & free duplicate re-check after rewrites
├── test_llm_call.py                  # Prompt caching markers, truncation retries & exponential backoff
├── test_list_limits.py               # List/export bounds, LIKE-wildcard escaping, create-only POST /batches, worker-save integrity
├── test_logging_context.py           # Correlation IDs bound across async tasks & background jobs
├── test_medical_imaging.py           # All 7 medical modalities detection, safety sanitization, Reviewer visual audit boundary & Regenerator retention
├── test_mock_fixture_table.py        # Snapshot of the seven canned mock drafts (section x passage/independent)
├── test_modular_cleanup.py           # Codebase structural modularity, line budget enforcement & decoupling checks
├── test_multi_batch_concurrency.py   # Global worker semaphores, rate-limiting throttles & metrics
├── test_offline_mode.py              # OFFLINE_MODE gating: no mocks without it, tagged runs with it, fails loudly
├── test_openai.py                    # OpenAI text & image providers, pricing & vendor-masked config
├── test_ops_and_resolution.py        # Request IDs, body size limits, error sanitization & liveness
├── test_optimizations.py             # Query pipelining, count_batches, passage pagination & concurrency
├── test_optimizations_fullstack.py   # Session injection reusability, slim batch queries & passage repository mutations
├── test_packaging_sync.py            # pyproject.toml dependencies mirror backend/requirements*.txt (uv sync parity)
├── test_passage_blueprints_decomposition.py # Modulo attempt-based domain/condition replenishment rotation
├── test_passage_set_blueprints_and_dedup.py # 5-slot cognitive blueprints for CARS and natural sciences
├── test_pedagogy.py                  # Option length symmetry (spread ≤ max(3, ceil(0.20 × mean)) words), distractor traps & taxonomy parity
├── test_pgvector_rag.py              # pgvector RAG, normalized embeddings, cosine metrics & hybrid search
├── test_pricing_table.py             # Verified provider rates, model pricing resolution & cache billing
├── test_projected_reads.py           # Lightweight repository reads for batch monitoring performance
├── test_prometheus_metrics.py        # Prometheus /metrics exposition & telemetry middleware tracking
├── test_prompt_builder_blocks.py     # Decomposed generator user prompt sub-blocks (pedagogy, traps, stimulus)
├── test_question_repository_decomposition.py # DAL decomposition into question_queries and question_mutations
├── test_question_status_refill.py    # QuestionStatus enum, active question helpers & refill deficit
├── test_recovery.py                  # Startup recovery: orphaned running jobs marked failed cleanly
├── test_repository_mappers.py        # Pure mapping functions between SQLAlchemy models & Pydantic schemas
├── test_request_secrets.py           # Client API keys never persisted or returned; legacy payloads scrubbed
├── test_schema_migrations_decomposition.py # Schema migrations decomposition into focused DDL steps
├── test_schemas.py                   # Pydantic V2 model validation, serialization & constraint checks
├── test_shared_helpers.py            # Shared helper semantics (usage sums, mock usage, CARS checks)
├── test_slot_worker.py               # Isolated per-slot worker execution, retry tracking & budget guards
├── test_soft_delete_batch_integrity.py # Soft-delete & restore preserving batch progress metrics
├── test_sse_keepalive.py             # SSE keepalive comments during long LLM inferences
├── test_stream_emitter.py            # Workflow SSE queue draining, timeout polling & terminal event assembly
├── test_structured_output.py         # call_llm_validated repair retry and billing; strict JSON parsing
├── test_target_count_guarantee.py    # Dynamic job allocation, slot replenishment & target count guarantee
├── test_taxonomy_sync.py             # Byte-for-byte AAMC taxonomy synchronization between backend and frontend
├── test_tokens.py                    # Sub-micro-cent token cost math ($0.20/$0.60 DeepInfra, Anthropic tiers)
├── test_validators.py                # Deterministic question validators (A-D options, dashes, word counts)
├── test_visuals.py                   # AI image generation, SVG routing & visual stimulus persistence
├── test_workflow.py                  # Workflow streaming, event serialization & routing
└── test_workflow_nodes_decomposition.py # Decomposed lifecycle nodes (generator, reviewer, finalize facade)
```

### 2.2 Test Suite Execution Commands & Execution Modes

#### Execution Modes Breakdown
- **Offline / Isolated Mode** (PostgreSQL offline): The probe in `conftest.py` detects when PostgreSQL is not reachable (or rejects the configured credentials) and cleanly skips the 96 tests marked `requires_db`; the other 453 default tests (algorithmic, schema, prompt builder, taxonomy sync, HTTP caching, Prometheus metrics, AI native planning, token pricing) still run.
- **Full Database Mode** (PostgreSQL online): When Docker container `mcat_postgres` is healthy on `localhost:5432`, all 549 deterministic unit and integration tests execute across all 79 modules (10 live tests deselected). Wall-clock time depends on the machine (roughly tens of seconds); no precise figure is tracked here.
- **Live LLM Integration Mode**: The 10 `live_e2e` tests in `test_e2e_live.py` send HTTP requests to a separately running backend at `http://127.0.0.1:8000/api` (start it first, e.g. `pnpm run dev:backend`) with provider credentials configured in `.env` (for example `DEEPINFRA_API_KEY` for the default provider). They are excluded by default (`addopts = "-m 'not live_e2e'"`); run them with `-m live_e2e`.
- **Total Suite**: 559 backend tests across 80 test files (549 deterministic across 79 test files + 10 live E2E in `test_e2e_live.py`).

```bash
# 1. Activate backend virtual environment
source .venv/bin/activate

# 2. Run all deterministic unit and integration tests across 79 modules (549 tests)
# Smart auto-skip: If PostgreSQL is unreachable, 453 tests run and 96 requires_db tests cleanly skip
# conftest.py strips provider keys and enables OFFLINE_MODE for every non-live test, so none calls a live LLM
# (pyproject.toml sets the test path, PYTHONPATH and the "not live_e2e" marker)
pytest -v

# Or run via root package.json (backend only)
pnpm run test

# Database maintenance: purge discarded duplicate questions
pnpm run db:clean-duplicates

# 3. Run specific test modules
PYTHONPATH=backend pytest backend/tests/test_taxonomy_sync.py -v
PYTHONPATH=backend pytest backend/tests/test_batch_autonomous_retry.py -v
PYTHONPATH=backend pytest backend/tests/test_batch_dedup_hard_delete.py -v
PYTHONPATH=backend pytest backend/tests/test_anthropic.py -v
PYTHONPATH=backend pytest backend/tests/test_soft_delete_batch_integrity.py -v
PYTHONPATH=backend pytest backend/tests/test_additional_instructions.py -v
PYTHONPATH=backend pytest backend/tests/test_batch_review_withholding.py -v
PYTHONPATH=backend pytest backend/tests/test_target_count_guarantee.py -v
PYTHONPATH=backend pytest backend/tests/test_question_status_refill.py -v
PYTHONPATH=backend pytest backend/tests/test_deduplication.py -v
PYTHONPATH=backend pytest backend/tests/test_pgvector_rag.py -v
PYTHONPATH=backend pytest backend/tests/test_api_questions.py -v

# 4. Run live LLM tests (requires a running backend on 127.0.0.1:8000 and provider keys in .env)
PYTHONPATH=backend pytest backend/tests/test_e2e_live.py -v -m live_e2e
```

### 2.3 Detailed Test Module Coverage (549 Deterministic Tests across 79 Modules / 559 Total Backend Tests)

1. **`test_additional_instructions.py` (3 tests)**:
   - `test_generation_request_additional_instructions`: Validates Pydantic serialization and round-trip payload persistence of educator instructions.
   - `test_prompt_builder_includes_additional_instructions`: Verifies that custom authoring instructions are injected into the generator user prompt with high-priority pedagogical mandate.
   - `test_additional_instructions_is_canonical_field`: Validates that `additional_instructions` is the canonical instructions field and is directly injected into the prompt.
2. **`test_agents.py` (8 tests)**:
   - `test_all_mcat_sections_mock`: Verifies authentic section-specific mock fixtures for Chem/Phys, CARS, Bio/Biochem, and Psych/Soc.
   - `test_reviewer_heuristic_and_loop_routing`: Tests autonomous remediation loop triggers when score $\le 80$.
   - `test_strict_rejection_routing_when_score_le_90`: Verifies circuit-breaker termination when candidate fails after 3 cycles (remains below passing threshold).
   - `test_section_image_guard_routing`: Ensures CARS strictly forbids image generation.
   - `test_generate_question_with_self_critique_structure`: Validates fused single-pass drafting and 100-pt self-critique.
   - `test_blind_solver_node_agreement`: Verifies agreement between blind solver and generator draft.
   - `test_blind_solver_node_discrepancy_triggers_critique`: Verifies that key discrepancies immediately route candidate to reviewer critique.
   - `test_blind_solver_high_confidence_pass`: Confirms blind-solver confirmation when key matches and confidence $\ge 88\%$.
3. **`test_anthropic.py` (12 tests)**:
   - `test_anthropic_model_detection_and_settings`: Verifies model prefix recognition, provider auto-detection, and Settings initialization.
   - `test_provider_switcher_via_settings`: Tests dynamic switching between DeepInfra and Anthropic via `ACTIVE_LLM_PROVIDER`.
   - `test_anthropic_strict_api_key_enforcement`: Confirms missing Anthropic API key fails fast with actionable guidance.
   - `test_deepinfra_key_enforcement_preservation`: Ensures DeepInfra API key enforcement remains intact.
   - `test_claude_haiku_pricing_standard_tier`: Validates Claude Haiku 5.5 standard pricing ($0.10 in / $0.50 out per 1M tokens).
   - `test_claude_haiku_pricing_extended_tier`: Validates Claude Haiku 5.5 extended pricing for prompts $> 100\text{K}$ tokens ($0.50 in / $2.50 out per 1M tokens).
   - `test_claude_sonnet_pricing_auto_detection`: Verifies automatic rate lookup for Claude 3.5 Sonnet ($3.00 in / $15.00 out per 1M tokens).
   - `test_claude_opus_pricing_auto_detection`: Verifies automatic rate lookup for Claude 3 Opus ($15.00 in / $75.00 out per 1M tokens).
   - `test_custom_env_pricing_override`: Confirms explicit environment rate overrides take precedence over hardcoded rate cards.
   - `test_model_normalization_for_litellm`: Tests normalization of model identifiers for LiteLLM gateway compatibility.
   - `test_mock_llm_call_anthropic`: Validates mock LLM execution and response synthesis under Anthropic provider settings.
   - `test_health_and_config_endpoints_anthropic_reporting`: Confirms `/api/health` and `/api/config` report active provider, key status, and rates.
4. **`test_api_duplicates_passages_health.py` (7 tests)**:
   - Duplicate detection API, collision thresholds ($\ge 0.80$), educator side-by-side override audit trail, passage CRUD, server-side passage pagination and sorting (`sort_by`: `newest`, `oldest`, `title`, `questions`), CORS configuration, and health endpoints.
5. **`test_api_generation.py` (6 tests)**:
   - Multi-question batch generation flows through the API: independent discretes, single-passage sets, visual diagram handling, and SSE streaming lifecycles.
6. **`test_api_hardening.py` (15 tests)**:
   - Endpoint hardening: admin authorization gates, payload size constraints, SVG profile sanitization with SafeSvg, safe defaults, and database write validation.
7. **`test_api_questions.py` (4 tests)**:
   - Question Bank API: full CRUD operations, approval workflows, status lifecycles, server-side pagination, and `slim=True` lightweight projection.
8. **`test_api_security.py` (17 tests)**:
   - Optional `API_ACCESS_KEY` shared-secret gate on mutating routes, request length limits, hidden client API keys, paginated payload-free batch lists, consistent 500 error body, health admin key verification, and readiness probes. Also covers: `POST /api/questions/check-duplicate` stays exempt from the API key but is rate limited in its own bucket; length limits on the duplicate-check request fields; rate-limit identity taken from the transport peer (the `X-Forwarded-For` header is ignored, IPv6 addresses are grouped by /64); atomic reservation of active-batch slots; 413 for streamed (chunked) bodies over the limit; `GenerationRequest` field limits and `model_name` pattern; refusal of a model that is not server-configured when the caller supplies no `api_key`; size caps on the AI Copilot free-form payloads; streamed error events passed through `sanitize_error_text`; and a static check that `frontend/nginx.conf` overwrites `X-Forwarded-For` and the backend `Dockerfile` trusts no wildcard proxy list.
9. **`test_authoring_standards.py` (5 tests)**:
   - Shared option-spread and passage-word standards quoted consistently by every prompt; idempotent DDL helper that never locks migrated tables.
10. **`test_batch_aggregate_lock.py` (1 test)**:
    - Concurrent `refresh_batch_aggregates` calls converge safely under atomic row locks without foreign key deadlocks.
11. **`test_batch_autonomous_retry.py` (4 tests)**:
    - `test_job_trial_count_persistence`: Verifies `trial_count` is properly initialized on `GenerationJobModel` (default 1) and persisted across updates in PostgreSQL.
    - `test_resume_stopped_jobs_under_3_trials`: Confirms that `retry_incomplete_jobs_for_batch` resumes incomplete sets for manually paused batches when `trial_count < 3`.
    - `test_retry_strictly_blocked_after_3_trials`: Validates that `POST /api/batches/{id}/retry` strictly raises HTTP 400 when all incomplete jobs have exhausted 3 trials.
    - `test_run_single_job_autonomous_in_flight_retry`: Validates in-flight automatic replenishment up to 3 trials when question shortfall occurs due to psychometric threshold rejections.
12. **`test_batch_dedup_hard_delete.py` (2 tests)**:
    - `test_hard_delete_purges_duplicate_questions`: Confirms that resolving duplicates with `action="delete"` permanently purges redundant question rows from PostgreSQL via `hard_delete_questions_batch`, preventing ghost records in batch activity views.
    - `test_refresh_batch_aggregates_completion_guard`: Verifies that batch aggregate refreshes correctly calculate active questions and guard completion status.
13. **`test_batch_jobs_flow.py` (4 tests)**:
    - `test_batch_and_jobs_lifecycle`: End-to-end multi-job batch lifecycle (10 jobs x 5 questions = 50 total).
    - `test_mini_batch_lifecycle`: Validates single-job Practice Set lifecycle (1 job x 5 questions).
    - `test_refill_preserves_job_count_without_adding_sets`: Confirms that replenishment restores exact question deficits without creating redundant job sets.
    - `test_batch_status_transitions`: Validates state machine transitions across active, paused, completed, and failed batch states.
14. **`test_batch_retry_resume.py` (5 tests)**:
    - Retry/resume runs selected jobs despite stale status, ensures stopped jobs remain executable, and transitions stuck jobs to failed cleanly. A retry with no retryable jobs does not stop the running batch, and a failed background launch marks the batch failed instead of leaving it running.
15. **`test_batch_review_withholding.py` (3 tests)**:
    - `test_withhold_questions_until_batch_completed`: Confirms that questions from running batches stay in `batch_only` status, are excluded from the `GET /api/questions?status=ai_validated` review queue during generation, and are atomically promoted to `ai_validated` upon batch completion.
    - `test_cancelled_batch_does_not_promote_questions`: Verifies that questions from stopped or cancelled batches remain in `batch_only` and are never promoted to `ai_validated`.
    - `test_partial_batch_completion_promotes_qualifying`: Verifies that partially completed batches promote questions with score $> 80$ while withholding below-threshold items.
16. **`test_batch_state.py` (17 tests)**:
    - Batch state machine correctness: terminal resolution, stop/refill guards, cost accounting, and aggregate metrics synchronization. A passive refresh (for example resolve-duplicates) does not reopen a completed or failed batch.
17. **`test_blind_solver_vote.py` (12 tests)**:
    - Key parsing, layout-varied sampling, majority vote, split votes, confidence/ambiguity detection, and ensuring dedicated solver model never receives the client answer key.
18. **`test_config_and_pricing_polish.py` (6 tests)**:
    - Configuration defaults, pricing lookups, vendor-masked settings, and `/api/config` public exposure contracts.
19. **`test_config_docs.py` (4 tests)**:
    - All 73 `Settings` fields are documented in `SETUP_AND_CONFIG.md`, present in `.env.example`, documented defaults match code, and test counts in `TESTING_AND_QA.md` exactly match pytest collection.
20. **`test_cpu_async_hygiene.py` (5 tests)**:
    - CPU & async event loop hygiene: deduplication pruning keeps verdicts, large pools leave the loop, LiteLLM imports remain lazy, and threadpool executors avoid blocking.
21. **`test_database_structure.py` (8 tests)**:
    - `test_database_schema_initialization`: Verifies PostgreSQL tables, columns, and foreign key relations.
    - `test_passage_auto_sync_and_retrieval`: Validates passage synchronization and caching.
    - `test_batch_auto_sync_and_atomic_aggregation`: Ensures atomic calculation of batch metrics.
    - `test_hybrid_full_text_search`: Validates PostgreSQL tsvector hybrid FTS queries.
    - `test_api_passages_and_batches`: Confirms passage and batch REST endpoint contracts.
    - `test_centralized_repository_package_exports`: Ensures clean package exports across DAL layers.
    - `test_model_to_schema_none_options_safety`: Verifies null-safe deserialization when question options are null or empty.
    - `test_cascade_passage_deletion_multi_status_and_metrics`: Confirms that soft-deleting a passage soft-deletes associated questions across all statuses while maintaining batch metrics.
22. **`test_deduplication.py` (18 tests)**:
    - `test_normalize_text`: Verifies text normalization, case folding, punctuation removal, and whitespace trimming.
    - `test_extract_content_tokens`: Confirms extraction of domain-specific content tokens while filtering stop words.
    - `test_identical_questions_duplicate_detection`: Validates 1.0 similarity for verbatim question stems and options.
    - `test_paraphrased_high_similarity`: Evaluates token containment and hybrid similarity for paraphrased scientific stems sharing key terms ($> 0.80$).
    - `test_distinct_questions_in_same_subtopic_no_duplicate`: Confirms scoping isolation; distinct scientific concepts evaluate below the collision threshold ($< 0.35$).
    - `test_two_tier_threshold_and_soft_warning`: Verifies that a pair between the soft threshold (0.60) and the hard threshold passed to `evaluate_duplicate` is flagged as a soft warning rather than a duplicate (runtime defaults: hard 0.75, soft 0.60, API 0.80).
    - `test_cluster_questions_groups_duplicates_correctly`: Verifies pairwise similarity clustering of question batches into leader and duplicate items.
    - `test_auto_resolve_batch_and_refill`: Tests end-to-end auto-resolve and refill pipeline on duplicate clusters.
    - `test_auto_resolve_does_not_claim_refill_when_no_job_was_launched`: Confirms that auto-resolve cleanly handles zero-shortfall runs without superfluous replenishment jobs.
    - `test_stem_token_cache_is_keyed_by_content_and_evicts_one_at_a_time`: Validates content-keyed token caching and single-item FIFO eviction.
    - `test_duplicate_thresholds_come_from_config`: Ensures runtime threshold configuration binds to application settings.
    - `test_intra_passage_identical_answer_key_collision`: Detects multiple questions under the same stimulus reusing identical correct keys.
    - `test_same_passage_shared_answer_key_concept_substantive_tokens`: Tests concept containment flags on shared correct answers.
    - `test_intra_passage_stem_collision`: Identifies intra-passage stem overlap collisions.
    - `test_intra_passage_plural_normalized_key_collision`: Detects singular/plural answer key variations under the same passage.
    - `test_intra_passage_inverse_question_collision`: Detects inverse polarity questions testing the same clinical concept.
    - `test_judge_semantic_duplicate_offline`: Validates offline LLM judge fallback heuristics for ambiguous candidates.
    - `test_same_passage_distinct_questions_no_false_positive_collision`: Guarantees that distinct questions under the same passage do not produce false-positive collision flags.
23. **`test_deterministic_gate.py` (9 tests)**:
    - The review loop runs the validator before any LLM call (invalid drafts regenerate or reject without spending a review), reviewer and blind solver fail closed on provider errors and bad scores, generators never substitute mock questions for real failures, and review and solve run concurrently with both costs accounted for.
24. **`test_engine_cleanup.py` (1 test)**:
    - Closing the workflow stream early cleanly drains worker tasks without leaking in-flight background tasks.
25. **`test_engine_slices.py` (14 tests)**:
    - The closure-free pieces of `engine.py`: `_resolve_run_layout` (binary passage mode, CARS always linked, caller ids kept), `SlotLedger` (per-attempt folding, call budget, run totals with the passage spend), diversity context and drafting messages, passing-threshold precedence, offline attempt state, sibling-collision detection, the event factory and the shared passage/complete payloads.
26. **`test_http_caching.py` (5 tests)**:
    - HTTP `Cache-Control`, `ETag` generation, and HTTP 304 conditional revalidation on static and metadata endpoints, plus conditional ETag validation and 304 fast-path handling on `GET /api/batches/{id}` (`test_single_batch_endpoint_caching_and_etag`). The batch ETag also folds in a question-level fingerprint, so soft-deleting a question changes it (`test_batch_etag_changes_when_a_question_is_soft_deleted`).
27. **`test_image_calls.py` (5 tests)**:
    - Retry behavior and response handling of the provider image calls under simulated network faults and mocked HTTP responses.
28. **`test_in_flight_pool_and_dedup.py` (35 tests)**:
    - Comprehensive regression suite: in-flight deduplication pool, cross-slot collision checks, batch aggregate counting of active statuses only, pure batch status state machine (`_next_batch_status`, 14 cases), `enum_value`/`is_cars` safety, slot attempts following `WORKFLOW_MAX_WORKER_RETRIES`, cluster duplicate discovery with custom leaders, SSE event parsing, and public runtime field exposure. The in-flight embedding is computed before the pool lock is taken, and registration survives an embedding failure.
29. **`test_index_migration.py` (1 test)**:
    - Redundant single-column question indexes are dropped and covering composite indexes are created cleanly during migrations.
30. **`test_job_stream_consumer.py` (7 tests)**:
    - Shared stream consumer and request builder supporting batch job execution and in-place slot replenishment.
31. **`test_live_job_finalization.py` (3 tests)**:
    - Standalone runs always finalize job and batch records (including all-rejected runs), record total token spend, and clear in-flight registry entries.
32. **`test_llm_budget.py` (4 tests)**:
    - Hard per-slot LLM invocation budgets, spend throttling, and free duplicate re-checks following revision cycles.
33. **`test_llm_call.py` (6 tests)**:
    - `call_llm` request construction (Anthropic `cache_control`, avoidance of stacked LiteLLM retries), truncated-completion recovery, and worker semaphore release during backoff.
34. **`test_logging_context.py` (2 tests)**:
    - Correlation ids (batch, job, run, slot) bound with `bind_log_context` appear on log records, propagate to child tasks, and do not leak across asynchronous contexts.
35. **`test_medical_imaging.py` (19 tests)**:
    - All 7 medical & scientific modalities detection (Radiology, Histopathology, Gross Anatomy, Cellular Electron Microscopy, Physiology/ECG Traces, Clinical Pathology, Biochemical Schematics), gross anatomy safety prompt sanitization, OpenAI content moderation fallback retry, passage diagram modality routing, Reviewer Accompanying Visual Stimulus injection with anti-deduction audit mandate, and Regenerator Rule 12 visual stimulus retention.
36. **`test_mock_fixture_table.py` (8 tests)**:
    - Digest snapshot of the seven canned mock drafts in `agents/mock_drafts.py` (one per section and passage/independent variant) and the CARS passage-only rule, ensuring offline fixtures do not drift.
37. **`test_multi_batch_concurrency.py` (4 tests)**:
    - `test_global_concurrency_semaphores`: Confirms `GLOBAL_MAX_CONCURRENT_JOBS = 4` prevents thread saturation.
    - `test_call_llm_rate_limit_backoff`: Validates exponential backoff and jitter under HTTP 429 rate limit responses.
    - `test_refresh_batch_aggregates_atomic`: Ensures atomic SQL aggregation eliminates race conditions between parallel jobs.
    - `test_simultaneous_multi_batch_launch_and_metrics`: Tests simultaneous execution of multiple 50-question batches.
38. **`test_offline_mode.py` (3 tests)**:
    - `OFFLINE_MODE` gating: no mocks without explicit flag, tagged offline runs with it, and fail-fast behavior when API credentials are missing.
39. **`test_openai.py` (8 tests)**:
    - OpenAI provider detection, pricing calculation, token-billed `gpt-image-2.5-flare` and DALL-E 3 handling, and branded `/api/config` and `/api/health` payloads.
40. **`test_ops_and_resolution.py` (9 tests)**:
    - Request correlation IDs, request body length limits, error sanitization, liveness/readiness probes, and batch resolution helpers.
41. **`test_pedagogy.py` (6 tests)**:
    - `test_option_symmetry_and_anti_guessability_engine`: Mathematical validation that options stay within length parity tolerances.
    - `test_smart_ai_trap_and_explanation_breakdown`: Tests automatic cognitive trap assignment and 3-card mentor breakdown.
    - `test_manager_dependent_taxonomy_integration`: Verifies official AAMC syllabus tree mapping.
    - `test_taxonomy_json_parity_between_backend_and_frontend`: Enforces identical taxonomy trees across client and server.
42. **`test_pricing_table.py` (17 tests)**:
    - Verified provider price cards, model-based rate resolution, prompt cache write/read billing, and FLUX/OpenAI image pricing models.
43. **`test_projected_reads.py` (4 tests)**:
    - Lightweight, column-projected repository reads used by background batch workers to minimize memory overhead.
44. **`test_prometheus_metrics.py` (7 tests)**:
    - Real-time Prometheus/OpenMetrics exposition at `/metrics` and `/api/metrics`, telemetry middleware tracking, and path normalization. Also covers: the endpoints stay open when `ADMIN_API_KEY` is unset (and return 403 without a matching `x-admin-key` when it is set); the `endpoint` label is the matched route template or `unmatched`; methods outside the standard set collapse to `OTHER` and label values are escaped.
45. **`test_question_status_refill.py` (5 tests)**:
    - `test_question_status_enum_values`: Validates all explicit enum values in `QuestionStatus`.
    - `test_is_question_active_helper`: Confirms active status recognition (`in_bank`, `ai_validated`, `batch_only`, `approved`).
    - `test_status_update_requests_validation`: Validates Pydantic payloads for single and bulk status updates.
    - `test_batch_refill_deficit_calculation_with_discarded_questions`: Validates exact deficit computation when duplicate items are archived.
46. **`test_recovery.py` (2 tests)**:
    - Startup recovery: orphaned running batches and stuck jobs are reconciled, and `update_job_progress(clear=...)` resets fields cleanly.
47. **`test_repository_mappers.py` (8 tests)**:
    - Pure model mapping functions between SQLAlchemy Question/Passage models and Pydantic schemas, with `slim=True` optimization.
48. **`test_request_secrets.py` (3 tests)**:
    - Client-supplied API keys are never persisted or returned, and legacy batch payloads are scrubbed on startup.
49. **`test_schemas.py` (1 test)**:
    - Comprehensive Pydantic V2 schema boundary and validation tests across all generation requests and question payloads.
50. **`test_shared_helpers.py` (6 tests)**:
    - Shared utility functions (`sum_usage` latency semantics, `mock_usage` pricing, single `is_cars` helper) and prompt distinction between CARS and science passages.
51. **`test_soft_delete_batch_integrity.py` (2 tests)**:
    - `test_soft_delete_passage_and_batch_integrity`: Confirms soft-deleting a passage preserves parent batch metrics and linked job counters.
    - `test_soft_delete_question_and_restore`: Tests question soft-deletion, restoration via `POST /api/questions/{id}/restore`, and linked passage revival.
52. **`test_sse_keepalive.py` (2 tests)**:
    - SSE keep-alive comments are emitted while the LLM engine is thinking, and closing the wrapper safely terminates the upstream generator.
53. **`test_structured_output.py` (12 tests)**:
    - `call_llm_validated` repair retries, strict draft and key parsing, regenerator metadata preservation, and visual stimulus gating.
54. **`test_target_count_guarantee.py` (5 tests)**:
    - `test_dynamic_job_allocation_in_batch_runner`: Verifies dynamic job partitioning for 5, 50, and arbitrary question counts.
    - `test_auto_resolve_caps_excess_to_exact_target`: Verifies auto-resolve preserves exact target counts without excess items.
    - `test_refresh_batch_aggregates_reflects_active_questions`: Confirms batch counters aggregate active questions only.
    - `test_interactive_slot_replenishment_recovers_from_quality_rejection`: Tests automated in-place slot replenishment when quality gate drops a candidate.
    - `test_shortfall_job_and_batch_actual_count_synchronization`: Verifies that shortfall jobs and batch `actual_count` stay perfectly synchronized under dynamic refill conditions.
55. **`test_taxonomy_sync.py` (1 test)**:
    - Guarantees byte-for-byte synchronization between backend taxonomy (`backend/app/data/mcat_dependent_taxonomy.json`) and frontend constant (`frontend/src/constants/mcat_dependent_taxonomy.json`).
56. **`test_tokens.py` (9 tests)**:
    - DeepInfra model configuration, token and cost calculation verification, cumulative token tracking across multi-agent cycles, and API key enforcement.
57. **`test_validators.py` (14 tests)**:
    - Deterministic validator tests: 4-choice option IDs, key validity, single-choice enforcement, forbidden dashes and automatic hyphenation repair, all/none-of-the-above exclusion, passage association rules, length parity, and distractor coverage warnings.
58. **`test_visuals.py` (10 tests)**:
    - SVG vector generator, AI image modality routing, FLUX unit pricing formula, visual stimulus persistence to PostgreSQL, autonomous AI image discretion (`image_needed: True` vs `image_needed: False`), explicit require_image mandate handling, AI visual necessity validation for independent batch items, and batch item autonomous discretion preservation.
59. **`test_workflow.py` (3 tests)**:
    - Real-time Server-Sent Events (SSE) metadata, reviewer bypass when self-critique passes, and resilient JSON parsing of LLM outputs.
60. **`test_extractors.py` (4 tests)**:
    - Polymorphic question extraction routines, dict vs. Pydantic model duck-typing, and correct answer ID/text extraction fallbacks.
61. **`test_passage_set_blueprints_and_dedup.py` (6 tests)**:
    - Deterministic CARS and Science passage set slot schedules (Slots 1–5), psychometric archetype assignment, dynamic AI slot blueprint prompt directives, and semantic clone detection.
62. **`test_slot_worker.py` (5 tests)**:
    - Isolated question slot execution, attempt replenishment, quality gate routing, LLM budget ceilings, dynamic blueprints propagation, and `SlotWorkerContext` initialization.
63. **`test_workflow_nodes_decomposition.py` (7 tests)**:
    - Lifecycle node decomposition (`node_generator`, `node_reviewer`, `node_finalize`), facade symbol re-exports, object identity, dynamic monkeypatch synchronization, token usage accumulation, quality gate rejection payloads, and finalize entity assembly.
64. **`test_question_repository_decomposition.py` (7 tests)**:
    - DAL CQRS decomposition (`question_queries`, `question_mutations`), query/mutation domain segregation, facade symbol re-exports, package-level re-exports, `QuestionHead` immutability, and `test_session_parameter_support_across_repositories` verifying universal `session: AsyncSession | None = None` support across all repository functions.
65. **`test_prompt_builder_blocks.py` (9 tests)**:
    - Decomposed generator prompt sub-blocks (pedagogy, traps, passage stimulus, visual directive, cognitive archetype, length parity) and isolated formatting consistency.
66. **`test_stream_emitter.py` (7 tests)**:
    - Workflow SSE queue draining, timeout polling, terminal event assembly, error payload translation, and client-disconnect safety.
67. **`test_ai_native_planning.py` (9 tests)**:
    - Dynamic batch thematic brainstorming (`brainstorm_batch_thematic_angles`), offline deterministic topic angles, live LLM brainstorming with fallback, slot claim and blueprint extraction, and batch worker request injection.
68. **`test_api_ai.py` (4 tests)**:
    - Dedicated AI Copilot endpoints: prompt enhancement (`/enhance-instructions`), question refinement (`/refine-question`), passage editorial audit (`/audit-passage`), and structured study guide synthesis (`/study-guide`).
69. **`test_dedup_decomposition.py` (5 tests)**:
    - CQRS & structural decomposition of the deduplication engine: exact symbol re-exports, object identity equality between facade and submodules (`dedup_metrics`, `dedup_clustering`), metric computation equivalence, and graph clustering equivalence.
70. **`test_passage_blueprints_decomposition.py` (5 tests)**:
    - Modulo attempt-based domain and condition replenishment rotation, CARS domain resolution, Science experimental condition rotation, deterministic blueprint extraction, and backward compatibility with monolithic blueprint structures.
71. **`test_pgvector_rag.py` (14 tests)**:
    - pgvector RAG retrieval, normalized unit vector dimensions and norms, cosine similarity invariants, embedding caching, question and passage embedding storage, exemplar structure retrieval, hybrid vector-FTS search, RAG-grounded duplicate detection, and API endpoints (`/semantic-search`, `/rag-context`, `/check-duplicate`, `/backfill-embeddings`). A failed live embedding call returns no embedding (nothing is cached or persisted), and the embedding cache is a bounded 1024-entry LRU.
72. **`test_modular_cleanup.py` (5 tests)**:
    - Verifies modular decomposition architecture: `backend/app/data/thematic_angles.py` extraction with `batch_worker.py` re-export facade, `backend/app/services/csv_export.py` extraction with `api/v1/questions.py` re-export facade, `backend/app/services/readability.py` extraction with `services/ai_copilot.py` re-export facade, and `test_modular_facade_reexports_all_expected_symbols` ensuring comprehensive public facade symbol re-exports across `app.services` and `app.schemas`. Also verifies CSV export neutralizes spreadsheet formula injection (`test_csv_export_neutralizes_formula_injection`).
73. **`test_schema_migrations_decomposition.py` (4 tests)**:
    - Verifies database migration decomposition into `backend/app/db/schema_migrations.py`: exact step count assertions (13 schema steps, 6 data steps), `init_db.py` facade symbol re-exports and identity parity, `_IdempotentConnection` DDL bypass filtering, and `_timestamptz_migration_sql()` generation.
74. **`test_draft_parser.py` (11 tests)**:
    - Verifies decoupled Question Draft Parser & Cognitive Trap Extraction: 4-choice option parsing from standard lists, dictionary maps, prefixed strings, and candidate keys; correct answer key extraction and unknown key validation; cognitive trap classification across 20+ AAMC taxonomies; student mistake pattern extraction; and 100% identity parity re-exports in `app.agents.generator`.
75. **`test_optimizations.py` (6 tests)**:
    - Tests end-to-end optimizations: native SQL batch aggregation (`count_batches`), reading passage pagination (`limit`/`offset`) and counting (`count_passages`), concurrent database query pipelining in `GET /api/questions` via `asyncio.gather`, concurrent batch status retrieval in `GET /api/batches`, concurrent single passage and linked questions loading in `GET /api/passages/{passage_id}`, and pipelined batch detail with duplicate clusters retrieval in `GET /api/batches/{batch_id}` and `GET /api/batches/{batch_id}/duplicate-clusters`.
76. **`test_optimizations_fullstack.py` (3 tests)**:
    - Tests full-stack enterprise optimizations: database session injection and connection reusability across repository query functions (`get_questions`, `count_questions`, `get_repository_metrics`, `get_batches`, `count_batches`, `get_batch_by_id`, `get_jobs_by_batch_id`), slim telemetry projection on `GET /api/batches/{batch_id}?slim=true` omitting heavy JSONB audit payloads for >90% network transfer efficiency during live batch polling, and passage repository session injection with question mutations (`test_passage_session_injection_and_mutations`).
77. **`test_gzip_compression.py` (3 tests)**:
    - `GZipMiddleware` compresses responses of 1 KB or more when `Accept-Encoding: gzip` is sent, leaves small responses uncompressed, and returns plain bodies when the client does not ask for gzip.
78. **`test_list_limits.py` (7 tests)**:
    - List and export bounds and write integrity: `clamp_list_limit` and the `MAX_LIST_LIMIT` (2000) clamp on an unlimited `GET /api/questions`; `like_contains` escapes `%` and `_` so search treats them literally; `GET /api/questions/export` pages through the whole bank (500 rows per page); `POST /api/batches` is create-only (409 when the id exists); a job question never fabricates a missing batch (`BatchNotFoundError`).
79. **`test_packaging_sync.py` (2 tests)**:
    - `pyproject.toml` `[project].dependencies` and `[dependency-groups].dev` mirror `backend/requirements.txt` and `backend/requirements-dev.txt` exactly (the requirements files stay canonical for CI and the Dockerfile; this test guards drift so `uv sync` installs the same packages).
80. **`test_e2e_live.py` (10 live tests - marked as `live_e2e`)**:
    - Live end-to-end integration tests: health connectivity, cross-section syllabus hierarchy, live SSE streaming, PostgreSQL persistence, export serializers, strict quality gate rejection boundary, combination matrix validation, UUID4 contracts, and image serving endpoints.

### 2.4 Smart Offline Database Detection (`conftest.py`)

To keep local runs fast and CI-friendly even before the database is provisioned, `backend/tests/conftest.py` probes PostgreSQL once at import time (`is_postgres_available`):

1. A quick TCP connect (0.2 s) to the host and port from `DATABASE_URL`; if the port is closed, the database counts as unavailable.
2. If the port is open, an `asyncpg` connection with the configured user, password and database runs `SELECT 1;` (3 s timeout), so a server that rejects the credentials also counts as unavailable.

- When the probe fails, the autouse fixture `auto_skip_db_tests` skips every test marked `@pytest.mark.requires_db` with the message `PostgreSQL is not reachable with the configured DATABASE_URL (offline, or the credentials failed). Skipping database-dependent test.`
- 96 tests are marked `requires_db`, so the 453 other default tests run without Docker or PostgreSQL.
- Once PostgreSQL is started (`docker compose up -d`), all **549 deterministic tests across 79 modules** run.
- The autouse fixture `neutralize_llm_credentials` blanks `ANTHROPIC_API_KEY`, `DEEPINFRA_API_KEY` and `OPENAI_API_KEY` (config and environment) and sets `OFFLINE_MODE=True` for every test except those marked `live_e2e`.

---

## 3. TestSprite AI Playwright E2E Suite (TC001–TC015)

The application includes an automated End-to-End browser test suite executed with Playwright under the TestSprite AI testing harness, with 15 generated scripts in `e2e/` (`TC001`-`TC015`). They target `http://localhost:5173/` (override with the `E2E_BASE_URL` environment variable) with the backend running and are run by hand. There is no CI job for them, and Playwright is not in the backend requirements; `e2e/requirements.txt` lists it (`playwright>=1.45`), so install it with `pip install -r e2e/requirements.txt && playwright install chromium`. `e2e/testsprite_frontend_test_plan.json` describes 35 cases (TC001-TC035); only TC001-TC015 have generated scripts. TODO: verify the current pass/fail status of the scripts (no recorded run is kept in the repo).

### 3.1 Test Case Matrix

| ID | Test Scenario | Primary User Flow | Automated Verification |
| :---: | :--- | :--- | :--- |
| **TC001** | Configure and start guided generation | 3-Step Guided Wizard navigation | Validates all 3 wizard step transitions (Section Focus, Level & Format, Review & Launch) and initiates generation. |
| **TC002** | Start guided generation from workspace | Generator tab interaction | Launches configuration modal directly from the single-canvas workspace without regressions. |
| **TC003** | Complete generation run & review output | Full item generation | Streams single question, verifies 4 options, balanced word counts, and transition to Staged Review. |
| **TC004** | Live generation progress & logs | SSE Telemetry tray | Verifies step-by-step agent milestones, stopwatch timer, and collapsible log tray rendering. |
| **TC005** | Start guided generation from landing hero | Hero preset shortcuts | Launches wizard pre-configured with official AAMC section presets directly from hero buttons. |
| **TC006** | Review completed generation output | Candidate card inspection | Verifies primary cognitive trap chip, dual score pills, and 3-part mentor explanation cards. |
| **TC007** | Cancel active generation run | Pipeline interruption | Validates cancel button immediately halts SSE stream and preserves workspace state cleanly. |
| **TC008** | Approve staged question into bank | Admin review gate | Approves individual candidate, verifies persistence to PostgreSQL, and verifies question bank sync. |
| **TC009** | Start generation with default settings | Quick launch | Verifies generation with zero manual tweaks launches with authentic AAMC defaults. |
| **TC010** | Edit staged question & save revision | Inline editor | Edits stem text and options in-place, saves revision, and verifies updated content persists. |
| **TC011** | Approve all staged questions at once | Bulk approval | Atomically approves all candidate slots in a batch into the Question Bank in one operation. |
| **TC012** | Inspect staged question audit trail | Psychometric audit modal | Opens audit modal, inspects 4-pillar breakdown (25 pts each), per-agent token table, and micro-costs. |
| **TC013** | Switch between main workspace views | Tab bar navigation | Seamlessly transitions across Create Questions, Batch Progress, Review Queue, Question Bank, and Passage Bank. |
| **TC014** | Filter question bank | Repository search & filters | Filters the question bank by section, difficulty, and status (per the script title). |
| **TC015** | Delete question from the bank | Question deletion | Deletes item from bank, confirms modal prompt, and verifies row is purged from repository. |

### 3.2 Running E2E Playwright Tests

```bash
# Run individual TestSprite Playwright test scripts (frontend on :5173 and backend on :8000 must be running)
python3 e2e/TC001_Configure_and_start_guided_question_generation.py
python3 e2e/TC003_Complete_a_generation_run_and_review_the_results.py
python3 e2e/TC008_Approve_a_staged_question_into_the_bank.py
```

---

## 4. Frontend Vitest Automated Test Suite (203 Tests across 25 Suites)

The frontend test suite is executed using **Vitest** (jsdom where DOM APIs are required; components are rendered with `react-dom/client` and `act`, and no Testing Library package is installed) and covers pure data transforms, badge resolvers, question validation, distractor extraction, batch calculators, multi-format export builders, and custom hooks.

All **203 tests across 25 test files** pass (`pnpm --dir frontend run test`):

### 4.1 Frontend Test Suite Matrix

| # | Test Suite | File Location | Tests | Target Scope & Verification Purpose |
| :-: | :--- | :--- | :-: | :--- |
| **1** | `visualHelpers.test.js` | `src/utils/__tests__/` | 16 | Medical visual modality detection (radiology, histology, gross anatomy, electron microscopy, physiology traces, clinical photographs, SVG diagrams) and theme styling metadata. |
| **2** | `mcat.test.js` | `src/constants/__tests__/` | 19 | Section normalization, score scaling formulas, difficulty tier helpers, and dependent taxonomy structure integrity. |
| **3** | `sharedHelpers.test.js` | `src/utils/__tests__/` | 15 | Pure data transformers, score calculations, badge resolver helpers, formatting utilities, and central utils barrel re-exports. |
| **4** | `apiHelpers.test.js` | `src/utils/__tests__/` | 13 | HTTP client error wrapping, payload sanitization, query string builders, and response parsing. |
| **5** | `batchHelpers.test.js` | `src/utils/__tests__/` | 12 | Batch status aggregation, progress percent calculation, and multi-job stage management. |
| **6** | `useAiValidatedHandlers.test.js` | `src/hooks/__tests__/` | 12 | Review queue item selection, select-all toggle, passage expansion, and optimistic state mutations. |
| **7** | `duplicates.test.jsx` | `src/components/duplicates/__tests__/` | 12 | `DuplicateRiskBadge`, `DuplicateAlertBar` and `DuplicateCompareModal`: labels and tones, alert versus calm override note, side-by-side compare, disabled and hidden Override. |
| **8** | `export.test.js` | `src/utils/__tests__/` | 10 | CSV spreadsheet formula neutralisation, HTML metacharacter escaping, SVG script stripping, and paper preview doc builders. |
| **9** | `explanationHelpers.test.js` | `src/utils/__tests__/` | 9 | Distractor parsing, trap extractor, mentor explanation 3-card structure, and distractor sorting helpers. |
| **10** | `formatters.test.js` | `src/utils/__tests__/` | 8 | Date formatting, micro-cent cost displays, duration timers, and score badges. |
| **11** | `questionHelpers.test.js` | `src/utils/__tests__/` | 8 | Question draft validation, key resolution, option text checkers, and stem normalizers. |
| **12** | `batchJobHelpers.test.js` | `src/utils/__tests__/` | 8 | Visible question counting, actual count resolution, and batch job shortfall detection. |
| **13** | `useKeyboardShortcuts.test.jsx` | `src/hooks/__tests__/` | 8 | Review-queue `A`/`D` shortcuts plus existing `t` and `/`; ignored while typing, with a modal open, with modifiers or key repeat; `enabled=false`; listener cleanup. |
| **14** | `generatorFormAndPagination.test.js` | `src/utils/__tests__/` | 7 | Page size normalization, subtopic multi-select toggles, and select option wrapping navigation. |
| **15** | `questionVisuals.test.js` | `src/utils/__tests__/` | 6 | Image provider detection, SVG sanitizer checks, and figure attachment helpers. |
| **16** | `copilotAndSearchOptimizations.test.js` | `src/utils/__tests__/` | 6 | Slim batch query parameters (`fetchBatchDetail`), toast category token adherence (`error`), and adaptive vector cosine search ordering. |
| **17** | `duplicateHelpers.test.js` | `src/utils/__tests__/` | 6 | Duplicate levels (high, similar, overridden, none), the soft threshold, and when the alert bar and Compare action apply. |
| **18** | `CommonA11y.test.jsx` | `src/components/common/__tests__/` | 5 | `Modal` backdrop close (mousedown and click), default `ariaLabel`, `useFocusTrap` skipping hidden controls, `Toast` live region, and `ErrorBoundary` fallback and retry. |
| **19** | `useDuplicateOverride.test.jsx` | `src/hooks/__tests__/` | 5 | Compare dialog open/close, override flow with toast, error handling, double-click guard, and stable handler. |
| **20** | `ExportComponents.test.jsx` | `src/components/modals/__tests__/` | 4 | Scope selector button rendering, filter state hiding, and data format pane previews. |
| **21** | `QuestionBankViewHandlers.test.js` | `src/views/__tests__/` | 4 | Filter reset handlers, table row selection toggling, and stale selection pruning. |
| **22** | `BatchDuplicateAudit.test.jsx` | `src/components/batch/__tests__/` | 4 | On-demand duplicate check, empty result, confirmed resolve with deficit display, and error display. |
| **23** | `requestGuard.test.js` | `src/utils/__tests__/` | 3 | In-flight request deduplication, debounce guards, and idempotency key handlers. |
| **24** | `usePagination.test.jsx` | `src/hooks/__tests__/` | 2 | Server-driven pagination handling (`totalCount`, page boundaries, and navigation callbacks). |
| **25** | `useBatchActivity.test.jsx` | `src/hooks/__tests__/` | 1 | A failed final detail fetch of a just-completed batch is retried on the next poll. |
| **Total** | **25 Test Suites** | | **203 Tests** | **100% Pass Rate** |

### 4.2 Running Frontend Tests

```bash
# Run all 203 frontend unit tests via Vitest
pnpm --dir frontend run test
# or from root:
pnpm run test:frontend

# Run with verbose test-by-test reporting
pnpm --dir frontend run test --reporter=verbose
```

---

## 5. Code Hygiene, Formatting & Linters

Both backend and frontend enforce strict zero-defect policies in local development and continuous integration.

### 5.1 Python Standards (Ruff)

- **Target Version**: Python 3.11 (`py311`)
- **Max Line Length**: 100 characters
- **Rules Enforced**: `E` (pycodestyle errors), `W` (warnings), `F` (pyflakes), `I` (isort imports), `UP` (pyupgrade modern 3.11 idioms), `B` (bugbear), `C4` (comprehensions), `SIM` (simplify), `RET` (return), `G004` (lazy logging), `ASYNC` (flake8-async), `PT` (pytest style), `RUF` (ruff-specific). Source of truth: `[tool.ruff.lint]` in the root `pyproject.toml` (a few rules such as `E501` and `UP042` are ignored there; `PTH` is not enabled).

```bash
# Check Python code style across all modules and tests
uv run ruff check .

# Automatically fix linting issues
uv run ruff check --fix backend

# Format Python files
uv run ruff format .
```

### 5.2 Frontend Standards (Oxlint, CSS Checker, & Production Build)

- **Target**: React 19 JSX & ES2022
- **Scope**: 184 files, 106 rules (as reported by `oxlint` on its last run; `.oxlintrc.json` enables the `react` and `oxc` plugins plus a handful of explicit rules)
- **Automated Tests**: 203 passing unit/integration tests across 25 test files (100% pass rate via Vitest)
- **Policy**: 0 errors, 0 warnings (0 TODO, 0 FIXME, 0 console.log occurrences across codebase)
- **CSS Hygiene**: Enforced zero unused or missing CSS classes via `pnpm check:css`
- **Production Build**: Clean compilation with Vite 8 (`pnpm build`)

```bash
# Run frontend linter (oxlint)
pnpm --dir frontend lint

# Verify zero unused or missing CSS classes
pnpm --dir frontend run check:css

# Compile production bundle
pnpm --dir frontend run build
```

---

## 6. Full-Stack Concurrency & Load Benchmarking

The repository includes a dedicated in-process ASGI high-concurrency stress harness ([scripts/benchmark_concurrency.py](../scripts/benchmark_concurrency.py)) that measures response latencies, throughput, and connection pool stability under escalating concurrent client loads:

```bash
# Run multi-tier load benchmark (20, 50, 100 concurrent workers, 850 total requests)
pnpm run benchmark:concurrency
# or directly via Python harness:
PYTHONPATH=backend uv run python scripts/benchmark_concurrency.py
```

### 6.1 Verified Concurrency Results (850 Total Requests)

| Concurrency Tier | Concurrent Workers | Total Requests | Throughput | Median $p_{50}$ | 95th Percentile $p_{95}$ | 99th Percentile $p_{99}$ | HTTP Errors | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tier 1: Moderate Load** | 20 | 100 | **85.5 req/s** | 173.65 ms | 472.98 ms | 531.95 ms | **0 / 100** | **100% Passed** |
| **Tier 2: High Load** | 50 | 250 | **84.6 req/s** | 392.67 ms | 1,651.95 ms | 1,981.97 ms | **0 / 250** | **100% Passed** |
| **Tier 3: Stress Load** | 100 | 500 | **84.8 req/s** | 706.72 ms | 3,828.29 ms | 4,823.99 ms | **0 / 500** | **100% Passed** |

- **Micro-Benchmarks under 50 Concurrency**:
  - `GET /api/batches/{id}?slim=true`: **210.9 req/s** (4.7 ms mean latency).
  - `GET /api/questions?slim=true&limit=20`: **112.0 req/s** (8.9 ms mean latency).
  - `GET /api/passages?limit=20`: **34.0 req/s** (29.4 ms mean latency).
  - `GET /metrics`: **277.8 req/s** (3.6 ms mean latency).
- **Pool Resilience**: Zero connection leaks or pool starvation across 850 requests (`DB_POOL_SIZE = 10`, `DB_MAX_OVERFLOW = 10`).

---

## 7. Continuous Integration (CI) Pipeline

The repository integrates a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs on every pull request targeting `main` and on every push to `main`:

```yaml
# Summary of CI jobs (every job has a timeout)
1. code-quality:     Ruff lint + format check (backend)
2. backend-tests:    PostgreSQL 16 (pgvector) service, full deterministic Pytest suite with
                     --cov=app --cov-fail-under=85 (the job fails below 85% coverage) and a
                     coverage.xml artifact upload (backend-coverage)
3. frontend-build:   pnpm install, Oxlint, Vitest, unused-CSS check, Vite production build
4. docker-build:     builds the backend and web images (no push)
5. dependency-audit: pip-audit + pnpm audit (advisory, never blocks)
```

The Playwright scripts in `e2e/` are not run by CI.
