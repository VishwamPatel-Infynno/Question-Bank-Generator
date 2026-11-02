# Infynno Design System & UI Specification (DESIGN.md)

> **Infynno Solutions LLP • Infinite Innovations • [infynno.com](https://infynno.com/)**  
> **Product**: Infynno MCAT Question Bank Generator v2.0  
> **Aesthetic Philosophy**: Linear/Vercel-inspired high-precision minimalism, alabaster light mode default with dark obsidian mode, scientific research passages and CARS essays, and animated electric conduit telemetry.

---

## 1. Design Philosophy & Architectural Principles

The Infynno MCAT Question Studio is built for pre-med educators, test-prep authors, and aspiring medical candidates who require focused, fatigue-free reading environments combined with real-time multi-agent observability and official AAMC exam alignment.

1. **Precision Minimalism**: Quiet surfaces, hairline borders (`1px solid var(--border-light)`), subtle elevations, and zero card clutter.
2. **Editorial Typographic Hierarchy**: Clinical reading passages rendered in warm, high-legibility serif type (`Newsreader`, line-height `1.68`), while UI controls and telemetry use modern sans-serif (`Plus Jakarta Sans`) and monospace (`JetBrains Mono`).
3. **Reactive Observability**: Complex multi-agent workflow steps (Generator, Reviewer, Regenerator, Image Engine) are visualized through glowing electric conduit animations without distracting from the editorial workspace.
4. **Seamless Dual-Theme Ergonomics**: First-class alabaster light (`#f8fafc`) default and dark obsidian (`#080c14`) palettes toggled instantly with zero flicker (`T` shortcut or navbar control).
5. **Print & Export Fidelity**: Built-in `@media print` CSS rules and clean paper layouts for professional PDF exam booklets and student study packs.

---

## 2. Color System & Design Tokens

Design tokens are defined as CSS custom properties in [`frontend/src/index.css`](file:///Users/infynnosolutions/Desktop/Code/Question%20Bank%20Generator/frontend/src/index.css) and automatically respond to the `[data-theme="dark"]` and `[data-theme="light"]` attributes on the root `<html>` element.

### 2.1 Infynno Corporate Brand Palette
These core gradient tokens anchor the brand identity across buttons, active tab indicators, and progress tracks:

| Token Name | Hex / Value | Role |
| :--- | :--- | :--- |
| `--infynno-violet` | `#4F30B9` | Primary deep violet anchor |
| `--infynno-blue` | `#335ACF` | Core Infynno royal blue |
| `--infynno-cyan` | `#1E7ADF` | Vibrant electric cyan accent |
| `--infynno-gradient` | `linear-gradient(135deg, #4F30B9 0%, #335ACF 50%, #1E7ADF 100%)` | Interactive primary actions, badges, progress bars |
| `--infynno-glow` | `0 0 16px rgba(51, 90, 207, 0.25)` | Focused element glow |

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

| Status Pillar | Foreground Token | Dark BG / Border | Light BG / Border | Semantic Role |
| :--- | :--- | :--- | :--- | :--- |
| **Pass / Success** | `--status-success` (`#10b981`) | `rgba(16,185,129,0.06)` / `0.22` | `#ecfdf5` / `#a7f3d0` | Psychometric Score > 90, Approved |
| **Warning / Caution** | `--status-warning` (`#f59e0b`) | `rgba(245,158,11,0.06)` / `0.22` | `#fffbeb` / `#fde68a` | Remediation in progress, Borderline draft |
| **Reject / Danger** | `--status-danger` (`#f43f5e`) | `rgba(244,63,94,0.06)` / `0.22` | `#fff1f2` / `#fecdd3` | Score <= 90 after 3 cycles, Discarded draft |
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
- **JetBrains Mono**: Used for token metrics, stopwatch timers, cost calculations, JSON trees, and shortcut badges (`⌘↵`, `A`, `D`).

### 3.2 Spatial Scale & Border Radii
- **Workspace Canvas**: Constrained to `maxWidth: 1040px` centered with auto margins, ensuring consistent eye travel without overly wide reading lines.
- **Radius Hierarchy**:
  - `--radius-xs`: `4px` (micro tags, tooltips)
  - `--radius-sm`: `8px` (buttons, select menus, input fields)
  - `--radius-md`: `12px` (sub-cards, option containers)
  - `--radius-lg`: `16px` (main workspace cards, modal dialogs)
  - `--radius-full`: `9999px` (circular option badges A-D, theme switchers, status pills)

---

## 4. Component Design Specifications

### 4.1 Guided Question Wizard (`GuidedWizard.jsx`)
Streamlined 3-step authoring workflow:
- **Step 1: Section & Focus (`WizardStep1SectionFocus.jsx`)**: Official AAMC exam section selection (CP, CARS, BB, PS) with authentic pacing guides (~96s to ~101s per question), quick-start presets, and granular topic/subtopic syllabus focus. Streamlined to clean interactive cards without marketing slogans or explanatory noise.
- **Step 2: Level & Format (`WizardStep2LevelFormat.jsx`)**: Calibrated challenge level (**Low**, **Medium**, **High**), question format (Passage-Based vs Independent Single-Choice), and 2 calibrated Generation Scopes governed by the unified 5-question Job architecture, presented as streamlined cards without redundant badge pills:
  1. **Practice Set (5 Qs)**: 1 Single Job consisting of 5 questions linked to a shared reading passage (or 5 discretes), dispatched to the background worker pool (~35-50s) with automated AI validation and real-time telemetry streaming into Validated Bank and Batch Activity.
  2. **Full Exam (50 Qs)**: Enterprise background multi-job batch across 10 concurrent worker jobs (5 questions each) governed by the Global Worker Pool with automatic AI validation.
- **Step 3: Review & Advanced Calibration (`WizardStep3ReviewAdvanced.jsx`)**: Clean high-density review interface featuring:
  - **Compact Parameter Summary Table**: Instant tabular overview of selected section, topic, difficulty, and question count.
  - **Scientific Diagrams & Reaction Schemes Card**: Dedicated toggle card for natural science sections with full-card clickability and animated pill switch.
  - **Additional Authoring Instructions Textarea**: Dedicated textarea (`border: 1px solid var(--border-light)`, `background: var(--bg-surface-subtle)`) allowing educators to supply explicit clinical scenarios, Lineweaver-Burk derivation mandates, or custom distractor traps.
  - **Custom Instructions Active Badge**: An animated indicator pill badge (`border: 1px solid var(--border-brand)`, `background: var(--brand-light)`, `color: var(--brand-primary)`) rendered dynamically in the Advanced Settings drawer header when custom instructions are present.
  - **Expandable Advanced Configuration Accordion**: Collapsible drawer controlling cognitive distractor traps, reasoning skills, and targeted student misconception patterns.

### 4.2 Live Batch Activity & Concurrency Monitor (`BatchActivityView.jsx`, `ActiveMultiBatchMonitor.jsx`)
- **Global Concurrency & Worker Pool**: Live telemetry bar showing running background batches, active worker job slots (governed by the 10-worker pool), and real-time execution timers.
- **Batch Card Telemetry (`BatchCard.jsx`)**:
  - Displays batch scope badge (Practice Set 5 Qs vs Full Exam 50 Qs), section accent, target question count, completed slots, and overall completion percentage.
  - Expandable accordion displaying individual job status items with their assigned thematic angles, cognitive traps, and generated question items.
- **Set-Preserving Duplicate Resolution Section (`BatchDuplicateAuditSection.jsx`)**:
  - Interactive clustering panel analyzing pairwise question similarity (>75% threshold).
  - Permanent purge of duplicate drafts with in-place slot replenishment preserving the original set's reading passage and thematic angle.
  - Manual or automatic one-click "Purge & Refill" action ensuring exact target count delivery (e.g. exactly 50 questions across 10 jobs).

### 4.3 Editorial Review Desk & AI-Validated Triage (`AiValidatedQuestionsView.jsx`, `QuestionCard.jsx`)
- **Top Metadata Strip**: Displays section badge, difficulty chip, dual score pills (AAMC Scaled Score `118-132` + 100-pt Audit Score), AAMC Skill badge (SIRS 1-4 / CARS 1-3), cumulative token/cost telemetry, and a dedicated **Primary Cognitive Trap Badge Chip** (`rgba(139, 92, 246, 0.12)` background, purple border, `Tag` icon).
- **Withholding Queue Flow**: Batches hold incomplete or in-flight questions in `batch_only` status. Once a batch completes, questions passing the $\ge 90$ rubric standard atomically advance to `ai_validated` and appear in the review queue.
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

### 4.5 Export & Print Studio (`ExportPrintModal.jsx`, `ExportPaperPreview.jsx`)
- Accessible modal dialog providing live print preview and multi-format export:
  1. **Exam Paper (PDF / Print)**: Formatted with title blocks, candidate name lines, timing guidelines, and `.page-break` rules preventing awkward page splits.
  2. **Comprehensive Study Pack**: Includes full passages, question stems, answers, and in-depth step-by-step rationales.
  3. **CSV Export**: Standardized comma-delimited export ready for LMS and spreadsheet ingestion.
  4. **JSON Bundle**: Full relational representation including evolution histories and token metrics.

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
  - Content: Spotlights the dominant MCAT trap from the 11-trap taxonomy (`MCAT_TRAP_DEFINITIONS`), detailing the precise psychological **Error Mechanism** and providing an actionable **Student Defense Strategy** for test day.
- **Top Metadata Trap Badging**:
  - `QuestionCard.jsx` and `QuestionBankTable.jsx` render a persistent purple badge chip in the card header: background `rgba(139, 92, 246, 0.12)`, text `#a78bfa` (dark) / `#6d28d9` (light), border `rgba(139, 92, 246, 0.3)`.
- **Responsive Modes**: Supports `isCompact=true` for staged review decks and full expanded mode for in-depth editorial analysis.

### 4.7 Active Multi-Batch Concurrency Monitor (`ActiveMultiBatchMonitor.jsx`)
- **Real-Time Telemetry Strip**: Displays live worker pool occupancy against configured limits (`Global Jobs: X / 4`, `Active Inference Calls: Y / 10`).
- **Interactive Batch Lifecycle Actions**:
  - **1-Click Batch Stop**: Immediately halts running sub-tasks without deleting saved items.
  - **1-Click Batch Retry**: Relaunches failed or cancelled jobs into the global worker pool.
  - **Cancel All Batches**: Global administrative emergency stop.

### 4.8 Live Stopwatch & Precision Telemetry (`LiveStopwatch.jsx`)
- Renders an active runtime duration stopwatch using `font-family: var(--font-mono)` with glowing amber pulse animation during active generation runs.

### 4.9 Top-Level Application Views & Authoring Workflows
1. **Question Studio Landing & Guided Wizard (`HeroLanding.jsx`, `GuidedWizard.jsx`)**: The primary authoring portal (`activeTab: 'generator'`), switching smoothly between the minimalist welcome canvas (`HeroLanding.jsx` in `viewMode: 'hero'`) with instant section presets and target pacing badges (~96s to ~101s) and the streamlined 3-step authoring wizard (`GuidedWizard.jsx` in `viewMode: 'wizard'`). Live generation dispatches 1-job Practice Sets (5 Qs) or 10-job Full Exams (50 Qs) directly to background worker pools with real-time telemetry streaming into the Review Queue (`AiValidatedQuestionsView.jsx`) and Batch Progress dashboard (`BatchActivityView.jsx`) (Navigation Tab: `Create Questions`).
2. **AI Validated Questions View (`AiValidatedQuestionsView.jsx`)**: Dedicated review deck for items generated in background batches that passed the >90 quality threshold, supporting one-click individual or bulk publishing into the primary Question Bank (Navigation Tab: `Review Queue`).
3. **Question Bank View (`QuestionBankView.jsx`, `QuestionBankTable.jsx`)**: Full-featured searchable, filterable repository strictly consolidated on the canonical **Editorial Cards** view. Legacy table grid mode and view-switcher toolbar controls have been deprecated and removed, dedicating the entire layout to high-density reading cards with inline editing, multi-format CSV/JSON exports, bulk deletion, lifecycle status updates, and repository-wide token analytics (Navigation Tab: `Question Bank`).
4. **Batch Activity View (`BatchActivityView.jsx`)**: Live and historical monitor displaying running batch jobs, per-job question counts, status indicators, and background worker progress. Features dedicated scope filtering (`All Batches`, `Mini-Batches [1 Job]`, `Full Sections [10 Jobs]`) and visual badges distinguishing 1-job mini-batches from 10-job full mock sections (Navigation Tab: `Batch Progress`).
5. **Passage Bank View (`PassageBankView.jsx`)**: Full-featured reading passage stimuli repository and editorial workspace. Provides search by passage narrative or concept, section filtering (with instant return-to-catalog reset on tab navigation), and the interactive **Passage Editorial Desk** (`PassageEditorialDesk.jsx`). Supports in-place editing of passage text and metadata, attachment or discarding of figures (`PassageVisualStimulusEditor.jsx`), inspection of all linked questions (`PassageLinkedQuestionCard.jsx`), and dedicated cascade passage deletion with linked question removal via hoisted `DeletePassageModal` (Navigation Tab: `Passage Bank`).

### 4.10 Common Primitives & Accessible Pagination (`PaginationBar.jsx`)
- **Component**: [`frontend/src/components/common/PaginationBar.jsx`](file:///Users/infynnosolutions/Desktop/Code/Question%20Bank%20Generator/frontend/src/components/common/PaginationBar.jsx) provides a standardized, WCAG AA compliant pagination footer across all list-based views (`QuestionBankView.jsx`, `AiValidatedQuestionsView.jsx`, `BatchActivityView.jsx`).
- **Features**:
  - Live page range counter displaying `"Showing X - Y of Z items"`.
  - Configurable page size selector (`10`, `25`, `50`, `100` items/page).
  - Previous (`ChevronLeft`) and Next (`ChevronRight`) navigation buttons with disabled boundary states.
  - Page number buttons with dynamic window truncation (ellipsis for $> 5$ pages) and active gradient pill indicators.
- **Semantic CSS System Classes** defined in [`frontend/src/index.css`](file:///Users/infynnosolutions/Desktop/Code/Question%20Bank%20Generator/frontend/src/index.css):
  - `.pagination-bar`: Flexbox footer container with surface background and hairline top border.
  - `.view-loading-box`: Centered layout loading indicator container with pulse animation.
  - `.view-empty-state`: Clean empty state box with icon badge and descriptive guidance.
  - `.batch-activity-banner`: Top status information banner for batch execution monitors.

### 4.11 Duplicate Comparison & Override Modal (`DuplicateComparisonModal.jsx`)
- **Component**: [`frontend/src/components/modals/DuplicateComparisonModal.jsx`](file:///Users/infynnosolutions/Desktop/Code/Question%20Bank%20Generator/frontend/src/components/modals/DuplicateComparisonModal.jsx) provides a side-by-side inspection canvas comparing newly generated candidate items against conflicting Question Bank items.
- **Layout & Structure**:
  - Accessible dialog modal with keyboard focus trapping (`useFocusTrap.js`) and `Escape` key dismissal.
  - Responsive 2-column comparative layout (`grid grid-cols-1 lg:grid-cols-2 gap-6`).
  - **Left Column (Candidate Question Draft)**: Elevated card with primary accent header highlighting the staged item, its difficulty, section, 4 options, and explanation.
  - **Right Column (Existing Bank Item)**: Subtle card displaying the matched historical question from PostgreSQL.
- **Similarity Header & Warning Bar**:
  - Prominent alert bar styled with `--status-warning` (`bg-amber-500/10 border-amber-500/20 text-amber-300`).
  - Visual similarity pill: `⚠️ Duplicate Risk (86%)` indicating composite multi-metric collision score.
  - Match reason explanation (e.g. *"High question stem textual overlap (86%)"*).
- **Interactive Action Matrix**:
  - **"Override & Approve"**: Emerald button (`bg-emerald-600 hover:bg-emerald-500 text-white`) with shield icon that marks the candidate as explicitly approved, sets `is_duplicate_override = true`, and saves it to the Question Bank.
  - **"Regenerate Fresh Angle"**: Indigo button (`bg-indigo-600 hover:bg-indigo-500 text-white`) with refresh icon to re-draft the question from a novel clinical/scientific angle.
  - **"Discard Candidate"**: Rose outlined button (`bg-rose-600/20 border-rose-500/30 text-rose-300 hover:bg-rose-600/30`) with trash icon to purge the duplicate.
- **Badge Specifications**:
  - `⚠️ Duplicate Risk (XX%)`: Amber pill (`rgba(245, 158, 11, 0.12)`, text `#f59e0b`, border `rgba(245, 158, 11, 0.25)`).
  - `🛡️ Overridden`: Royal blue shield pill (`rgba(51, 90, 207, 0.12)`, text `#60a5fa`, border `rgba(51, 90, 207, 0.25)`), rendered in both staging cards and verified bank cards to signify audited editorial exemptions.

### 4.12 Polymorphic Figure & Diagram Viewer (`VisualStimulusViewer.jsx`)
- **Component**: [`frontend/src/components/question/VisualStimulusViewer.jsx`](file:///Users/infynnosolutions/Desktop/Code/Question%20Bank%20Generator/frontend/src/components/question/VisualStimulusViewer.jsx) provides a publication-grade viewer for AAMC scientific figures, reaction pathways, and experimental charts.
- **Polymorphic Dual-Engine Rendering**:
  - **Programmatic Vector SVG**: Inlines sanitized scalable vector graphics directly into the DOM with crisp, high-DPI rendering, zero blur, and transparent background support.
  - **Neural Visual Illustrations**: Renders FLUX-2-klein-4b neural image outputs with lazy loading and error fallback.
  - **Passage & Item Polymorphism**: Dynamically extracts stimulus from either standalone question fields or passage-level attributes (`passage_visual_stimulus`).
- **Interactive Action Toolbar**:
  - **Click-to-Zoom Lightbox**: Fullscreen inspection canvas triggered by clicking the figure or the `Maximize2` button.
  - **Pan & Zoom Controls**: Dynamic zoom level scaling from 0.5x to 3.0x with reset control (`RotateCcw`).
  - **Copy SVG Source**: 1-click clipboard button with checkmark feedback to export raw SVG XML for external documentation or publication.
  - **Inline Description Editing**: In editorial mode, renders an editable textarea allowing educators to refine the figure's alt-text and clinical description in real time.

### 4.13 Interactive Practice & Editorial Question Card (`QuestionCard.jsx`)
- **Component**: [`frontend/src/components/question/QuestionCard.jsx`](file:///Users/infynnosolutions/Desktop/Code/Question%20Bank%20Generator/frontend/src/components/question/QuestionCard.jsx) serves as the primary presentation surface for reviewing, practicing, and editing candidate items.
- **Multi-Tab Workspace Architecture**:
  - **Preview Tab (`preview`)**: Standard student practice canvas with 4-choice interactive selection, immediate feedback, and collapsible mentor explanation cards.
  - **Scorecard Tab (`scorecard`)**: 100-point rubric accordion breaking down the 4 pillars with itemized reviewer feedback.
  - **Telemetry Tab (`telemetry`)**: Deep stage JSON inspector displaying raw inference payloads, timing metrics, and token costs.
- **Editorial Quick-Edit Mode**:
  - Toggles in-place inputs for the question stem, optional passage/scenario, 4 options, and explanation without navigating away.
  - Integrates the **Option Length Symmetry Engine** (`calculateOptionSymmetry`), showing live percentage word-count deviations to guarantee options stay within the AAMC $\pm 15\%$ anti-guessability standard.
- **Collision & Override Integration**:
  - Evaluates `duplicate_info`: displays amber collision warning banner when similarity $\ge 80\%$, and opens `DuplicateComparisonModal` upon clicking "Compare with Existing Question".
  - Displays persistent `🛡️ Overridden` badge when an educator has verified and cleared the candidate for bank storage.

### 4.14 Reusable Accessible Confirmation Dialog (`ConfirmationModal.jsx`)
- **Component**: [`frontend/src/components/modals/ConfirmationModal.jsx`](file:///Users/infynnosolutions/Desktop/Code/Question%20Bank%20Generator/frontend/src/components/modals/ConfirmationModal.jsx) replaces native browser `window.confirm` popups across all application views with an accessible, WCAG AA compliant confirmation dialog.
- **Features & Architecture**:
  - **Focus Trapping**: Integrated with `useFocusTrap` to prevent background tabbing and restore focus upon dismissal.
  - **Keyboard Accelerators**: Full keyboard dismissal on `Escape` key and confirm action triggers.
  - **Theme-Aware Backdrops**: Utilizes `.modal-backdrop-theme` and `.modal-card-theme` respecting both Dark Obsidian and Light Alabaster color palettes.
  - **Semantic Action Variants**: Supports `danger` (`--status-danger`), `warning` (`--status-warning`), and `info` (`--brand-primary`) accents with contextual warning banners.
  - **Contextual Telemetry**: Renders live target count badges and button loading spinners during async mutations.

### 4.15 Passage Deletion & Cascade Warning Modal (`DeletePassageModal.jsx`)
- **Component**: [`frontend/src/components/modals/DeletePassageModal.jsx`](file:///Users/infynnosolutions/Desktop/Code/Question%20Bank%20Generator/frontend/src/components/modals/DeletePassageModal.jsx) provides a dedicated cascade deletion confirmation dialog when removing shared reading passages from the Passage Bank.
- **Hoisted Single-Instance Architecture**:
  - Mounted as a single hoisted instance in [`PassageBankView.jsx`](file:///Users/infynnosolutions/Desktop/Code/Question%20Bank%20Generator/frontend/src/views/PassageBankView.jsx), guaranteeing modal availability whether the educator is on the master passage catalog table or inside the active [`PassageEditorialDesk.jsx`](file:///Users/infynnosolutions/Desktop/Code/Question%20Bank%20Generator/frontend/src/components/passage/PassageEditorialDesk.jsx).
  - Eliminates DOM unmounting, duplicate listeners, and state race conditions during passage navigation.
- **Theme-Aware Backdrops & Containers**:
  - Backdrop: Uses `.modal-backdrop-theme` with `backgroundColor: 'rgba(8, 12, 20, 0.72)'` and `backdropFilter: 'blur(6px)'` (`WebkitBackdropFilter: 'blur(6px)'`).
  - Modal Card: Uses `.modal-card-theme` with `backgroundColor: 'var(--bg-surface-elevated)'`, `borderRadius: 'var(--radius-lg, 16px)'`, `border: '1px solid var(--border-light)'`, and `boxShadow: 'var(--shadow-lg)'`.
  - Header: Styled with `var(--status-danger-bg)` and `var(--status-danger)` accents for high-visibility destructive action confirmation.
- **Features & Architecture**:
  - **Linked Questions Audit Counter**: Queries and itemizes the exact number of linked questions across all lifecycle statuses (`in_bank`, `ai_validated`, `batch_only`) that will be soft-deleted.
  - **Batch Preservation Notice**: Clearly communicates to educators that soft-deleting the passage removes it from active catalogs while preserving batch progress history intact.
  - **Accessible Focus Management**: Implements `useFocusTrap` to contain keyboard focus, with `Escape` key cancellation and autofocus on the cancel action for safety.

---

## 5. Micro-Animations & Dynamic Feedback

1. **Electric Conduit Pulse**:
```css
@keyframes conduitFlow {
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
}
```
2. **Skeleton Shimmer**:
```css
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```
3. **Card Lift**: Subtle `-1px` vertical translation on button and interactive card hover paired with `--shadow-md`.
4. **Theme Transition**: Smooth `0.18s ease-out` transition applied to background colors and borders to eliminate abrupt flashes when switching between dark and light themes.

---

## 6. Keyboard Shortcuts & Accessibility Standards

- **WCAG AA Compliance**: All text tokens in both Dark and Light themes maintain a minimum contrast ratio of 4.5:1 for body copy and 3:1 for large text and UI components.
- **Visible Focus Rings**: Custom focus outlines (`outline: 2px solid var(--brand-primary); outline-offset: 2px;`) across all accessible inputs and buttons.
- **Global Keyboard Accelerators**:
  - `⌘ + Enter` / `Ctrl + Enter`: Trigger question or batch generation.
  - `T`: Instant toggle between Dark and Light themes.
  - `/`: Immediately focus the Question Bank search input.
  - `A`: Approve active staged question.
  - `D`: Discard active staged question.
  - `Escape`: Close any open dialog modal (Audit View, Stage JSON, Export Studio).

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
  - *Save to Bank* or *Save Question*
  - *Save All Ready* or *Save Selected*
  - *Discard*
  - *Edit Question*
- **Tone of Voice**: Professional, clear, direct, and unpretentious editor voice (seasoned pre-med instructor explaining concepts to colleagues and students without AI filler or marketing hype).
