# Infynno MCAT Question Bank Generator v2.0
## System Architecture, End-to-End Workflows & Client Master Guide

> **Prepared by**: Infynno Solutions LLP • Infinite Innovations • [infynno.com](https://infynno.com/)  
> **Product**: Infynno MCAT Question Bank Generator v2.0  
> **Target Audience**: Client Leadership, Product Stakeholders, Medical Admissions Educators, Pre-Med Faculty, and Test-Prep Authors  
> **System Status**: Fully Implemented, Tested (549 Deterministic Backend Tests across 79 Modules, 559 Total Backend Tests + 203 Frontend Tests across 25 Test Files), and Production-Ready  

---

## Table of Contents
1. [Executive Summary & Value Proposition](#1-executive-summary--value-proposition)
2. [Official AAMC MCAT Foundations & Pacing Rules](#2-official-aamc-mcat-foundations--pacing-rules)
3. [Autonomous Multi-Agent AI Pipeline](#3-autonomous-multi-agent-ai-pipeline)
4. [Pedagogical Quality, Anti-Guessability & Distractor Traps](#4-pedagogical-quality-anti-guessability--distractor-traps)
5. [Anti-Collision, Deduplication & pgvector Semantic RAG](#5-anti-collision-deduplication--pgvector-semantic-rag)
   - 5.1 [Multi-Metric Similarity Algorithm](#51-multi-metric-similarity-algorithm)
   - 5.2 [Intra-Batch Clustering & Autonomous Replenishment](#52-intra-batch-clustering--autonomous-replenishment)
   - 5.3 [pgvector Semantic RAG & Anti-Collision Shield](#53-pgvector-semantic-rag--anti-collision-shield)
   - 5.4 [Duplicate Flags & Override Audit Trail](#54-duplicate-flags--override-audit-trail)
6. [The 5 Top-Level Workstation Views](#6-the-5-top-level-workstation-views)
   - 6.1 [Create Questions: Question Studio & 3-Step Wizard](#61-create-questions-question-studio--3-step-wizard)
   - 6.2 [Batch Progress: Concurrency Monitor & Resilient Processing](#62-batch-progress-concurrency-monitor--resilient-processing)
   - 6.3 [Review Queue: AI-Validated Triage & Editorial Staging](#63-review-queue-ai-validated-triage--editorial-staging)
   - 6.4 [Question Bank: Canonical Repository & Inline Editorial Desk](#64-question-bank-canonical-repository--inline-editorial-desk)
   - 6.5 [Passage Bank: Stimulus Curation & Cascading Management](#65-passage-bank-stimulus-curation--cascading-management)
   - 6.6 [AI Copilot Studio & In-Line Refinement](#66-ai-copilot-studio--in-line-refinement)
   - 6.7 [Hero Landing & Quick-Start Presets Desk](#67-hero-landing--quick-start-presets-desk)
7. [Export & Study Studio (Anki, Exam Simulation PDF, Study Guide)](#7-export--study-studio)
8. [Financial Telemetry & Micro-Dollar Cost Accounting](#8-financial-telemetry--micro-dollar-cost-accounting)
9. [UI Design System, Ergonomics & Accessibility](#9-ui-design-system-ergonomics--accessibility)
10. [Technical Architecture, Security & Production Readiness](#10-technical-architecture-security--production-readiness)

---

## 1. Executive Summary & Value Proposition

Preparing medical school candidates for the **AAMC MCAT (Medical College Admission Test)** requires simulating the exact cognitive rigor, multi-disciplinary depth, and strict timing of North American medical admissions testing. Unlike standard memorization tests, the MCAT evaluates deep critical reasoning across physical sciences, biochemistry, humanities, and behavioral dynamics under extreme time pressure (**~96 to ~101 seconds per question**).

```mermaid
flowchart LR
    A["Pre-Med Educator / Author"] --> B["Infynno Studio 3-Step Wizard"]
    B --> C["Question Generator<br>(First-Pass 100/100 Directive)"]
    C --> G["Deduplication & Anti-Collision Check<br>(>= 75% similarity triggers a rewrite)"]
    G --> V["Free Structural Validator<br>(options, key, dashes)"]
    V --> E["Senior Psychometric Auditor<br>(100-pt 4-Pillar Rubric)"]
    V --> D["Blind-Solver Algorithmic Candidate<br>(No Answer Key Access, >=88% Conf)<br>runs concurrently with the Auditor"]
    E --> F["Autonomous Remediation<br>(Up to 3 In-Place Cycles)"]
    D --> F
    F --> V
    E --> H["Editorial Review Queue<br>& Canonical Question Bank"]
    D --> H
```

### The Critical Flaws of Generic AI in Medical Test Prep
Standard generative AI setups fail when applied to official MCAT question authoring:
1. **The "Longest Option" Give-Away**: Language models naturally over-explain the correct answer, creating a giveaway choice that test-savvy students exploit without reading the passage.
2. **Superficial & Unrealistic Distractors**: Off-the-shelf AI creates distractors that are obviously wrong or absurd. Official MCAT questions use distractors that reflect authentic student misconceptions, inverted math ratios, or out-of-scope extrapolations.
3. **Disjointed Trivia vs. Experimental Passages**: Real MCAT sections require dense, publication-grade research passages featuring experimental controls, Lineweaver-Burk kinetics, gel electrophoresis, or complex humanities rhetoric. Naive prompts generate isolated trivia.
4. **AI Style Tell-Tales**: Generic AI outputs frequently use unnatural em-dashes (`—`) and repetitive robotic phrasing (`"It is important to remember that..."`) that destroy test authenticity.

### The Infynno Engineered Solution
The **Infynno MCAT Question Bank Generator v2.0** eliminates these failures through an enterprise-grade multi-agent platform:
- **Mathematical Option Symmetry**: Option lengths are held to a word-count spread of at most `max(3, ceil(20% of the mean))` words, with parallel grammatical structure.
- **Blind-Solver Dual Validation**: An independent AI agent solves the question without the answer key. If it disagrees or confidence is $< 88\%$, the question is automatically rejected or remediated.
- **100-Point Psychometric Audit**: Every draft is graded across 4 pillars of 25 points each. Only items scoring $> 80$ reach the review queue.
- **Autonomous Deduplication**: Multi-metric mathematical similarity guarantees zero question repetition across mock sets.
- **Human-Centric Editorial Control**: Pre-med instructors retain full editorial power with 1-click in-place editing, override shields, and publication-ready multi-format exports (PDF, CSV, JSON).

---

## 2. Official AAMC MCAT Foundations & Pacing Rules

The entire application is strictly aligned with the four official AAMC MCAT sections:

| Section Code | Official AAMC Section Name | Questions | Time Limit | Target Pacing | Formatting Mandates |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **`chem_phys`** | **Chemical and Physical Foundations of Biological Systems** | 59 | 95 mins | **~96s / question** | General chemistry, organic chemistry, physics, thermodynamics, kinetics. Supports Passage Sets or Discretes. |
| **`cars`** | **Critical Analysis and Reasoning Skills** | 53 | 90 mins | **~101s / question** | Humanities, ethics, philosophy, social sciences. **Strictly 100% Passage-Based (Discretes forbidden). Zero diagrams.** |
| **`bio_biochem`** | **Biological and Biochemical Foundations of Living Systems** | 59 | 95 mins | **~96s / question** | Molecular genetics, metabolic pathways, microbiology, organ physiology. Supports Passage Sets or Discretes. |
| **`psych_soc`** | **Psychological, Social, and Biological Foundations of Behavior** | 59 | 95 mins | **~96s / question** | Cognitive psychology, healthcare sociology, sensory perception, research ethics. Supports Passage Sets or Discretes. |

### AAMC Scientific Inquiry & Reasoning Skills (SIRS)
The platform explicitly targets and categorizes questions by the official AAMC reasoning framework:
- **Skill 1: Knowledge of Scientific Concepts and Principles** — Identifying scientific definitions, models, and fundamental relationships.
- **Skill 2: Scientific Reasoning and Problem-Solving** — Analyzing scientific theories, evaluating hypotheses, and synthesizing concepts.
- **Skill 3: Reasoning About the Design and Execution of Research** — Evaluating experimental variables, positive/negative controls, validity, and ethics.
- **Skill 4: Data-Based and Statistical Reasoning** — Reading reaction graphs, scatter plots, Lineweaver-Burk plots, p-values, and confidence intervals.

---

## 3. Autonomous Multi-Agent AI Pipeline

The core intelligence consists of five specialized autonomous agents orchestrated by a deterministic state engine:

```mermaid
sequenceDiagram
    autonumber
    actor Educator as Educator / Author
    participant Orchestrator as Engine Orchestrator
    participant Generator as Question Generator
    participant Validator as Deterministic Validator
    participant Auditor as Senior Psychometric Auditor
    participant BlindSolver as Blind-Solver Safeguard
    participant Remediator as Autonomous Remediation Loop
    participant StimulusEngine as Vector / Diagram Engine
    participant DB as PostgreSQL 16 & Staging Deck

    Educator->>Orchestrator: Dispatch Run (wizard offers 5 or 50 Questions)
    Orchestrator->>Generator: Author Scenario + Symmetric Options (draft only by default)
    Note over Generator: Calibrated to First-Pass 100/100 Standard.<br>Self-critique only if ALWAYS_INDEPENDENT_REVIEW=false
    Generator-->>Orchestrator: Draft Payload (Stem, Options A-D, Rationales)
    Orchestrator->>Orchestrator: Duplicate / anti-collision check (rewrite if similarity >= 75%)
    Orchestrator->>Validator: Free structural checks + dash repair

    alt Blocking defect and Cycle < 3
        Validator-->>Orchestrator: Defect list
        Orchestrator->>Remediator: Repair draft (Max 3 Cycles)
        Remediator-->>Orchestrator: Revised Draft (back to validation)
    else Clean
        par Independent audit
            Orchestrator->>Auditor: 100-pt 4-Pillar Evaluation
            Note over Auditor: Injects Accompanying Figure Spec<br>Audits Stem & Figure Alignment
        and Blind solve (concurrent by default)
            Orchestrator->>BlindSolver: Solve Blindly (No Key, No Explanations)
        end
        Auditor-->>Orchestrator: Score
        BlindSolver-->>Orchestrator: Verdict (verdict applied after the audit is routed)
        alt Score > 80 and key verified (>= 88% confidence)
            opt Section != CARS and Diagram Needed
                Orchestrator->>StimulusEngine: Generate Scalable Vector SVG / Diagram (only after both checks pass)
                StimulusEngine-->>Orchestrator: Inline SVG / Visual Stimulus
            end
            Orchestrator->>DB: Staged (ai_validated once the batch completes)
        else Score <= 80 or solver mismatch, Cycle < 3
            Orchestrator->>Remediator: Repair Stems & Options (solver failure caps the score at 75)
            Remediator-->>Orchestrator: Revised Draft (back to validation)
        else Final cycle, 70 <= Score <= 80 and key verified
            Orchestrator->>DB: Retained as Good Quality batch item (batch_only)
        else Final cycle, Score < 70 or solver failure
            Note over Orchestrator: Circuit Breaker Rejection - discard the draft
        end
    end
```

### 3.1 Question Generator (`generator.py`, optional fused self-critique)
- **First-Pass 100/100 Excellence Directive**: Explicitly instructed to author perfect items on the initial attempt, maximizing authenticity, distractor sharpness, and explanation rigor.
- **Draft-only by default**: With the default `ALWAYS_INDEPENDENT_REVIEW=true`, the generator returns a draft only and the independent Auditor and Blind-Solver check every item. The "fused" mode (draft plus self-critique in one round trip, where a high self-score lets the Auditor be skipped) is used only if that setting is switched off.
- **Anti-AI Formatting Standard**: Strictly forbids unspaced em-dashes (`—`), en-dashes (`–`), or double hyphens (`--`). Uses clean spaced single hyphens (`-`).
- **Option Length Symmetry**: The word-count spread between the longest and shortest option must stay within `max(3, ceil(20% of the mean))` words, checked by the free validator and repaired by the Regenerator, so no single option stands out.

### 3.2 Blind-Solver Dual-Validation Safeguard (`blind_solver.py`)
- **Simulated Test Candidate**: Solves the candidate question purely from the passage and question stem, without access to the author's answer key or explanation.
- **Strict Verification Gate**: Requires both **exact key agreement** and **$\ge 88\%$ algorithmic confidence**. By default two solver samples run concurrently on different option orders (a strict majority on the author's key is required); a failed verdict lowers the item's score to at most 75 and routes it into remediation, and at the final cycle it rejects the item.
- **Runs alongside the Auditor**: by default the Auditor and the Blind-Solver evaluate the draft at the same time; the Blind-Solver's verdict is applied after the Auditor's score has been routed.

### 3.3 Senior Psychometric Auditor (`reviewer.py`)
Evaluates items across four equal 25-point pillars (100 points total):
1. **Pillar 1: Authenticity & Scientific Rigor (25 pts)** — Alignment with AAMC syllabus, clinical or laboratory depth, and professional tone.
2. **Pillar 2: Clarity & Scientific Logic (25 pts)** — Syntactic precision, unambiguous phrasing, and absence of linguistic traps.
3. **Pillar 3: Distractor Traps & Option Symmetry (25 pts)** — Plausibility of wrong choices, length symmetry (spread within `max(3, ceil(20% of the mean))` words), and cognitive trap alignment.
4. **Pillar 4: Explanation & Proof Rigor (25 pts)** — Incontrovertible mathematical or deductive proof citing explicit passage evidence.

- **Accompanying Visual Stimulus & Empirical Data Audit Boundary**:
  When an educator or candidate question requires empirical findings (such as Lineweaver-Burk enzyme kinetics, 12-lead ECG traces, chest CT scans, or renal biopsy histology slides), the Senior Psychometric Auditor receives the complete Accompanying Visual Stimulus Specification. The Auditor is strictly instructed **never to penalize references to "Figure 1", "the plot", or "the radiograph below"** in standalone stems, verifying instead that the question stem, answer choices, and scientific proof logically align with the described empirical figure.

### 3.4 Autonomous Remediation Loop (`regenerator.py`)
- Automatically repairs drafts scoring $\le 80$ (or flagged by the structural validator or the Blind-Solver).
- Ingests specific auditor critique notes, adjusts distractors, equalizes option word counts, and sharpens step-by-step proofs.
- **Visual Stimulus Preservation Guarantee**: Mandates that items requiring medical imaging or scientific diagrams retain `image_needed: True` and preserve references to "Figure 1". The regenerator remediates pedagogical traps and explanation depth without flattening empirical visual findings into plain text numbers.
- Maximum 3 cycles. At the final cycle an item scoring 70 to 80 (with the key verified by the Blind-Solver) is kept as Good Quality (`batch_only`); an item below 70, or one the Blind-Solver rejects, is discarded by the circuit breaker.

### 3.5 Visual Stimulus & Medical Imaging Engine (`image_generator.py` & `medical_imaging.py`)
- **Unrestricted Medical & Scientific Visual Generation**: Synthesizes publication-grade scientific figures, anatomical illustrations, and clinical diagnostic stimuli across both discrete questions and passage-linked item sets whenever required (`draft.image_needed: true` or `req.require_image: true`).
- **Autonomous AI Discretion for Standalone Questions**: In standalone question generation with "Include Images When Needed" enabled, visual creation is 100% dependent on autonomous AI pedagogical discretion (without pre-defined artificial modulo or forced question indices).
  - *Frontend Decoupling*: The toggle sets `allow_ai_images: true` while defaulting `require_image: false`, permitting figures when necessary without forcing generation across every item.
  - *Per-Item Request Derivation*: Each worker item request keeps `require_image` only if the parent request explicitly sets it (never for CARS) and turns on `allow_ai_images` when the parent enables images, so "Include Images When Needed" never mandates a figure on every item.
  - *Unrestricted AI Pedagogical Discretion*: The generator has complete freedom to incorporate visuals across all supported modalities whenever an accompanying figure, clinical photograph, or diagram enriches the question. If the model chooses a pure text-based question, it sets `image_needed: false`, rendering cleanly with zero empty placeholders or wasted image generation compute.
  - *Full-Spectrum Modality Diversity*: The system is calibrated across all sections so that the AI autonomously explores the full range of medical and scientific modalities—preventing generative clustering on standard 2D line plots and actively incorporating authentic diagnostic radiology, histology biopsies, gross anatomical dissections, electron microscopy, and physiological traces even without custom prompt specifications.
- **The 7 Supported Medical & Scientific Modalities** (internal ids from `medical_imaging.py`: `radiology`, `histology`, `gross_anatomy`, `cellular_microscopy`, `physiology_trace`, `clinical_pathology`, `scientific_diagram`; the histology id is shown as "Histopathology (H&E)"):
  1. **Radiology**: Axial, coronal, and sagittal CT scans, MRI (T1, T2, FLAIR sequences), chest radiographs, ultrasound sonograms, and fluoroscopic views.
  2. **Histopathology**: Light micrographs featuring hematoxylin and eosin (H&E) staining, specialized tissue biopsies, and cytological smears (e.g., Reed-Sternberg cells, renal glomerular crescents).
  3. **Gross Anatomy**: Anatomical atlas-style dissections, organ systems, neurovascular pathways, and visceral cross-sections with automated safety sanitization for academic purity.
  4. **Cellular Electron Microscopy**: High-magnification TEM and SEM micrographs highlighting organellar ultrastructure (mitochondria, rough ER, Golgi, ciliated axonemes).
  5. **Physiological & ECG Traces**: Standard 12-lead ECG rhythm strips, myocardial action potential curves, cardiac pressure-volume (PV) loops, and pulmonary spirometric flow-volume loops.
  6. **Clinical Pathology**: Clinical photographic presentations, dermatological lesions (melanoma margins, erythema migrans), and ophthalmic fundoscopic examinations.
  7. **Scientific Diagrams & Reaction Pathways**: Clean, scalable vector graphics (**programmatic SVGs**) directly rendered with DOMPurify sanitization (metabolic pathways, Lineweaver-Burk plots, optical ray tracings, chromatography apparatus).
- **Educator Customization via Step 3 Instructions**:
  Educators can direct specific modalities, projections, and clinical findings using the **Additional Authoring Instructions** textarea in Step 3 of the Guided Wizard:
  - *"Include an axial contrast-enhanced CT showing acute appendicitis with an appendicolith."*
  - *"Provide an H&E histological section of cardiac muscle showing contraction band necrosis."*
  - *"Generate a Lead II rhythm strip demonstrating second-degree Mobitz Type I AV block."*
- **Interactive Full-Screen Lightbox & Zoom Inspection**:
  Candidate cards and review desks integrate the interactive `VisualStimulusLightboxModal`:
  - **Full-Screen Canvas**: Accessible dialog with focus trapping (`useFocusTrap`) and Escape key dismissal.
  - **Zoom & Pan Controls**: Scalable zoom from $0.5\times$ to $3.0\times$ with 1-click reset (`RotateCcw`).
  - **Copy SVG Source**: Direct clipboard export of raw vector XML.
- **High-Contrast Dark Container Presentation**:
  To protect clinical visual fidelity, figures classified under **Radiology** or **Electron Microscopy** automatically render inside a dedicated high-contrast dark container (`isDarkContainer: true`) even in Alabaster Light mode, preventing washed-out whites and preserving diagnostic micro-details.
- **CARS Safeguard**: In strict accordance with official AAMC test regulations, diagram generation is permanently disabled for Critical Analysis and Reasoning Skills (CARS).

### 3.6 Passage-Set Slot Blueprints & Retry Rotation
Within a 5-question passage set, each slot has a fixed cognitive archetype (`backend/app/workflow/passage_blueprints.py`) so the five questions test different things:

| Slot | CARS archetype | Science archetype |
| :---: | :--- | :--- |
| 1 | `Central Claim / Main Thesis` | `Scientific Concept & Principle Foundation` |
| 2 | `Local Detail & Passage Evidence` | `Data, Figure & Graph Interpretation` |
| 3 | `Rhetorical Function / Author's Stance` | `Experimental Design & Methodological Rationale` |
| 4 | `Reasoning Beyond the Text: Novel Scenario Application` | `Scientific Reasoning & Problem Solving / Downstream Mechanism` |
| 5 | `Reasoning Beyond the Text: Challenge / Weaken Assumptions` | `Novel Experimental Condition / Hypothesis Testing` |

When a question slot is re-attempted after rejection (up to 3 attempts per slot), the CARS slot 4 scenario domain and the science slot 5 follow-up condition rotate through 10-entry pools (`CARS_SLOT4_APPLICATION_DOMAINS`, `SCIENCE_SLOT5_EXPERIMENTAL_CONDITIONS`; full lists in `MCAT_RUBRIC.md` section 9.2) so a retry does not repeat the same scenario.

---

## 4. Pedagogical Quality, Anti-Guessability & Distractor Traps

### 4.1 3-Card Structured Mentor Explanations
Every item generated presents a comprehensive 3-card pedagogical breakdown designed to train medical reasoning:

```mermaid
graph TD
    subgraph MentorView ["3-Card Structured Mentor Explanation"]
        C1["Card 1: Why Option [Key] is Correct<br/>(Emerald / Success)<br/>• Step-by-step deductive/mathematical proof<br/>• Explicit passage citations"]
        C2["Card 2: Why Other Options are Incorrect<br/>(Amber / Warning)<br/>• Sub-card for each wrong choice [A, C, D]<br/>• Details specific misconception or math error"]
        C3["Card 3: Primary Cognitive Trap Spotlight<br/>(Purple / Defense)<br/>• Identifies exact test trap mechanism<br/>• Actionable student defense strategy"]
    end
```

### 4.2 The 25-Trap Cognitive Taxonomy
The system uses an internal taxonomy of **25** cognitive traps (ids in `backend/app/data/mcat_dependent_taxonomy.json`; labels and advice text from `frontend/src/constants/mcatTraps.js`). These are internal generation labels, not official AAMC categories. One primary trap is assigned per question.

| Trap Name | Trap id | Error mechanism / student advice |
| :--- | :--- | :--- |
| **Concept Confusion** | `CONCEPT_CONFUSION` | Conflates two closely related scientific concepts, models, or physiological mechanisms. |
| **Wrong Base or Reference Value** | `WRONG_BASE` | Uses the incorrect initial quantity, baseline value, or denominator when computing changes. |
| **Unit Conversion Error** | `UNIT_CONVERSION` | Forgets or mishandles dimensional unit conversions (e.g., nm to m, mL to L, or kJ to J). |
| **Formula Misapplication** | `FORMULA_MISAPPLICATION` | Selects a formula whose underlying assumptions or physical boundary conditions are violated. |
| **Sign or Direction Convention** | `SIGN_CONVENTION` | Reverses a vector direction, thermodynamic sign convention (+/- Delta G/H), or electrochemical potential. |
| **Proportionality Error** | `PROPORTIONALITY_ERROR` | Mistakes an inverse relationship for direct proportionality, or overlooks a squared/square-root exponent. |
| **Missed Assumption or Condition** | `ASSUMPTION_MISSED` | Fails to check essential boundary conditions (e.g. STP, ideal gas, steady-state enzyme kinetics). |
| **Cause-Effect Confusion** | `CAUSE_EFFECT_CONFUSION` | Reverses the direction of causality between two biological, biochemical, or social phenomena. |
| **Correlation vs. Causation** | `CORRELATION_CAUSATION` | Mistakes an observed statistical association for proof of a direct mechanistic cause-and-effect relationship. |
| **Control-Group Confusion** | `CONTROL_GROUP_CONFUSION` | Confuses the negative/vehicle control with experimental manipulation groups or baseline states. |
| **Independent/Dependent Variable Confusion** | `VARIABLE_CONFUSION` | Swaps the variable manipulated by researchers with the outcome variable being measured. |
| **Sampling or Sample-Size Bias** | `SAMPLE_SIZE_BIAS` | Draws broad clinical or population generalizations from an underpowered or non-representative sample. |
| **Statistical Significance Misconception** | `STATISTICAL_SIGNIFICANCE` | Equates failure to reject the null hypothesis with proof of no effect, or confuses p-values with effect magnitude. |
| **Graph or Axis Misreading** | `GRAPH_AXIS_MISREADING` | Misreads axes, logarithmic scales, inverted coordinates, or compares mismatched experimental series. |
| **Table Comparison Error** | `TABLE_COMPARISON_ERROR` | Misaligns rows and columns or compares treatment groups without normalizing to baseline controls. |
| **Unsupported Trend Extrapolation** | `TREND_EXTRAPOLATION` | Extrapolates a linear or monotonic trend beyond the empirical range tested in the study. |
| **Mechanism Confusion** | `MECHANISM_CONFUSION` | Proposes an unverified reaction pathway, enzymatic intermediate, or physiological cascade. |
| **Exception or Qualifier Overlooked** | `EXCEPTION_OVERLOOKED` | Ignores crucial qualifying conditions in the stem such as "under aerobic conditions only" or "at physiological pH". |
| **Negation or NOT/EXCEPT Misread** | `NEGATION_MISREAD` | Overlooks negative phrasing (e.g., "LEAST likely", "EXCEPT", "NOT supported") and picks a true statement. |
| **Scope Shift** | `SCOPE_SHIFT` | Generalizes a finding observed in cell culture or animal models directly to whole-organism human physiology. |
| **Unsupported Inference** | `UNSUPPORTED_INFERENCE` | Selects an answer that sounds scientifically plausible but lacks empirical proof in the supplied passage. |
| **Passage Contradiction** | `PASSAGE_CONTRADICTION` | States a claim that directly contradicts experimental data, figures, or author arguments in the passage. |
| **Overgeneralization** | `OVERGENERALIZATION` | Uses unhedged absolutes ("always", "never", "invariably") where only a conditional effect was shown. |
| **Distractor Overinterpretation** | `DISTRACTOR_OVERINTERPRETATION` | Reads complex unstated motives or unwarranted biochemical consequences into simple factual data. |
| **Answer-Choice Conflation** | `ANSWER_CHOICE_CONFLATION` | Merges elements of two distinct answer choices to form a seemingly comprehensive but erroneous hybrid. |

> **Smart AI Automatic Selection**: In addition to manual trap targeting in the wizard, the generator features an `Automatic` mode where the AI analyzes the scenario to select the most pedagogically appropriate trap from the 25 ids above and records it on the question (shown as the primary trap tag on question cards). Separately, an optional `likely_mistake_pattern` (23 curated student-misconception ids, e.g. `CONFUSES_KM_VMAX`) can be targeted so at least one distractor attracts that specific error.

---

## 5. Anti-Collision, Deduplication & pgvector Semantic RAG

In high-stakes MCAT preparation, duplicate questions damage student outcomes by creating artificially inflated scores and wasting timed practice stamina.

```mermaid
flowchart TD
    Candidate["Candidate Question Drafted"] --> ScopedPool["Reference Pool<br/>(Same Section + Subtopic, batch siblings, in-flight drafts)"]
    ScopedPool --> MathCheck["Multi-Metric Similarity Check<br/>• 35% Token Containment<br/>• 25% 1-Gram Jaccard<br/>• 20% 2-Gram Jaccard<br/>• 20% SequenceMatcher<br/>• Answer-choice overlap and same-passage key checks"]

    MathCheck -->|"Similarity >= 75% (hard)"| Pivot["Autonomous Pivot Loop<br/>(Re-prompts generator with collision notice, 1 retry)"]
    MathCheck -->|"60% to 75% (soft)"| Warn["Variety warning logged<br/>(no forced rewrite)"]
    MathCheck -->|"Similarity < 60%"| Continue["Continue to quality review"]
    Pivot --> Continue
    Warn --> Continue

    Continue --> Flags["Staged with duplicate_info<br/>(is_duplicate / is_soft_warning flags)"]
    Flags -->|"Override and approve (badge, alert bar or Compare dialog)"| Override["is_duplicate_override = true<br/>duplicate_info.is_overridden"]
    Flags -->|"Batch card: Check duplicates, then Resolve duplicates"| Resolve["Archive duplicates (the default, recoverable)<br/>and show the batch deficit"]
```

> The web interface shows duplicate awareness in four places: a risk badge on review-queue cards, batch question items and Question Bank rows, an alert bar in the Question Bank inspector, and a side-by-side compare dialog. Levels are **high** (hard duplicate, 75% or more), **similar** (60% to below 75%, derived in the browser from `DUPLICATE_SOFT_THRESHOLD`), **overridden** and none. A similar question is only a warning; a hard duplicate must be looked at before it is saved.

### 5.1 Multi-Metric Similarity Algorithm
The anti-collision engine calculates a composite mathematical similarity score:
$$\text{Similarity} = 0.35(\text{Token Containment}) + 0.25(\text{1-Gram Jaccard}) + 0.20(\text{2-Gram Jaccard}) + 0.20(\text{SequenceMatcher})$$
Answer choices are compared option by option (an option counts as matched when it is identical or at least 70% similar by sequence ratio); when 75% or more of the choices match and the stems are moderately alike, the options overlap raises the overall similarity score. A pair is reported as a duplicate only when the final score reaches the configured thresholds: **75% (hard duplicate)**, **60% (soft warning)**, and **80% for the on-demand `check-duplicate` API**. Questions that share one reading passage get extra checks on their correct-answer concepts.

### 5.2 Intra-Batch Clustering & Autonomous Replenishment
In background multi-job batches (e.g. 50 questions), the system performs autonomous pairwise clustering at the hard threshold (75% similarity). After a batch finishes, the automatic resolver keeps the highest-scoring item of each cluster, permanently deletes the redundant duplicates, trims any set that exceeds its target, and replenishes the shortfall with fresh drafts (up to 3 refill rounds) to deliver the target quota without passage drift. The manual `resolve-duplicates` API instead archives duplicates by default (recoverable) and deletes them only when asked.

### 5.3 pgvector Semantic RAG & Anti-Collision Shield
Beyond lexical string overlap, the system integrates **native PostgreSQL 16 `pgvector`** semantic indexing:
- **1536-Dimensional Vector Embeddings**: Every candidate and published question stem, options set, and mentor proof is translated into a 1536-dimensional vector embedding (`vector(1536)`), computed through LiteLLM with the configured embedding model (a deterministic hash-based vector is used offline or when no embedding key is configured; if a live provider call fails, no embedding is stored for that question).
- **In-Context Exemplar Retrieval**: Queries historical bank questions scoring $\ge 90$ points within the identical section and subtopic. Injects these top-performing items into generator prompts as concrete stylistic and cognitive benchmarks.
- **Negative Avoidance Shielding**: Searches the HNSW cosine vector index (`vector_cosine_ops`) for nearest neighbors in the same section and subtopic. Up to 4 questions with cosine similarity of at least 0.60 are supplied to the LLM generator as explicit **Avoidance Stems**, commanding the model to explore distinct clinical angles, unaddressed enzymatic conditions, or novel sociological theories. A separate semantic duplicate check during generation flags a draft whose embedding similarity to an existing question reaches 0.80.

### 5.4 Duplicate Flags & Override Audit Trail
Each question stores a `duplicate_info` record (hard/soft flag, similarity score, matched question id and stem, reason). When an educator decides two questions examine distinct principles (e.g., competitive vs. uncompetitive enzyme inhibition using the same substrate), the `POST /api/questions/{id}/override-duplicate` endpoint sets `is_duplicate_override = true`, stamps `is_overridden` and an `overridden_at` timestamp into `duplicate_info`, and approves the question into the bank (a question still held by a running batch stays `batch_only`). In the web interface the educator can open the comparison from the duplicate badge or alert bar and choose **Override and approve** (a direct click followed by a confirmation toast). On the batch card, **Check duplicates** (on demand, never automatic) lists groups of near-identical questions and **Resolve duplicates** (after a confirmation) keeps the best question of each group and archives the rest (`action=archive`, recoverable), then shows how many questions the batch is now short of its target.

---

## 6. The 5 Top-Level Workstation Views

```mermaid
graph LR
    Nav["Infynno MCAT Studio Navigation"]
    Nav --> Tab1["1. Create Questions<br/>(Hero Landing & 3-Step Wizard)"]
    Nav --> Tab2["2. Batch Progress<br/>(Worker Pool & Concurrency Monitor)"]
    Nav --> Tab3["3. Review Queue<br/>(AI-Validated Staging Deck)"]
    Nav --> Tab4["4. Question Bank<br/>(Canonical Repository & Inline Editor)"]
    Nav --> Tab5["5. Passage Bank<br/>(Stimulus Curation & Cascade Manager)"]
```

---

### 6.1 Create Questions: Question Studio & 3-Step Wizard
The primary authoring portal switches between a minimalist welcome canvas (`HeroLanding.jsx`) and the streamlined 3-step authoring wizard (`GuidedWizard.jsx`):

1. **Step 1: Section & Focus (`WizardStep1SectionFocus.jsx`)**:
   - Official AAMC section selection (`CP`, `CARS`, `BB`, `PS`).
   - Granular syllabus navigation: major units and concept subtopics.
2. **Step 2: Level, Format & Scope (`WizardStep2LevelFormat.jsx`)**:
   - **Generation Scope**:
     - **5 Questions (1 Single Job)**: Rapid background worker drafting on a shared passage or discrete set (~35-50s) with live telemetry.
     - **50 Questions (10 Jobs)**: Enterprise background multi-job batch of 10 jobs (running up to the server's concurrent-job limit).
     - These are the two presets in the wizard; the backend accepts any quantity from 1 to 50 and splits it into jobs of 5 questions (for example 12 questions become jobs of 5, 5 and 2).
   - **Challenge Level**: Low, Medium, High difficulty calibration.
   - **Binary Format**: Passage-Based Set vs. Independent Discretes.
3. **Step 3: Review & Launch (`WizardStep3ReviewAdvanced.jsx`)**:
   - **Parameter Summary Card**: Compact tabular review of section, topics, difficulty, and question count (`.wizard-review-card`, 12px radius).
   - **Scientific Diagrams Toggle Card**: 1-click toggle card for natural science sections (`.wizard-diagram-card`, 12px radius).
   - **Additional Authoring Instructions**: High-priority textarea allowing educators to specify custom clinical scenarios or derivations (triggers animated `+ Custom Prompt Active` badge).
   - **Advanced Settings Drawer**: Fine-grained selection of specific cognitive traps, SIRS reasoning skills, and targeted mistake patterns.
4. **Spatial Ergonomics & Radius Scale**:
   - The outer Guided Wizard dock (`.wizard-card`) is styled with `border-radius: var(--radius-lg)` (`16px`), matching top-level workspace panels and modal dialogs.
   - Nested decision containers—such as difficulty choice cards (`.wizard-tier-card`), review parameter summaries (`.wizard-review-card`), and the diagram toggle card (`.wizard-diagram-card`)—consistently enforce `border-radius: var(--radius-md)` (`12px`), providing a harmonious, fatigue-free authoring environment that eliminates visual sibling drift.

---

### 6.2 Batch Progress: Concurrency Monitor & Resilient Processing
A real-time monitor (`BatchActivityView.jsx`, `ActiveMultiBatchMonitor.jsx`) tracking multi-job background batches:

- **Global Worker Pool Concurrency Gauge**: Displays live worker slot occupancy against server semaphores (defaults: `4` concurrent jobs, `10` concurrent LLM calls). Other server guards: up to 8 question pipelines in flight, at most 5 running batches, and 30 generation requests per client per minute; question workers inside a run start slightly staggered so siblings can see each other for duplicate checks.
- **Dual-Track Progress Indication**:
  - **Uncapped Mathematical Progress Bar**: Accurately reflects `actual_count / target_count * 100%`.
  - **5-Question Progress Strips**: Visual micro-pills (`Q1`–`Q5`) showing exact slot lifecycle:
    - `✓ Q1` (Emerald): Completed and ready for review.
    - `✓ Q1` (Purple): Completed and approved into Question Bank.
    - `● Q2` (Pulsing Cyan): Actively generating or self-evaluating candidate.
    - `Q3` (Dashed Muted): Pending placeholder awaiting worker slot.
- **Autonomous In-Flight 3-Trials Retry Policy**: If questions fail quality benchmarks, background jobs automatically execute up to 3 replenishment trials, displaying `AUTO-RETRYING (X/3)` or `3/3 TRIALS EXHAUSTED`.
- **Review Queue Withholding Guarantee**: Items generated in background batches remain in `batch_only` status while the batch is running. Only when the batch cleanly finishes are items with score $> 80$ promoted to the Review Queue, ensuring educators never review incomplete sets.
- **1-Click Batch Stop & Controlled Resume**: Educators can stop a running batch safely. Paused batches with remaining trials display a **"Resume Sets"** action to resume execution.

---

### 6.3 Review Queue: AI-Validated Triage & Editorial Staging
A dedicated triage desk (`AiValidatedQuestionsView.jsx`) for items that scored $> 80$ in batch runs:

- **Fast Editorial Scanning**: Displays section badges, difficulty chips (`badge-emerald`, `badge-amber`, `badge-rose`), score badges (`<Award size={11} /> Score/100`), subtopic, and primary trap tag.
- **Passage Inspection with `SharedPassageCard`**: Expandable reading passages formatted in `Newsreader` serif typography with word-count badges, font scaling controls (A-, 100%, A+), and embedded diagrams.
- **1-Click Editorial Actions**:
  - **Save to Question Bank**: Moves the question to the permanent bank.
  - **Discard**: Permanently removes the question.
  - **Quality Review**: Opens the comprehensive 4-pillar psychometric breakdown modal.
- **Bulk Actions**: Select individual or all questions to "Save Selected to Question Bank" or "Discard Selected".

---

### 6.4 Question Bank: Canonical Repository & Inline Editorial Desk
The primary searchable and filterable repository (`QuestionBankView.jsx`), strictly consolidated on the canonical **Editorial Cards** view:

- **Multi-Factor Filtering & Search**: Instant keyword search (focused via `/` keyboard shortcut), section dropdown, difficulty filter, and sorting.
- **Inline Question Editor (`QuestionInlineEditor.jsx`)**: In-place editing of question stem, options, and explanations without navigating away, powered by live **Option Length Symmetry** calculations.
- **Card Drawer Expansion**: Inline preview showing the full reading passage via `SharedPassageCard`, 2x2 option grid with correct key highlight, and full 3-card mentor explanations.
- **Full Question Inspector Modal**: Accessible dialog with 3 inspection tabs:
  - **Preview Tab**: Student practice mode with interactive selection and mentor explanations.
  - **Scorecard Tab**: Itemized 100-point rubric with reviewer critique.
  - **Details Tab**: Deep stage outcome JSON inspector showing raw multi-agent payloads.
- **Bulk Management**: Multi-select questions for batch deletion (with accessible confirmation dialog) or export.

---

### 6.5 Passage Bank: Stimulus Curation & Cascading Management
A specialized repository (`PassageBankView.jsx`) dedicated to reading passages and research narratives:

- **Passage Editorial Desk (`PassageEditorialDesk.jsx`)**: Split-pane editorial canvas featuring:
  - Live in-place text editor for the passage narrative styled in **Newsreader Serif** (`font-size: 1.05rem; line-height: 1.68; letter-spacing: -0.01em;`) matching clinical publication guidelines.
  - Real-time word counter with MCAT pacing metrics.
  - Figure showcase and discard tool (`PassageVisualStimulusEditor.jsx`) supporting all 7 medical modalities with 1-click detachment.
  - **Passage Readability & Alignment Diagnostics**: 1-click assessment (`/api/ai/audit-passage`) calculating Flesch-Kincaid grade level, reading ease, empirical anchor density, and sentence counts, styled in a dedicated diagnostics card with decoupled status badges (`Alignment: Strong` / `Alignment: Calibrating`).
  - **Linked Questions Stepper Carousel (`PassageQuestionsCarousel.jsx`)**: Carousel inspecting all questions associated with the passage with keyboard arrow shortcuts (`←` / `→`) and decoupled status pills (`Ready for Review` / `In Bank`) eliminating raw internal score math.
- **Safe Cascade Deletion Modal (`DeletePassageModal.jsx`)**: Accessible dialog that audits and displays the exact number of linked questions across all lifecycle statuses (`in_bank`, `ai_validated`, `batch_only`) that will be soft-deleted, while cleanly preserving historical batch execution progress.

---

### 6.6 AI Copilot Studio & In-Line Refinement
The platform integrates an interactive AI Copilot Studio embedded directly into editorial review and generation workflows:

1. **Question Copilot Strip (`QuestionCopilotStrip.jsx`)**:
   - Rendered directly inside candidate question cards in the Review Queue and Question Bank.
   - Provides 1-click intelligent refinement actions:
     - **Polish Distractors**: Enhances plausibility, eliminates giveaway length differences, and tightens distractor trap subtlety.
     - **Simplify Explanation**: Sharpens mentor explanations into concise step-by-step proofs without sacrificing scientific rigor.
     - **Invert Sibling**: Synthesizes a reverse question testing the opposing physiological mechanism or inverted mathematical ratio.
     - **Custom Instruction Drawer**: An expandable drawer allowing educators to enter custom editorial commands (e.g., *"Shift focus to Lineweaver-Burk y-intercept changes under competitive inhibition"*).
   - Generates an in-place preview with side-by-side diffing before the educator commits changes.

2. **Authoring Prompt Enhancement (`/api/ai/enhance-instructions`)**:
   - **Enhance Instructions**: Enhances informal instructor notes into an authoritative AAMC prompt mandate with authentic clinical terminology, distractor constraints, and calculation trap directives directly inside the Guided Wizard Step 3.

---

### 6.7 Hero Landing & Quick-Start Presets Desk
The entry landing surface (`HeroLanding.jsx`) welcomes educators with an uncluttered command canvas, providing two clear primary pathways and instant 1-click AAMC section presets:

- **Dual Primary Actions**:
  - **Create Questions**: Launches the streamlined 3-step Guided Wizard to configure custom sections, pacing, and focus.
  - **Question Bank**: Navigates directly to the canonical repository of verified, high-scoring questions.
- **Instant Section Quick-Start Presets**: 4 pre-calibrated preset chips allowing educators to bypass repetitive configuration:
  - **Chemical and Physical Foundations (CP)**: Pacing 95s, Passage-Based, High difficulty.
  - **Critical Analysis and Reasoning Skills (CARS)**: Pacing 100s, Passage-Based, High difficulty.
  - **Biological and Biochemical Foundations (BB)**: Pacing 95s, Passage-Based, High difficulty.
  - **Psychological, Social, and Biological Foundations (PS)**: Pacing 95s, Passage-Based, Medium difficulty.
- **Enterprise Accessibility (WCAG AA)**: Built with native semantic `<button>` elements, explicit `aria-label`s on brand link and preset chips, and hidden decorative Lucide icons (`aria-hidden="true"`).

---

## 7. Export & Study Studio

The platform includes a comprehensive, accessible export studio (`ExportPrintModal.jsx`) decomposed into specialized sub-panes for scope selection, data formatting, and study guide compilation:

- **Scope Selector (`ExportScopeSelector.jsx`)**: Allows educators to export all approved bank items (`in_bank`, shown as "All"), the items matching the active filters ("Filtered", shown when filters are active) or the checked items ("Selected").
- **Data Format Pane (`ExportDataFormatPane.jsx`)**: Shows the CSV and JSON previews; the modal's formats are Printable Exam / Study Pack (print or save as PDF), CSV, JSON and Study Guide.
- **Study Guide Export Pane (`StudyGuideExportPane.jsx`)**: Interfaces with `POST /api/ai/study-guide` to synthesize executive summaries, trap checklists, and flashcards; the guide downloads as Markdown (`.md`) and the flashcards as an Anki-compatible tab-separated file (`.tsv`).

```mermaid
graph TD
    Repo[(Question Bank Repository)] --> Scope[ExportScopeSelector<br/>Selected / Filtered / All in Bank]
    Scope --> Studio[Export & Study Studio]
    Studio --> F1["1. Printable Exam Paper (student mode)<br/>• Candidate name / date / time-allowed header<br/>• @media print CSS with page-break rules<br/>• Print or Save as PDF"]
    Studio --> F2["2. Study Pack (print / PDF)<br/>• Reading passages & visual figures<br/>• Answers, explanations and trap spotlights"]
    Studio --> F3["3. Standardized CSV Spreadsheet<br/>• Comma-delimited rows for Excel, Google Sheets<br/>• Formula-safe cells"]
    Studio --> F4["4. Normalized JSON Bundle<br/>• Question objects as fetched (slim payload)"]
    Studio --> F5["5. High-Yield Markdown Study Guide (.md)<br/>• Thematic executive summary<br/>• Cognitive trap checklists"]
    Studio --> F6["6. Anki Flashcards (.tsv)<br/>• Tab-separated front / back / tags from the study guide's flashcard pairs"]
```

---

## 8. Financial Telemetry & Micro-Dollar Cost Accounting

Every inference request calculates exact sub-micro-cent USD expenditure using real-time token tracking:

$$\text{Cost (USD)} = \left(\frac{\text{Prompt Tokens}}{1,000,000} \times R_{\text{in}}\right) + \left(\frac{\text{Completion Tokens}}{1,000,000} \times R_{\text{out}}\right) + \text{Cache Costs}$$

### Supported Inference Providers & Standard Rate Cards
- **DeepInfra (DeepSeek V4.1 Flash Reasoning Engine)**:
  - Input: **$0.20 / 1M tokens**
  - Output: **$0.60 / 1M tokens**
  - FLUX-2 Neural Visual Stimulus: **$0.014 / image**
- **Anthropic Claude (default model Claude Haiku 5.5; other Claude model ids are accepted by the code)**:
  - Claude Haiku 5.5: **$0.10 input / $0.50 output per 1M tokens** (prompts up to 100K tokens; higher tier above) with native prompt caching discounts.
- **OpenAI (`gpt-4o-mini`)**: Supported via provider toggle.

### Operational Cost Benchmarks
- A complete, quality-audited **5-question set** typically costs between **$0.006 and $0.012 USD** under DeepInfra.
- An enterprise **50-question mock section (10 jobs)** costs between **$0.06 and $0.12 USD**.
- Accumulated repository tokens, execution durations, and total dollar investments are displayed live in the Question Bank header.

---

## 9. UI Design System, Ergonomics & Accessibility

- **Linear/Vercel-Inspired Minimalist Aesthetic**: Quiet surfaces, hairline dividers (`1px solid var(--border-light)`), subtle box shadows, and zero card clutter.
- **Dual-Theme Ergonomics**: First-class Alabaster Light (`#f8fafc`) default and Dark Obsidian (`#080c14`) theme with zero-flicker toggle via navbar switch or keyboard shortcut (`T`).
- **Editorial Typography Hierarchy**:
  - `Plus Jakarta Sans`: Clean, geometric sans-serif for UI controls, buttons, wizards, and tables.
  - `Newsreader Serif`: Clinical reading passages and stimuli rendered in high-legibility serif (`1.05rem`, `line-height: 1.68`) to eliminate reading fatigue.
  - `JetBrains Mono`: Monospace typography for token counts, stopwatch timers, cost calculations, and keyboard shortcuts.
- **WCAG AA Accessibility Standards**:
  - Minimum contrast ratio of 4.5:1 for body copy and 3:1 for large text/badges across both themes.
  - Strict keyboard focus trapping (`useFocusTrap`) across all modals (`Modal`, `ConfirmationModal`, `DeletePassageModal`, `ExportPrintModal`), restoring focus to origin controls upon `Escape` or dismissal.
- **Global Keyboard Accelerators**:
  - `⌘ + Enter` / `Ctrl + Enter`: Trigger question or batch generation.
  - `T`: Instant toggle between Dark and Light themes.
  - `/`: Immediately focus the Question Bank search input.
  - `A`: In the Review Queue only, save the active card to the bank (a hard duplicate that has not been overridden opens the comparison instead).
  - `D`: In the Review Queue only, discard the active card (asks for confirmation first).
  - Single-key shortcuts (`T`, `/`, `A`, `D`) are ignored while typing in a field, while a dialog is open, with Cmd/Ctrl/Alt held, or on key repeat.
  - `Escape`: Dismiss open dialogs and drawers.
- **Everyday Human Language Standard**: Replaces robotic AI jargon with classroom-authentic terms (*Reading passage*, *Independent question*, *Quality Review*, *Create Questions*, *Common Traps*).

---

## 10. Technical Architecture, Security & Production Readiness

### Full-Stack Architecture Specifications
- **Frontend**: React 19, Vite 8, Lucide Icons, pure token-driven CSS (no bulky utility frameworks), oxlint, Vitest (203 unit tests across 25 test files).
- **Backend**: FastAPI (Python 3.11), SQLAlchemy Async 2.0, asyncpg connection pooling, Pydantic v2 schemas, pytest (549 deterministic test suite across 79 modules; 559 total tests).
- **Database**: PostgreSQL 16 with native JSONB columns for multi-stage payloads, rubrics, and token tracking; UUID4 primary keys; automated schema migrations on startup.
- **Observability**: Prometheus `/metrics` endpoint exposing real-time worker pool occupancy, batch lifecycle states, and token expenditures.
- **Security & Hygiene**:
  - Input sanitization via DOMPurify SVG profile (`SafeSvg`) preventing XSS in diagrams.
  - Strict CORS validation and API key redaction in logging contexts.
  - Pre-development port hygiene scripts ensuring clean local boot.

---

## Summary Deliverable Overview

| Dimension | Infynno MCAT Generator v2.0 Capability |
| :--- | :--- |
| **Exam Alignment** | 100% compliant with official AAMC syllabus, SIRS skills, and CARS pure-passage rules. |
| **Pedagogical Integrity** | Option symmetry (length spread within `max(3, ceil(20% of mean))` words), 3-card mentor explanations, 25-trap taxonomy. |
| **Verification & Safeguards** | Algorithmic Blind-Solver test candidate ($\ge 88\%$ confidence), 100-pt 4-pillar auditor. |
| **Duplicate Prevention** | Multi-metric anti-collision loop (hard threshold 75%, soft 60%), intra-batch clustering, duplicate badges and compare dialog, override audit trail, on-demand batch duplicate audit. |
| **Batch Capabilities** | Dual-track progress monitor, 4-stage stepper, 3-trials autonomous retries, withholding queue guarantee. |
| **Editorial Workflows** | Canonical Editorial Cards bank, inline question editor, passage editorial desk, cascade delete safety. |
| **Export Formats** | Exam Booklets (PDF/Print with page-break protection), Study Packs, CSV, Normalized JSON. |
| **Economics & Telemetry** | Micro-dollar precision tracking ($0.006–$0.012 per 5-question set) across DeepInfra / Anthropic Claude. |
| **Design & Accessibility** | Alabaster Light / Dark Obsidian, Newsreader serif typography, WCAG AA focus trapping, keyboard shortcuts. |

---
*Infynno Solutions LLP • Infinite Innovations • Confidential & Proprietary Client Deliverable*
