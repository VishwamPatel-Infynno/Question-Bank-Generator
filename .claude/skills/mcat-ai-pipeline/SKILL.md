---
name: mcat-ai-pipeline
description: Work on the multi-agent question-generation pipeline of the Question Bank Generator: LangGraph workflow (nodes, routes, state, engine), agents (generator, reviewer, regenerator, blind solver, image generator, option balancer), prompts, prompt builder, scoring thresholds, LLM provider wiring, token and cost tracking, mock fixtures. Use whenever changing how questions are generated, scored, validated, regenerated or priced, editing any prompt, or debugging why questions are rejected, low quality, or mis-costed.
---

# AI pipeline

## Flow (production path: workflow/engine.py + engine_helpers.py)
`fused_generator` (draft + honest 100-point self-critique) -> dedup/anti-collision loop -> `_run_question_review_loop`: deterministic validator (`agents/validators.py`, free; auto-repairs dashes; blocking defects regenerate or reject without any review call) -> reviewer and blind solver run **concurrently** (`run_review_and_solve`; both billed) -> `route_after_review`: score > threshold and solver verified goes to `image_generator` (only if a diagram is needed) then `finalize`; otherwise `regenerator` and back to the validator; attempts exhausted goes to `reject`.

`workflow/graph.py` and `routes.py` hold an equivalent LangGraph definition and routing helpers that tests still import; the live engine does not execute the compiled graph, so change `engine_helpers.py` first and keep `routes.py` in sync.

Files: `workflow/nodes.py` (node fns plus `build_review_update`, `build_solver_update`, `build_usage_only_update`, `run_review_and_solve`), `routes.py`, `state.py` (`AgentWorkflowState`), `engine.py` + `engine_helpers.py`, `agents/*` (LLM calls), `agents/validators.py`, `agents/prompts.py`, `agents/prompt_builder.py`.

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
- Reviewer and blind solver raise `QualityCheckUnavailableError` after two failed attempts instead of passing an item. Only `LLMNotConfiguredError` (no credentials, offline demo/tests) uses heuristic fixtures. Tests that simulate offline mode must raise `LLMNotConfiguredError`, not a generic error.
- Generator and regenerator no longer substitute mock questions for real provider failures; the engine's slot retry handles the exception.
- `ALWAYS_INDEPENDENT_REVIEW=true` forces the reviewer even if the self-critique passed. Truncated completions (`finish_reason == "length"`) are retried with a larger budget up to `LLM_MAX_TOKENS_CEILING`.

## Editing prompts
Prompts are long and heavily tuned. Make surgical edits, keep section numbering, and run `test_agents.py`, `test_pedagogy.py`, `test_additional_instructions.py`. If a rubric or threshold changes, update `docs/MCAT_RUBRIC.md` and `docs/ARCHITECTURE.md` too.

## Providers and cost
- Providers resolve through `config.ACTIVE_LLM_PROVIDER` (deepinfra, anthropic, openai). LLM calls go through LiteLLM; model-id normalization (e.g. the `anthropic/` prefix) lives in `agents/base.py`, so add provider behavior there, not inside feature agents.
- Token and cost math is deterministic and lives with `schemas/token.py` plus config price properties: DeepInfra $0.098 in / $0.294 out per 1M; Anthropic and OpenAI have their own rates (cache read/write for Anthropic); images use a flat per-image rate scaled by size. Re-read `docs/TOKEN_TRACKING.md` and run `test_tokens.py` after any change. Every LLM call, including blind solver and calls whose verdict is discarded, must be counted; `duration_ms` rides on `TokenUsage` into the usage breakdown.

## Tests without live LLMs
Mock fixtures are in `agents/mock_fixtures.py` and `_mock_tokens.py`. Tests marked `live_e2e` hit real APIs and are excluded by default; never run them without the user's say-so since they cost money.
