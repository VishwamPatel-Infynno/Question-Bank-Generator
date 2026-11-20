# Infynno MCAT Question Bank Generator - Frontend

Modern, high-performance web workstation for **Infynno MCAT Question Bank Generator**, engineered by **[Infynno Solutions LLP](https://infynno.com/)** (*"Infinite Innovations"*).

Built with **React 19**, **Vite 8**, **Oxlint**, and a custom dark-glass precision design system.

---

## 🎨 Architectural Overview

The frontend provides an intuitive, real-time command canvas for AAMC MCAT question generation, AI team tracking, and question bank management:

- **Streamlined 3-Step Guided Wizard**: High-velocity authoring workflow consolidating section selection, syllabus disciplines, major units, multi-select subtopic concepts, difficulty calibration (**Low**, **Medium**, **High**), format (Passage-Based vs Independent Single-Choice), streamlined generation scope (**5 Questions** vs **50 Questions**), visual stimuli, and the new **Additional Authoring Instructions** input textarea (with visible `Custom Instructions Active` badge pill) into three focused decision stages (Section & Focus, Level & Format, Review & Launch).
- **2 Calibrated Generation Scopes**:
  - **5 Questions**: 1 Single Job background worker drafting on a shared passage or discrete set (~35-50s) streamed into the AI Validated Bank and Batch Activity Desk with live telemetry.
  - **50 Questions**: Enterprise background multi-job batch (10 concurrent jobs x 5 questions) with automatic AI validation and in-place slot replenishment.
- **Review Queue Withholding Guarantee**: Questions generated during background batches are held in `batch_only` status while the batch is running to keep the "Ready for Review" queue clean of incomplete drafts. Upon clean batch completion, high-scoring questions (>80) are atomically promoted to `ai_validated`.
- **Live Background Batch Activity, In-Memory ETag Cache & Smart Delta Polling**: Real-time batch and worker job monitoring dashboard (`useBatchActivity.js`) featuring dual-cadence adaptive polling (1,500ms during active batch execution / 10,000ms idle when terminal) and instantaneous `window.addEventListener('focus')` tab wakeups. In-memory `etagCache` (`api.js`) transmits `If-None-Match` headers for conditional `304 Not Modified` fast-paths without JSON parsing, paired with a client-side Smart Delta Polling algorithm that compares aggregate batch signatures (`status`, `completed_jobs`, `actual_count`, `failed_jobs`, `total_tokens`) to bypass unnecessary React re-renders and question tree reconciliation when telemetry has not changed.
- **High-Scale Server-Driven Pagination & Persistent Cross-Page Selection**: Standardized `usePagination.js` operating in both client-slice and server-driven modes driven by backend `totalCount` (`GET /api/questions`, `GET /api/passages`), paired with `PaginationBar.jsx` across Question Bank, AI Validated Questions, Batch Activity, and Passage Bank views. Question Bank retains persistent multi-selection across page boundaries with a dedicated `.qbank-clear-selection-btn` to clear selections globally.
- **AI-Validated Editorial Review Desk**: High-speed triage desk where educators inspect, inline-edit, discard, or approve validated questions into the canonical Question Bank.
- **Passage Editorial Desk & Readability Diagnostics**: Dedicated split-pane reading passage workstation (`PassageEditorialDesk.jsx`) rendered in **Newsreader Serif** with medical journal typography (`font-size: 1.05rem; line-height: 1.68; letter-spacing: -0.01em;`), live word count, figure attachment showcase, server-driven pagination with database sort modes (`newest`, `oldest`, `title`, `questions`), and **Passage Readability & Alignment Diagnostics** (`/api/ai/audit-passage`) with decoupled status pills (`Alignment: Strong` / `Alignment: Calibrating`). Linked questions carousel displays decoupled status badges (`Ready for Review` / `In Bank`).
- **Question Quality & Cost Breakdown**: Comprehensive 100-point 4-pillar quality check with itemized token tracking and micro-dollar cost calculations.
- **AI Copilot Studio (`QuestionCopilotStrip.jsx`)**: Real-time context-aware assistant strip anchored to the generation and review workspace, offering in-flight cognitive tools: Prompt Enhancement (`/enhance-instructions`), Question Refinement (`/refine-question`), Passage Audit (`/audit-passage`), and High-Yield Study Guide Generation (`/study-guide`).
- **Comprehensive 6-Format Publication & Export Studio**: Decomposed modal architecture (`ExportPrintModal.jsx`, `ExportScopeSelector.jsx`, `ExportDataFormatPane.jsx`, `StudyGuideExportPane.jsx`) supporting Official Exam Booklet (Standard PDF), Exam Simulation Booklet (Split-Pane AAMC Layout PDF), Comprehensive Study Pack (Annotated Review PDF), Anki Flashcard Deck (TSV with Cloze / QA Tags), Standardized CSV, and Normalized JSON.
- **Publication-Grade Medical & Scientific Visual Studio**: Dedicated figure renderer supporting all 7 clinical and experimental modalities (Radiology, Histopathology, Gross Anatomy, Cellular Electron Microscopy, Physiology/ECG Traces, Clinical Pathology, and SVG Vector Diagrams) with modality badging, autonomous AI visual discretion for standalone and passage questions ("Include Images When Needed"), high-contrast dark container rendering for radiographic clarity, and click-to-zoom accessible lightbox inspection (`VisualStimulusLightboxModal.jsx`).
- **Enterprise Question Bank**: High-speed searchable, filterable repository with multi-format export, lifecycle status management, and copy-to-clipboard actions.
- **WCAG AA Semantic Controls & Universal Focus Rings**: All interactive buttons across wizards, filter bars, cards, and modal dialogs are implemented as native semantic `<button>` elements with explicit `aria-pressed`, `aria-current="step"`, `aria-expanded`, and descriptive `aria-label`s on selection checkboxes and bulk actions. Universal WCAG 2.1 AA `:focus-visible` dual-ring brand glow outline (`2px solid var(--brand-primary)` with 2px offset and `var(--brand-ring)` box shadow) in `accessibility.css` ensures complete keyboard accessibility across all interactive controls.

---

## 📁 Component Directory Structure

```
frontend/src/
├── views/                        # Top-level application view screens (code-split)
│   ├── index.js                  # Views barrel export
│   ├── AiValidatedQuestionsView.jsx # Dedicated review deck for AI-validated items (Review Queue)
│   ├── BatchActivityView.jsx     # Live & historical batch monitoring dashboard (Batch Progress)
│   ├── PassageBankView.jsx       # Reading passages repository & editorial desk (Passage Bank)
│   └── QuestionBankView.jsx      # Verified Question Bank view & editorial cards (Question Bank)
├── components/
│   ├── index.js                  # Centralized barrel export for all components
│   ├── bank/
│   │   ├── index.js              # Question bank barrel export
│   │   ├── QuestionBankFilters.jsx # Section, difficulty (Low/Medium/High), and search filters
│   │   ├── QuestionBankCardRow.jsx # Decomposed high-density question card row
│   │   └── QuestionBankTable.jsx # Canonical Editorial Cards view, batch selection, and actions
│   ├── batch/
│   │   ├── index.js              # Batch barrel export
│   │   ├── ActiveMultiBatchMonitor.jsx # Global concurrency metrics & live multi-batch controller
│   │   ├── BatchCard.jsx         # Summary status card for generation batches & Resume Sets action
│   │   ├── BatchEmptyState.jsx   # Decomposed zero-state canvas for batch activity
│   │   ├── BatchFiltersBar.jsx   # Section, status, and search filters
│   │   ├── BatchHeaderBanner.jsx # Decomposed top summary banner for active batch metrics
│   │   ├── BatchJobCard.jsx      # Per-set worker card with 5-question visual progress strip
│   │   ├── BatchJobTelemetryBadges.jsx # Live telemetry badges (in-progress, completed, needs polish)
│   │   ├── BatchOutcomeCard.jsx  # Final batch outcome and completion summary card
│   │   ├── BatchQuestionActions.jsx # Decomposed question row actions
│   │   ├── BatchQuestionItem.jsx # Staged question item with review modal
│   │   └── BatchStatsHeader.jsx  # High-level aggregate batch statistics
│   ├── common/
│   │   ├── index.js              # Common primitives barrel export
│   │   ├── CustomSelect.jsx      # Accessible custom dropdown select primitive
│   │   ├── EmptyState.jsx        # Decomposed zero-state canvas with customizable icons & actions
│   │   ├── ErrorBoundary.jsx     # Production React error boundary with fallback UI
│   │   ├── FormattedText.jsx     # Inline markdown & cognitive trap chip highlighter
│   │   ├── InfynnoLogo.jsx       # Official corporate vector logo primitive
│   │   ├── LiveStopwatch.jsx     # High-precision live stopwatch timer
│   │   ├── LoadError.jsx         # Standardized network/offline error banner with retry trigger
│   │   ├── Modal.jsx             # Base accessible modal wrapper with focus trap & keyboard escape
│   │   ├── PaginationBar.jsx     # Accessible pagination bar with page range counter & controls
│   │   ├── SafeSvg.jsx           # Renders untrusted SVG markup through DOMPurify (SVG profile); use instead of dangerouslySetInnerHTML
│   │   └── Toast.jsx             # Floating toast notification system
│   ├── layout/
│   │   ├── index.js              # Layout barrel export
│   │   ├── Footer.jsx            # Infynno Solutions LLP attribution & resource footer
│   │   └── Navbar.jsx            # Header with branding, navigation tabs, status, and theme toggle
│   ├── copilot/
│   │   ├── index.js              # Copilot barrel export
│   │   └── QuestionCopilotStrip.jsx # Interactive in-flight educator assistance strip
│   ├── modals/
│   │   ├── index.js              # Modals barrel export
│   │   ├── ConfirmationModal.jsx # Accessible WCAG AA confirmation modal replacing native window.confirm
│   │   ├── DeletePassageModal.jsx# Dedicated passage deletion and cascade warning dialog
│   │   ├── ExportPaperPreview.jsx# Live print layout previewer
│   │   ├── ExportPrintModal.jsx  # 6-format Export Studio modal (Focus Trapped)
│   │   ├── ExportScopeSelector.jsx# Decomposed export scope & filter selector
│   │   ├── ExportDataFormatPane.jsx# Decomposed CSV / JSON / Anki TSV format configuration
│   │   └── StudyGuideExportPane.jsx# Decomposed study guide settings pane
│   ├── passage/
│   │   ├── index.js              # Passage bank barrel export
│   │   ├── PassageBankFilters.jsx# Passage search, section, and difficulty filters
│   │   ├── PassageBankTable.jsx  # Passage stimuli repository table
│   │   ├── PassageBankCardRow.jsx# Memoized passage card row with isolated clipboard state
│   │   ├── PassageEditorialDesk.jsx # Reading passage editor & preview desk
│   │   ├── PassageLinkedQuestionCard.jsx # Linked question card within passage editorial desk
│   │   ├── PassageQuestionsCarousel.jsx # Decomposed questions carousel for linked passages
│   │   └── PassageVisualStimulusEditor.jsx # Passage diagram & figure attachment editor
│   ├── question/
│   │   ├── index.js              # Question review desk barrel export
│   │   ├── AuditIterationTimeline.jsx # Refinement rounds timeline for quality modal
│   │   ├── AuditMetricsGrid.jsx  # Key audit score metrics cards grid
│   │   ├── AuditStageBreakdown.jsx # Model latency and cost breakdown by pipeline stage
│   │   ├── MentorExplanationView.jsx # 3-card mentor explanation view (Intuition, Distractors, Trap)
│   │   ├── QuestionCard.jsx      # Primary student practice & review card orchestrator
│   │   ├── QuestionCardFooter.jsx# Decomposed footer with token metrics, cost in USD & actions
│   │   ├── QuestionCardHeader.jsx# Decomposed header with status badge, score, trap & timers
│   │   ├── QuestionInlineEditor.jsx # In-place authoring & remediation editor
│   │   ├── QuestionOptionsList.jsx# Decomposed 4-choice options renderer with symmetry validation
│   │   ├── QuestionScorecardTab.jsx # 100-point rubric breakdown accordion
│   │   ├── ReviewAuditView.jsx   # 100-point rubric breakdown & token cost modal (Focus Trapped)
│   │   ├── SharedPassageCard.jsx # Shared reading passage stimulus display card
│   │   ├── StageJsonInspector.jsx# Deep stage outcome JSON inspector accordion
│   │   ├── VisualStimulusLightboxModal.jsx # Accessible click-to-zoom fullscreen modal with focus-trapping & pan controls
│   │   └── VisualStimulusViewer.jsx # Publication-grade medical & scientific figure renderer (7 modalities)
│   ├── validated/
│   │   ├── index.js              # AI Validated barrel export
│   │   ├── AiValidatedFiltersBar.jsx # Filters for AI-validated questions
│   │   ├── AiValidatedQuestionCard.jsx # High-density review card integrating SharedPassageCard, Award score badge & Quality Review modal
│   │   └── AiValidatedStatsBar.jsx # Quick-action statistics header
│   └── wizard/
│       ├── index.js              # Wizard barrel export
│       ├── GuidedWizard.jsx      # Streamlined 3-step guided exam generation wizard dock (16px radius)
│       ├── HeroLanding.jsx       # Welcome landing hero header with hoisted HERO_PRESETS & HERO_PRESET_ICONS
│       ├── WizardChoiceCard.jsx  # Accessible decision card primitive with selection checkmark indicator (12px radius)
│       ├── WizardFooterNav.jsx   # Sticky bottom navigation controls and action buttons (Back, Quick Start, Generate)
│       ├── WizardHeaderStepper.jsx # Interactive step tracker and continuous progress bar (Step 1, 2, 3)
│       ├── wizardConstants.js    # STEP_CONFIG, QUICK_PRESETS, and frozen HERO_PRESETS definitions
│       └── steps/                # Streamlined 3-step modular components
│           ├── index.js          # Steps barrel export
│           ├── WizardAdvancedSettings.jsx    # Decomposed collapsible advanced settings drawer
│           ├── WizardReviewSummary.jsx       # Decomposed compact parameter review summary table
│           ├── WizardStep1SectionFocus.jsx   # Step 1: Section, pacing & focus
│           ├── WizardStep2LevelFormat.jsx    # Step 2: Level (Low/Med/High), format & scope (5/50)
│           └── WizardStep3ReviewAdvanced.jsx # Step 3: Streamlined review & launch orchestrator
├── constants/
│   ├── index.js                  # Constants barrel export
│   ├── mcat.js                   # MCAT sections, pacing specs, icons, and fallback topics
│   ├── mcat_dependent_taxonomy.json # AAMC-aligned foundational concepts and skills
│   └── mcatTraps.js              # AAMC cognitive trap definitions and defense strategies
├── hooks/
│   ├── index.js                  # Barrel export for custom hooks
│   ├── useAiValidated.js         # Review Queue data, debounced server-side GIN search query integration, selection, and confirm dialogs
│   ├── useAppState.js            # Centralized view routing, toasts, generator launch & global event broker
│   ├── useBankDeletion.js        # Question Bank single/bulk delete behind one confirm dialog
│   ├── useBatchActivity.js       # Batch monitor polling (in-flight guard, exponential backoff on errors, hidden-tab pause)
│   ├── useBatchFilters.js        # Batch Progress search/status filters and the / shortcut
│   ├── useBatchMutations.js      # Stop, retry, delete, cancel-all and question actions on batches
│   ├── useConfirmModal.js        # Standard accessible confirmation-dialog state
│   ├── useCopyToClipboard.js     # Clipboard copy with a transient copied flag
│   ├── useDebouncedValue.js      # Debounced value for search inputs
│   ├── useExportActions.js       # Download, copy and print actions of the export dialog
│   ├── useFocusTrap.js           # Accessible WCAG AA keyboard focus-trapping hook for modals
│   ├── useGeneratorForm.js       # Wizard form state, DEFAULT_GENERATOR_FORM (with explicit visual_type: 'AI_FLUX_Image'), and toggle helpers
│   ├── useGlobalCounts.js        # Navbar live numbers: running batches, review-queue count, backend status
│   ├── useKeyboardShortcuts.js   # Global hotkeys (⌘↵ to generate on the review step, T to toggle theme, / to focus search, Escape)
│   ├── usePagination.js          # Page index, page size and slicing with filter-driven resets
│   ├── usePassageBank.js         # Passage catalogue, detail, save and delete flows
│   ├── useQuestionBank.js        # Debounced search, adaptive semantic similarity ranking preservation, sorting, and bank fetching
│   ├── useQuestionDraft.js       # Editable copy of a question's text fields with reset
│   ├── useRequestGuard.js        # AbortController guard: only the newest request may write state
│   └── useTheme.js               # Dark/light mode persistence
├── services/
│   ├── index.js                  # Services barrel export
│   └── api.js                    # FastAPI client & SSE stream reader (29 methods: question CRUD/restore, pgvector search, AI Copilot, batches, passages)
├── utils/
│   ├── index.js                  # Utilities barrel export
│   ├── batchHelpers.js           # Calculates current execution stage, badges, descriptions, and refill status for a batch
│   ├── batchJobHelpers.js        # Batch stage, structural-sharing and cache-patch helpers
│   ├── batchPayload.js           # The POST /batches/start payload builder with defense-in-depth CARS visual suppression
│   ├── download.js               # Text file download helper
│   ├── explanationHelpers.js     # Pure JS distractor line & trap parser
│   ├── export/                   # csv.js, json.js, htmlDoc.js (print builder), printPaperCss.js, escape.js, anki.js, index.js
│   ├── formatters.js             # Currency, pacing, and token formatting
│   ├── generatorFormState.js     # Pure wizard form reducers: subtopic toggles, section rules
│   ├── ids.js                    # RFC4122-style random id. crypto.randomUUID only exists in secure contexts (HTTPS/localhost),
│   ├── optionHelpers.js          # Option length parity & calculateOptionSymmetry engine
│   ├── pagination.js             # Shared page-size options
│   ├── passageHelpers.js         # Passage sorting and question counts
│   ├── questionHelpers.js        # Correct answers, images, review pillars, audit cost breakdown, text filter
│   ├── requestGuard.js           # Keeps only the newest of overlapping requests relevant
│   ├── selectHelpers.js          # Keyboard navigation over enabled select options
│   ├── selection.js              # Toggle-id / toggle-all selection helpers
│   ├── taxonomyHelpers.js        # Taxonomy flattening for the wizard
│   ├── trapHelpers.js            # Cognitive trap detection & resolution
│   └── visualHelpers.js          # Intelligent medical modality classification, presentation badges & dark container resolution
├── styles/
│   ├── tokens.css                # Authoritative design tokens (colors, z-index layers --z-*) (Light/Dark obsidian themes)
│   ├── base.css                  # Global reset, scrollbars, buttons, primitives
│   ├── layout.css                # App shell, Navbar, Footer, Toast, Pagination
│   ├── wizard.css                # Hero landing & 3-step authoring wizard
│   ├── question.css              # Master Question Card, Mentor explanation, Stimulus, Scorecard
│   ├── question-copilot.css      # Floating AI Copilot strip styles
│   ├── stage-inspector.css       # Pipeline stage inspector accordion styles
│   ├── study-guide-modal.css     # Decomposed study guide export pane styles
│   ├── batch.css                 # Batch base: concurrency gauge, progress pills
│   ├── batch-activity.css        # Batch Activity Monitor styles
│   ├── batch-card-summary.css    # Batch card summary styles
│   ├── bank.css                  # Canonical Question Bank & AI-Validated Review Queue
│   ├── passage.css               # Passage Bank & Editorial Desk workspace
│   ├── modals.css                # Standardized modal dialogs, Confirmation, Audit modal
│   ├── print.css                 # Exam Paper print preview & @media print styles
│   └── accessibility.css         # Accessible utilities, focus rings, and screen reader styles
├── index.css                     # Aggregator hub importing all domain stylesheets
└── main.jsx                      # Application entry point
```

---

## 🚀 Available Scripts

In the repository root or `frontend` directory, you can run:

```bash
# Start local development server with Hot Module Replacement (HMR)
# Automatically runs 'predev' hook to clean ports 8000 and 5173
pnpm dev

# Run Vitest automated test suite (150 tests across 18 test files, 100% pass rate)
pnpm test
# or from root:
pnpm run test:frontend

# Run Oxlint high-speed linter across frontend sources (0 errors, 0 warnings policy)
pnpm lint

# Check CSS class usage and verify zero unused or missing classes
pnpm check:css

# Synchronize backend taxonomy JSON to frontend constants
pnpm run sync:taxonomy

# Build production bundle with Vite (compiles cleanly)
pnpm build

# Preview the production build locally
pnpm preview
```

---

## 🧪 Automated Testing Suite (Vitest)

The frontend test suite covers pure helpers, formatters, question validation, distractor extraction, batch calculators, multi-format export builders, and custom hooks across **18 test files (150 total tests)**:

| Test Suite | Path | Tests | Coverage |
| :--- | :--- | :-: | :--- |
| `visualHelpers.test.js` | `src/utils/__tests__/` | 16 | Medical visual modality detection & styling metadata |
| `mcat.test.js` | `src/constants/__tests__/` | 19 | Section normalization, score scaling, taxonomy integrity |
| `sharedHelpers.test.js` | `src/utils/__tests__/` | 15 | Pure data transformers, score calculations, badge helpers |
| `batchHelpers.test.js` | `src/utils/__tests__/` | 12 | Batch status aggregation, progress percent calculation |
| `explanationHelpers.test.js` | `src/utils/__tests__/` | 9 | Distractor parsing, trap extractor, mentor explanation structure |
| `export.test.js` | `src/utils/__tests__/` | 9 | CSV formula neutralisation, HTML metacharacter escaping, SVG sanitizing |
| `apiHelpers.test.js` | `src/utils/__tests__/` | 9 | HTTP client error wrapping, payload sanitization, response parsing |
| `formatters.test.js` | `src/utils/__tests__/` | 8 | Date formatting, micro-cent cost displays, duration timers |
| `questionHelpers.test.js` | `src/utils/__tests__/` | 8 | Question draft validation, key resolution, option text checkers |
| `batchJobHelpers.test.js` | `src/utils/__tests__/` | 8 | Visible question counting, actual count resolution, shortfall detection |
| `generatorFormAndPagination.test.js` | `src/utils/__tests__/` | 7 | Page size normalization, subtopic multi-select, select option navigation |
| `questionVisuals.test.js` | `src/utils/__tests__/` | 6 | Image provider detection, SVG sanitizer checks, figure attachment |
| `copilotAndSearchOptimizations.test.js` | `src/utils/__tests__/` | 6 | Slim batch query parameters, toast token contracts, adaptive semantic sort preservation |
| `useAiValidatedHandlers.test.js` | `src/hooks/__tests__/` | 5 | Review queue selection, select-all toggle, passage expansion |
| `ExportComponents.test.jsx` | `src/components/modals/__tests__/` | 4 | Scope selector button rendering, filter state hiding, data format previews |
| `QuestionBankViewHandlers.test.js` | `src/views/__tests__/` | 4 | Filter reset handlers, table row selection toggling, stale selection pruning |
| `requestGuard.test.js` | `src/utils/__tests__/` | 3 | In-flight request deduplication, debounce guards, idempotency keys |
| `usePagination.test.jsx` | `src/hooks/__tests__/` | 2 | Server-driven pagination handling (`totalCount`, page boundaries, and navigation callbacks) |
| **Total** | **18 Suites** | **150** | **100% Pass Rate (~670ms)** |

---

## 💎 Design System & Infynno Brand Tokens

The frontend uses an enterprise precision design system. For exhaustive tokens, typography hierarchies, component contracts, and accessibility specifications, consult the authoritative guide:

👉 **[UI/UX Design System Specification (DESIGN.md)](../DESIGN.md)**

- **Brand Violet**: `#4F30B9`
- **Brand Blue**: `#335ACF`
- **Brand Cyan**: `#1E7ADF`
- **Gradient**: `linear-gradient(135deg, #4F30B9 0%, #335ACF 50%, #1E7ADF 100%)`
- **Typography**: Plus Jakarta Sans (Sans-serif), Newsreader (Serif for reading passages), JetBrains Mono (Monospace)

---

## ♿ Accessibility & Code Quality Contracts

1. **Native Semantic Controls**: Synthetic non-semantic clickable `<div>` elements have been eliminated. All interactive triggers are native `<button type="button">` with focus rings and standard keyboard actuation (`Space` / `Enter`).
2. **Dynamic ARIA State**:
   - `aria-pressed={isActive}` on filter pills (Section, Difficulty, Scope, Status).
   - `aria-current="step"` on the Wizard Header Stepper.
   - `aria-expanded` and `aria-controls` on the Advanced Settings accordion drawer.
   - Explicit `aria-label`s on selection checkboxes and icon buttons across Question Bank, Review Queue, Batch Activity, and Passage Bank.
3. **Zero-Defect Code Hygiene**:
   - **0 TODO**, **0 FIXME**, and **0 `console.log`** statements in source code.
   - Canonical status constants (`QUESTION_STATUS.AI_VALIDATED`) instead of raw strings.
   - Unidirectional symmetric state pairs (`[rawSelectedIds, setRawSelectedIds]`).
   - Zero lint errors or warnings via Oxlint (`0 warnings and 0 errors across 168 files`).
