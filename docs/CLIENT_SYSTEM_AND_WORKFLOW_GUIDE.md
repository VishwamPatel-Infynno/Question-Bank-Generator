# Infynno MCAT Question Bank Generator v2.0: System Architecture & Client Workflow Guide

> **Author**: Lead Software Architect & Systems Builder  
> **Target Audience**: Client Leadership, Product Stakeholders, and Medical Admissions Educators  
> **System Status**: Fully Implemented, Tested, and Production-Ready  

---

## 1. Executive Summary & Architecture Overview

Preparing candidates for the **AAMC MCAT (Medical College Admission Test)** requires simulating the exact cognitive rigor, multi-disciplinary depth, and strict timing of North American medical admissions testing. Unlike standard memorization tests, the MCAT evaluates deep critical reasoning across physical sciences, biochemistry, humanities, and behavioral dynamics under extreme time pressure (**~96 to ~101 seconds per question**).

### The Problem With Standard AI Question Generation
Most off-the-shelf generative AI setups produce flawed test questions for four reasons:

1. **The "Longest Option" Giveaway**: Language models tend to over-explain the correct answer, creating a giveaway choice that test-savvy students exploit without doing the science.
2. **Superficial Distractors**: Generic models write wrong options that are obviously nonsensical. Official MCAT items use distractors that reflect authentic student misconceptions, inverted ratios, or out-of-scope extrapolations.
3. **Pacing & Passage Realism**: Official MCAT passages demand dense experimental narratives with figures, reaction kinetics, and control groups. Naive prompts generate disjointed trivia stems.
4. **AI Style Tell-Tales**: Generic AI outputs frequently use unnatural em dashes ("—") and repetitive qualifiers that immediately break immersion.

### How Infynno Engineered the Solution
The **Infynno MCAT Question Bank Generator v2.0** solves these challenges with five core pillars:

- **Calibrated Multi-Tier Generation Scopes**:
  - **Practice Set (5 Qs)**: Rapid background worker drafting on a shared passage or discrete set (~35-50s) streamed into the AI Validated Bank and Batch Activity Desk with live telemetry.
  - **Full Exam (50 Qs)**: Enterprise background multi-job batch (10 concurrent jobs x 5 questions) with automatic AI validation.
- **Binary Passage Architecture**: In a generation run, the studio generates either:
  - **Passage-Based Set**: 1 comprehensive scientific or rhetoric passage linked to all questions in the set; OR
  - **Independent Discretes**: Standalone scientific stems with zero stimulus text.
- **CARS Pure Passage Standard**: For **Critical Analysis and Reasoning Skills (CARS)**, the system strictly enforces 100% passage-based sets, locking discrete mode out in accordance with AAMC regulations.
- **Fused Draft-and-Critique Cognitive Engine**: Authors the scenario, symmetric options, and mentor explanation while simultaneously self-scoring the item across a standardized 100-point rubric in a single unified round-trip. Every draft is then independently audited by a separate reviewer and a blind solver.
- **Blind-Solver Dual-Validation Safeguard**: Acts as an algorithmic test candidate, solving the drafted question completely blind without access to the author's answer key or explanation. Any discrepancy in the answer key or low confidence ($< 88\%$) instantly forces the item into remediation, eliminating false keys and ambiguous stems before human review.
- **AAMC Dual Split-Pane Reading Mode**: Provides an authentic side-by-side split reading canvas for passage sets. The left pane anchors the dense research passage with sticky scrolling, while the right pane presents candidate stems, options, and rationales with independent vertical navigation.
- **Autonomous Remediation & Strict Quality Gate (>90 Points)**: Items scoring $\le 90$ undergo up to three cycles of independent auditing and remediation. Unrepaired items are discarded and never committed to the database.

---

## 2. The 4 Official AAMC MCAT Sections & Pacing Standards

The platform is engineered around the official syllabus, cognitive traps, and pacing rules of the four AAMC MCAT sections:

| Section Code | Official Section Name | Total Qs | Time Limit | Target Pacing | Core Focus & Purity Rules |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **chem_phys** | **Chemical and Physical Foundations of Biological Systems** | 59 | 95 mins | **~96s / question** | General chemistry, organic chemistry, physics, thermodynamics, enzymatic kinetics. Supports Passage Sets or Discretes. |
| **cars** | **Critical Analysis and Reasoning Skills** | 53 | 90 mins | **~101s / question** | Humanities and social science rhetoric, authorial tone, thesis extraction. **Strictly 100% Passage-Based (Discretes forbidden).** |
| **bio_biochem** | **Biological and Biochemical Foundations of Living Systems** | 59 | 95 mins | **~96s / question** | Molecular genetics, metabolic pathways, microbiology, organ physiology. Supports Passage Sets or Discretes. |
| **psych_soc** | **Psychological, Social, and Biological Foundations of Behavior** | 59 | 95 mins | **~96s / question** | Cognitive psychology, healthcare sociodemographics, sensory perception. Supports Passage Sets or Discretes. |

---

## 3. End-to-End User Experience & Streamlined 3-Step Guided Wizard

The workstation provides an interactive **Streamlined 3-Step Guided Wizard** docked beside the full-width workspace, organizing authoring decisions into three high-velocity stages:

```
[ Step 1: Section & Topic Focus ] ──> [ Step 2: Level, Format & Scope ] ──> [ Step 3: Review & Launch (Advanced Calibration) ]
```

1. **Step 1: Section & Topic Focus**: 
   - **Exam Section Selection**: Choose from the 4 official AAMC sections (Chemical and Physical Foundations, CARS, Biological and Biochemical Foundations, Psychological, Social, and Biological Foundations). Selecting CARS automatically primes the wizard for 100% passage-based operation and disables image generation.
   - **Discipline & Major Unit**: Select syllabus discipline and unit taxonomy.
   - **High-Yield Concept Subtopics**: Multi-select granular subtopics or select all concepts for a balanced mix.
2. **Step 2: Level, Format & Scope**:
   - **Generation Scope**: Select **Practice Set (5 Qs, 1 Job)** for fast iterative authoring (~35-50s) or **Full Exam (50 Qs, 10 Jobs)** for comprehensive background mock section generation. Cards feature clean, streamlined selection buttons without distracting redundant badge pills.
   - **Challenge Level**: Calibrate between **Low**, **Medium**, and **High** difficulty tiers with color-coded badges and plain-English descriptors.
   - **Binary Passage Mode**: Passage-Based Set vs Independent Discretes.
   - **Question Breakdown**: Calibrate single-choice and multi-choice proportions.
3. **Step 3: Review & Launch (with Advanced Calibration)**:
   - **Compact Parameter Summary Table**: Review selected section, topics, difficulty, and question count at a glance in a high-density tabular summary card.
   - **Dedicated Scientific Diagrams & Reaction Schemes Toggle Card**: Prominently positioned for all natural science sections with full-card clickability and animated pill switch, allowing educators to immediately enable or disable programmatic SVG diagrams and reaction schemes without opening advanced menus.
   - **Additional Authoring Instructions Textarea**: High-priority guidance field allowing educators to supply custom pedagogical constraints, clinical scenarios, or negative rules (e.g. *"Focus on Lineweaver-Burk plots with competitive inhibition calculation traps"*). When populated, the Step 3 card header displays a visible, animated indicator badge: **`+ Custom Prompt Active`**.
   - **Expandable Advanced Accordion**: Collapsible drawer giving fine-grained control over:
     - *Cognitive Distractor Traps*: Multi-select official AAMC cognitive traps (Formula Trap, Extreme Quantifiers, False Causation, etc.).
     - *AAMC Reasoning Skills*: Target specific SIRS reasoning skills (Skill 1–4) and likely student mistake patterns.
   - **Unified Launch Action**: Launch real-time SSE streaming for practice sets or dispatch enterprise background mock runs.


---

## 4. Multi-Agent Pipeline & Strict Quality Gate

```mermaid
graph TD
    User([Educator / User]) -->|POST /api/generate| Engine[Multi-Agent Orchestrator]
    Engine --> Worker1[Worker Question 1]
    Engine --> Worker2[Worker Question 2]
    Engine --> Worker3[Worker Question 3]
    Engine --> Worker4[Worker Question 4]
    Engine --> Worker5[Worker Question 5]

    subgraph "Per-Item Autonomous StateGraph"
        Worker1 --> Fused[Fused Draft & Self-Critique]
        Fused -->|Score > 90| ImageGen[Vector/SVG Engine]
        Fused -->|Score <= 90| Remediation[Remediation Loop]
        Remediation --> Auditor[Independent Auditor]
        Auditor -->|Pass > 90| ImageGen
        Auditor -->|Fail <= 90 & Max Cycles| Reject[Strict Quality Gate Reject]
        ImageGen --> Staged[Staged in Review Deck]
    end
```

### 4.1 Fused Draft-and-Critique Cognitive Engine (`fused_generator_node`)
- Crafts high-yield clinical or scientific scenarios, 4 symmetric options ($A, B, C, D$), and 3-card mentor explanations.
- Simultaneously generates a 100-point self-critique object in a single inference call. By default the independent reviewer and blind solver still audit every draft (`ALWAYS_INDEPENDENT_REVIEW`), running concurrently to save time.
- Strictly forbids em dashes (`—`) and enforces option word count symmetry ($\pm 15\%$).

### 4.2 Blind-Solver Dual-Validation Safeguard (`blind_solver.py`)
- Acts as an algorithmic test candidate, solving the drafted question completely blind without knowing the author's key or explanation.
- Evaluates whether the question stem and passage provide unambiguous mathematical or deductive proof to identify the intended key.
- Requires both **answer key agreement** and **$\ge 88\%$ confidence**. If the blind solver selects a different option or confidence is low, the item is automatically redirected to remediation to remove ambiguity.

### 4.3 Independent Senior Psychometric Auditor (`reviewer.py`)
- Engaged if a draft scores $\le 90$, fails blind-solver verification, or has undergone remediation.
- Evaluates four 25-point pillars:
  1. *MCAT Authenticity & Scientific Rigor* (0-25)
  2. *Clarity & Logical Soundness* (0-25)
  3. *Distractor Trap Quality & Anti-Guessability* (0-25)
  4. *Explanation & Key Rigor* (0-25)

### 4.4 Autonomous Remediation Engine (`regenerator.py`)
- Repairs identified distractor weaknesses, equalizes option lengths, and sharpens pedagogical proofs.
- Loops up to 3 cycles before triggering the deterministic rejection circuit breaker.

### 4.5 Strict Quality Gate Benchmark ($> 90$ Points)
- Any item unable to achieve $> 90$ points after 3 cycles is completely rejected and excluded from the Question Bank.

---

## 5. Mentor Explanations & 11 Cognitive Traps

Every approved question presents a comprehensive **3-Card Mentor Explanation**:

1. **Card 1: Why Option [Key] is Correct** (Emerald / Success) — Clear deductive or mathematical proof citing specific passage data.
2. **Card 2: Why Other Options are Incorrect** (Amber / Warning) — Itemized distractor cards dissecting the exact fallacy in each incorrect choice ($A, B, C, D$).
3. **Card 3: Primary Cognitive Trap Spotlight** (Purple / Tactical Defense) — Details the exact psychological trap, the underlying student error mechanism, and an actionable test-day defense strategy.

### Supported Trap Taxonomy:
- `Scope_Shift`, `Keyword_Trap`, `Extreme_Language`, `Correlation_vs_Causation`, `Partial_Match`, `Half_Truth`, `Unwarranted_Assumption`, `Calculation_Formula_Trap`, `Out_of_Scope`, `False_Dichotomy`, `Over_generalisation`.

---

## 6. Financial Transparency, Concurrency & Batch Resiliency

Every generated item tracks real-time inference telemetry and costs across dual first-class inference providers (DeepInfra DeepSeek V4.1 Flash or Anthropic Claude Haiku 5.5 / Sonnet / Opus with prompt caching):

$$\text{Total Cost (DeepInfra)} = \left(\frac{\text{Input Tokens}}{1{,}000{,}000} \times \$0.098\right) + \left(\frac{\text{Output Tokens}}{1{,}000{,}000} \times \$0.294\right)$$

- **Predictable Micro-Costs**: An audited 5-question batch typically costs **between $0.006 and $0.012 USD** in total inference under DeepInfra, or competitive prompt-cached rates under Anthropic Claude.
- **Repository Observability**: The Question Bank header displays accumulated input tokens, output tokens, total execution time, and cumulative investment across the entire repository.
- **Enterprise Multi-Batch Concurrency & Resiliency**:
  - The background batch runner operates under global worker semaphores (`4 concurrent jobs`, `10 concurrent LLM calls`) ensuring safe execution without API rate limit bottlenecks.
  - **Review Queue Withholding Guarantee**: Questions produced during background batches are held safely in `batch_only` status while the batch is in progress. The "Ready for Review" queue remains clean of incomplete or draft items until the batch cleanly completes, at which point questions with `final_score > 90` are atomically promoted to `ai_validated`. Cancelled or stopped batches retain questions in `batch_only` so educators never review partial runs.
  - **1-Click Batch Stop**: Educators can pause a 50-question mock run at any time without losing items already generated and validated.
  - **Autonomous In-Flight 3-Trials Retry Policy**: If candidate questions fail quality thresholds during a run, background jobs automatically execute in-flight replenishment retries up to **3 max trials per set**. Active jobs broadcast live `AUTO-RETRYING (X/3)` telemetry badges, transitioning to `3/3 TRIALS EXHAUSTED` when trials are completed.
  - **Controlled "Resume Sets" Resumption**: Manual retry buttons are hidden during generation and eliminated for completed or failed runs. Batches stopped manually mid-run display a clear **"Resume Sets"** button, allowing educators to resume paused sets that have trials remaining (`trial_count < 3`). Retrying exhausted runs is blocked with an explicit error message.
  - **Batch Duplicate Clustering & Auto-Refill**: Educators can inspect intra-batch similarity clusters, designate custom leaders, permanently purge duplicates (`action="delete"`), and automatically launch replacement jobs to deliver exact target quotas.
- **Dedicated Application Views**: Seamlessly navigate between:
  1. **Create Questions (`HeroLanding.jsx`, `GuidedWizard.jsx`)**: Interactive question studio featuring the welcome canvas with instant section presets and the streamlined 3-Step Guided Wizard dispatching to background worker pools.
  2. **Batch Progress (`BatchActivityView.jsx`)**: Real-time monitor tracking running batch jobs, per-job question counts, status indicators, and background worker progress. Features **Dual-Track Progress Indication**: an aggregate progress bar tracking overall batch completion alongside per-set **5-Question Progress Strips** with discrete slot pills (`✓ Q1` ready for review in emerald, `✓ Q1` in bank in purple, pulsing `● Q2` actively generating, and dashed `Q3` pending slot).
  3. **Review Queue (`AiValidatedQuestionsView.jsx`)**: High-quality items (>90 points) awaiting one-click educator publishing into the Question Bank. Score labels are streamlined to clean status badges, and obsolete Discarded/Needs Polish counters are pruned.
  4. **Question Bank (`QuestionBankView.jsx`)**: Primary verified repository strictly presented in high-density **Editorial Cards** (with search, multi-factor filtering, in-place inline editing, bulk deletion, and PDF/CSV/JSON export; legacy table grid mode removed).
  5. **Passage Bank (`PassageBankView.jsx`)**: Comprehensive repository of reading passages and research narratives. Features the interactive **Passage Editorial Desk** for live editing of passage content, attaching and previewing figures/diagrams (`PassageVisualStimulusEditor.jsx`), reviewing all linked practice questions (`PassageLinkedQuestionCard.jsx`), and dedicated passage deletion with linked question cascade removal via `DeletePassageModal`, preserving historical batch execution progress intact.

---

## 7. Question Deduplication, Collision Avoidance & Editorial Override

### 7.1 Why Duplicate Prevention is Serious for Medical Education
In high-stakes MCAT preparation, item duplication severely damages product credibility:
- **Artificially Inflated Diagnostic Scores**: If a student encounters two nearly identical questions across different practice exams, their score reflects rote memory rather than authentic scientific reasoning.
- **Wasted Student Pacing**: Candidates have roughly ~96 seconds per question. Encountering repetitive stems wastes valuable mock testing stamina.
- **Content Dilution**: High-value question banks must span comprehensive cognitive angles rather than clustering around identical textbook phrasing.

### 7.2 The Autonomous Anti-Collision Loop
During both live single-pass authoring and high-throughput batch generation:
1. **Targeted Reference Scoping**: The candidate question is compared against all existing bank items within the **exact Section and Subtopic**, as well as sibling questions generated within the active batch.
2. **Multi-Metric Textual & Distractor Evaluation**: Stems and options are evaluated using token containment, 1-gram/2-gram Jaccard overlap, SequenceMatcher ratio, and distractor set similarity.
3. **Autonomous Pivot**: If composite similarity exceeds **80%**, the generator is automatically re-prompted with the colliding stem and instructed to pivot to an alternative clinical presentation, distinct enzymatic mechanism, or novel calculation angle.

### 7.3 The Educator Review & Override Workflow
When an item with potential overlap is presented for editorial review:

```
[ Candidate Question Staged ] ──> [ ⚠️ Duplicate Risk (XX%) Badge Displayed ]
                                                 │
                                                 ▼
                                  [ Open Comparison Modal ]
                                  (Candidate vs Conflicting Item)
                                                 │
             ┌───────────────────────────────────┼───────────────────────────────────┐
             ▼                                   ▼                                   ▼
    [ Override & Approve ]             [ Regenerate Fresh Angle ]                 [ Discard ]
   • Stamps audit trail               • Re-prompts generator                     • Completely purges
   • Status -> 'in_bank'              • Injects avoidance directive               substandard draft
   • Badge -> 🛡️ Overridden          • Discards current candidate
```

1. **Visual Alert**: Question cards in the staging deck and bank display an unmistakable warning pill: `⚠️ Duplicate Risk (86%)`.
2. **Collision Diagnostics & Context**:
   - The card displays the exact similarity percentage and the primary collision cause (e.g. *"High question stem textual overlap (86%)"*), giving educators full context on the potential duplicate.
3. **Three Editorial Paths**:
   - **Override & Approve (Emerald Shield)**: If the educator verifies that the question explores a distinct scientific principle (for example, competitive vs uncompetitive inhibition under identical kinetics conditions), clicking "Override & Approve" persists the item, sets `is_duplicate_override=true`, and records the exact override timestamp. The question card badge transitions to a protected blue badge: `🛡️ Overridden`.
   - **Regenerate Fresh Angle (Indigo Refresh)**: Dispatches an autonomous re-generation task requiring the engine to pick a completely different scientific angle while discarding the collision.
   - **Discard (Rose Trash)**: Discards the redundant draft from the active review deck.
4. **Permanent Audit Trail**: All overrides are preserved in the PostgreSQL `duplicate_info` JSONB column and included in administrative JSON and CSV exports.
