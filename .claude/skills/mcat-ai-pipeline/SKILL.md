---
name: mcat-ai-pipeline
description: Work on the multi-agent question-generation pipeline of the Question Bank Generator: workflow engine (nodes, routes, state, engine), agents (generator, reviewer, regenerator, blind solver, image generator, option balancer), prompts, prompt builder, scoring thresholds, LLM provider wiring, token and cost tracking, mock fixtures. Use whenever changing how questions are generated, scored, validated, regenerated or priced, editing any prompt, or debugging why questions are rejected, low quality, or mis-costed.
---

# AI pipeline

## Flow (production path: workflow/engine.py + review_loop.py, passage_prep.py, dedup_inflight.py, live_job_store.py)
`fused_generator` (draft + honest 100-point self-critique) -> dedup/anti-collision loop -> `_run_question_review_loop`: deterministic validator (`agents/validators.py`, free; auto-repairs dashes; blocking defects regenerate or reject without any review call) -> reviewer, then blind solver (sequential by default; `PARALLEL_REVIEW_AND_SOLVE=true` runs both at once through `run_review_and_solve`; both billed either way) -> `route_after_review`: score > threshold and solver verified goes to `image_generator` (only if a diagram is needed) then `finalize`; otherwise `regenerator` and back to the validator; attempts exhausted goes to `reject`.

There is no LangGraph runtime: the flow is the hand-written loop in `engine.py`/`review_loop.py`; `routes.py` only provides `route_after_review` (used by the loop). Change the loop and keep `route_after_review` consistent with it.

Files: `workflow/nodes.py` (node fns plus `build_review_update`, `build_solver_update`, `build_usage_only_update`, `run_review_and_solve`), `routes.py`, `state.py` (`AgentWorkflowState`), `engine.py` + `review_loop.py`/`passage_prep.py`/`dedup_inflight.py`/`live_job_store.py`, `agents/*` (LLM calls), `agents/validators.py`, `agents/prompts.py`, `agents/prompt_builder.py`.

## Invariants (do not weaken without the user asking)
- Quality gate: score must be above the threshold (`config.passes_quality_gate`, never a literal 90); up to 3 regeneration attempts; then reject.
- Blind solver independently answers without seeing the key; a key mismatch or confidence below 88% triggers remediation.
- Exactly 4 options A-D, one correct answer; option lengths within +/-15% of each other (`option_balancer.py`).
- Single hyphens only: em dashes and en dashes are forbidden in prompts and in generated output.
- Discrete questions (no passage) must not emit a passage; CARS uses only passage-justified reasoning, no outside science.
- `additional_instructions` from the educator must be injected with high priority into passage drafting, question drafting and remediation prompts (covered by `test_additional_instructions.py`).
- Explanations follow the mentor style with per-option trap breakdowns (trap names live in `frontend/src/constants/mcatTraps.js` and the prompts; keep them aligned).

## Quality-gate behavior (fail closed)
- `agents/validators.py` runs free structural checks (and repairs forbidden dashes) before any LLM review; blocking findings go to the regenerator or reject.
- Reviewer and blind solver raise `QualityCheckUnavailableError` after two failed attempts instead of passing an item. Only `LLMNotConfiguredError` (no credentials) combined with `OFFLINE_MODE=true` uses heuristic fixtures; `tests/conftest.py` enables it for offline tests. Tests that simulate offline mode must raise `LLMNotConfiguredError`, not a generic error.
- Generator and regenerator no longer substitute mock questions for real provider failures; the engine's slot retry handles the exception.
- `ALWAYS_INDEPENDENT_REVIEW=true` forces the reviewer even if the self-critique passed. Truncated completions (`finish_reason == "length"`) are retried with a larger budget up to `LLM_MAX_TOKENS_CEILING`.

## Authoring standards, outputs and the solver
- Numbers (option-length spread, passage word bands) live only in `agents/standards.py`; prompts use `<<TOKEN>>` placeholders resolved there, and the validator imports the same values. Never hardcode "within N words" or a passage length in a prompt.
- Model JSON is parsed with `call_llm_validated` (one repair retry at temperature 0, both calls billed). Tests that fake the LLM patch `app.agents.base.call_llm`, not a per-agent attribute. A missing key raises; never default it.
- The blind solver samples two option layouts (`BLIND_SOLVER_SAMPLES`), requires a strict majority on the author's key, and never receives the client's `api_key` when `BLIND_SOLVER_MODEL` is set.
- Mocks need `OFFLINE_MODE=true` (set by `tests/conftest.py`); without it a missing key raises and the run fails fast.

## Cost controls
- `MAX_LLM_CALLS_PER_SLOT` caps calls per question slot (counted from the `calls` field of usage entries; mock results count zero). Any new loop that can spend LLM calls must check `llm_budget_exhausted(state)` first.
- Default flow is sequential: the solver runs only after the reviewer passes (`PARALLEL_REVIEW_AND_SOLVE=false`). A regenerated draft is duplicate-checked for free before the next review.

## Editing prompts
Prompts are long and heavily tuned. Make surgical edits, keep section numbering, and run `test_agents.py`, `test_pedagogy.py`, `test_additional_instructions.py`. If a rubric or threshold changes, update `docs/MCAT_RUBRIC.md` and `docs/ARCHITECTURE.md` too.

## Providers and cost
- Providers resolve through `config.ACTIVE_LLM_PROVIDER` (deepinfra, anthropic, openai). LLM calls go through LiteLLM; model-id normalization (e.g. the `anthropic/` prefix) lives in `agents/base.py`, so add provider behavior there, not inside feature agents.
- Token and cost math is deterministic and lives with `schemas/token.py` plus config price properties: rates follow the MODEL's own provider (`Settings.get_default_pricing_rates`, `agents/base.calculate_token_cost`), never the active provider; built-in prices and where they were verified live in `core/pricing.py` (`PRICE_SOURCES`): DeepInfra DeepSeek standard $0.20 in / $0.60 out per 1M (cached 3%), Claude Haiku 5.5 tiered at 100K prompt tokens with cache read/write, gpt-4o-mini $0.15 / $0.60 (cached 50%); FLUX-2-klein is per image scaled by area and gpt-image-2.5-flare is billed from the returned token usage. When a price changes: re-check the provider page, update the `Settings` default, `.env.example`, `docs/TOKEN_TRACKING.md` and `docs/SETUP_AND_CONFIG.md` together (tests enforce the drift), and run `test_pricing_table.py` and `test_tokens.py`. Every LLM call, including blind solver and calls whose verdict is discarded, must be counted; `duration_ms` rides on `TokenUsage` into the usage breakdown.

## Tests without live LLMs
Mock fixtures are in `agents/mock_fixtures.py` and `_mock_tokens.py`. Tests marked `live_e2e` hit real APIs and are excluded by default; never run them without the user's say-so since they cost money.

## Runtime hygiene
- The SSE event queue is bounded (`_EVENT_QUEUE_MAX`): a slow consumer slows workers instead of growing memory; no event is dropped. The monitor ends the stream via a flag, never a blocking put.
- `clear_in_flight_batch` runs in the engine's `finally`; per-worker `remove_in_flight_draft` remains for normal paths.
- `litellm` is imported lazily through `_get_litellm()` in `agents/base.py`; never add a top-level `import litellm` (a test guards it).
- `compute_*_similarity(..., prune=True)` returns upper bounds for clearly distinct pairs: use it only to decide duplicate status, not to display exact scores.
