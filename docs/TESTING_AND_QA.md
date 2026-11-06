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
        UnitTests[97 Deterministic Unit & Integration Tests across 20 Modules]
        LiveE2E[10 Live LLM API E2E Integration Tests (320 Total Backend Tests)]
    end

    subgraph "Tier 3: Browser E2E Automation"
        TestSprite[TestSprite Playwright E2E Suite: TC001-TC015]
    end

    subgraph "Tier 4: Runtime Quality Gate"
        StrictGate[Strict 90+ Score Psychometric Evaluation]
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
| **Static Code Hygiene** | PEP 8, syntax correctness, modern JS/JSX idioms | **Ruff** (Python 3.11 with SIM & RET), **Oxlint** (React 19) | 0 errors, 0 warnings policy (90 frontend files, 100% ruff compliance across backend) |
| **Deterministic Unit & Integration** | Schemas, agents, DAL, API endpoints, tokens, batch runner, deduplication, withholding guards, multi-provider, soft-delete, 3-trial retries, hard-delete dedup, taxonomy sync | **Pytest**, **pytest-asyncio**, SQLite / PG Mock | **310 passing tests across 53 modules** (~23-28s) |
| **Live Multi-Agent Integration** | End-to-end LLM inference, DeepInfra & Anthropic gateways | **Pytest** (`-m live_e2e`) | 10 dedicated live tests (320 total backend tests across 54 modules) |
| **Automated Browser E2E** | Guided wizard, SSE streaming, UI modals, bank CRUD | **Playwright**, **TestSprite AI** | 15 generated scripts in `e2e/`; run manually (not part of CI) |
| **Runtime Psychometric Gate** | 100-point 4-pillar rubric, AAMC distractor traps | **Async workflow engine** | Threshold $> 90$ points |

---

## 2. Backend Pytest Test Suite

The deterministic test suite verifies all backend logic without making live external API calls or incurring token costs.

### 2.1 Test Directory Structure

```
backend/tests/
├── conftest.py                       # Socket probe for offline DB auto-skipping, async client fixtures & DB overrides
├── test_additional_instructions.py   # Educator custom authoring instructions and prompt builder integration
├── test_agents.py                    # Multi-agent worker nodes, heuristics, and blind solver
├── test_anthropic.py                 # Multi-provider switching, Anthropic models, prompt cache pricing & API keys
├── test_api_questions.py             # CRUD, approval, status lifecycle, pagination and slim projection
├── test_api_generation.py            # Batch generation, passage sets and visual stimuli through the API
├── test_api_duplicates_passages_health.py # Duplicate detection, passage lifecycle, CORS and health endpoints
├── test_api_security.py              # Optional `API_ACCESS_KEY` gate on mutating routes, request length li
├── test_authoring_standards.py       # Shared option-spread and passage-band standards quoted consistently 
├── test_batch_aggregate_lock.py      # Concurrent `refresh_batch_aggregates` calls converge (row lock witho
├── test_batch_autonomous_retry.py    # Autonomous 3-trials policy, trial count persistence, HTTP 400 rejection, and in-flight retries
├── test_batch_dedup_hard_delete.py   # Hard-delete duplicate purge during batch deduplication and completion guards
├── test_batch_jobs_flow.py           # Background batch execution lifecycle (10 jobs x 5 questions) and refill integrity
├── test_batch_retry_resume.py        # Retry runs its selected jobs despite stale status, stopped jobs are 
├── test_batch_review_withholding.py  # Review queue withholding during batch execution and atomic promotion
├── test_blind_solver_vote.py         # Key parsing, layout-varied sampling, majority vote, split votes, con
├── test_database_structure.py        # SQLAlchemy schema, hybrid FTS, cascade deletion, and atomic aggregations
├── test_deduplication.py             # Multi-metric similarity scoring, clustering, and auto-refill
├── test_shared_helpers.py            # Shared helper semantics (usage sums, mock usage, CARS check)
├── test_config_docs.py               # Settings vs .env.example vs setup guide drift
├── test_deterministic_gate.py        # Deterministic validator gate in the review loop, fail-closed reviewer/solver, parallel review and solve
├── test_engine_cleanup.py            # No leaked worker tasks when the workflow stream is closed early
├── test_engine_slices.py             # Pure engine pieces: run layout, slot ledger, diversity context, sibling collision, event payloads
├── test_live_job_finalization.py     # Standalone runs always finalize the job (all-rejected, closed on `wo
├── test_llm_call.py                  # call_llm: prompt caching marker, truncation retry, LLM slot release during backoff
├── test_logging_context.py           # Correlation ids on log records (batch, job, run, slot)
├── test_multi_batch_concurrency.py   # Global semaphores, rate limiting backoff, and metrics
├── test_offline_mode.py              # `OFFLINE_MODE` gating: no mocks without it, tagged runs with it, fai
├── test_openai.py                    # OpenAI provider, pricing, image models, vendor-masked config and health
├── test_pedagogy.py                  # Option symmetry (±15%), distractor traps, and taxonomy parity
├── test_question_status_refill.py    # QuestionStatus enum, active question helpers, and refill deficit calculations
├── test_recovery.py                  # Startup recovery of orphaned batches/jobs and explicit field clearing
├── test_request_secrets.py           # API keys never stored or returned; legacy payloads scrubbed on start
├── test_schemas.py                   # Pydantic V2 model validation and serialization
├── test_soft_delete_batch_integrity.py # Soft deletion & restoration preserving batch progress integrity
├── test_structured_output.py         # `call_llm_validated` repair retry and billing, strict draft/key pars
├── test_sse_keepalive.py             # SSE keepalive comments and source cleanup
├── test_target_count_guarantee.py    # Dynamic job allocation, slot replenishment, and target count guarantees
├── test_tokens.py                    # Sub-micro-cent token cost math ($0.098 in / $0.294 out) and config cascade
├── test_validators.py                # Deterministic question validators and dash repair
├── test_visuals.py                   # SVG vector generation and FLUX image cost formulas
├── test_workflow.py                  # Workflow streaming, event serialization, and routing
└── test_e2e_live.py                  # Live LLM inference suite (marked as live_e2e)
```

### 2.2 Test Suite Execution Commands & Execution Modes

#### Execution Modes Breakdown
- **Offline / Isolated Mode** (PostgreSQL offline): The smart socket probe in `conftest.py` automatically detects when PostgreSQL is not running on port 5432 and cleanly skips the 78 database-dependent tests, executing all 232 algorithmic, schema, prompt builder, taxonomy sync, and token pricing unit tests in ~12 seconds (`220 passed, 76 skipped, 10 deselected`).
- **Full Database Mode** (PostgreSQL online): When Docker container `mcat_postgres` is healthy on `localhost:5432`, all 310 deterministic unit and integration tests execute across all 53 modules in ~23-28 seconds (10 live tests deselected).
- **Live LLM Integration Mode**: When live API keys are provided in `.env`, all 10 live end-to-end multi-agent inference tests run in `test_e2e_live.py` (`10 passed`).
- **Total Suite**: 320 backend tests across 54 test files.

```bash
# 1. Activate backend virtual environment
source .venv/bin/activate

# 2. Run all deterministic unit and integration tests across 53 modules
# Smart auto-skip: If PostgreSQL is offline on localhost:5432, 232 pure unit tests pass and 78 DB tests cleanly skip
# Note: ACTIVE_LLM_PROVIDER=deepinfra ensures deterministic offline mocking without calling live external LLMs
ACTIVE_LLM_PROVIDER=deepinfra pytest backend/tests -v -m "not live_e2e"

# Or run via root package.json
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
PYTHONPATH=backend pytest backend/tests/test_api_questions.py -v

# 4. Run live LLM tests (requires DEEPINFRA_API_KEY in .env)
PYTHONPATH=backend pytest backend/tests/test_e2e_live.py -v -m live_e2e
```

### 2.3 Detailed Test Module Coverage (310 Deterministic Tests across 52 Modules / 320 Total Backend Tests)

1. **`test_additional_instructions.py` (3 tests)**:
   - `test_generation_request_additional_instructions`: Validates Pydantic serialization and round-trip payload persistence of educator instructions.
   - `test_prompt_builder_includes_additional_instructions`: Verifies that custom authoring instructions are injected into the generator user prompt with high-priority pedagogical mandate.
   - `test_prompt_builder_falls_back_to_custom_prompt`: Validates graceful backward-compatibility fallback when `custom_prompt` is provided without `additional_instructions`.
2. **`test_agents.py` (7 tests)**:
   - `test_all_mcat_sections_mock`: Verifies authentic section-specific mock fixtures for Chem/Phys, CARS, Bio/Biochem, and Psych/Soc.
   - `test_reviewer_heuristic_and_loop_routing`: Tests autonomous remediation loop triggers when score $\le 90$.
   - `test_strict_rejection_routing_when_score_le_90`: Verifies circuit-breaker termination when candidate fails after 3 cycles.
   - `test_section_image_guard_routing`: Ensures CARS strictly forbids image generation.
   - `test_generate_question_with_self_critique_structure`: Validates fused single-pass drafting and 100-pt self-critique.
   - `test_blind_solver_node_agreement`: Verifies agreement between blind solver and generator draft.
   - `test_blind_solver_node_discrepancy_triggers_critique`: Verifies that key discrepancies immediately route candidate to reviewer critique.
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
4. **`test_api_questions.py`, `test_api_generation.py`, `test_api_duplicates_passages_health.py` (16 tests, formerly a single `test_api.py`)**:
   - `test_database_crud`: Full CRUD lifecycle verification against question repository.
   - `test_admin_approval_and_persistence_endpoints`: Verifies admin approval workflow and PostgreSQL persistence.
   - `test_multichoice_and_passage_support`: Validates 4-choice purity and shared stimulus passage handling.
   - `test_batch_generation_and_staging_flow`: End-to-end multi-question staging and approval cycle.
   - `test_single_passage_multi_question_set`: Verifies multiple questions sharing a single passage stimulus.
   - `test_binary_passage_and_independent_batches`: Confirms binary passage mode (all passage-linked or all independent).
   - `test_independent_question_direct_no_stimulus`: Ensures independent questions omit stimulus without errors.
   - `test_passage_set_with_passage_level_visual_stimulus`: Validates shared reading passage diagrams.
   - `test_question_status_lifecycle_and_counts`: Verifies question lifecycle counts and transitions.
   - `test_deduplication_and_override_api`: Full API workflow verification: creates reference question in bank, checks candidate collision via `POST /api/questions/check-duplicate` ($\ge 0.80$), triggers `POST /api/questions/{id}/override-duplicate`, verifies `is_duplicate_override=True`, `status='in_bank'`, and verifies DB persistence.
   - `test_batch_duplicate_clusters_and_resolve_endpoints`: Validates cluster inspection and duplicate archive/deletion resolution via REST API.
   - `test_cors_patch_allowed`: Confirms that HTTP PATCH methods are fully permitted under CORS policy.
   - `test_questions_pagination_and_slim_projection`: Validates `limit`, `offset`, and `slim=True` payload projection, reducing response payload by 70%+ by omitting heavy diagnostics.
5. **`test_batch_autonomous_retry.py` (4 tests)**:
   - `test_job_trial_count_persistence`: Verifies `trial_count` is properly initialized on `GenerationJobModel` (default 1) and persisted across updates in PostgreSQL.
   - `test_resume_stopped_jobs_under_3_trials`: Confirms that `retry_incomplete_jobs_for_batch` resumes incomplete sets for manually paused batches when `trial_count < 3`.
   - `test_retry_strictly_blocked_after_3_trials`: Validates that `POST /api/batches/{id}/retry` strictly raises HTTP 400 when all incomplete jobs have exhausted 3 trials.
   - `test_run_single_job_autonomous_in_flight_retry`: Validates in-flight automatic replenishment up to 3 trials when question shortfall occurs due to psychometric threshold rejections.
6. **`test_batch_dedup_hard_delete.py` (2 tests)**:
   - `test_hard_delete_purges_duplicate_questions`: Confirms that resolving duplicates with `action="delete"` permanently purges redundant question rows from PostgreSQL via `hard_delete_questions_batch`, preventing ghost records in batch activity views.
   - `test_refresh_batch_aggregates_completion_guard`: Verifies that batch aggregate refreshes correctly calculate active questions and guard completion status.
7. **`test_batch_jobs_flow.py` (4 tests)**:
   - `test_batch_and_jobs_lifecycle`: End-to-end multi-job batch lifecycle (10 jobs x 5 questions = 50 total).
   - `test_mini_batch_lifecycle`: Validates single-job Practice Set lifecycle (1 job x 5 questions).
   - `test_refill_preserves_job_count_without_adding_sets`: Confirms that replenishment restores exact question deficits without creating redundant job sets.
8. **`test_batch_review_withholding.py` (2 tests)**:
   - `test_withhold_questions_until_batch_completed`: Confirms that questions from running batches stay in `batch_only` status, are excluded from the `GET /api/questions?status=ai_validated` review queue during generation, and are atomically promoted to `ai_validated` upon batch completion.
   - `test_cancelled_batch_does_not_promote_questions`: Verifies that questions from stopped or cancelled batches remain in `batch_only` and are never promoted to `ai_validated`.
9. **`test_database_structure.py` (8 tests)**:
   - `test_database_schema_initialization`: Verifies PostgreSQL tables, columns, and foreign key relations.
   - `test_passage_auto_sync_and_retrieval`: Validates passage synchronization and caching.
   - `test_batch_auto_sync_and_atomic_aggregation`: Ensures atomic calculation of batch metrics.
   - `test_hybrid_full_text_search`: Validates PostgreSQL tsvector hybrid FTS queries.
   - `test_api_passages_and_batches`: Confirms passage and batch REST endpoint contracts.
   - `test_centralized_repository_package_exports`: Ensures clean package exports across DAL layers.
   - `test_model_to_schema_none_options_safety`: Verifies null-safe deserialization when question options are null or empty.
   - `test_cascade_passage_deletion_multi_status_and_metrics`: Confirms that soft-deleting a passage soft-deletes associated questions across all statuses while maintaining batch metrics.
10. **`test_deduplication.py` (8 tests)**:
    - `test_normalize_text`: Verifies text normalization, case folding, punctuation removal, and whitespace trimming.
    - `test_extract_content_tokens`: Confirms extraction of domain-specific content tokens while filtering stop words.
    - `test_identical_questions_duplicate_detection`: Validates 1.0 similarity for verbatim question stems and options.
    - `test_paraphrased_high_similarity`: Evaluates token containment and hybrid similarity for paraphrased scientific stems sharing key terms ($> 0.80$).
    - `test_distinct_questions_in_same_subtopic_no_duplicate`: Confirms scoping isolation; distinct scientific concepts evaluate below the collision threshold ($< 0.35$).
    - `test_two_tier_threshold_and_soft_warning`: Verifies hard duplicate threshold ($\ge 0.80$) and soft warning threshold ($0.65 - 0.79$).
    - `test_cluster_questions_groups_duplicates_correctly`: Verifies pairwise similarity clustering of question batches into leader and duplicate items.
    - `test_auto_resolve_batch_and_refill`: Tests end-to-end auto-resolve and refill pipeline on duplicate clusters.
11. **`test_multi_batch_concurrency.py` (4 tests)**:
    - `test_global_concurrency_semaphores`: Confirms `GLOBAL_MAX_CONCURRENT_JOBS = 4` prevents thread saturation.
    - `test_call_llm_rate_limit_backoff`: Validates exponential backoff and jitter under HTTP 429 rate limit responses.
    - `test_refresh_batch_aggregates_atomic`: Ensures atomic SQL aggregation eliminates race conditions between parallel jobs.
    - `test_simultaneous_multi_batch_launch_and_metrics`: Tests simultaneous execution of multiple 50-question batches.
12. **`test_pedagogy.py` (4 tests)**:
    - `test_option_symmetry_and_anti_guessability_engine`: Mathematical validation that options stay within $\pm 15\%$ word count.
    - `test_smart_ai_trap_and_explanation_breakdown`: Tests automatic cognitive trap assignment and 3-card mentor breakdown.
    - `test_manager_dependent_taxonomy_integration`: Verifies official AAMC syllabus tree mapping.
    - `test_taxonomy_json_parity_between_backend_and_frontend`: Enforces identical taxonomy trees across client and server.
13. **`test_question_status_refill.py` (5 tests)**:
    - `test_question_status_enum_values`: Validates all explicit enum values in `QuestionStatus`.
    - `test_is_question_active_helper`: Confirms active status recognition (`in_bank`, `ai_validated`, `batch_only`, `approved`).
    - `test_status_update_requests_validation`: Validates Pydantic payloads for single and bulk status updates.
    - `test_batch_refill_deficit_calculation_with_discarded_questions`: Validates exact deficit computation when duplicate items are archived.
14. **`test_schemas.py` (1 test)**:
    - `test_schemas_validation`: Comprehensive Pydantic V2 schema boundary and validation tests.
15. **`test_soft_delete_batch_integrity.py` (2 tests)**:
    - `test_soft_delete_passage_and_batch_integrity`: Confirms soft-deleting a passage preserves parent batch metrics and linked job counters.
    - `test_soft_delete_question_and_restore`: Tests question soft-deletion, restoration via `POST /api/questions/{id}/restore`, and linked passage revival.
16. **`test_target_count_guarantee.py` (4 tests)**:
    - `test_dynamic_job_allocation_in_batch_runner`: Verifies dynamic job partitioning for 5, 50, and arbitrary question counts (e.g., 12 Qs $\to$ 5, 5, 2).
    - `test_auto_resolve_caps_excess_to_exact_target`: Verifies that auto-resolve preserves exact target count without excess items.
    - `test_refresh_batch_aggregates_reflects_active_questions`: Confirms that batch counters accurately aggregate active questions only.
    - `test_interactive_slot_replenishment_recovers_from_quality_rejection`: Tests automated in-place slot replenishment when quality gate drops a candidate.
17. **`test_taxonomy_sync.py` (1 test)**:
    - `test_taxonomy_files_are_synchronized`: Guarantees that the backend taxonomy definition (`backend/app/data/mcat_dependent_taxonomy.json`) and frontend constant (`frontend/src/constants/mcat_dependent_taxonomy.json`) remain byte-for-byte synchronized, preventing drift in syllabus topics, disciplines, and foundational concepts.
18. **`test_tokens.py` (8 tests)**:
    - `test_deepinfra_model_configuration`: Verifies model identifier, cascade settings, and endpoint parameters.
    - `test_token_and_cost_calculation`: Sub-micro-cent mathematical calculation verification ($0.20/$0.60 per 1M).
    - `test_workflow_token_accumulation`: Verifies cumulative token tracking across multi-agent cycles.
    - `test_deepinfra_strict_api_key_enforcement`: Ensures missing API keys fail fast with actionable guidance.
    - `test_max_tokens_settings_and_config_endpoint`: Validates token limit configuration contracts on `/api/config`.
    - `test_call_llm_effective_max_tokens_and_temperature`: Confirms temperature, fast model cascade, and token constraints per agent.
19. **`test_visuals.py` (5 tests)**:
    - `test_strict_ai_image_generator`: Validates SVG vector generator and AI visual filters.
    - `test_flux_image_cost_formula`: Verifies FLUX unit cost scaling ($0.014 normalized baseline).
    - `test_image_node_workflow_accumulation`: Ensures visual synthesis costs accumulate into total run cost.
    - `test_visual_stimulus_persistence_in_finalize_node`: Confirms diagram SVG/URL persistence to PostgreSQL.
    - `test_autonomous_ai_determined_image_workflow`: Validates AI-determined visual stimulus routing.
20. **`test_workflow.py` (4 tests)**:
    - `test_per_question_stage_metadata_in_events`: Verifies SSE event payload metadata and stage tracking.
    - `test_fused_generator_node_passing_and_routing`: Validates fused single-pass drafting and fast-path routing.
    - `test_fused_workflow_bypasses_reviewer_when_self_critique_passed`: Confirms the reviewer bypass path when self-critique passes (opt-in: the test sets `ALWAYS_INDEPENDENT_REVIEW=false`).
    - `test_safe_json_loads_and_resilient_parsing`: Ensures resilient JSON parsing of LLM outputs.
21. **`test_openai.py` (8 tests)**: OpenAI provider detection, pricing, image-model handling, and branded (vendor-masked) `/api/config` and `/api/health` payloads.
22. **`test_validators.py` (11 tests)**: Deterministic validator: option ids, key validity, single-choice, forbidden dashes and their automatic repair, all/none-of-the-above, passage rules, length-parity and distractor-coverage warnings.
23. **`test_deterministic_gate.py` (9 tests)**: The review loop runs the validator before any LLM call (invalid drafts regenerate or reject without spending a review), reviewer and blind solver fail closed on provider errors and bad scores, generators never substitute mock questions for real failures, and review and solve run concurrently with both costs accounted for.
24. **`test_llm_call.py` (4 tests)**: `call_llm` request construction (Anthropic `cache_control`, no stacked litellm retries), truncated-completion retry with a larger budget, and LLM slot release during backoff.
25. **`test_engine_cleanup.py` (1 test)**: Closing the workflow stream early leaves no running worker or monitor tasks.
26. **`test_recovery.py` (2 tests, DB)**: Startup reconciliation stops orphaned batches and their running jobs; `update_job_progress(clear=...)` resets fields explicitly.
27. **`test_logging_context.py` (2 tests)**: Correlation ids (batch, job, run, slot) appear on log records, are inherited by child tasks, and do not leak back.
28. **`test_sse_keepalive.py` (2 tests)**: SSE keepalive comments are emitted while the source is quiet, and closing the wrapper closes the source.
29. **`test_api_security.py` (6 tests)**: Optional `API_ACCESS_KEY` gate on mutating routes, request length limits, hidden `api_key`, paginated payload-free batch list, consistent 500 body, health admin key, readiness probe.
30. **`test_authoring_standards.py` (5 tests)**: Shared option-spread and passage-band standards quoted consistently by every prompt; idempotent DDL helper skips existing columns/indexes.
31. **`test_batch_aggregate_lock.py` (1 tests)**: Concurrent `refresh_batch_aggregates` calls converge (row lock without FK deadlocks).
32. **`test_batch_retry_resume.py` (3 tests)**: Retry runs its selected jobs despite stale status, stopped jobs are executable, stuck jobs are failed.
33. **`test_blind_solver_vote.py` (12 tests)**: Key parsing, layout-varied sampling, majority vote, split votes, confidence/ambiguity, dedicated solver model never receives the client key.
34. **`test_live_job_finalization.py` (3 tests)**: Standalone runs always finalize the job (all-rejected, closed on `workflow_complete`), report spend of rejected runs, leave no in-flight registry entries.
35. **`test_offline_mode.py` (3 tests)**: `OFFLINE_MODE` gating: no mocks without it, tagged runs with it, fail-fast without credentials.
36. **`test_request_secrets.py` (3 tests)**: API keys never stored or returned; legacy payloads scrubbed on startup.
37. **`test_structured_output.py` (12 tests)**: `call_llm_validated` repair retry and billing, strict draft/key parsing, regenerator metadata preservation and image gating.
38. **`test_config_docs.py` (2 tests)**: Every `Settings` field is present in `.env.example` and the setup guide, and `.env.example` has no malformed lines.
39. **`test_shared_helpers.py` (6 tests)**: Shared helpers (`sum_usage` latency semantics, `mock_usage` pricing, single CARS helper) and a regression test that CARS and science passage prompts differ.
40. **`test_engine_slices.py` (14 tests)**: The closure-free pieces of `engine.py`: `_resolve_run_layout` (binary passage mode, CARS always linked, caller ids kept), `SlotLedger` (per-attempt folding, call budget, run totals with the passage spend), diversity context and drafting messages, passing-threshold precedence, offline attempt state, sibling-collision detection, the event factory and the shared passage/complete payloads.
41. **`test_e2e_live.py` (10 live tests - marked as `live_e2e`)**:
    - `test_e2e_health_and_db_connectivity`: Confirms health endpoint connectivity to live PostgreSQL and LiteLLM models.
    - `test_e2e_all_four_sections_metadata`: Verifies live metadata and taxonomy tree across all 4 AAMC sections.
    - `test_e2e_config_endpoint`: Validates live runtime model configuration and token rate parameters.
    - `test_e2e_live_generation_sse_stream`: Full live end-to-end question generation with SSE streaming and stage events.
    - `test_e2e_question_bank_crud_and_filtering`: Validates live database CRUD and multi-criteria filtering against PostgreSQL.
    - `test_e2e_export_json_and_csv`: Tests export endpoint across CSV and JSON formats.
    - `test_e2e_strict_threshold_rejection_boundary`: Verifies strict quality gate rejection boundary when score fails rubric.
    - `test_e2e_manager_combination_matrix_and_stage_outcomes`: Tests cross-section combination matrix and stage metadata.
    - `test_e2e_uuid_architecture`: Ensures all persisted entities adhere strictly to UUID4 primary key contracts.
    - `test_e2e_question_image_endpoint`: Validates visual stimulus retrieval and content negotiation.

### 2.4 Smart Offline Database Detection (`conftest.py`)

To maximize local developer velocity and ensure seamless CI execution even before database provisioning, `backend/tests/conftest.py` implements an active TCP socket probe:

```python
def is_postgres_available(host: str = "localhost", port: int = 5432, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
```

- When PostgreSQL is offline, `auto_skip_db_tests` dynamically detects tests decorated with `@pytest.mark.requires_db` and cleanly skips them with `PostgreSQL on localhost:5432 is offline. Skipping database-dependent test.`
- All **232 pure unit and algorithmic tests** execute and pass with 100% velocity without requiring Docker or PostgreSQL.
- Once PostgreSQL is started (`docker compose up -d`), all **310 deterministic tests across 53 modules** execute and pass automatically in ~23-28 seconds.

---

## 3. TestSprite AI Playwright E2E Suite (TC001–TC015)

The application includes an automated End-to-End browser test suite executed with Playwright under the TestSprite AI testing harness, with 15 generated scripts in `e2e/` (`TC001`-`TC015`). They target `http://localhost:5173/` (override with the `E2E_BASE_URL` environment variable) with the backend running, are run by hand, and are not part of the CI pipeline; the last recorded manual run passed 15/15.

### 3.1 Test Case Matrix

| ID | Test Scenario | Primary User Flow | Automated Verification | Status |
| :---: | :--- | :--- | :--- | :---: |
| **TC001** | Configure and start guided generation | 3-Step Guided Wizard navigation | Validates all 3 wizard step transitions (Section Focus, Level & Format, Review & Launch) and initiates generation. | ✅ Passed |
| **TC002** | Start guided generation from workspace | Generator tab interaction | Launches configuration modal directly from the single-canvas workspace without regressions. | ✅ Passed |
| **TC003** | Complete generation run & review output | Full item generation | Streams single question, verifies 4 options, balanced word counts, and transition to Staged Review. | ✅ Passed |
| **TC004** | Live generation progress & logs | SSE Telemetry tray | Verifies step-by-step agent milestones, stopwatch timer, and collapsible log tray rendering. | ✅ Passed |
| **TC005** | Start guided generation from landing hero | Hero preset shortcuts | Launches wizard pre-configured with official AAMC section presets directly from hero buttons. | ✅ Passed |
| **TC006** | Review completed generation output | Candidate card inspection | Verifies primary cognitive trap chip, dual score pills, and 3-part mentor explanation cards. | ✅ Passed |
| **TC007** | Cancel active generation run | Pipeline interruption | Validates cancel button immediately halts SSE stream and preserves workspace state cleanly. | ✅ Passed |
| **TC008** | Approve staged question into bank | Admin review gate | Approves individual candidate, verifies persistence to PostgreSQL, and verifies question bank sync. | ✅ Passed |
| **TC009** | Start generation with default settings | Quick launch | Verifies generation with zero manual tweaks launches with authentic AAMC defaults. | ✅ Passed |
| **TC010** | Edit staged question & save revision | Inline editor | Edits stem text and options in-place, saves revision, and verifies updated content persists. | ✅ Passed |
| **TC011** | Approve all staged questions at once | Bulk approval | Atomically approves all candidate slots in a batch into the Question Bank in one operation. | ✅ Passed |
| **TC012** | Inspect staged question audit trail | Psychometric audit modal | Opens audit modal, inspects 4-pillar breakdown (25 pts each), per-agent token table, and micro-costs. | ✅ Passed |
| **TC013** | Switch between main workspace views | Tab bar navigation | Seamlessly transitions across Create Questions, Batch Progress, Review Queue, Question Bank, and Passage Bank. | ✅ Passed |
| **TC014** | Filter question bank | Repository search & filters | Filters repository by section, difficulty, and keyword search with debounced queries. | ✅ Passed |
| **TC015** | Delete question from the bank | Question deletion | Deletes item from bank, confirms modal prompt, and verifies row is purged from repository. | ✅ Passed |

### 3.2 Running E2E Playwright Tests

```bash
# Run individual TestSprite Playwright test scripts
python3 e2e/TC001_Configure_and_start_guided_question_generation.py
python3 e2e/TC003_Complete_a_generation_run_and_review_the_results.py
python3 e2e/TC008_Approve_a_staged_question_into_the_bank.py
```

---

## 4. Code Hygiene, Formatting & Linters

Both backend and frontend enforce strict zero-defect policies in local development and continuous integration.

### 4.1 Python Standards (Ruff)

- **Target Version**: Python 3.11 (`py311`)
- **Max Line Length**: 100 characters
- **Rules Enforced**: `E` (pycodestyle errors), `W` (warnings), `F` (pyflakes), `I` (isort imports), `UP` (pyupgrade modern 3.11 idioms).

```bash
# Check Python code style
ruff check .

# Automatically fix linting issues
ruff check --fix backend

# Format Python files
ruff format .
```

### 4.2 Frontend Standards (Oxlint)

- **Target**: React 19 JSX & ES2022
- **Scope**: 86 source files, 104 lint rules
- **Policy**: 0 errors, 0 warnings

```bash
# Run frontend linter
pnpm lint
```

---

### 2.4 Newer Test Modules
- `test_llm_budget.py`: hard per-slot LLM call budget, free duplicate-rewrite loop, sequential review/solve default.
- `test_projected_reads.py`, `test_index_migration.py`: column-projected worker reads, constant-query batch saves, redundant-index migration (idempotent).
- `test_cpu_async_hygiene.py`: dedup pruning equivalence, thread offload, in-flight cleanup, lazy `litellm`.
- `test_batch_state.py`: terminal status resolution, stop/refill guards, cost accounting, DB init retry.
- `test_api_hardening.py`: admin gate, image safety, safe defaults, write validation, rate limit and batch cap.
- `test_ops_and_resolution.py`: request ids, body limits, error sanitising, liveness, batch-resolution helpers.
- `test_job_stream_consumer.py`: the shared workflow-stream reader and request builder used by job runs and refills.
- `test_pricing_table.py`: verified provider prices (defaults checked without `.env`), tier and cache billing, model-based rate resolution, override scoping, name variants, token-billed image cost.
- `test_image_calls.py`: image retry helper and OpenAI image call handling (HTTP mocked).
- `test_backend_polish.py`: difficulty alias filtering/sorting, OpenAPI build, parse failures.
- Shared builders live in `backend/tests/factories.py` (`make_draft`, `make_question`).

### 2.5 Frontend Unit Tests
`pnpm --dir frontend run test` (Vitest + jsdom) covers the pure helpers: batch stage/structural-sharing/cache-patch helpers, question-status helpers, formatters, and the export escaping, CSV and print-HTML builders. `pnpm --dir frontend run check:css` fails when a CSS class is no longer used anywhere in `src`.

## 5. Continuous Integration (CI) Pipeline

The repository integrates a GitHub Actions workflow (`.github/workflows/ci.yml`) that validates every pull request:

```yaml
# Summary of CI jobs (every job has a timeout)
1. code-quality:     Ruff lint + format check (backend)
2. backend-tests:    PostgreSQL 16 service, full deterministic Pytest suite (--durations=15)
3. frontend-build:   pnpm install once, Oxlint, taxonomy copy sync check, Vite production build
4. docker-build:     builds the backend and web images
5. dependency-audit: pip-audit + pnpm audit (advisory, never blocks)
```
