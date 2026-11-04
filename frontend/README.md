# Infynno MCAT Question Bank Generator - Frontend

Modern, high-performance web workstation for **Infynno MCAT Question Bank Generator**, engineered by **[Infynno Solutions LLP](https://infynno.com/)** (*"Infinite Innovations"*).

Built with **React 19**, **Vite 8**, **Oxlint**, and a custom dark-glass precision design system.

---

## 🎨 Architectural Overview

The frontend provides an intuitive, real-time command canvas for AAMC MCAT question generation, AI team tracking, and question bank management:

- **Streamlined 3-Step Guided Wizard**: High-velocity authoring workflow consolidating section selection, syllabus disciplines, major units, multi-select subtopic concepts, difficulty calibration (**Low**, **Medium**, **High**), format (Passage-Based vs Independent Single-Choice), streamlined generation scope (**Practice Set [5 Qs]** vs **Full Exam [50 Qs]**), visual stimuli, and the new **Additional Authoring Instructions** input textarea (with visible `Custom Instructions Active` badge pill) into three focused decision stages (Section & Focus, Level & Format, Review & Launch).
- **2 Calibrated Generation Scopes**:
  - **Practice Set (5 Qs)**: 1 Single Job background worker drafting on a shared passage or discrete set (~35-50s) streamed into the AI Validated Bank and Batch Activity Desk with live telemetry.
  - **Full Exam (50 Qs)**: Enterprise background multi-job batch (10 concurrent jobs x 5 questions) with automatic AI validation and in-place slot replenishment.
- **Review Queue Withholding Guarantee**: Questions generated during background batches are held in `batch_only` status while the batch is running to keep the "Ready for Review" queue clean of incomplete drafts. Upon clean batch completion, high-scoring questions (>90) are atomically promoted to `ai_validated`.
- **Live Background Batch Activity & Telemetry**: Real-time batch and worker job monitoring dashboard displaying live progress, per-job question cards, duplicate audit clusters, and manual or automated in-place refills.
- **AI-Validated Editorial Review Desk**: High-speed triage desk where educators inspect, inline-edit, discard, or approve validated questions into the canonical Question Bank.
- **Question Quality & Cost Breakdown**: Comprehensive 100-point 4-pillar quality check with itemized token tracking and micro-dollar cost calculations.
- **Export & Print Studio**: Professional modal for exporting PDF Exam Papers (with candidate headers and page breaks), Study Packs, CSV, and JSON bundles.
- **Enterprise Question Bank**: High-speed searchable, filterable repository with multi-format export, lifecycle status management, and copy-to-clipboard actions.

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
│   │   └── QuestionBankTable.jsx # Canonical Editorial Cards view, batch selection, and actions
│   ├── batch/
│   │   ├── index.js              # Batch barrel export
│   │   ├── ActiveMultiBatchMonitor.jsx # Global concurrency metrics & live multi-batch controller
│   │   ├── BatchCard.jsx         # Summary status card for generation batches & Resume Sets action
│   │   ├── BatchEmptyState.jsx   # Decomposed zero-state canvas for batch activity
│   │   ├── BatchFiltersBar.jsx   # Section, status, and search filters
│   │   ├── BatchHeaderBanner.jsx # Decomposed top summary banner for active batch metrics
│   │   ├── BatchJobCard.jsx      # Per-set worker card with 5-question visual progress strip (in-bank, done, active, pending) & autonomous retry telemetry
│   │   ├── BatchQuestionItem.jsx # Staged question item with review modal
│   │   └── BatchStatsHeader.jsx  # High-level aggregate batch statistics
│   ├── common/
│   │   ├── index.js              # Common primitives barrel export
│   │   ├── CustomSelect.jsx      # Accessible custom dropdown select primitive
│   │   ├── ErrorBoundary.jsx     # Production React error boundary with fallback UI
│   │   ├── FormattedText.jsx     # Inline markdown & cognitive trap chip highlighter
│   │   ├── InfynnoLogo.jsx       # Official corporate vector logo primitive
│   │   ├── LiveStopwatch.jsx     # High-precision live stopwatch timer
│   │   ├── Modal.jsx             # Base accessible modal wrapper with focus trap & keyboard escape
│   │   ├── PaginationBar.jsx     # Accessible pagination bar with page range counter & controls
│   │   └── Toast.jsx             # Floating toast notification system
│   ├── layout/
│   │   ├── index.js              # Layout barrel export
│   │   ├── Footer.jsx            # Infynno Solutions LLP attribution & resource footer
│   │   └── Navbar.jsx            # Header with branding, navigation tabs, status, and theme toggle
│   ├── modals/
│   │   ├── index.js              # Modals barrel export
│   │   ├── ConfirmationModal.jsx # Accessible WCAG AA confirmation modal replacing native window.confirm
│   │   ├── DeletePassageModal.jsx# Dedicated passage deletion and cascade warning dialog
│   │   ├── ExportPaperPreview.jsx# Live print layout previewer
│   │   └── ExportPrintModal.jsx  # Exam Paper (PDF), Study Pack, CSV and JSON export modal (Focus Trapped)
│   ├── passage/
│   │   ├── index.js              # Passage bank barrel export
│   │   ├── PassageBankFilters.jsx# Passage search, section, and difficulty filters
│   │   ├── PassageBankTable.jsx  # Passage stimuli repository cards & question sets
│   │   ├── PassageEditorialDesk.jsx # Reading passage editor & preview desk
│   │   ├── PassageLinkedQuestionCard.jsx # Linked question card within passage editorial desk
│   │   └── PassageVisualStimulusEditor.jsx # Passage diagram & figure attachment editor
│   ├── question/
│   │   ├── index.js              # Question review desk barrel export
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
│   │   └── VisualStimulusViewer.jsx # SVG & neural visual diagram renderer
│   ├── validated/
│   │   ├── index.js              # AI Validated barrel export
│   │   ├── AiValidatedFiltersBar.jsx # Filters for AI-validated questions
│   │   ├── AiValidatedQuestionCard.jsx # Card with direct bank approval actions
│   │   └── AiValidatedStatsBar.jsx # Quick-action statistics header
│   └── wizard/
│       ├── index.js              # Wizard barrel export
│       ├── GuidedWizard.jsx      # Streamlined 3-step guided exam generation wizard dock
│       ├── HeroLanding.jsx       # Welcome landing hero header
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
│   ├── useAppState.js            # Centralized view routing & global event broker
│   ├── useFocusTrap.js           # Accessible WCAG AA keyboard focus-trapping hook for modals
│   ├── useGeneratorForm.js       # Form state & validation logic
│   ├── useKeyboardShortcuts.js   # Global hotkeys (⌘↵ to generate, A to approve, D to discard, T to toggle theme)
│   ├── usePagination.js          # Client and server pagination calculations and state management
│   ├── useQuestionBank.js        # Debounced search, sorting, and bank fetching
│   └── useTheme.js               # Dark/light mode persistence
├── services/
│   ├── index.js                  # Services barrel export
│   └── api.js                    # FastAPI client & SSE stream reader (28 methods including question restoration, pagination & duplicate override)
├── utils/
│   ├── index.js                  # Utilities barrel export
│   ├── explanationHelpers.js     # Pure JS distractor line & trap parser
│   ├── exportUtils.js            # CSV, JSON, and print-ready HTML doc generators
│   ├── formatters.js             # Currency, pacing, and token formatting
│   ├── optionHelpers.js          # Option length parity & calculateOptionSymmetry engine
│   └── trapHelpers.js            # Cognitive trap detection & resolution
├── index.css                     # Design tokens, electric conduit animations, and typography
└── main.jsx                      # Application entry point
```

---

## 🚀 Available Scripts

In the repository root or `frontend` directory, you can run:

```bash
# Start local development server with Hot Module Replacement (HMR)
# Automatically runs 'predev' hook to clean ports 8000 and 5173
pnpm dev

# Run Oxlint high-speed linter across 90 frontend files (0 errors, 0 warnings policy)
pnpm lint

# Build production bundle with Vite (compiles cleanly)
pnpm build

# Preview the production build locally
pnpm preview
```

---

## 💎 Design System & Infynno Brand Tokens

The frontend uses an enterprise precision design system. For exhaustive tokens, typography hierarchies, component contracts, and accessibility specifications, consult the authoritative guide:

👉 **[UI/UX Design System Specification (DESIGN.md)](file:///Users/infynnosolutions/Desktop/Code/Question%20Bank%20Generator/DESIGN.md)**

- **Brand Violet**: `#4F30B9`
- **Brand Blue**: `#335ACF`
- **Brand Cyan**: `#1E7ADF`
- **Gradient**: `linear-gradient(135deg, #4F30B9 0%, #335ACF 50%, #1E7ADF 100%)`
- **Typography**: Plus Jakarta Sans (Sans-serif), Newsreader (Serif for reading passages), JetBrains Mono (Monospace)
