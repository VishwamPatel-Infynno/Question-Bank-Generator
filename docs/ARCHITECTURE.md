# System Architecture & Multi-Agent Workflow

Engineered by **[Infynno Solutions LLP](https://infynno.com/)** (*"Infinite Innovations"*).

This document details the software architecture, multi-agent design patterns, state management, database schema, background batch execution services, and frontend systems powering the **Infynno MCAT Question Bank Generator v2.0**.

---

## 1. High-Level Architecture Overview

The system is constructed as an asynchronous, event-driven multi-agent workflow orchestrated by the engine in `app/workflow/engine.py` (nodes and routing in `nodes.py` / `routes.py`; `graph.py` keeps an equivalent LangGraph StateGraph definition) and served via **FastAPI** with **Server-Sent Events (SSE)** to a high-performance **React 19** frontend featuring a streamlined **3-Step Guided Question Wizard**, a dedicated full-width **Generation & Review Workspace**, and an enterprise **Batch Execution Engine**.

```mermaid
graph TD
    User([User / Web Client]) -->|POST /api/generate| API[FastAPI Orchestrator]
    API -->|Initialize State| Graph[LangGraph Fused Engine]
    
    subgraph "Quality-Gated Generation Workflow"
        Graph --> NodeFused[Fused Draft & Self-Critique Engine]
        NodeFused --> NodeVal[Deterministic Validator<br>free structural checks + dash repair]

        NodeVal -->|Blocking defect & Iteration < 3| NodeRegen[Autonomous Remediation Engine]
        NodeVal -->|Blocking defect & Iteration >= 3| NodeReject[Strict Quality Gate Reject]
        NodeVal -->|Clean| Par[Run concurrently]

        Par --> NodeRev[Independent Psychometric Auditor]
        Par --> NodeBlind[Blind-Solver Dual Validation Agent]

        NodeRev -->|Audit Score <= 90 & Iteration < 3| NodeRegen
        NodeRev -->|Score <= 90 & Iteration >= 3| NodeReject
        NodeBlind -->|Discrepancy OR Confidence < 88% & Iteration < 3| NodeRegen
        NodeBlind -->|Discrepancy OR Confidence < 88% & Iteration >= 3| NodeReject
        NodeRegen --> NodeVal

        NodeRev -->|Score > 90 AND Solver verified| NodeVis{Needs Visual?}
        NodeBlind --> NodeVis
        NodeVis -->|Yes| NodeImg[Infynno Visual & Vector Engine]
        NodeVis -->|No| NodeFin[Finalize & Staging Node]
        NodeImg --> NodeFin
    end

    NodeReject -->|Halt & Discard Draft| SSEStream[SSE Event Stream]
    NodeFin -->|Stage for Admin Review or Save| PG[(PostgreSQL 16 DB)]
    NodeFin --> SSEStream
    SSEStream -->|Real-Time SSE JSON Updates| User
```

### 1.2 Dual First-Class AI Inference Architecture

The multi-agent workflow is architected with a decoupled, provider-agnostic inference layer orchestrated by **LiteLLM**. The active inference engine is switchable on demand via the `ACTIVE_LLM_PROVIDER` environment variable without code modifications:

1. **DeepInfra Provider (`ACTIVE_LLM_PROVIDER=deepinfra`)**:
   - **Primary Model**: `deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017`
   - **Characteristics**: Extreme throughput (~110-140 tok/s), 1,024,000-token context window, sub-second TTFT (Time-To-First-Token).
   - **Official Rate Card**: $0.098 input / $0.294 output per 1M tokens.
   - **Visual Stimuli**: Integrated with `black-forest-labs/FLUX-2-klein-4b` ($0.014/unit base rate).

2. **Anthropic Provider (`ACTIVE_LLM_PROVIDER=anthropic`)**:
   - **Primary Model**: `claude-haiku-5-5` (or aliases `claude-3-5-haiku-20241022`, `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`).
   - **Characteristics**: High nuance and instruction obedience, 200,000-token context window.
   - **Official Rate Card (Claude Haiku 5.5)**: $0.10 input / $0.50 output per 1M tokens ($\le$ 100K prompt); $0.50 input / $2.50 output (> 100K prompt).
   - **Prompt Caching Accounting**: First-class tracking for Anthropic ephemeral cache read ($0.01 / 1M tokens) and cache creation ($0.125 / 1M tokens) with automatic mathematical price calculations.

Both engines strictly enforce model parameter constraints (`DEFAULT_TEMPERATURE = 0.2`, `REVIEWER_TEMPERATURE = 0.1`, `BLIND_SOLVER_TEMPERATURE = 0.1`) and feed identical Pydantic transfer schemas into the LangGraph state machine.

---

## 2. Multi-Agent StateGraph Workflow

The workflow enforces a strict psychometric quality contract. A question **must score higher than 90 out of 100** on the psychometric rubric and pass **Blind-Solver independent validation** to be approved for publication.

### 2.1 StateGraph Workflow Diagram

```mermaid
stateDiagram-v2
    [*] --> FusedGenerator: Start Generation

    FusedGenerator --> Validator: Draft + honest self-critique
    note right of FusedGenerator
        Offline mode only (no credentials):
        mock fixtures. Real provider errors
        raise and the slot retries.
    end note

    state ValidatorRouter <<choice>>
    Validator --> ValidatorRouter: Deterministic checks + dash repair
    ValidatorRouter --> Regenerator: Blocking defect AND Cycles < 3
    ValidatorRouter --> StrictQualityGate: Blocking defect AND Cycles == 3
    ValidatorRouter --> ReviewFork: Clean

    state ReviewFork <<fork>>
    ReviewFork --> Reviewer
    ReviewFork --> BlindSolver
    state ReviewJoin <<join>>
    Reviewer --> ReviewJoin: 100-pt rubric (fails closed on bad output)
    BlindSolver --> ReviewJoin: Key agreement + confidence (fails closed)

    state GateRouter <<choice>>
    ReviewJoin --> GateRouter
    GateRouter --> Regenerator: Score <= 90 OR solver discrepancy/confidence < 88% (Cycles < 3)
    GateRouter --> StrictQualityGate: Same failure at Cycles == 3
    Regenerator --> Validator: Remediated draft (Cycle + 1)

    GateRouter --> ImageGenerator: Passed AND Image Required
    GateRouter --> FinalizeNode: Passed AND Text Only
    ImageGenerator --> FinalizeNode: Attach SVG / AI Visual

    StrictQualityGate --> RejectedEnd: Discard Draft & Bypass DB
    RejectedEnd --> [*]

    FinalizeNode --> PostgreSQL: Persist Question with Token Metrics
    PostgreSQL --> CompletedEnd: Publish to Bank
    CompletedEnd --> [*]
```

### 2.3 Two-Tier Quality Threshold Architecture

The system implements a calibrated two-tier quality threshold model to ensure uncompromising individual question bank admission while enabling resilient high-throughput batch evaluation:

| Tier | Governing Threshold | Scope & Application | System Consequence |
| :--- | :---: | :--- | :--- |
| **Tier 1: Question Bank & AI Validated Gate** | **$> 90$ Points**<br>`PASSING_SCORE_THRESHOLD = 90` | Applied to every candidate question drafted in live sessions or batch workers. | Questions scoring $> 90$ qualify for admission into the permanent **Question Bank** or the dedicated **AI Validated** repository (`status = 'ai_validated'`). Candidate items scoring $\le 90$ must be remediated or discarded. |
| **Tier 2: Batch Activity Run Evaluation Gate** | **$> 85$ Points**<br>`BATCH_PASSING_SCORE_THRESHOLD = 85` | Applied across aggregate generation jobs in multi-job background batches (e.g. 10 jobs x 5 questions = 50 total). | Jobs achieving an aggregate question quality $\ge 85$ are marked as passing batch runs (`status = 'completed'`). Jobs with sub-85 averages are highlighted for instructor review or targeted retry. |

---

## 3. Agent Specifications & Prompt Engineering

The system coordinates specialized autonomous engines with a deterministic quality gate:

### 3.1 Fused Draft-and-Critique Cognitive Engine (`fused_generator_node` / `generator.py`)
- **Mission**: Primary workflow entry point. Synthesizes a high-yield clinical or scientific scenario for the selected AAMC MCAT section with 4 distinct options (A, B, C, D) and immediately conducts an internal 100-point self-critique within a single LLM round-trip.
- **Core Prompt Strategy**:
  - Uses section-specific rules (e.g., enzyme kinetics and thermodynamics for Chem/Phys, rhetorical thesis and authorial intent for CARS, molecular pathways and biochemical regulation for Bio/Biochem, and behavioral theories and sociological stratification for Psych/Soc).
  - Explicitly crafts 1 definitive correct key and 3 sophisticated distractors representing realistic cognitive biases, arithmetic sign inversions, or calculation traps.
  - **Option Symmetry & Anti-Guessability Engine**: Enforces strict word count parity (all options within $\pm 15\%$ or 2-4 words of each other), parallel grammatical syntax, and balanced epistemic qualification.
  - **Anti-AI Punctuation Standard**: Strictly forbids em dashes (`—`), en dashes (`–`), or double hyphens (`--`); enforces standard single hyphens (`-`).
  - **3-Part Structured Mentor Explanations**: Generates a rigorous 3-card explanation layout:
    1. *Why Option [Key] is Correct*: Establishes core intuition and step-by-step mathematical or deductive proof.
    2. *Why Other Options are Incorrect*: Itemized distractor cards dissecting why each wrong choice fails and why students are tempted.
    3. *Primary Cognitive Trap Spotlight*: Dedicated spotlight with exact Trap classification, Error Mechanism, and actionable Student Defense Strategy.
  - **Automatic (Smart AI Choice) Cognitive Trap Engine**: When `primary_trap` is `"Automatic"`, the generator evaluates the drafted item and dynamically selects the best-fit trap from the 11 official MCAT trap types (`Scope_Shift`, `Keyword_Trap`, `Extreme_Language`, `Correlation_vs_Causation`, `Partial_Match`, `Half_Truth`, `Unwarranted_Assumption`, `Calculation_Formula_Trap`, `Out_of_Scope`, `False_Dichotomy`, `Over_generalisation`). The chosen trap is recorded in `draft.primary_trap` and persisted across the workflow.
  - **Fallback Trap Detection**: If `primary_trap` is omitted or unpopulated, `generator.py` and `nodes.py` run regex taxonomy matching against the explanation text to extract and assign the trap automatically.
  - **Immediate Self-Critique Object**: Evaluates Authenticity, Clarity, Distractor Traps, and Explanation Rigor.
- **Review Routing**:
  - The self-critique is an honest, evidence-based pre-check (points are deducted for every named flaw; scores are not scripted). With `ALWAYS_INDEPENDENT_REVIEW=true` (default) the independent Auditor and the Blind Solver audit every draft regardless of the self-score. Setting it to `false` restores the legacy shortcut where a self-score above 90 skips the Auditor.
  - A draft that fails the Deterministic Validator never reaches an LLM reviewer: it is regenerated with the exact findings, or rejected once attempts are exhausted.
- **Custom Authoring Instructions Priority**:
  - Accepts educator-specified pedagogical directives (`additional_instructions`) from `GenerationRequest` via Guided Wizard Step 3.
  - Bound directly to the LangGraph `WorkflowState` and injected with high-priority mandate into prompt builders (`app/agents/prompt_builder.py`, `app/agents/generator.py`, and `app/agents/regenerator.py`).
  - Governs scientific constraints, clinical scenarios, calculation traps, and reasoning boundaries across passage generation, question generation, and all remediation critique cycles.
- **Modular Prompt Construction (`prompt_builder.py`)**: User-turn prompt assembly, section instructions, cognitive trap specifications, and cross-item diversity calibration strings are decoupled into [`backend/app/agents/prompt_builder.py`](../backend/app/agents/prompt_builder.py) (`_build_generator_user_prompt`), ensuring pure deterministic string assembly without external LLM side effects.
- **Inference Gateway & Fast Model Cascade**: High-throughput enterprise reasoning model (~110-140 tok/s, Temperature: `0.2` for strict instruction adherence). Powered by `DEFAULT_TEXT_MODEL` with fallback to `FAST_MODEL_CASCADE` identifiers parsed via `parse_fast_model_cascade`.

### 3.2 Blind-Solver Dual-Validation Agent (`blind_solver.py` / `blind_solver_node`)
- **Mission**: Acts as an algorithmic test candidate, solving the drafted question completely blind without access to the author's answer key, explanation, or self-critique rubric.
- **Solving Mechanism**:
  - Receives only the scientific passage or discrete scenario and the four unlabelled options ($A, B, C, D$).
  - Independently derives the scientific solution, identifies the correct key, and assigns a numerical confidence score ($0 - 100\%$).
- **Dual-Validation Contract**:
  - **Key Agreement**: The blind-solver's selected answer key must match the draft's intended `correct_answer_id`.
  - **Confidence Benchmark**: The blind-solver's confidence must satisfy $\ge 88\%$ (`BLIND_SOLVER_CONFIDENCE_THRESHOLD = 88`).
- **Fail-Closed Behavior**: Missing or invalid solver output (bad key, missing confidence) is retried once and then raises `QualityCheckUnavailableError`; an item is never certified because the solver errored. The only bypass is offline mode (no LLM credentials configured at all).
- **Independence & voting**: With `BLIND_SOLVER_SAMPLES=2` (default) two samples solve the question concurrently on different option layouts (original and reversed; a third, rotated layout only breaks a tie when `BLIND_SOLVER_SAMPLES=3`). Layout variation is skipped when an option refers to another by letter. Verification needs a strict majority on the author's key, mean confidence of the agreeing samples at or above the threshold, and no majority ambiguity flag; a split vote is never verified. The optional `BLIND_SOLVER_MODEL` runs the solver on a different model than the generator, and the figure description is included when a diagram is required. Answers are parsed from standalone letters ("Option C", "THE ANSWER IS D"), and the reasoning is requested before the key.
- **Concurrency**: With `PARALLEL_REVIEW_AND_SOLVE=true` (default) the solver runs concurrently with the Auditor, saving one LLM round trip per question. Both calls are billed even when the review fails first.
- **Autonomous Rerouting**:
  - If the blind solver **agrees** with high confidence ($\ge 88\%$), `blind_solver_passed = True`, and the question bypasses lengthy remediation directly to the visual engine or finalize node.
  - If the blind solver **disagrees** or has low confidence ($< 88\%$), the discrepancy proves that the distractors or stem contain genuine ambiguity or misleading premises. The workflow sets `blind_solver_passed = False` and routes the draft directly to the Remediation Engine with the blind solver's dissenting proof.
- **Inference Gateway**: High-throughput enterprise reasoning model (Temperature: `0.1` for deterministic, zero-hallucination solving, max tokens: `1200`).

### 3.3 Independent Senior Psychometric Auditor (`reviewer.py`)
- **Mission**: Acts as an impartial Senior Psychometric Auditor, independently evaluating candidate questions whenever the initial draft does not clear the self-critique threshold, fails blind-solver validation, or has completed a remediation cycle.
- **Evaluation Rubric (100 Points)**:
  1. *MCAT Authenticity & Scientific Rigor* (0-25 points)
  2. *Clarity & Logical Soundness* (0-25 points)
  3. *Distractor Trap Quality & Anti-Guessability* (0-25 points) - Docks 5-8 points if option length disparity $\ge 20\%$.
  4. *Explanation & Key Rigor* (0-25 points)
- **Quality Benchmark**:
  - Passing Score: **$> 90$** points ($91 - 100$).
  - Failing Score: **$\le 90$** points ($0 - 90$).
- **Strict Parsing**: Every pillar score must be present and within 0-25. Missing or out-of-range scores no longer default to a passing value; the call is retried once and then fails closed with `QualityCheckUnavailableError`.
- **Output**: Returns numerical pillar scores, observed strengths, specific weaknesses, and actionable remediation instructions.
- **Inference Gateway**: High-throughput enterprise reasoning model (Temperature: `0.1` for objective, deterministic evaluation).

### 3.4 Autonomous Remediation Engine (`regenerator.py`)
- **Mission**: Triggered exclusively when the score is $\le 90$ or blind solver fails. It digests the exact critique, distractor deficiencies, dissenting blind-solver rationales, and recommendations to repair the draft.
- **Rules**:
  - Fixes borderline ambiguities, equalizes option lengths, and sharpens distractor plausibility.
  - Deepens step-by-step rationales explaining why the key is incontrovertible and why every distractor fails.
  - Re-submits the updated draft back to the Reviewer for re-audit.
- **Inference Gateway**: High-throughput enterprise reasoning model (Temperature: `0.2` for disciplined remediation).

### 3.5 Strict Quality Gate (`reject_node` in `app/workflow/nodes.py`)
- **Mission**: Deterministic circuit breaker. If a candidate draft fails to exceed 90 points after reaching the maximum permitted remediation cycles (`MAX_REGENERATION_ATTEMPTS = 3`), the workflow halts immediately.
- **Safety Guarantee**:
  - **Bypasses Image Generation**: Prevents wasted computation and unnecessary token expenses.
  - **Discards from Database**: Zero substandard questions enter the PostgreSQL repository.
  - **Diagnostic Payload**: Transmits full rejection telemetry and history via SSE for audit inspection.

### 3.6 Infynno Visual & Vector Engine (`image_generator.py`)
- **Mission**: Generates visual stimuli for questions requiring graphical diagrams (e.g., metabolic cycles, enzyme kinetics, gel electrophoresis assays, optics diagrams; strictly disabled for CARS).
- **Autonomous AI Routing**: Supports autonomous AI-driven stimulus synthesis when `allow_ai_images` is enabled and deemed pedagogically necessary.
- **Hybrid Visual Engine**:
  - *Programmatic SVG Renderer*: Generates clean, crisp, scalable vector graphics for reaction mechanisms, cell transport, coordinate grids, and statistical bar charts.
  - *FLUX-2-klein-4b Neural Visual Engine*: State-of-the-art rectified-flow transformer (`black-forest-labs/FLUX-2-klein-4b`) hosted on DeepInfra for photorealistic scientific illustrations with dynamic provider cost extraction and a flat $0.014 unit baseline rate.

### 3.7 Question Deduplication & Collision Prevention Subsystem (`deduplication.py`)
- **Mission**: Autonomous real-time safeguard against cognitive repetition, duplicate stems, and identical question angles across the question repository. Guarantees that neither live-generated items nor high-throughput batch sets introduce redundant questions into the bank.
- **Multi-Metric Mathematical Similarity Scoring Model**:
  Operates on normalized question stems (case-folding, alphanumeric filtering, and common English/scientific stopword removal) and 4-choice distractor sets:
  $$\text{Composite Similarity} = 0.35 \times S_{\text{containment}} + 0.25 \times S_{\text{jaccard\_1gram}} + 0.20 \times S_{\text{jaccard\_2gram}} + 0.20 \times S_{\text{sequence\_ratio}}$$
  1. *Token Containment Metric* ($S_{\text{containment}}$, 35% weight): Evaluates asymmetric lexical inclusion $\frac{|T_{\text{candidate}} \cap T_{\text{reference}}|}{\min(|T_{\text{candidate}}|, |T_{\text{reference}}|)}$ to detect paraphrased questions sharing the same scientific core despite differing introductory clauses.
  2. *1-Gram Jaccard Metric* ($S_{\text{jaccard\_1gram}}$, 25% weight): Evaluates vocabulary overlap $\frac{|T_1 \cap T_2|}{|T_1 \cup T_2|}$.
  3. *2-Gram Jaccard Metric* ($S_{\text{jaccard\_2gram}}$, 20% weight): Measures preservation of adjacent scientific bigrams (e.g., "activation energy", "uncompetitive inhibition", "capillary hydrostatic pressure").
  4. *SequenceMatcher Ratio* ($S_{\text{sequence\_ratio}}$, 20% weight): Captures character-level longest contiguous matching sub-sequences via Gestalt pattern matching.
  5. *Distractor Options Overlap Booster*: Evaluates pairwise lexical similarity across candidate and reference option sets ($A, B, C, D$). If $\ge 75\%$ of options are identical or near-identical, the engine applies an options collision penalty that elevates overall similarity or establishes an empirical collision floor.
- **Collision Decision Boundary**:
  - **Threshold $\ge 0.80$ (80%)**: Flagged as a duplicate collision (`is_duplicate = True`). Triggers the autonomous anti-collision loop or flags the item for educator review.
  - **Score $< 0.80$**: Cleared as a distinct pedagogical item (`is_duplicate = False`).
- **Autonomous Anti-Collision Loop (`_run_deduplication_anti_collision_loop`)**:
  When drafting questions during batch or live generation, the candidate is compared against:
  1. Existing questions in PostgreSQL matching the exact **Section** and **Subtopic**.
  2. Previously generated sibling items within the active batch session.
  If a collision ($\ge 0.80$) is detected during generation, the engine executes an autonomous anti-collision prompt injection:
  ```
  CRITICAL: The drafted question is too similar to an existing item in this subtopic.
  Conflicting Item: "[matched_question_stem]"
  You MUST pivot to a completely different clinical scenario, distinct biochemical mechanism,
  or alternative calculation angle while preserving the target AAMC skill.
  ```
- **Administrative Inspection & Override Audit Trail**:
  If a flagged question is presented to educators during review, the UI displays an amber badge `⚠️ Duplicate Risk (XX%)`. Educators can open the side-by-side **Duplicate Comparison Modal** to compare stems, options, and explanations. Choosing **"Override & Approve"** dispatches `POST /api/questions/{id}/override-duplicate`, stamping the record with:
  ```json
  {
    "is_duplicate_override": true,
    "duplicate_info": {
      "is_duplicate": true,
      "similarity_score": 0.88,
      "matched_question_id": "ref-uuid",
      "matched_question_stem": "Existing stem...",
      "match_reason": "High question stem textual overlap (88%)",
      "is_overridden": true,
      "overridden_at": "2026-10-28T17:15:00Z"
    }
  }
  ```
- **Batch Duplicate Cluster Resolution & Permanent Purge**:
  When clustering batch questions via `GET /api/batches/{id}/duplicate-clusters`, educators can resolve duplicate groups via `POST /api/batches/{id}/resolve-duplicates`. Under `action="delete"`, identified redundant duplicates are permanently hard-deleted from PostgreSQL via `hard_delete_questions_batch`, completely eliminating ghost records from batch monitors and ensuring clean subsequent refills. Alternatively, `action="archive"` marks duplicate items with status `discarded`.

---

### 3.8 Deterministic Validator (`validators.py`)
- **Mission**: Free, pure-Python structural checks that run before any LLM review, so structural defects are caught for certain instead of depending on a model's opinion.
- **Blocking checks**: exactly four unique options A-D; valid key present and in the options (single key for single-choice); no all/none-of-the-above; no empty stem, option or explanation.
- **Auto-repair**: em dashes, en dashes and `--` are replaced with a single hyphen (`sanitize_draft_dashes`) before validation, enforcing the Anti-AI Punctuation Standard in code, not only in prompts.
- **Warnings (recorded, non-blocking)**: option length ratio above 1.25, correct answer being the longest option, passage word band, unaddressed distractors. The verdict is stored in `stage_outcomes["deterministic_validation"]`.
- **Remediation**: blocking findings are packaged as a failing review so the regenerator fixes exactly those defects.

### 3.9 Fail-Closed Generation Policy
- Reviewer, Blind Solver, Generator, Fused Generator, Passage Writer and Regenerator use heuristic or mock fixtures **only** when no LLM credentials are configured **and** `OFFLINE_MODE=true` is set explicitly (demos and offline tests). Without the flag, a missing key raises `LLMNotConfiguredError`, the run fails fast with a clear message (no slot retries), and mock-produced questions are tagged `stage_outcomes.offline_mode`.
- Any real provider failure raises instead; the per-slot retry in `engine.py` (up to 3 attempts) absorbs it and emits `question_failed` if all attempts fail. No canned question is ever saved in place of a failed generation.
- Truncated completions (`finish_reason == "length"`) are retried with a doubled token budget up to `LLM_MAX_TOKENS_CEILING` rather than being "repaired" from partial JSON.

---

## 4. State Management & Lifecycle

Workflow state is tracked via a typed dictionary `AgentWorkflowState` defined in [`backend/app/workflow/state.py`](../backend/app/workflow/state.py):

```python
class AgentWorkflowState(TypedDict, total=False):
    request: Dict[str, Any]  # Original GenerationRequest parameters
    current_draft: Optional[Dict[str, Any]]  # Active candidate QuestionDraft
    current_review: Optional[Dict[str, Any]]  # Latest ReviewScore rubric
    iteration_count: int  # Current iteration counter (1, 2, 3)
    iterations_history: List[Dict[str, Any]]  # Full audit history of drafts and reviews
    image_url: Optional[str]  # URL if external image generated
    image_svg: Optional[str]  # Embedded SVG markup
    image_description: Optional[str]  # Accessibility alt text
    final_question: Optional[Dict[str, Any]]  # Finalized Question model
    rejection_data: Optional[Dict[str, Any]]  # Telemetry if rejected by Quality Gate
    status: str  # Workflow lifecycle phase
    active_agent: str  # Currently executing agent node
    log_messages: List[str]  # Running log entries

    # Per-Request Token Usage & Cost Accumulator
    total_tokens: int  # Cumulative tokens consumed
    total_prompt_tokens: int  # Cumulative input tokens
    total_completion_tokens: int  # Cumulative output tokens
    total_cost_usd: float  # Cumulative cost in USD ($0.098 in / $0.294 out)
    agent_usage_breakdown: List[Dict[str, Any]]  # Itemized usage per agent cycle
    latest_usage: Optional[Dict[str, Any]]  # Usage of the most recently executed node
```

### 4.1 State Accumulation Pattern
At each node execution, token consumption from the LLM response is unpacked and added to cumulative state counters:
1. `fused_generator_node`: Accumulates single-pass authoring and 100-point self-critique tokens, appending `Question Writer & Reviewer` entry to `agent_usage_breakdown`.
2. `regenerator_node`: Accumulates remediation tokens if initial score $\le 90$ and appends `Question Improver` entry.
3. `reviewer_node`: Accumulates independent audit tokens during remediation cycles and records usage in `iterations_history`.
4. `image_node`: Accumulates visual stimulus synthesis tokens / compute units for `Diagram & Chart Maker`.
5. `finalize_node`: Binds final accumulated totals and itemized breakdown directly into the `Question` schema for database persistence.

### 4.2 Modular Execution Architecture (`engine.py` & `engine_helpers.py`)
The streaming execution pipeline is implemented in [`backend/app/workflow/engine.py`](../backend/app/workflow/engine.py) via `run_workflow_stream` and `run_workflow`. High-level orchestration helpers are decoupled into [`backend/app/workflow/engine_helpers.py`](../backend/app/workflow/engine_helpers.py):
- `_prepare_shared_passage_and_visual`: Asynchronously generates shared stimulus reading passages and visual diagrams.
- `_run_review_and_repair_loop`: Coordinates iterative remediation cycles against the 100-point rubric.
- `_persist_live_question`: Handles transactional database persistence of approved candidate items.

---

## 5. Background Batch Execution Service (`batch_runner.py`)

The backend utilizes an asynchronous worker pool managed by [`backend/app/services/batch_runner.py`](../backend/app/services/batch_runner.py) supporting 2 calibrated Generation Scopes governed by the unified 5-question Job architecture:

1. **Practice Set (5 Questions, 1 Single Job)**:
   - Dispatches a single background worker job comprising 5 questions linked to a shared reading passage (or 5 discretes).
   - Generates and self-audits within ~35-50s, streaming real-time status and automatically staging passing items (`score > 90`) into the **AI Validated** bank (`status = 'ai_validated'`).
2. **Full Exam (50 Questions, 10 Parallel Jobs)**:
   - Enterprise background batch spawning 10 parallel jobs (5 questions each) across the global worker pool.
   - Automatically provisions shared passages per job, coordinates concurrent inference calls under rate-limit semaphores, and dynamically aggregates batch completion metrics.

```mermaid
graph TD
    Client[Web Client] -->|POST /api/batches/start| API[Batches API Endpoint]
    API --> Runner[launch_background_batch]
    
    Runner --> BatchDB[Create Batch Record in DB]
    Runner --> JobDB[Create Job Records in DB: 1 for Practice Set, 10 for Full Exam]
    Runner --> BackgroundTask[Spawn Async Background Worker Pool]
    
    API -->> Client|202 Accepted + Batch/Job UUIDs| Client

    subgraph "Parallel Worker Execution (1 Job [5 Qs] or 10 Jobs [50 Qs])"
        BackgroundTask --> Job1[Job 1: 5 Qs]
        BackgroundTask --> Job2[Job 2: 5 Qs]
        BackgroundTask --> Job3[Job 3: 5 Qs]
        BackgroundTask --> Job4[Job 4: 5 Qs]
        BackgroundTask --> JobDots[...]
        BackgroundTask --> Job10[Job 10: 5 Qs]
        
        Job1 --> Workflow1[Multi-Agent LangGraph]
        Job2 --> Workflow2[Multi-Agent LangGraph]
        Job3 --> Workflow3[Multi-Agent LangGraph]
        Job4 --> Workflow4[Multi-Agent LangGraph]
        Job10 --> Workflow10[Multi-Agent LangGraph]
    end

    Workflow1 --> PersistQ[(Save Questions to DB with status=ai_validated)]
    Workflow2 --> PersistQ
    Workflow3 --> PersistQ
    Workflow4 --> PersistQ
    Workflow10 --> PersistQ
    
    PersistQ --> AtomicUpdate[refresh_batch_aggregates Atomic DB Sync]
    AtomicUpdate --> UpdateBatch[Update Batch & Job status to completed]
```

### 5.1 Global Worker Pool Concurrency & Rate Limiting Engine

To support heavy concurrent workloads and prevent thread starvation or provider rate limits, the batch execution engine implements multi-layered concurrency controls:

1. **Global Worker Pool Semaphore (`_GLOBAL_JOB_SEMAPHORE`)**:
   - Initialized as a singleton semaphore: `asyncio.Semaphore(config.GLOBAL_MAX_CONCURRENT_JOBS)` (default: **4 concurrent jobs**).
   - Constrains simultaneous job execution across **all active running batches** in the system, preventing resource exhaustion when multiple batches are launched concurrently.
2. **Global LLM Concurrency Limiter**:
   - Managed via `config.GLOBAL_MAX_CONCURRENT_LLM_CALLS` (default: **10 concurrent inference calls**).
   - Bounds the maximum number of simultaneous HTTP requests dispatched to DeepInfra.
3. **Exponential Backoff & Rate-Limit Resilience (`call_llm` in `app/agents/base.py`)**:
   - Automatically intercepts HTTP 429 (Rate Limit) and 503 (Service Unavailable) responses.
   - Retries up to `LLM_MAX_RETRIES = 4` times using exponential backoff:
     $$\text{Wait Seconds} = \text{base\_backoff} \times 2^{\text{attempt}} + \text{jitter}$$
     with `LLM_BASE_BACKOFF_SECONDS = 1.5` and random fractional jitter to prevent thundering herd problems.
4. **Atomic Database State Aggregation (`refresh_batch_aggregates`)**:
   - Executes atomic SQL subqueries to calculate `completed_jobs`, `failed_jobs`, `actual_count`, `total_tokens`, and `cost_usd` directly inside PostgreSQL.
   - Eliminates read-modify-write race conditions between parallel background worker tasks.
5. **Autonomous In-Flight 3-Trials Policy & Resilient Batch Lifecycle**:
   - **Autonomous In-Flight Retries**: When executing batch jobs (`_run_single_job`), if fewer than the target number of questions are generated (e.g., due to strict psychometric threshold rejections), the runner automatically executes in-flight retries up to `3 max trials per set`. Each trial is tracked in `job.trial_count` and persisted to PostgreSQL.
   - **Live Telemetry & Trial State Indicators**: Active jobs undergoing shortfall retries broadcast live `AUTO-RETRYING (X/3)` status. If all 3 trials are completed without achieving the target count, the UI displays `3/3 TRIALS EXHAUSTED`, clearly signaling that no further autonomous trials remain.
   - **Graceful Batch Halt (`POST /api/batches/{id}/stop`)**: Cancels running asyncio worker tasks and updates remaining pending jobs to `"cancelled"` while preserving all successfully generated questions in the bank.
   - **Controlled Resume Sets (`POST /api/batches/{id}/retry`)**: Strictly reserved for manually stopped or cancelled batches that have incomplete jobs with remaining trials (`trial_count < 3`). Re-launches incomplete jobs into the worker pool. If all incomplete jobs have already exhausted 3 trials, the endpoint returns an explicit **HTTP 400 Bad Request** (`All incomplete sets in batch have already reached the maximum 3-trial limit or have already completed, and cannot be retried.`), preventing infinite retry loops.
   - **Global Halt (`POST /api/batches/cancel-all`)**: System-wide fail-safe terminating all active runner tasks cleanly.

### 5.2 Dual-Track Progress Architecture & Worker Telemetry Engine

The batch execution engine implements a **Dual-Track Progress Architecture** that decouples localized set-level replenishment from global batch milestone progress:

```mermaid
flowchart TD
    subgraph DualTrack["Dual-Track Batch Progress System"]
        subgraph Track1["Track 1: Batch-Level Aggregated Progress"]
            TotalTarget["Total Target: 50 Questions"] --> TotalAgg["Atomic DB Aggregation: actual_count / target_count"]
            TotalAgg --> TopBar["Top Progress Meter & Overall % Completion"]
        end

        subgraph Track2["Track 2: Job-Level Set Progress Strip"]
            SetTarget["Set Target: 5 Questions"] --> VisibleQs["Visible Validated Questions"]
            VisibleQs --> Pill1["Slot 1: in_bank / done"]
            VisibleQs --> Pill2["Slot 2: in_bank / done"]
            VisibleQs --> Pill3["Slot 3: active (generating)"]
            VisibleQs --> Pill4["Slot 4: pending"]
            VisibleQs --> Pill5["Slot 5: pending"]
        end
    end

    subgraph RefillLoop["In-Flight Replenishment Loop (_run_single_job_refill)"]
        Trial1["Trial 1: Draft Initial 5 Questions"] --> CheckShortfall{"Deficit > 0 & trial < 3?"}
        CheckShortfall -->|Yes| BumpTrial["Increment trial_count (e.g., Trial 2/3)"]
        BumpTrial --> ExtractPassage["Reuse Initial Set Passage & Stimulus"]
        ExtractPassage --> GenDeficit["Generate Exactly (target - actual) Replacements"]
        GenDeficit --> Recheck{"Passed Quality Gate?"}
        Recheck -->|Yes| FillSlots["Fill Pending Slots Atomically"]
        Recheck -->|No| CheckShortfall
        CheckShortfall -->|No / Exhausted| TerminateJob["Mark Job completed / failed"]
    end

    Track2 --> RefillLoop
```

1. **Job-Level Set Progress Track**:
   - Each set displays a 5-question visual progress strip (`job-q-pill-strip`) rendering the exact state of each question slot in the set:
     - `.in-bank`: Formally approved question in the Question Bank (purple accent).
     - `.done`: Validated question passing psychometric audit and ready for review (emerald accent).
     - `.active`: Currently generating or self-evaluating candidate (pulsing electric conduit animation).
     - `.pending`: Muted placeholder slot awaiting worker assignment.
2. **Batch-Level Aggregate Track**:
   - Aggregates accepted questions across all 10 concurrent worker jobs against the total batch target (50 questions), recalculating completion percentage atomically via PostgreSQL subqueries.
3. **In-Flight Deficit Replenishment (`_run_single_job_refill`)**:
   - When a job produces fewer than 5 valid questions on its first attempt, the runner does not discard the existing approved items or create a redundant passage. Instead, it extracts the passage and stimulus from existing set items and launches targeted generation for only the shortfall deficit, incrementing `trial_count` up to 3.

### 5.3 Question Lifecycle State Machine
Every question in the system progresses through an explicit, strictly guarded lifecycle state:

```mermaid
stateDiagram-v2
    [*] --> InProgressBatch: Batch Initiated (/api/batches/start)
    InProgressBatch --> QuestionGenerating: Job Workers Dispatched
    QuestionGenerating --> WithheldStatus: Question Evaluated
    state WithheldStatus {
        direction LR
        ScoreOver85: score > 85 (batch_only)
        ScoreUnder85: score <= 85 (below_threshold)
    }
    WithheldStatus --> WithheldStatus: Withheld from Review Queue (exclude_in_progress_batch=True)
    WithheldStatus --> BatchCompleted: All Jobs Finish Successfully
    BatchCompleted --> AtomicPromotion: promote_completed_batch_questions()
    state AtomicPromotion {
        direction LR
        PromotedToReview: score > 90 -> ai_validated
        RetainedBatchOnly: 85 < score <= 90 -> batch_only
    }
    WithheldStatus --> BatchFailedOrCancelled: Batch Stopped / Cancelled
    BatchFailedOrCancelled --> RetainedWithheld: Questions stay in batch_only (No Promotion)
    
    PromotedToReview --> InBank: Educator Approves into Bank
    PromotedToReview --> Discarded: Educator Rejects or Duplicate Archived
    InBank --> Discarded: Archive / Delete
    Discarded --> InBank: Restore Question
```

- **`batch_only`**: Active withholding status. Questions generated during live sessions or background batches are saved in `batch_only` (if score $> 85$) while the parent batch is running. This strictly prevents incomplete batches or intermediate drafts from leaking into the educator's "Ready for Review" queue.
- **`ai_validated`**: Background batch questions that cleared the 90+ quality gate (`score > 90`) whose parent batch has successfully completed (`status == 'completed'`). Atomically promoted by `promote_completed_batch_questions` and visible in the educator's review queue.
- **`in_bank`**: Formally approved questions published in the primary searchable Question Bank repository.
- **`below_threshold`**: Drafts that failed to achieve >85 points after remediation cycles (flagged or discarded).
- **`discarded`**: Archived or rejected items removed from active question banks or resolved during duplicate clustering.

### 5.4 Canonical Status Determination, Withholding Guards & Batch Idempotency

1. **Review Queue Withholding Safeguard**:
   During active batch execution, candidate questions scoring $> 85$ are saved with `status = 'batch_only'`. All repository search and count queries ([`backend/app/repositories/question_repository.py`](../backend/app/repositories/question_repository.py)) enforce an active subquery guard:
   ```python
   in_progress_batches = select(GenerationBatchModel.id).where(
       GenerationBatchModel.status == "in_progress"
   )
   stmt = stmt.where(
       or_(
           QuestionModel.batch_id.is_(None),
           QuestionModel.batch_id.notin_(in_progress_batches),
       )
   )
   ```
   This prevents questions from running batches from appearing in the "Ready for Review" tab or inflating repository status counts until the entire batch has cleanly completed.

2. **Atomic Batch Promotion (`promote_completed_batch_questions`)**:
   Implemented in [`backend/app/repositories/batch_repository.py`](../backend/app/repositories/batch_repository.py), this function runs atomically when a batch concludes and transitions to `"completed"` or `"partially_completed"`:
   - High-scoring questions (`final_score > 90`) in `batch_only` are promoted to `ai_validated` (making them immediately available in the educator's review queue).
   - Questions scoring between 86 and 90 (`85 < final_score <= 90`) remain in `batch_only` for historical inspection.
   - If a batch is actively stopped, cancelled, or aborted mid-run, `promote_completed_batch_questions` is bypassed entirely, safely retaining questions in `batch_only` without polluting review queues.

3. **Dynamic Job Allocation & Exact Target Count Guarantees**:
   In [`backend/app/services/batch_runner.py`](../backend/app/services/batch_runner.py), `launch_background_batch` dynamically partitions target quotas into parallel jobs capped at 5 questions per job:
   - 5 questions $\to$ 1 job of 5 items.
   - 50 questions $\to$ 10 jobs of 5 items.
   - 12 questions $\to$ 3 jobs of 5, 5, and 2 items.
   When duplicate resolution or quality gate dropouts create a deficit, `auto_resolve_batch_and_refill` and `refill_batch_deficit` launch targeted replacement jobs with diverse thematic angles, ensuring exact target count delivery.

4. **Idempotent Batch Counter Synchronization**:
   [`backend/app/repositories/question_repository.py`](../backend/app/repositories/question_repository.py) enforces idempotent batch counter updates in `save_question`. When editing an existing question or re-saving an approved item, the repository detects the existing record and skips counter increments, preventing counter inflation across re-edits or stage-to-bank transitions.

---

## 6. PostgreSQL 16 Database Architecture

The persistence tier runs on **PostgreSQL 16** managed through **SQLAlchemy 2.0 Async** and the **`asyncpg`** driver, featuring enterprise connection pooling and zero-downtime startup migrations (`init_db()` in [`backend/app/db/session.py`](../backend/app/db/session.py), delegating to schema and FTS verification in [`backend/app/db/init_db.py`](../backend/app/db/init_db.py)):

### 6.1 Enterprise Connection Pooling Parameters
To prevent database connection drops and handle parallel batch worker loads, the async engine is configured with:
- `pool_size = 20`: Core persistent database connections maintained in the pool.
- `max_overflow = 30`: Additional burst connections during heavy multi-batch load (total 50 connections).
- `pool_timeout = 60`: Seconds to wait before timing out if all connections are busy.
- `pool_recycle = 1800`: Automatically recycles connections after 30 minutes to prevent stale TCP sockets.
- `pool_pre_ping = True`: Automatically validates connection health prior to checking out.

### 6.2 Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    PASSAGES ||--o{ QUESTIONS : "contains (1:N)"
    BATCHES ||--o{ JOBS : "contains (1:N)"
    BATCHES ||--o{ QUESTIONS : "groups (1:N)"
    JOBS ||--o{ QUESTIONS : "produces (1:N)"

    PASSAGES {
        VARCHAR(64) id PK "Unique UUID4 passage identifier"
        VARCHAR(64) section "MCAT section enum (chem_phys, cars, bio_biochem, psych_soc)"
        VARCHAR(128) subtopic "Categorized syllabus topic"
        TEXT passage_text "Shared clinical or academic reading passage"
        TEXT visual_stimulus_svg "Programmatic SVG diagram"
        TEXT visual_stimulus_url "External diagram URL"
        TEXT visual_description "Alt text description"
        INTEGER question_count "Number of questions sharing this passage"
        BOOLEAN is_deleted "Soft-delete flag (admin DELETE triggers cascade question purge)"
        VARCHAR(64) deleted_at "ISO-8601 UTC deletion timestamp"
        VARCHAR(64) created_at "ISO-8601 UTC timestamp"
    }

    BATCHES {
        VARCHAR(64) id PK "Unique UUID4 batch identifier"
        VARCHAR(64) section "MCAT section enum"
        VARCHAR(128) subtopic "Categorized syllabus topic"
        VARCHAR(32) difficulty "low | medium | high"
        INTEGER total_questions "Total items requested in batch (e.g. 50)"
        INTEGER staged_questions "Items verified and staged"
        VARCHAR(32) status "in_progress | completed | failed"
        VARCHAR(64) created_at "ISO-8601 UTC timestamp"
    }

    JOBS {
        VARCHAR(64) id PK "Unique UUID4 job identifier"
        VARCHAR(64) batch_id FK "Reference to parent BATCHES"
        INTEGER job_number "Sequential index (1 to 10)"
        VARCHAR(32) status "pending | in_progress | completed | failed"
        INTEGER target_count "Target items for this job (e.g. 5)"
        INTEGER actual_count "Completed items count"
        INTEGER trial_count "Autonomous trial count (1 to 3 max)"
        VARCHAR(64) created_at "ISO-8601 UTC timestamp"
    }

    QUESTIONS {
        VARCHAR(64) id PK "Unique UUID4 identifier"
        VARCHAR(64) passage_id FK "Optional reference to PASSAGES"
        VARCHAR(64) batch_id FK "Optional reference to BATCHES"
        VARCHAR(64) job_id FK "Optional reference to JOBS"
        VARCHAR(64) section "MCAT section enum"
        VARCHAR(128) section_label "Human-readable subtest name"
        VARCHAR(128) subtopic "Categorized syllabus topic"
        VARCHAR(32) difficulty "low | medium | high"
        VARCHAR(32) status "in_bank | ai_validated | below_threshold | discarded"
        BOOLEAN is_deleted "Soft-delete flag preserving batch progress"
        VARCHAR(64) deleted_at "ISO-8601 UTC deletion timestamp"
        INTEGER mcat_scaled_score "Calibrated scaled score (118-132)"
        VARCHAR(128) aamc_skill "AAMC SIRS (Skill 1-4) or CARS Skill"
        TEXT stimulus_text "Clinical passage or context scenario"
        TEXT question_stem "Core question prompt"
        JSONB options "Array of strictly 4 options [{id, text}]"
        VARCHAR(8) correct_answer_id "A | B | C | D"
        TEXT explanation "3-part structured cognitive rationale"
        TEXT image_url "Optional external diagram URL"
        TEXT image_svg "Programmatic inline SVG markup"
        TEXT image_description "Accessibility alt text"
        INTEGER final_score "Reviewer score (> 90)"
        JSONB review_rubric "4-pillar scores, strengths, remediation"
        INTEGER iteration_count "Cycles executed (1-3)"
        JSONB iterations_history "Full evolutionary diff log"
        INTEGER total_tokens "Cumulative tokens consumed"
        INTEGER prompt_tokens "Cumulative prompt tokens"
        INTEGER completion_tokens "Cumulative completion tokens"
        DOUBLE_PRECISION cost_usd "Total cost in USD (rate per active provider)"
        JSONB token_usage_details "Per-agent itemized token breakdown"
        VARCHAR(64) combination_id "Matrix combination code (CMB00001)"
        VARCHAR(64) run_id "Execution run UUID4"
        VARCHAR(128) subcategory "Matrix subcategory taxonomy"
        VARCHAR(128) content_domain "Matrix domain (Science, Ethics)"
        VARCHAR(128) question_type "Passage_Based_Set, Independent_Discrete"
        VARCHAR(64) interaction_type "single_choice"
        VARCHAR(128) primary_trap "Cognitive distractor trap classification"
        VARCHAR(16) passage_required "Yes or No"
        INTEGER passage_questions "Passage question count"
        VARCHAR(16) image_required "Yes or No"
        VARCHAR(64) visual_type "None, SVG_Diagram, AI_FLUX_Image"
        JSONB duplicate_info "Collision metrics, matched stem & override timestamp"
        BOOLEAN is_duplicate_override "Explicit administrative override flag"
        TSVECTOR tsv_content "PostgreSQL FTS token vector for hybrid search"
        VARCHAR(64) created_at "ISO-8601 UTC timestamp"
    }
```

### 6.3 Passage Entity Lifecycle, Soft-Deletion & Batch Integrity
When multiple questions are generated as a passage set, they share a foreign key reference (`passage_id`) pointing to the parent `PASSAGES` record:
- **Passage Association**: Educators can browse shared passages in the Passage Bank and inspect all linked questions simultaneously.
- **Non-Destructive Soft-Deletion (`DELETE /api/passages/{passage_id}`)**: When an administrator deletes a reading passage via `delete_passage`, the repository soft-deletes both the passage and all associated questions (`is_deleted = true`, `deleted_at = now()`) in a single atomic SQL transaction.
- **Batch History Preservation**: Crucially, soft-deletion does **not** clear `job.passage_id` and does **not** decrement job or batch `actual_count` metrics. This guarantees that Batch Progress monitors and audit historical execution records remain 100% intact even if an educator deletes questions from the Question Bank.
- **Restoration Architecture**: Soft-deleted questions can be restored at any time via `POST /api/questions/{question_id}/restore` (`restore_question`). If the restored question references a soft-deleted passage, the parent passage is automatically restored (`is_deleted = false`, `deleted_at = null`) alongside it.
- **Composite Index Optimization**: To maintain high-velocity querying across thousands of questions, the `questions` table maintains 7 composite indexes:
  - `ix_questions_status_created` (`status`, `created_at`)
  - `ix_questions_section_created` (`section`, `created_at`)
  - `ix_questions_batch_job` (`batch_id`, `job_id`)
  - `ix_questions_section_subtopic` (`section`, `subtopic`)
  - `ix_questions_is_duplicate_override` (`is_duplicate_override`)
  - `ix_questions_section_difficulty` (`section`, `difficulty`)
  - `ix_questions_status_final_score` (`status`, `final_score`)

### 6.4 Deduplication & Override Schema Architecture
The deduplication subsystem extends the PostgreSQL schema with two persistent fields:
1. `duplicate_info JSONB`: Stores the serialized collision payload:
   ```json
   {
     "is_duplicate": true,
     "similarity_score": 0.88,
     "matched_question_id": "c1f7a012-3456-789a-bcde-f0123456789a",
     "matched_question_stem": "Under physiological conditions, which factor...",
     "match_reason": "High question stem textual overlap (88%)",
     "is_overridden": true,
     "overridden_at": "2026-10-28T17:15:00Z"
   }
   ```
2. `is_duplicate_override BOOLEAN DEFAULT FALSE`: Indexed boolean enabling lightning-fast administrative filtering of overridden questions in the Question Bank table.
- **Database Self-Healing**: Automated migration in [`init_db.py`](../backend/app/db/init_db.py) applies idempotent DDL statements (`ALTER TABLE questions ADD COLUMN IF NOT EXISTS duplicate_info JSONB;` and `ALTER TABLE questions ADD COLUMN IF NOT EXISTS is_duplicate_override BOOLEAN DEFAULT FALSE;`) upon application bootstrap.

---

## 7. Export & Print Studio Architecture

The **Export & Print Studio** ([`ExportPrintModal.jsx`](../frontend/src/components/modals/ExportPrintModal.jsx)) provides client-side document synthesis and multi-format export capabilities for educators and candidates.

```mermaid
graph TD
    QB[Question Bank / Filtered Items] --> Studio[Export & Print Studio Engine]
    
    Studio --> PDF[PDF Exam Paper]
    Studio --> StudyPack[Comprehensive Study Pack]
    Studio --> CSV[Standardized CSV Export]
    Studio --> JSON[Normalized JSON Bundle]
    
    PDF --> PrintStyles["@media print Layout Engine<br>(Header block, timer, page-break rules)"]
    StudyPack --> PrintStyles
    CSV --> BrowserDL[Browser Direct Download]
    JSON --> BrowserDL
```

### 7.1 Export Modes
1. **Official Exam Paper (PDF / Print)**:
   - Formatted for classroom and mock exam printing with candidate name/date header, official pacing instructions (~96s to ~101s per item), and clean typographic separation.
   - Enforces `.page-break { break-before: page; }` CSS print rules to ensure reading passages and question options never split awkwardly across page folds.
2. **Comprehensive Study Pack (PDF / Print)**:
   - Includes reading stimulus, question stem, answer key, and the complete step-by-step cognitive proof and distractor trap analysis.
3. **CSV Export Engine**:
   - Converts relational questions into standardized comma-separated columns (`id`, `section`, `subtopic`, `difficulty`, `stem`, `option_a` through `option_d`, `key`, `explanation`, `score`).
4. **JSON Relational Bundle**:
   - Serializes question items including full 4-pillar review rubrics, per-agent token tracking telemetry, and evolution histories.

---

## 8. Frontend Domain-Driven Architecture

The frontend follows an enterprise domain-driven component architecture split into top-level views, specialized domain components, and centralized hooks:

```
frontend/src/
├── views/                        # Top-level application view screens (code-split)
│   ├── index.js                  # Views barrel export
│   ├── AiValidatedQuestionsView.jsx # Dedicated AI Validated (>90) quality review desk
│   ├── BatchActivityView.jsx     # Live & historical batch monitoring dashboard
│   ├── PassageBankView.jsx       # Reading passages repository & editorial desk
│   └── QuestionBankView.jsx      # Verified Question Bank view & editorial cards
├── components/
│   ├── index.js                  # Centralized barrel export for all components
│   ├── wizard/                   # Streamlined 3-Step Guided Question Wizard
│   │   ├── GuidedWizard.jsx      # Central 3-step wizard controller
│   │   ├── HeroLanding.jsx       # Welcome landing hero header with instant presets
│   │   ├── index.js              # Wizard barrel export
│   │   └── steps/                # Streamlined 3-step modular components
│   │       ├── WizardStep1SectionFocus.jsx # Step 1: Section, pacing & focus
│   │       ├── WizardStep2LevelFormat.jsx  # Step 2: Level (Low/Med/High), format & scope (5/50)
│   │       ├── WizardStep3ReviewAdvanced.jsx # Step 3: Compact review table & advanced accordion
│   │       └── index.js          # Steps barrel export
│   ├── question/                 # Question presentation & editing
│   │   ├── MentorExplanationView.jsx # 3-card mentor explanation view (Intuition, Distractors, Trap)
│   │   ├── QuestionCard.jsx      # Interactive student practice & review card
│   │   ├── QuestionInlineEditor.jsx # In-place authoring & remediation editor
│   │   ├── QuestionScorecardTab.jsx # 100-point rubric breakdown accordion
│   │   ├── ReviewAuditView.jsx   # 100-point rubric breakdown & token cost modal (Focus Trapped)
│   │   ├── SharedPassageCard.jsx # Shared reading passage stimulus display card
│   │   ├── StageJsonInspector.jsx# Deep stage outcome JSON inspector accordion
│   │   ├── VisualStimulusViewer.jsx # SVG & neural visual diagram renderer
│   │   └── index.js              # Question barrel export
│   ├── passage/                  # Reading passage bank components
│   │   ├── PassageBankFilters.jsx# Passage search, section, and difficulty filters
│   │   ├── PassageBankTable.jsx  # Passage stimuli repository cards & question sets
│   │   ├── PassageEditorialDesk.jsx # Reading passage editor & preview desk
│   │   ├── PassageLinkedQuestionCard.jsx # Linked question card within passage editorial desk
│   │   ├── PassageVisualStimulusEditor.jsx # Passage diagram & figure attachment editor
│   │   └── index.js              # Passage bank barrel export
│   ├── bank/                     # Question Bank repository
│   │   ├── QuestionBankFilters.jsx # Section, difficulty (Low/Medium/High), and search filters
│   │   ├── QuestionBankTable.jsx # Canonical Editorial Cards view, batch selection, and actions
│   │   └── index.js              # Bank barrel export
│   ├── batch/                    # Batch monitoring components
│   │   ├── ActiveMultiBatchMonitor.jsx # Global concurrency metrics & live multi-batch controller
│   │   ├── BatchCard.jsx         # Summary status card for generation batches
│   │   ├── BatchEmptyState.jsx   # Decomposed zero-state canvas for batch activity
│   │   ├── BatchFiltersBar.jsx   # Section, status, and search filters
│   │   ├── BatchHeaderBanner.jsx # Top summary banner for active batch metrics
│   │   ├── BatchJobCard.jsx      # Per-set worker card with 5-question visual progress strip & retry telemetry
│   │   ├── BatchQuestionItem.jsx # Staged question item with review modal
│   │   ├── BatchStatsHeader.jsx  # High-level aggregate batch statistics
│   │   └── index.js              # Batch barrel export
│   ├── validated/                # AI Validated bank components
│   │   ├── AiValidatedFiltersBar.jsx # Filters for AI-validated questions
│   │   ├── AiValidatedQuestionCard.jsx # Card with direct bank approval actions
│   │   ├── AiValidatedStatsBar.jsx # Quick-action statistics header
│   │   └── index.js              # Validated barrel export
│   ├── modals/                   # Accessible dialog modals (WCAG AA Focus Trapped)
│   │   ├── ConfirmationModal.jsx # Accessible confirmation modal replacing window.confirm
│   │   ├── DeletePassageModal.jsx# Dedicated passage deletion and cascade warning dialog (Hoisted)
│   │   ├── ExportPaperPreview.jsx# Live print layout previewer
│   │   ├── ExportPrintModal.jsx  # Exam Paper (PDF), Study Pack, CSV and JSON export modal
│   │   └── index.js              # Modals barrel export
│   ├── layout/                   # Global layout
│   │   ├── Footer.jsx            # Infynno Solutions LLP attribution & resource footer
│   │   ├── Navbar.jsx            # Header with branding, navigation tabs, and theme toggle
│   │   └── index.js              # Layout barrel export
│   └── common/                   # Shared UI primitives
│       ├── CustomSelect.jsx      # Accessible custom dropdown select primitive
│       ├── ErrorBoundary.jsx     # Production React error boundary with fallback UI
│       ├── FormattedText.jsx     # Inline markdown & cognitive trap chip highlighter
│       ├── InfynnoLogo.jsx       # Official corporate vector logo primitive
│       ├── LiveStopwatch.jsx     # High-precision live stopwatch timer
│       ├── PaginationBar.jsx     # Accessible pagination bar with page range counter & controls
│       ├── Toast.jsx             # Floating toast notification system
│       └── index.js              # Common primitives barrel export
├── constants/
│   ├── index.js                  # Constants barrel export
│   ├── mcat.js                   # MCAT sections, pacing specs, icons, and fallback topics
│   ├── mcatTraps.js              # AAMC cognitive trap definitions and defense strategies
│   └── mcat_dependent_taxonomy.json # AAMC-aligned foundational concepts and skills
├── hooks/
│   ├── index.js                  # Barrel export for custom hooks
│   ├── useAppState.js            # Centralized view routing & global event broker
│   ├── useFocusTrap.js           # Accessible WCAG AA keyboard focus-trapping hook for modals
│   ├── useGeneratorForm.js       # Form state & validation logic
│   ├── useKeyboardShortcuts.js   # Global hotkeys (⌘↵, A, D, T, /, Esc)
│   ├── usePagination.js          # Client and server pagination calculations and state management
│   ├── useQuestionBank.js        # Debounced search, sorting, and bank fetching
│   └── useTheme.js               # Dual-theme engine (dark / light with localStorage)
├── services/
│   ├── api.js                    # FastAPI client & SSE stream reader (28 methods)
│   └── index.js                  # Services barrel export
├── utils/                        # Pure utility helpers
│   ├── explanationHelpers.js     # Structured explanation parser
│   ├── exportUtils.js            # A4 HTML print document builder, CSV & JSON serializers
│   ├── formatters.js             # Time, word count, token & currency formatters
│   ├── index.js                  # Utilities barrel export
│   ├── optionHelpers.js          # Option length parity & calculateOptionSymmetry engine
│   └── trapHelpers.js            # Cognitive trap resolution & text detectors
├── styles/                       # Modular domain stylesheets (tokens, base, layout, wizard, question, batch, bank, passage, modals, print)
├── index.css                     # Aggregator hub importing all domain stylesheets
└── main.jsx                      # React 19 application root
```

For complete UI design tokens, color scales, typography guidelines, and component contracts, consult [`DESIGN.md`](../DESIGN.md).

---

## 9. Reliability, Recovery & Observability

- **Graceful shutdown**: the FastAPI lifespan hook stops all running batches (progress and generated questions are preserved) and disposes the database engine.
- **Restart recovery**: on startup, `in_progress` batches become `stopped`, their qualifying questions are promoted, and jobs left `pending`/`running` become `stopped` so the UI never shows phantom running work. Stopped jobs below target remain retryable through the standard retry flow (3-trial ceiling).
- **No leaked workers**: `run_workflow_stream` cancels and drains all worker and monitor tasks on every exit path (completion, error, cancellation, or consumer close).
- **LLM call hygiene**: the global LLM semaphore is held only during the API call, never during retry backoff; 500/502/503/504/529 and rate-limit errors are retried once at a single layer; request timeout scales with `max_tokens`; static system prompts are marked cacheable for Anthropic (`ENABLE_PROMPT_CACHING`).
- **Health probes**: `GET /api/health` (liveness, reports `degraded` when PostgreSQL is unreachable) and `GET /api/health/ready` (readiness, `503` when the database is down). With `ADMIN_API_KEY` set, the full diagnostic payload requires a matching `x-admin-key` header.
- **Correlation logging**: every log line inside a batch job or worker carries `batch_id`, `job_id`, `run_id` and `slot` (`LOG_FORMAT=json` for structured output). Each LLM call records `duration_ms` in the per-agent usage breakdown.
- **SSE keepalive**: `/api/generate` emits a `: keepalive` comment every 15 seconds during quiet LLM stages so proxies do not drop the stream.
