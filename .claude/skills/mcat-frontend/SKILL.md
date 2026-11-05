---
name: mcat-frontend
description: Conventions for editing the React 19 + Vite frontend of the Question Bank Generator: components, hooks, views, CSS, design tokens, light/dark theme, modals, API client, SSE, print/export. Use for any work under frontend/src, such as adding a component, changing the wizard, fixing styling, adding a filter or table column, wiring a new endpoint into the UI, or "make the UI look right", even if the user does not mention React.
---

# Frontend conventions

Stack: React 19 (JSX, no TypeScript), Vite 8, oxlint, lucide-react icons, plain CSS. Entry `src/main.jsx` -> `App.jsx`.

## Structure
- `views/` top-level screens, lazy-loaded with `React.lazy` (that is why they are not in component barrels).
- `components/<feature>/` (wizard, question, passage, bank, batch, validated, modals, layout, common). Each folder has an `index.js` barrel; export new components there and import from the barrel.
- `hooks/` stateful logic (`useQuestionBank`, `usePassageBank`, `useBatchActivity`, `useGeneratorForm`, `useTheme`, ...). Components stay presentational; fetching and state go in hooks.
- `services/api.js` is the only place that calls `fetch` (base `/api`). Add one function per endpoint, build queries with `buildQuery`, and surface errors through `assertOk`. Keep JSDoc on exports.
- `utils/` pure helpers; `constants/` shared constants, including a copy of the MCAT taxonomy JSON (it must stay in sync with `backend/app/data/mcat_dependent_taxonomy.json`; `tests/test_taxonomy_sync.py` checks this; edit the backend copy and run `pnpm run sync:taxonomy`).

## Sections and layers
- Section labels, codes, badge classes, colors and pacing come from the single `SECTIONS` table in `constants/mcat.js` (use `normalizeSectionId`, `getSectionColor`, `getSectionBadgeClass`, `getSectionPacingSeconds`); never add another per-section map.
- Stacking uses the `--z-sticky/dropdown/modal/toast/overlay` tokens in `styles/tokens.css`, not literal z-index values.
- Export code lives in `utils/export/` (`csv.js`, `json.js`, `htmlDoc.js`, `printPaperCss.js`) behind the `exportUtils.js` shim. `react/exhaustive-deps` is enforced by oxlint.

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
- Copy uses plain everyday language for educators (DESIGN.md "everyday human language"). Use single hyphens only; never em dashes or en dashes in UI text.
- MCAT items always have exactly four options A-D.

## Workflow
1. Make the change following the above.
2. `pnpm lint` (oxlint, zero warnings policy) and `pnpm build`.
3. Look at it in the running app (see mcat-dev-env) in both themes; screenshot if verifying visually.
4. If a prop contract, component, or token changed, update `frontend/README.md` or `DESIGN.md` (see mcat-docs-sync).
- Pure helpers are unit-tested with Vitest (`pnpm --dir frontend run test`, files in `utils/__tests__/`); add a test when you change one. `pnpm --dir frontend run check:css` fails on CSS classes nothing references, so delete styles together with the markup that used them. Status strings come from `BATCH_STATUS`/`JOB_STATUS`/`QUESTION_STATUS` in `constants/mcat.js`, and clipboard/download code from `useCopyToClipboard` and `downloadTextFile`.
