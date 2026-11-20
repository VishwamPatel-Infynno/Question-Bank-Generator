---
name: mcat-frontend
description: Conventions for editing the React 19 + Vite frontend of the Question Bank Generator: components, hooks, views, CSS, design tokens, light/dark theme, modals, API client, SSE, print/export. Use for any work under frontend/src, such as adding a component, changing the wizard, fixing styling, adding a filter or table column, wiring a new endpoint into the UI, or "make the UI look right", even if the user does not mention React.
---

# Frontend conventions

Stack: React 19 (JSX, no TypeScript), Vite 8, oxlint, lucide-react icons, plain CSS. Entry `src/main.jsx` -> `App.jsx`.

## Structure
- `views/` top-level screens, lazy-loaded with `React.lazy` (that is why they are not in component barrels).
- `components/<feature>/` (wizard, question, passage, bank, batch, duplicates, validated, modals, layout, common). Each folder has an `index.js` barrel; export new components there and import from the barrel.
- `hooks/` stateful logic (`useQuestionBank`, `usePassageBank`, `useBatchActivity`, `useGeneratorForm`, `useDuplicateOverride`, `useBatchDuplicateAudit`, `useTheme`, ...). Components stay presentational; fetching and state go in hooks.
- `services/api.js` is the only place that calls `fetch` (base `/api`). Add one function per endpoint, build queries with `buildQuery`, and surface errors through `assertOk`. Keep JSDoc on exports.
- `utils/` pure helpers; `constants/` shared constants, including a copy of the MCAT taxonomy JSON (it must stay in sync with `backend/app/data/mcat_dependent_taxonomy.json`; `tests/test_taxonomy_sync.py` checks this; edit the backend copy and run `pnpm run sync:taxonomy`).

## Sections and layers
- Section labels, codes, badge classes, colors and pacing come from the single `SECTIONS` table in `constants/mcat.js` (use `normalizeSectionId`, `getSectionColor`, `getSectionBadgeClass`, `getSectionPacingSeconds`); never add another per-section map.
- Stacking uses the `--z-sticky`, `--z-dropdown`, `--z-toast` and `--z-overlay` tokens in `styles/tokens.css` (there is no `--z-modal` token), not literal z-index values.
- Export code lives in `utils/export/` (`csv.js`, `json.js`, `escape.js`, `htmlDoc.js`, `printPaperCss.js`) behind `utils/export/index.js` (there is no `exportUtils.js`). `react/exhaustive-deps` is enforced by oxlint.

## Styling
- Source of truth: `DESIGN.md` and `src/styles/tokens.css`. Use CSS custom properties (`var(--bg-surface)`, `var(--border-light)`, `--infynno-gradient`), never raw hex values, so both `[data-theme="light"]` and `[data-theme="dark"]` work with no extra code.
- Put styles in the matching feature file (`wizard.css`, `batch.css`, `question.css`, ...), aggregated by `index.css`. Reuse an existing selector before adding a near-duplicate.
- Fonts: Newsreader for passages, Plus Jakarta Sans for UI, JetBrains Mono for telemetry.
- Print/export rules live in `print.css`; check them when touching exam-paper layouts.

## Behavior and UX rules
- Never use `dangerouslySetInnerHTML` with model or backend content; render SVG through `components/common/SafeSvg` (DOMPurify).
- Polling hooks must guard against overlapping requests and back off on errors (see `useBatchActivity.js`).
- Modals reuse `Modal`/`ConfirmationModal` and `useFocusTrap` for accessible focus handling; do not hand-roll overlays.
- Destructive actions go through `useConfirmModal`.
- Duplicate awareness: read a question's state only through `utils/duplicateHelpers.js` (`getDuplicateState` levels `high`/`similar`/`overridden`/`none`, `hasDuplicateAlert`, `canCompare`); `DUPLICATE_SOFT_THRESHOLD` (0.6) in `constants/mcat.js` mirrors the backend and must stay in step with `config.DUPLICATE_SOFT_THRESHOLD`. Use `components/duplicates/` (`DuplicateRiskBadge`, `DuplicateAlertBar`, `DuplicateCompareModal`) and `useDuplicateOverride` (override is a direct click plus a toast, no extra confirmation); the batch audit is on demand only (`BatchDuplicateAudit` + `useBatchDuplicateAudit`, archive by default), never on a poll.
- Keyboard: `useKeyboardShortcuts` (Escape and Cmd/Ctrl+Enter always; `t`, `/`, `a`, `d` are single-key shortcuts that are ignored with modifiers, on key repeat, while typing in a field and while any modal dialog is open; option `enabled` turns them off). `A` (save, but a hard unoverridden duplicate opens the compare dialog instead) and `D` (discard through the confirm modal) are wired only in the review queue (`useAiValidated`).
- Accessibility primitives: `Modal` closes on the backdrop only when mousedown and click both hit it and takes an optional `ariaLabel` (default "Dialog"); `useFocusTrap` skips hidden and `tabindex=-1` elements; `Toast` keeps a polite live region mounted and uses `role="alert"` for errors; the root `ErrorBoundary` in `main.jsx` offers Retry (page reload).
- `services/api.js` no longer exports `fetchSections`, `fetchTaxonomy`, `fetchRAGContext` or `backfillEmbeddings` (unused); it exports `overrideQuestionDuplicate`, `fetchBatchDuplicateClusters` and `resolveBatchDuplicates`, and keeps `checkQuestionDuplicate`, `fetchHealth` and `fetchConfig`.
- Copy uses plain everyday language for educators (DESIGN.md "everyday human language"). Use single hyphens only; never em dashes or en dashes in UI text.
- MCAT items always have exactly four options A-D.

## Workflow
1. Make the change following the above.
2. `pnpm lint` (oxlint, zero warnings policy) and `pnpm build`.
3. Look at it in the running app (see mcat-dev-env) in both themes; screenshot if verifying visually.
4. If a prop contract, component, or token changed, update `frontend/README.md` or `DESIGN.md` (see mcat-docs-sync).
- Pure helpers are unit-tested with Vitest (`pnpm --dir frontend run test`, files in `__tests__/` folders next to the code: `utils/`, `hooks/`, `constants/`, `views/` and `components/<feature>/`; components are rendered with `react-dom/client` and `act`, no Testing Library); add a test when you change one. `pnpm --dir frontend run check:css` fails on CSS classes nothing references, so delete styles together with the markup that used them. Status strings come from `BATCH_STATUS`/`JOB_STATUS`/`QUESTION_STATUS` in `constants/mcat.js`, and clipboard/download code from `useCopyToClipboard` and `downloadTextFile`.
- Overlapping fetches use `useRequestGuard()` (`utils/requestGuard.js`): `const req = guard.begin()`, pass `req.signal`, and check `req.isCurrent()` before setting state. Difficulty goes through `normalizeDifficulty`/`DIFFICULTY`, empty and failed lists through `EmptyState`/`LoadError`, and the export dialog's actions live in `useExportActions`. `no-undef` is enforced by oxlint, so a missing import fails `pnpm lint`.
