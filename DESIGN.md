# Infynno Design System & UI Specification (DESIGN.md)

> **Infynno Solutions LLP • Infinite Innovations • [infynno.com](https://infynno.com/)**  
> **Product**: Infynno MCAT Question Bank Generator v2.0  
> **Aesthetic Philosophy**: Linear/Vercel-inspired high-precision minimalism, alabaster light mode default with dark obsidian mode, scientific research passages and CARS essays, and live batch telemetry.

---

## 1. Design Philosophy & Architectural Principles

The Infynno MCAT Question Studio is built for pre-med educators, test-prep authors, and aspiring medical candidates who require focused, fatigue-free reading environments combined with real-time multi-agent observability and official AAMC exam alignment.

1. **Precision Minimalism**: Quiet surfaces, hairline borders (`1px solid var(--border-light)`), subtle elevations, and zero card clutter.
2. **Editorial Typographic Hierarchy**: Clinical reading passages rendered in warm, high-legibility serif type (`Newsreader`, line-height `1.68`), while UI controls and telemetry use modern sans-serif (`Plus Jakarta Sans`) and monospace (`JetBrains Mono`).
3. **Reactive Observability**: Complex multi-agent workflow steps (Generator, Reviewer, Regenerator, Image Engine) are visualized through live progress strips, pulse indicators and stage badges without distracting from the editorial workspace.
4. **Seamless Dual-Theme Ergonomics**: First-class alabaster light (`#f8fafc`) default and dark obsidian (`#080c14`) palettes toggled instantly with zero flicker (`T` shortcut or navbar control).
5. **Print & Export Fidelity**: Built-in `@media print` CSS rules and clean paper layouts for professional PDF exam booklets and student study packs.

---

## 2. Color System & Design Tokens

Design tokens are defined as CSS custom properties in [`frontend/src/styles/tokens.css`](frontend/src/styles/tokens.css) and aggregated with domain stylesheets via [`frontend/src/index.css`](frontend/src/index.css). The design system automatically responds to the `[data-theme="dark"]` and `[data-theme="light"]` attributes on the root `<html>` element.

The styling architecture is strictly modularized across domain-specific CSS files:
- `tokens.css`: Core design tokens, brand gradients, radii, z-index layers (`--z-*`), and dark/light color palettes.
- `base.css`: Global CSS reset, font declarations, accessible button primitives, and base form controls.
- `layout.css`: Application shell, Navbar, Footer, Toast notifications, and pagination footer.
- `wizard.css`: Hero landing screen, 3-step question generation wizard dock, decision cards, and presets.
- `question.css`: QuestionCard, 3-card mentor explanation view, stimulus viewer container, scorecard.
- `question-copilot.css`: Floating AI Copilot strip, tool popovers, streaming state chips.
- `stage-inspector.css`: Deep 5-stage pipeline outcome JSON inspector accordion.
- `study-guide-modal.css`: Decomposed study pack and high-yield takeaway options pane.
- `batch.css`, `batch-activity.css`, `batch-card-summary.css`: Concurrency gauges, progress strips, batch cards.
- `bank.css`: Canonical Question Bank editorial cards and AI-Validated review queue.
- `passage.css`: Passage catalog cards, editorial desk, and figure attachment editor.
- `modals.css`: Standardized modal backdrop, card shells, and focus-trapped dialog wrappers.
- `print.css`: Professional `@media print` paper styling and page-break rules.
- `accessibility.css`: High-contrast accessible utility classes, focus visible outlines, and screen-reader utilities (`sr-only`).

### 2.1 Infynno Corporate Brand Palette
These core gradient tokens anchor the brand identity across buttons, active tab indicators, and progress tracks:

| Token Name | Hex / Value | Role |
| :--- | :--- | :--- |
| `--infynno-violet` | `#4F30B9` | Primary deep violet anchor |
| `--infynno-blue` | `#335ACF` | Core Infynno royal blue |
| `--infynno-cyan` | `#1E7ADF` | Vibrant electric cyan accent |
| `--infynno-gradient` | `linear-gradient(135deg, #4F30B9 0%, #335ACF 50%, #1E7ADF 100%)` | Interactive primary actions, badges, progress bars |
| `--infynno-glow` | `0 0 20px rgba(51, 90, 207, 0.25)` | Focused element glow |

---

### 2.2 Theme Surface & Border Variables

```mermaid
graph LR
    subgraph "Alabaster Light (Default)"
        L_Canvas[--bg-canvas: #f8fafc] --> L_Surface[--bg-surface: #ffffff]
        L_Surface --> L_Elevated[--bg-surface-elevated: #ffffff]
        L_Elevated --> L_Border[--border-light: #e8ecf2]
    end
    subgraph "Dark Obsidian"
        D_Canvas[--bg-canvas: #080c14] --> D_Surface[--bg-surface: #0d121d]
        D_Surface --> D_Elevated[--bg-surface-elevated: #121826]
        D_Elevated --> D_Border[--border-light: rgba(255,255,255,0.06)]
    end
```

| Token | Dark Theme (`[data-theme="dark"]`) | Light Theme (`[data-theme="light"]`) | Usage |
| :--- | :--- | :--- | :--- |
| `--bg-app` / `--bg-canvas` | `#080c14` | `#f8fafc` | Viewport backdrop |
| `--bg-surface` | `#0d121d` | `#ffffff` | Standard card panels |
| `--bg-surface-elevated`| `#121826` | `#ffffff` | Modals, active states, dropdowns |
| `--bg-surface-subtle`  | `#0a0e18` | `#f8fafc` | Inactive steps, table headers |
| `--bg-surface-hover`   | `#151c2c` | `#f1f5f9` | Hover states |
| `--border-light`       | `rgba(255, 255, 255, 0.06)` | `#e8ecf2` | Primary panel hairline dividers |
| `--border-medium`      | `rgba(255, 255, 255, 0.10)` | `#cbd5e1` | Input focus, active borders |
| `--border-strong`      | `rgba(255, 255, 255, 0.16)` | `#94a3b8` | Elevated modal outlines |
| `--text-primary`       | `#f8fafc` | `#0f172a` | Headers, reading passages, keys |
| `--text-secondary`     | `#94a3b8` | `#475569` | Body copy, secondary options |
| `--text-muted`         | `#64748b` | `#64748b` | Metadata, micro-badges, hints |
| `--text-dim`           | `#475569` | `#94a3b8` | Placeholders, inactive labels |

---

### 2.3 Status & Psychometric Scoring Tokens

The foreground hex values below are the dark-theme values; the light theme uses darker foregrounds (success `#059669`, danger `#e11d48`, purple `#7c3aed`; warning `#d97706`) defined in `tokens.css`.

| Status Pillar | Foreground Token (dark theme) | Dark BG / Border | Light BG / Border | Semantic Role |
| :--- | :--- | :--- | :--- | :--- |
| **Pass / Success** | `--status-success` (`#10b981`) | `rgba(16,185,129,0.06)` / `0.22` | `#ecfdf5` / `#a7f3d0` | Psychometric Score > 80, Approved |
| **Warning / Caution** | `--status-warning` (`#f59e0b`) | `rgba(245,158,11,0.06)` / `0.22` | `#fffbeb` / `#fde68a` | Remediation in progress, Borderline draft |
| **Reject / Danger** | `--status-danger` (`#f43f5e`) | `rgba(244,63,94,0.06)` / `0.22` | `#fff1f2` / `#fecdd3` | Rejected draft (score below 70 after 3 cycles), Discarded draft |
| **Cognitive Trap** | `--status-purple` (`#8b5cf6`) | `rgba(139,92,246,0.06)` / `0.22` | `#f5f3ff` / `#ddd6fe` | Distractor analysis, trap rationalization |

---

### 2.4 MCAT Section Accents

Each official AAMC MCAT section receives a dedicated signature accent for instant identification across wizards, cards, and filters:

```
Chemical and Physical Foundations (CP)   -> Sky Blue      (#38bdf8 / #0284c7)
Critical Analysis & Reasoning (CARS)    -> Rose Crimson  (#f43f5e / #e11d48)
Biological & Biochemical Foundations (BB)-> Emerald Green (#10b981 / #059669)
Psychological, Social & Biological (PS)  -> Royal Violet  (#a855f7 / #7c3aed)
```

---

## 3. Typography & Spatial Layout

### 3.1 Font Stacks
```css
--font-sans:  'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
--font-serif: 'Newsreader', Georgia, serif;
--font-mono:  'JetBrains Mono', monospace;
```

- **Plus Jakarta Sans**: Primary application typography. Clean, modern geometric proportions ensure high legibility in buttons, tabs, wizards, and tables.
- **Newsreader Serif**: Used exclusively for clinical reading passages and stimulus articles. Set with `font-size: 1.05rem`, `line-height: 1.68`, and letter-spacing `-0.01em` to emulate high-end medical journal formatting and prevent cognitive fatigue.
- **JetBrains Mono**: Used for token metrics, stopwatch timers, cost calculations, JSON trees, and shortcut badges (`⌘↵`).

### 3.2 Spatial Scale & Border Radii
- **Workspace Canvas**: `.app-main-content` (`layout.css`) is constrained to `max-width: 1440px`, centered with auto margins and `24px` padding. The guided wizard dock (`.wizard-card`) is narrower (`max-width: 880px`).
- **Radius Hierarchy**:
  - `--radius-xs`: `4px` (micro tags, tooltips)
  - `--radius-sm`: `8px` (buttons, select menus, input fields)
  - `--radius-md`: `12px` (sub-cards, option containers)
  - `--radius-lg`: `16px` (main workspace cards, modal dialogs)
  - `--radius-full`: `9999px` (circular option badges A-D, theme switchers, status pills)

---

## 4. Component Design Specifications

### 4.1 Guided Question Wizard & Hero Landing (`GuidedWizard.jsx`, `HeroLanding.jsx`)
Streamlined 3-step authoring workflow with quick-launch hero presets:
- **Hero Landing Header (`HeroLanding.jsx`)**: Welcome landing hero with instant 1-click exam preset chips (`HERO_PRESETS` hoisted in `wizardConstants.js`) paired with the module-level `HERO_PRESET_ICONS` lookup table (`chem_phys: FlaskConical`, `cars: BookOpen`, `bio_biochem: Dna`, `psych_soc: Brain`). Clicking any preset triggers `handleApplyPresetAndNavigate` in `useAppState.js`, immediately applying calibrated section rules, default challenge levels, and navigating directly into Step 1 of the guided wizard dock.
- **Wizard Header Stepper (`WizardHeaderStepper.jsx`)**: Modern breadcrumb stepper featuring native `<button type="button">` step indicators with accessible `aria-current={isCurrent ? 'step' : undefined}` badges, keyboard focus rings, and completed checkmark cues.
- **Step 1: Section & Focus (`WizardStep1SectionFocus.jsx`)**: Official AAMC exam section selection (CP, CARS, BB, PS) with quick-start presets and granular topic/subtopic syllabus focus. Implemented with native semantic `<button type="button">` elements equipped with `aria-pressed={isSelected}` for assistive screen reader announcements and standard keyboard navigation (`Tab` + `Space`/`Enter`), completely eliminating synthetic non-semantic clickable `<div>` containers.
- **Step 2: Level & Format (`WizardStep2LevelFormat.jsx`)**: Calibrated challenge level (**Low**, **Medium**, **High**), question format (Passage-Based vs Independent Single-Choice), and 2 calibrated Generation Scopes governed by the unified 5-question Job architecture, presented as streamlined cards without redundant badge pills:
  1. **5 Questions**: 1 Single Job consisting of 5 questions linked to a shared reading passage (or 5 discretes), dispatched to the background worker pool (~35-50s) with automated AI validation and real-time telemetry streaming into Validated Bank and Batch Activity.
  2. **50 Questions**: Enterprise background multi-job batch across 10 concurrent worker jobs (5 questions each) governed by the Global Worker Pool with automatic AI validation.
- **Step 3: Review & Advanced Calibration (`WizardStep3ReviewAdvanced.jsx`)**: Modular, high-density review interface cleanly decomposed into two dedicated components:
  - **Review Summary (`WizardReviewSummary.jsx`)**: Instant tabular overview of selected section, topic, challenge level, and question count in a compact parameter summary card with descriptive `aria-label`s on all quick-jump edit buttons (`"Edit section"`, `"Edit topic"`, `"Edit level"`, `"Edit format"`, `"Edit question count"`).
  - **Scientific Diagrams Toggle (`Include Images When Needed`)**: Prominently positioned toggle card for natural science sections implemented as a native accessible `<button type="button" role="switch" aria-checked={allowAiImages}>` with animated pill switch and keyboard actuation. Controls autonomous AI discretion (`allowAiImages: true`, `requireImage: false`, `visual_type: 'AI_FLUX_Image'`) giving the model full creative and pedagogical freedom to generate visual stimuli whenever helpful or illustrative across all 7 medical/scientific modalities. Permanently hidden in the UI for CARS, and defense-in-depth normalized in `batchPayload.js` (`normalizeSectionId(selectedSection) === SECTION_IDS.CARS`) to guarantee visual properties are strictly suppressed for CARS at the API boundary.
  - **Additional Authoring Instructions**: Dedicated textarea (`border: 1px solid var(--border-light)`, `background: var(--bg-surface-subtle)`) allowing educators to supply explicit clinical scenarios, Lineweaver-Burk derivation mandates, or custom distractor traps. When populated, an animated indicator badge (`+ Custom Prompt Active`) is rendered dynamically in the card header. Enhanced with `.wizard-enhance-instructions-btn` for 1-click pedagogical prompt enrichment via the AI copilot suite.
  - **Advanced Settings Drawer (`WizardAdvancedSettings.jsx`)**: Decomposed collapsible accordion drawer giving fine-grained control over cognitive distractor traps, SIRS reasoning skills, and targeted student mistake patterns. Accordion header uses `.wizard-advanced-header-title-group` for structured semantic heading alignment and is an accessible native `<button type="button">` with `aria-expanded={showAdvanced}` and `aria-controls="wizard-advanced-panel"`, paired with `id="wizard-advanced-panel"` on the collapsible content container.
- **Spatial Radius & Transition Scale Compliance (`.wizard-card` & Sub-Cards)**:
  - `.wizard-card` (the outer dock) strictly enforces `border-radius: var(--radius-lg)` (`16px`), aligning with main workspace panels and modal dialogs per §3.2.
  - Sub-cards and option decision containers—including `.wizard-section-card` (Step 1 section choices), `.wizard-tier-card` (difficulty & format choices), `.wizard-review-card` (Step 3 parameter overview), and `.wizard-diagram-card` (scientific diagrams toggle)—strictly enforce `border-radius: var(--radius-md)` (`12px`) and `transition: var(--transition-ui)` (the interactive-state property list in `tokens.css` at `var(--transition-fast)`, `0.12s ease-out`), eliminating sibling radius drift across wizard steps.
  - Section badges within cards enforce `border-radius: var(--radius-full)`.
  - Action buttons and tags strictly enforce `border-radius: var(--radius-sm)` (`8px`) and `var(--radius-xs)` (`4px`).

### 4.2 Live Batch Activity & Concurrency Monitor (`BatchActivityView.jsx`, `ActiveMultiBatchMonitor.jsx`)
- **Dual-Track Progress Indication Architecture**:
  - **Uncapped Mathematical Progress Bar**: Calculates true question delivery (`actual_count / target_count * 100%`), eliminating artificial 95% caps and render-time mutations. Completed batches lock at 100% emerald.
  - **4-Stage Visual Lifecycle Stepper (`.batch-lifecycle-stepper`)**:
    1. `Drafting Sets`: Parallel item generation across active worker slots (`Layers` icon).
    2. `Duplicate Audit`: Autonomous pairwise clustering (hard duplicate threshold 0.75 similarity) and quality rubric gate (`ShieldCheck` icon).
    3. `In-Set Refill`: Autonomous replenishment trials (2-3) targeting deficient slots without passage drift (`RotateCcw` icon; marked `Fulfilled` if no refills required).
    4. `Ready for Review`: Atomic elevation to Review Queue (`CheckCircle2` icon).
- **Contextual Batch Outcome Banners (`.batch-outcome-card`)**:
  - **Completed Batches**: High-leverage emerald card (*"All X Questions Successfully Generated & Verified"*) with direct 1-click `[Open Review Queue (X)]` and `[View in Bank]` CTAs.
  - **Partially Completed Batches**: Amber notification detailing fulfilled vs shortfall counts after 3 exhausted trials with 1-click access to valid questions.
  - **Stopped Batches**: Neutral summary showing safely preserved question counts with instant `[Resume Sets]` controlled resumption.
- **Job Card Live Micro-Progress (`BatchJobCard.jsx`)**:
  - **Worker Queue State**: Explicitly highlights `⏳ Queued in Worker Pool` for jobs waiting for semaphore capacity vs `⚡ Active Worker Slot` with a pulse dot (`.batch-job-pulse-dot`).
  - **5-Question Progress Pills (`.job-q-pill-strip`)**: Micro-status pills (`Q1`–`Q5`) displaying exact question slot lifecycle states via `resolveStatus`:
    - `.done`: Completed and ready for review (`✓ Q1`), emerald accent (`var(--emerald)`).
    - `.in-bank`: Completed and already approved into the Question Bank (`✓ Q1`), royal violet accent (`var(--infynno-violet)`).
    - `.active`: Currently generating or self-evaluating candidate (`● Q2`), brand-colored glow (`var(--brand-light)` background, `var(--brand-primary)` text, `box-shadow: 0 0 6px var(--brand-ring)`).
    - `.pending`: Muted placeholder slot awaiting worker assignment (`Q3`), hairline dashed outline (`var(--border-light)`).
    - `.failed`: Slot that did not produce a question (styled in `batch.css`).
  - **Resilient Autonomous Trial Telemetry Badges**:
    - `Replenishing Slot (Trial X/3)`: Active-slot badge (`.worker-queue-badge.active-slot.batch-job-badge-replenish`, shown when `trial_count > 1`) indicating in-flight shortfall replenishment.
    - `3/3 TRIALS EXHAUSTED`: Warning badge (`.badge.badge-warning.batch-job-status-badge`) signaling that the maximum 3 trial attempts have completed without hitting full target count.
    - `CANCELLED`: Neutral badge for user-aborted sets.
  - **Live Duration Stopwatch**: Self-contained runtime counter (`LiveStopwatch`) tracking elapsed generation duration on running sets and active batches.
- **Autonomous Set-Preserving Duplicate Resolution Engine (`batch_resolution.py`)**:
  - Autonomous pairwise clustering analyzing question similarity (hard duplicate threshold `DUPLICATE_HARD_THRESHOLD=0.75`).
  - Permanent purge (`action="delete"`) of duplicate drafts with automatic in-place slot replenishment preserving the original set's reading passage and thematic angle.
  - Guaranteed exact target count delivery (e.g. exactly 50 questions across 10 jobs) without requiring manual educator intervention.

### 4.3 Editorial Review Desk & AI-Validated Triage (`AiValidatedQuestionsView.jsx`, `AiValidatedQuestionCard.jsx`)
- **Review Queue Architecture**:
  - **Review Queue Card (`AiValidatedQuestionCard.jsx`)**: High-density triage card rendering the question index, section badge (`getSectionBadgeClass`), difficulty chip (`badge ${getDifficultyBadgeClass(q.difficulty)}`), primary cognitive trap tag (`Tag` icon), AAMC reasoning skill badge, diagram pill, and canonical score badge (`<Award size={11} /> {q.final_score}/100`). Includes accessible item selection checkbox with explicit dynamic `aria-label={isSelected ? `Deselect question ${index + 1}` : `Select question ${index + 1}`}`.
  - **Accessible Passage Header Bar**: The passage toggle banner (`.validated-passage-header`) is implemented as a native semantic `<button type="button">` with clean CSS resets (`border: none; background: transparent; text-align: left; cursor: pointer; width: 100%`). The inner expand/collapse indicator is rendered as a `<span aria-hidden="true">` rather than a nested `<button>`, strictly adhering to W3C HTML specifications by preventing illegal nested interactive controls while providing full keyboard actuation (`Space`/`Enter`) and assistive tech announcements.
  - **Embedded Reading Passage (`SharedPassageCard.jsx`)**: When expanded, reading passages render via the canonical `SharedPassageCard` component in publication-grade `Newsreader` serif typography (`font-size: 1.05rem`, `line-height: 1.68`), accompanied by live word-count chips and interactive font-size scaling controls (`A-`, `100%`, `A+`).
  - **Top Metrics Banner (`AiValidatedStatsBar.jsx`)**: Real-time counter strip distinguishing items *Ready for Review*, *In Question Bank*, and *Good Quality* with instant refresh action.
  - **Toolbar & Bulk Operations (`AiValidatedFiltersBar.jsx`)**: Real-time keyword search (with `/` shortcut indicator), section dropdown, bulk select-all checkbox with explicit `aria-label="Select all questions across queue"`, and bulk action triggers (*Save Selected to Question Bank*, *Discard Selected*, *Save All to Question Bank*) with explicit descriptive `aria-label`s.
  - **Action Controls**: Individual 1-click actions: **Save to Question Bank** (`btn-primary`, `aria-label={`Save question ${index + 1} to question bank`}`), **Discard** (`btn-secondary`, `aria-label={`Discard question ${index + 1}`}`), and **Quality Review** (`btn-secondary`, `aria-label={`Open quality review audit for question ${index + 1}`}`, opens `ReviewAuditView` modal).
- **Withholding Queue Flow**: Batches hold incomplete or in-flight questions in `batch_only` status. Once a batch completes, questions passing the $> 80$ rubric standard atomically advance to `ai_validated` and appear in the review queue.
- **Option Badges**: Standard 4 circular `A`, `B`, `C`, `D` pills that highlight emerald on correct answers and crimson on incorrect distractors with clear checkmark/cross indicators.
- **Distractor Rationalization Drawers**: Collapsible cards detailing the exact psychometric reason why each wrong option constitutes a realistic cognitive trap.
- **Inline Editor (`QuestionInlineEditor.jsx`)**: Live editable fields allowing educators to adjust stem text, key letters, or explanation proofs before committing to the canonical question bank.
- **Deep Stage Outcome JSON Inspector (`StageJsonInspector.jsx`)**: Collapsible 5-stage accordion inspector allowing educators and developers to inspect raw agent payloads across Drafting, Quality Review, Polish & Refine, Figures, and Final Question records.

### 4.4 Psychometric Audit Modal & Accessible Focus Trapping (`ReviewAuditView.jsx`)
- **Modal Architecture**: Accessible dialog overlay implementing strict WCAG AA focus trapping and escape dismissal:
  - Traps keyboard focus (`Tab` and `Shift+Tab`) within the dialog boundaries, preventing background tabbing via `useFocusTrap`.
  - Restores focus to the triggering element upon dismissal (`Escape` key or backdrop click).
  - ARIA attributes: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="audit-modal-title"`.
- **Theme-Harmonized Styling**: Styled using consistent brand design tokens:
  - Header & Accents: Uses `var(--brand-primary)` and `var(--brand-light)` for target indicators, cognitive trap badges, and visual stimulus indicators.
  - Surfaces: Uses `var(--bg-surface-elevated)` for card containers with hairline borders (`var(--border-light)`).
- Displays the 4-pillar breakdown (Authenticity, Clarity, Distractor Traps, Explanation Rigor) scored out of 25 each.
- Itemized per-cycle token usage table detailing prompt tokens, completion tokens, execution time, and sub-micro-cent USD cost.

### 4.5 Publication & Export Studio (`ExportPrintModal.jsx`, `ExportPaperPreview.jsx`)
- **Decomposed Modular Panes**:
  - `ExportScopeSelector.jsx`: Target scope configuration (All In-Bank, Current Page, or Staged Review Queue).
  - `ExportDataFormatPane.jsx`: Format configuration for the tabular exports (CSV, JSON).
  - `StudyGuideExportPane.jsx`: Study guide compilation parameters, active recall questions, takeaway depth, and the Anki-compatible TSV download.
- **4 Export Formats** (`format` state in `ExportPrintModal.jsx`: `paper`, `csv`, `json`, `study_guide`):
  1. **Paper (printable)**: Print layout with a live preview (`ExportPaperPreview.jsx`) and two paper types (`paperMode`): `Student Test` (questions only, with examination title block and timing) and `Full Study Pack` (adds the correct key, cognitive trap analysis, and step-by-step rationales). `.page-break` rules in the print CSS prevent awkward page splits across stems and options.
  2. **CSV (`mcat_question_bank.csv`)**: Normalized tabular dataset of questions, options, keys, rubrics, and token metrics for spreadsheet manipulation.
  3. **JSON (`mcat_question_bank.json`)**: Complete hierarchical export preserving metadata, agent evolutions, and psychometric scores.
  4. **Study Guide**: AI-compiled high-yield study guide (`/api/ai/study-guide`) with an additional **Anki flashcard deck (`.tsv`)** download implemented inside `StudyGuideExportPane.jsx`.

### 4.6 Conversational Mentor Explanation View (`MentorExplanationView.jsx`)
Renders pedagogical rationales across three distinct, beautifully styled visual cards:
- **Card 1: Why Option [Key] is Correct (Emerald / Success)**:
  - Tokens: Background `rgba(16, 185, 129, 0.06)` (dark) / `#ecfdf5` (light), border `rgba(16, 185, 129, 0.22)` (dark) / `#a7f3d0` (light), text `--status-success` (`#10b981`), `CheckCircle2` icon.
  - Purpose: Sets the core intuition and step-by-step mathematical or deductive proof demonstrating why the correct key is incontrovertible.
- **Card 2: Why Other Options are Incorrect (Amber / Warning)**:
  - Tokens: Background `rgba(245, 158, 11, 0.06)` (dark) / `#fffbeb` (light), border `rgba(245, 158, 11, 0.22)` (dark) / `#fde68a` (light), text `--status-warning` (`#f59e0b`), `AlertTriangle` icon.
  - Structure: Contains individual itemized sub-cards for each distractor choice (`[A]`, `[C]`, `[D]`) detailing the specific fallacy, miscalculation, or deceptive wording that disqualifies it.
- **Card 3: Primary Cognitive Trap Spotlight (Purple / Tactical Defense)**:
  - Tokens: Background `rgba(139, 92, 246, 0.06)` (dark) / `#f5f3ff` (light), border `rgba(139, 92, 246, 0.25)` (dark) / `#ddd6fe` (light), text `--status-purple` (`#8b5cf6`), `Zap` & `ShieldCheck` icons.
  - Content: Spotlights the dominant MCAT trap from the 25-trap taxonomy (`MCAT_TRAP_DEFINITIONS`), detailing the precise psychological **Error Mechanism** and providing an actionable **Student Defense Strategy** for test day.
- **Top Metadata Trap Badging**:
  - `QuestionCard.jsx` and `QuestionBankTable.jsx` render a persistent purple badge chip in the card header: background `rgba(139, 92, 246, 0.12)`, text `#a78bfa` (dark) / `#6d28d9` (light), border `rgba(139, 92, 246, 0.3)`.
- **Responsive Modes**: Supports `isCompact=true` for staged review decks and full expanded mode for in-depth editorial analysis.

### 4.7 Active Multi-Batch Concurrency Monitor (`ActiveMultiBatchMonitor.jsx`)
- **Global Worker Pool Concurrency Gauge**: Displays live worker slot occupancy against server semaphore limits (`Worker Pool Concurrency`: `N / 4 Slots Busy`, `N Sets Generating in Parallel`, `N Sets Queued for Slots`). The limit `4` is hard-coded in `ActiveMultiBatchMonitor.jsx`, not read from the server.
- **Live Operational Stage Breakdown**: Aggregate status chips distinguishing sets generating in parallel, queued sets, and completed sets.
- **Uncapped Progress Telemetry**: Accurate overall percentage across active batches without artificial progress throttling.
- **Interactive Batch Lifecycle Actions**:
  - **1-Click Batch Stop**: Immediately halts running sub-tasks without deleting saved items.
  - **1-Click Batch Retry**: Relaunches failed or cancelled jobs into the global worker pool.
  - **Cancel All Batches**: Global administrative emergency stop.

### 4.8 Live Stopwatch & Precision Telemetry (`LiveStopwatch.jsx`)
- Renders an active runtime duration stopwatch using `font-family: var(--font-mono)` while a generation run is active.

### 4.9 Top-Level Application Views & Accessible Filter Controls
1. **Question Studio Landing & Guided Wizard (`HeroLanding.jsx`, `GuidedWizard.jsx`)**: The primary authoring portal (`activeTab: 'generator'`), switching smoothly between the minimalist welcome canvas (`HeroLanding.jsx` in `viewMode: 'hero'`) with instant section presets and the streamlined 3-step authoring wizard (`GuidedWizard.jsx` in `viewMode: 'wizard'`). Live generation dispatches 1-job 5-Question Sets or 10-job 50-Question Batches directly to background worker pools with real-time telemetry streaming into the Review Queue (`AiValidatedQuestionsView.jsx`) and Batch Progress dashboard (`BatchActivityView.jsx`) (Navigation Tab: `Create Questions`).
2. **AI Validated Questions View (`AiValidatedQuestionsView.jsx`)**: Dedicated review deck for items generated in background batches that passed the >80 quality threshold, supporting one-click individual or bulk publishing into the primary Question Bank (Navigation Tab: `Review Queue`).
3. **Question Bank View (`QuestionBankView.jsx`, `QuestionBankFilters.jsx`, `QuestionBankTable.jsx`)**: Full-featured searchable, filterable repository strictly consolidated on the canonical **Editorial Cards** view. Legacy table grid mode and view-switcher toolbar controls have been deprecated and removed, dedicating the entire layout to high-density reading cards with inline editing, multi-format CSV/JSON exports, bulk deletion, lifecycle status updates, and repository-wide token analytics (Navigation Tab: `Question Bank`). Supports persistent multi-selection across page boundaries paired with the dedicated `.qbank-clear-selection-btn` button to reset selected sets globally. Toolbar features full WCAG AA compliance with explicit `type="button"` and descriptive `aria-label`s on Select All and Bulk Delete buttons, `aria-pressed={isActive}` on Section and Difficulty filter pills, and standardized `var(--transition-ui)` animations.
4. **Batch Activity View (`BatchActivityView.jsx`, `BatchFiltersBar.jsx`, `BatchCardSummary.jsx`)**: Live and historical monitor displaying running batch jobs, per-job question counts, status indicators, and background worker progress. Features dedicated scope filtering (`All Sets`, `Quick Sets (5 Questions)`, `Full Sets (50 Questions)`) and visual badges distinguishing 1-job mini-batches from 10-job full mock sections (Navigation Tab: `Batch Progress`). Toolbar controls implement `aria-pressed` on Scope tabs and Status tabs, `aria-label="Toggle live auto-sync polling"` on the auto-sync checkbox, and descriptive `aria-label`s on Stop, Resume Sets, and Delete batch action buttons.
5. **Passage Bank View (`PassageBankView.jsx`, `PassageBankFilters.jsx`)**: Full-featured reading passage stimuli repository and editorial workspace. Provides search by passage narrative or concept, section filtering (with instant return-to-catalog reset on tab navigation), server-driven pagination with database sort modes (`newest`, `oldest`, `title`, `questions`), and the interactive **Passage Editorial Desk** (`PassageEditorialDesk.jsx`). Supports in-place editing of passage text and metadata, attachment or discarding of figures (`PassageVisualStimulusEditor.jsx`), inspection of all linked questions (`PassageLinkedQuestionCard.jsx`), and dedicated cascade passage deletion with linked question removal via hoisted `DeletePassageModal` (Navigation Tab: `Passage Bank`). Toolbar features `aria-pressed` on Section filter pills and descriptive `aria-label`s on Reset and "+ New Passage" buttons.

### 4.10 Common Primitives & Accessible Pagination (`PaginationBar.jsx`)
- **Component**: [`frontend/src/components/common/PaginationBar.jsx`](frontend/src/components/common/PaginationBar.jsx) provides a standardized, WCAG AA compliant pagination footer across all list-based views (`QuestionBankView.jsx`, `AiValidatedQuestionsView.jsx`, `BatchActivityView.jsx`, `PassageBankView.jsx`).
- **Features**:
  - Live page range counter (`Showing X-Y of Z`).
  - Configurable page size selector (`PAGE_SIZE_OPTIONS = [15, 30, 50, -1]` in `utils/pagination.js`; `-1` means All).
  - Previous (`ChevronLeft`) and Next (`ChevronRight`) navigation buttons with disabled boundary states.
  - Page number buttons with dynamic window truncation (ellipsis for $> 5$ pages) and active gradient pill indicators.
- **Semantic CSS System Classes** defined across [`frontend/src/styles/`](frontend/src/styles) (aggregated in [`frontend/src/index.css`](frontend/src/index.css)):
  - `.pagination-bar`: Flexbox footer container with surface background and hairline top border.
  - `.view-loading-box`: Centered layout loading indicator container with pulse animation.
  - `.view-empty-state`: Clean empty state box with icon badge and descriptive guidance.
  - `.batch-activity-banner`: Top status information banner for batch execution monitors.

### 4.11 Autonomous Duplicate Resolution & Collision Avoidance
- **Architecture**: Question deduplication is handled autonomously in the backend pipeline (`services/deduplication.py` and `services/batch_resolution.py`) using multi-metric mathematical similarity (token containment, 1-gram & 2-gram Jaccard, SequenceMatcher ratio). Thresholds come from `core/config.py`: hard duplicate `DUPLICATE_HARD_THRESHOLD=0.75`, soft warning `DUPLICATE_SOFT_THRESHOLD=0.60`, API-level check `DUPLICATE_API_THRESHOLD=0.80`.
- **UI status**: The frontend does not currently render duplicate-collision UI. There is no similarity alert bar, `Duplicate Risk (XX%)` badge, `Overridden` shield badge, or comparison modal in `frontend/src` (no references to `duplicate_info` or `is_duplicate_override`). Duplicates are resolved in the background and surface to educators only through batch outcomes (see §4.2). TODO: verify whether a duplicate-collision UI is planned.

### 4.12 Polymorphic Figure & Diagram Viewer (`VisualStimulusViewer.jsx`)
- **Component**: [`frontend/src/components/question/VisualStimulusViewer.jsx`](frontend/src/components/question/VisualStimulusViewer.jsx) provides a publication-grade viewer for AAMC scientific figures, reaction pathways, and experimental charts across all 7 medical and scientific modalities.
- **Intelligent Medical Modality Classification (`visualHelpers.js`)**:
  Stimuli are classified via `detectVisualModality`, dynamically resolving domain badges and presentation metadata via `getModalityMetadata`:
  | Modality Key | UI Badge Label | Badge Token Class | High-Contrast Dark Container |
  | :--- | :--- | :--- | :---: |
  | `radiology` | Radiology (X-Ray / CT / MRI) | `badge-cyan` | Yes (`isDarkContainer: true`) |
  | `histology` | Histopathology (H&E) | `badge-purple` | No |
  | `gross_anatomy` | Gross Anatomy Specimen | `badge-amber` | No |
  | `cellular_microscopy` | Electron Microscopy (TEM/SEM) | `badge-indigo` | Yes (`isDarkContainer: true`) |
  | `physiology_trace` | Physiology / ECG Trace | `badge-rose` | No |
  | `clinical_pathology` | Clinical Pathology Photograph | `badge-emerald` | No |
  | `svg_diagram` | SVG Vector Diagram | `badge-purple` | No |
  | `scientific_diagram` | Scientific Figure | `badge-neutral` | No |
- **High-Contrast Dark Container Contract**:
  Radiology scans and Electron Micrographs require deep black backdrops for clinical authenticity. The viewer enforces `isDarkContainer: true`, rendering the canvas inside `#080c14` with a subtle hairline border (`rgba(255, 255, 255, 0.08)`) even when the user has Alabaster Light mode active, preventing washed-out whites and preserving diagnostic micro-details.
- **Polymorphic Dual-Engine Rendering**:
  - **Programmatic Vector SVG**: Inlines sanitized scalable vector graphics directly into the DOM with crisp, high-DPI rendering, zero blur, and transparent background support.
  - **Neural Visual Illustrations**: Renders OpenAI GPT Image 2.5 and FLUX-2-klein-4b neural image outputs with lazy loading and error fallback.
  - **Passage & Item Polymorphism**: Dynamically extracts stimulus from either standalone question fields or passage-level attributes (`passage_visual_stimulus`).
- **Interactive Action Toolbar & Lightbox Modal (`VisualStimulusLightboxModal.jsx`)**:
  - **Click-to-Zoom Lightbox**: Fullscreen inspection canvas triggered by clicking the figure or the `Maximize2` button. Exposed as `role="dialog"` with `aria-modal="true"`, focus trapping and focus restore via `useFocusTrap`; Escape closes it.
  - **Safe SVG Rendering**: All raw SVG markup is rendered through `SafeSvg` (DOMPurify SVG profile), never directly with `dangerouslySetInnerHTML`.
  - **Pan & Zoom Controls**: Dynamic zoom level scaling from 0.5x to 3.0x with reset control (`RotateCcw`).
  - **Copy SVG Source**: 1-click clipboard button with checkmark feedback to export raw SVG XML for external documentation or publication.
  - **Inline Description Editing**: In editorial mode, renders an editable textarea allowing educators to refine the figure's alt-text and clinical description in real time.

### 4.13 Interactive Practice & Editorial Question Card (`QuestionCard.jsx`)
- **Component**: [`frontend/src/components/question/QuestionCard.jsx`](frontend/src/components/question/QuestionCard.jsx) serves as the primary presentation surface for reviewing, practicing, and editing candidate items.
- **Decomposed Architectural Structure**:
  To maintain high maintainability, reduce re-render cycles, and enforce strict single-responsibility boundaries, `QuestionCard` is decomposed into four specialized subcomponents:
  1. **Question Card Header (`QuestionCardHeader.jsx`)**: Renders the section badge, score badge (`<Award /> final_score/100`), primary cognitive trap chip (`primary_trap`), question index counter, elapsed generation timer, and top action buttons: **Quality Review** (`ShieldCheck` icon, opens psychometric modal) and **Edit** (`Edit3` icon, toggles inline editor).
  2. **Question Card Footer (`QuestionCardFooter.jsx`)**: Renders itemized prompt and completion token counters, calculated micro-dollar inference cost in USD, and primary lifecycle transition actions (e.g., Approve into Bank, Discard).
  3. **Question Options List (`QuestionOptionsList.jsx`)**: Renders the 4 options ($A, B, C, D$) with length-symmetry indicators ($\pm 15\%$), interactive student practice selection, correct key highlighting (emerald), and distractor failure indications (crimson).
  4. **Conversational Mentor Explanations (`MentorExplanationView.jsx`)**: 3-part structured breakdown cards (*Why Correct*, *Why Other Options Incorrect*, *Primary Cognitive Trap Spotlight*).
- **Multi-Tab Workspace Architecture**:
  - **Preview Tab (`preview`)**: Standard student practice canvas with 4-choice interactive selection, immediate feedback, and collapsible mentor explanation cards.
  - **Scorecard Tab (`scorecard`)**: 100-point rubric accordion breaking down the 4 pillars with itemized reviewer feedback.
  - **Details Tab (`telemetry`, labelled `Details`)**: Deep stage JSON inspector displaying raw inference payloads, timing metrics, and token costs.
- **Editorial Quick-Edit Mode (`QuestionInlineEditor.jsx`)**:
  - Toggles in-place inputs for the question stem, optional passage/scenario, 4 options, and explanation without navigating away.
  - Integrates the **Option Length Symmetry Engine** (`calculateOptionSymmetry`), showing live percentage word-count deviations to guarantee options stay within the AAMC $\pm 15\%$ anti-guessability standard.
- **Collision & Override Integration**: Not implemented in the current UI (see §4.11).

### 4.14 Reusable Accessible Confirmation Dialog (`ConfirmationModal.jsx`)
- **Component**: [`frontend/src/components/modals/ConfirmationModal.jsx`](frontend/src/components/modals/ConfirmationModal.jsx) replaces native browser `window.confirm` popups across all application views with an accessible, WCAG AA compliant confirmation dialog.
- **Features & Architecture**:
  - **Focus Trapping**: Integrated with `useFocusTrap` to prevent background tabbing and restore focus upon dismissal.
  - **Keyboard Accelerators**: Full keyboard dismissal on `Escape` key and confirm action triggers.
  - **Theme-Aware Backdrops**: Utilizes `.modal-backdrop-theme` and `.modal-card-theme` respecting both Dark Obsidian and Light Alabaster color palettes.
  - **Semantic Action Variants**: Supports `danger` (`--status-danger`), `warning` (`--status-warning`), and `info` (`--brand-primary`) accents with contextual warning banners.
  - **Contextual Telemetry**: Renders live target count badges and button loading spinners during async mutations.

### 4.15 Passage Deletion & Cascade Warning Modal (`DeletePassageModal.jsx`)
- **Component**: [`frontend/src/components/modals/DeletePassageModal.jsx`](frontend/src/components/modals/DeletePassageModal.jsx) provides a dedicated cascade deletion confirmation dialog when removing shared reading passages from the Passage Bank.
- **Hoisted Single-Instance Architecture**:
  - Mounted as a single hoisted instance in [`PassageBankView.jsx`](frontend/src/views/PassageBankView.jsx), guaranteeing modal availability whether the educator is on the master passage catalog table or inside the active [`PassageEditorialDesk.jsx`](frontend/src/components/passage/PassageEditorialDesk.jsx).
  - Eliminates DOM unmounting, duplicate listeners, and state race conditions during passage navigation.
- **Theme-Aware Backdrops & Containers**:
  - Backdrop: Uses `.modal-backdrop-theme` with `backgroundColor: 'rgba(8, 12, 20, 0.72)'` and `backdropFilter: 'blur(6px)'` (`WebkitBackdropFilter: 'blur(6px)'`).
  - Modal Card: Uses `.modal-card-theme` with `backgroundColor: 'var(--bg-surface-elevated)'`, `borderRadius: 'var(--radius-lg, 16px)'`, `border: '1px solid var(--border-light)'`, and `boxShadow: 'var(--shadow-lg)'`.
  - Header: Styled with `var(--status-danger-bg)` and `var(--status-danger)` accents for high-visibility destructive action confirmation.
- **Features & Architecture**:
  - **Linked Questions Cascade Audit Counter**: Queries and itemizes the exact number of linked questions across all lifecycle statuses (`in_bank`, `ai_validated`, `batch_only`) that will be soft-deleted.
  - **Batch Preservation Notice**: Clearly communicates to educators that soft-deleting the passage removes it and its linked questions from active catalogs while preserving batch progress history intact.
  - **Accessible Focus Management**: Implements `useFocusTrap` to contain keyboard focus, with `Escape` key cancellation and autofocus on the cancel action for safety.

### 4.16 Base Accessible Modal Primitive (`components/common/Modal.jsx`)
- **Component**: [`frontend/src/components/common/Modal.jsx`](frontend/src/components/common/Modal.jsx) provides the underlying accessible dialog framework for all system overlays.
- **Core Contracts**:
  - **React Portal Mounting**: Mounts dialogs directly into `document.body` to avoid parent container CSS clipping (`overflow: hidden`) and z-index stacking conflicts.
  - **Backdrop Blur & Scrim**: Smooth animated backdrop fade with keyboard escape listener.
  - **WCAG AA Focus Trap**: Intercepts `Tab` and `Shift+Tab` keystrokes to ensure focus cycles within the modal boundaries, restoring focus to the origin element upon close.
  - **Standardized Size Constraints**: Accommodates `sm`, `md`, `lg`, `xl`, and `full` widths with automatic vertical scrolling on overflow.

### 4.17 AI Copilot Studio (`QuestionCopilotStrip.jsx`, `question-copilot.css`)
- **Component**: [`frontend/src/components/question/QuestionCopilotStrip.jsx`](frontend/src/components/question/QuestionCopilotStrip.jsx) delivers a context-aware floating educator assistance strip anchored directly to the question generation and review workspace.
- **Design Tokens & Styling**:
  - Backdrop: `var(--bg-surface-elevated)` with hairline border `1px solid var(--border-medium)` and elevation shadow `var(--shadow-lg)`.
  - Border Radius: `var(--radius-full)` (`9999px`) for the floating pill capsule, with `var(--radius-sm)` (`8px`) on popover panels.
  - Accent Gradient: Active states glow with `var(--infynno-gradient)` and `var(--infynno-glow)`.
- **4 Cognitive Tool Actions**:
  - **Prompt Enhancement (`/enhance-instructions`)**: Wand icon, expands rough prompts with authentic AAMC phrasing and distractor rules.
  - **Question Refinement (`/refine-question`)**: Edit icon, proposes targeted fixes for ambiguous wording or flawed distractors.
  - **Passage Audit (`/audit-passage`)**: Shield icon, checks stimulus length, vocabulary density, and scientific validity.
  - **Study Guide (`/study-guide`)**: BookOpen icon, compiles high-yield clinical takeaway sheets.
- **Accessibility & Focus**: Implements full keyboard navigation (`Tab`, `Space`, `Enter`, `Escape` to close active tool popovers) and dynamic `aria-expanded` attributes.

### 4.18 Hero Landing & Quick-Start Presets Desk (`HeroLanding.jsx`, `wizard.css`)
- **Component**: [`frontend/src/components/wizard/HeroLanding.jsx`](frontend/src/components/wizard/HeroLanding.jsx) delivers the welcoming hero canvas that greets educators with immediate action pathways and calibrated AAMC presets.

### 4.19 Passage Editorial Desk & Stimulus Viewer (`PassageEditorialDesk.jsx`, `passage.css`)
- **Component**: [`frontend/src/components/passage/PassageEditorialDesk.jsx`](frontend/src/components/passage/PassageEditorialDesk.jsx) delivers a side-by-side reading passage and linked question editorial workstation.
- **Editorial Typography Standard**:
  - Textarea (`.passage-desk-textarea`) set in **Newsreader Serif** with exact journal proportions: `font-size: 1.05rem`, `line-height: 1.68`, and `letter-spacing: -0.01em` conforming to §3.1.
  - Live word count pill (`.passage-desk-pill-words`) with real-time feedback.
- **Passage Readability & Alignment Card (`.passage-diagnostics-card`)**:
  - Header (`.passage-diagnostics-header`): Displays `Passage Readability & Alignment` with decoupled status pill (`.passage-diagnostics-score`: `Alignment: Strong` / `Alignment: Calibrating`), eliminating internal score math.
  - Metrics Grid (`.passage-diagnostics-grid`): Itemizes Flesch-Kincaid Grade Level, Reading Ease, Empirical Anchors, and Sentence Counts in high-legibility sans-serif.
  - Pedagogical Diagnostics List (`.passage-diagnostics-list`): Itemizes structural recommendations.
- **Linked Question Carousel (`PassageQuestionsCarousel.jsx`, `PassageLinkedQuestionCard.jsx`)**:
  - Right-column stepper carousel with keyboard arrow navigation (`←` / `→`).
  - Score Decoupling: In accordance with §8, question cards display clean status pills (`Ready for Review` / `In Bank`) instead of raw score math.
- **Visual Architecture & Design Tokens**:
  - **Hero Container (`.hero-wrapper` / `.hero-content`)**: Centered layout with vertical rhythm and responsive padding.
  - **Status Pill (`.hero-landing-badge-inline`)**: Anchors brand identity via `InfynnoLogo` and provides a clean interactive link to Infynno Solutions with `aria-label="Infynno Solutions (opens in a new tab)"`.
  - **Headline Typography**: High-contrast heading (`.hero-title`) combining primary text with an electric brand gradient highlight (`var(--infynno-gradient)`).
  - **Dual Primary Actions (`.hero-cta-group`)**:
    - `.hero-primary-cta` (`#btn-hero-get-started`, "Create Questions"): Primary gradient button using `var(--infynno-gradient)` with `var(--text-on-accent)` and trailing `<ArrowRight size={16} aria-hidden="true" />`.
    - `.hero-secondary-cta` (`#btn-hero-open-bank`, "Question Bank"): Elevated secondary action button using `var(--bg-surface-elevated)` and border `var(--border-medium)` with leading `<Database size={15} aria-hidden="true" />`.
  - **Section Presets Dock (`.hero-presets-container`, with `.hero-presets-label` and `.hero-presets-chips`)**:
    - Section presets for **Chemical and Physical (CP)**, **Critical Analysis (CARS)**, **Biological and Biochemical (BB)**, and **Psychological and Social (PS)**.
    - Each preset is an interactive chip (`.hero-preset-chip`) styled with `var(--bg-surface-subtle)`, border `var(--border-subtle)`, and hover elevation.
- **Accessibility & WCAG AA Conformance**:
  - **Native Button Controls**: Every interactive preset and CTA is rendered as a native semantic `<button type="button">`.
  - **Screen Reader Announcements**: Preset buttons carry explicit accessible labels (`aria-label={"Start with " + preset.label + " preset"}`).
  - **Decorative Icon Hiding**: Lucide icons (`ArrowRight`, `Database`, and subject icons) are marked with `aria-hidden="true"` to prevent redundant auditory clutter.
  - **Keyboard Focus Management**: Adheres to `var(--brand-ring)` focus styles on keyboard `Tab` navigation.

### 4.20 Component Memoization & Render Isolation
To ensure high-frequency interface responsiveness during live SSE streaming and large dataset operations, performance-critical components implement explicit render memoization and local state isolation:
1. **Passage Stimuli Row Card (`PassageBankCardRow.jsx`)**: Extracted from `PassageBankTable.jsx` and wrapped in `React.memo`. Internalizes transient `isCopied` clipboard state so clicking "Copy Passage ID" on a passage row isolates re-rendering to that specific card, completely eliminating catalog-wide re-render cascades.
2. **Question Bank Row Card (`QuestionBankCardRow.jsx`)**: Wrapped in `React.memo` to isolate question state mutations and card expansions during Question Bank exploration.
3. **Shared Reading Stimulus Card (`SharedPassageCard.jsx`)**: Wrapped in `React.memo` to stabilize passage typography and layout across preview panels when non-passage parent state updates.
4. **Passage Linked Question Card (`PassageLinkedQuestionCard.jsx`)**: Wrapped in `React.memo` to isolate question card edits within the Passage Editorial Desk.
5. **Batch Monitor Cards (`BatchJobCard.jsx`, `BatchQuestionItem.jsx`)**: Wrapped in `React.memo` to eliminate unnecessary DOM recalculations on sibling jobs during live SSE progress updates and automated retries.

---

## 5. Micro-Animations & Dynamic Feedback

1. **Defined keyframes** (`frontend/src/styles/`): `wizardFadeEnter` (`wizard.css`), `toast-slide-in`, `modalScaleIn`, `fadeIn`, and `spin` (`base.css`). The batch pulse dots (`.batch-monitor-pulse-dot`, `.batch-summary-pulse-dot`, `.batch-job-pulse-dot`) are static colored dots; there are no `conduitFlow` or `shimmer` keyframes in the stylesheets.
2. **Card Lift**: Subtle `-1px` vertical translation on button and interactive card hover paired with `--shadow-md`.
3. **Theme Transition**: Smooth `0.18s ease-out` transition applied to background colors and borders to eliminate abrupt flashes when switching between dark and light themes.

---

## 6. Keyboard Shortcuts & Accessibility Standards

- **WCAG AA Compliance**: All text tokens in both Dark and Light themes maintain a minimum contrast ratio of 4.5:1 for body copy and 3:1 for large text and UI components.
- **Visible Focus Rings**: Custom focus outlines (`outline: 2px solid var(--brand-primary); outline-offset: 2px;`) across all accessible inputs and buttons.
- **Global Keyboard Accelerators**:
  - `⌘ + Enter` / `Ctrl + Enter`: Trigger question or batch generation.
  - `T`: Instant toggle between Dark and Light themes.
  - `/`: Focus the active view's search input (ignored while typing in a form field; wired in the Question Bank, Review Queue, Batch Progress and Passage Bank views).
  - `Escape`: Dismiss the open modal or editor (handled in `useKeyboardShortcuts.js`, works even while typing).

---

## 7. Anti-AI Dash Standard

To ensure human editorial authenticity and eliminate unstyled typographical artifacts:
- Never use unspaced em-dashes (`—`) or en-dashes (`–`) in UI copy, prompts, or generated questions.
- Use clean single hyphens (`-`) flanked by standard spacing when connecting clauses (e.g., `Question Bank - Filter by Section`).

---

## 8. Everyday Human Language Standard

To ensure the product feels thoughtfully crafted by human educators rather than generated by artificial intelligence:
- **No Robotic Self-References**: Never display robotic phrases such as *"Autonomous Pipeline Active"*, *"AI Team Creating Questions"*, *"3 Specialized AI Milestones"*, or *"Fused Draft & Audit (~40% Faster)"* in the interface.
- **Clear Human Navigation Tabs**:
  - `Create Questions` (instead of abbreviated *Create*)
  - `Batch Progress` (instead of *Batches*)
  - `Review Queue` (instead of *Review*)
  - `Question Bank` (instead of *Bank*)
  - `Passage Bank` (instead of *Passages*)
- **Natural Classroom & Editorial Terminology**:
  - *Reading passage* instead of *stimulus vignette*
  - *Independent question* instead of *individual vignette*
  - *Wrong choices & common traps* instead of *cognitive distractor fallacies*
  - *Verified correct answer* instead of *indisputable key*
  - *Quality check & score* instead of *100-pt psychometric audit*
  - *Usage & Cost* instead of *AI Compute Units* or *telemetry*
  - *Figure / Diagram* instead of *Visual Stimulus / AI Diagram / Neural Diagram*
- **Action-Oriented Verbs**:
  - *Create New Questions* or *Create Questions*
  - *Save to Bank* or *Save Question*
  - *Save All Ready* or *Save Selected*
  - *Quality Review*
  - *Discard*
  - *Edit Question*
- **Score Decoupling & Streamlined UI Copy**:
  - Internal rubric score ranges (`>80`, `70-80`) are removed from user-facing badges, stats bars, and cards to keep the UI clean and student-focused.
  - Telemetry badges show clean status labels (*Ready for Review*, *In Bank*, *Replenishing Slot (Trial X/3)*, *3/3 Trials Exhausted*) without internal score math cluttering the visual hierarchy.
  - Unused or noisy auxiliary counters (such as *Discarded* or *Needs Polish* counters on review desks) are pruned in favor of direct actionable items with permanent purge confirmation.
- **Tone of Voice**: Professional, clear, direct, and unpretentious editor voice (seasoned pre-med instructor explaining concepts to colleagues and students without AI filler or marketing hype).
