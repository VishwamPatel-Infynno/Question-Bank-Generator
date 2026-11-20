# Design Audit Plan: Passage Editorial Desk & Stimulus Viewer

> **Status: resolved.** All three findings below are already fixed in the code, so this plan is kept as a historical record. Verified against the current sources:
> - Finding 1: `.passage-desk-textarea` in `frontend/src/styles/passage.css` uses `font-size: 1.05rem`, `line-height: 1.68` and `letter-spacing: -0.01em`.
> - Finding 2: `frontend/src/components/passage/PassageLinkedQuestionCard.jsx` shows a status badge (`In Bank` or `Ready for Review`) instead of the raw score.
> - Finding 3: `frontend/src/components/passage/PassageEditorialDesk.jsx` labels the button `Passage Readability`, has no inline style dictionaries left, and styles the panel with `.passage-diagnostics-card` and related classes in `passage.css`. The score header reads `Alignment: Strong` or `Alignment: Calibrating` (the plan proposed `Passage Alignment: Strong` / `Needs Polish`; the shipped wording differs slightly).
> - The "Evidence" column and line numbers in the table describe the code as it was when the audit was written and no longer match the files.

## Design language
- Audited surface: Passage Editorial Desk & Stimulus Viewer (`frontend/src/views/PassageBankView.jsx`, `frontend/src/components/passage/PassageEditorialDesk.jsx`, `frontend/src/components/passage/PassageLinkedQuestionCard.jsx`, `frontend/src/components/passage/PassageVisualStimulusEditor.jsx`, `frontend/src/styles/passage.css`)
- Design sources: `DESIGN.md` (Section 1: Precision Minimalism & Editorial Typographic Hierarchy; Section 2: Tokens & Surface Architecture; Section 3.1: Font Stacks & Newsreader Serif metrics; Section 8: Everyday Human Language & Score Decoupling)
- Documented decisions:
  - Reading passages rendered in warm, high-legibility serif type (`Newsreader`, font-size `1.05rem`, line-height `1.68`, letter-spacing `-0.01em`) to emulate medical journals and prevent reader fatigue.
  - No robotic self-references (`AI Diagnostics` / `AI Compute Units`); use natural classroom & editorial terminology (*Passage Readability* / *Passage Quality Check*).
  - Score decoupling: internal raw score math (`Score: 88/100`) removed from card headers in favor of clean status labels (*Ready for Review*, *In Bank*).
  - Modular CSS: all surface layouts governed by `tokens.css` and `passage.css` hairline borders (`1px solid var(--border-light)`), eliminating un-tokenized inline style blocks.
- Governing owners and consumers:
  - Component owner: `PassageEditorialDesk.jsx`, `PassageLinkedQuestionCard.jsx`, `PassageVisualStimulusEditor.jsx`
  - Style owner: `frontend/src/styles/passage.css`, `frontend/src/styles/tokens.css`
  - Upstream consumer: `PassageBankView.jsx`
- Explicit exceptions: None documented

---

## Findings

| # | Problem | Evidence | Proposed change | Scope | Confidence |
| - | - | - | - | - | - |
| 1 | **Passage textarea deviates from Newsreader serif design contract** | `DESIGN.md` §3.1 mandates Newsreader Serif set with `font-size: 1.05rem`, `line-height: 1.68`, and `letter-spacing: -0.01em`. In `frontend/src/styles/passage.css` (lines 224-225), `.passage-desk-textarea` is configured with `font-size: 0.98rem; line-height: 1.7;` and lacks `letter-spacing: -0.01em`. | In `frontend/src/styles/passage.css`, update `.passage-desk-textarea` to `font-size: 1.05rem; line-height: 1.68; letter-spacing: -0.01em;` matching the official clinical editorial typographic hierarchy. | `frontend/src/styles/passage.css` | High |
| 2 | **Raw internal score math displayed on linked question carousel card** | `DESIGN.md` §8 mandates Score Decoupling where raw internal score ranges and math (`>80`, `Score: XX/100`) are removed from user-facing badges in favor of clean status labels. In `frontend/src/components/passage/PassageLinkedQuestionCard.jsx` (lines 130-134), it renders `<span className="badge badge-emerald">Score: {question.final_score}/100</span>`. | In `frontend/src/components/passage/PassageLinkedQuestionCard.jsx`, replace the raw score badge with a clean status badge displaying `Ready for Review` (or `In Bank` if `question.status === 'in_bank'`). | `frontend/src/components/passage/PassageLinkedQuestionCard.jsx` | High |
| 3 | **Robotic terminology and un-tokenized inline styles in passage diagnostics panel** | `DESIGN.md` §8 prohibits robotic terminology and mandates everyday editorial phrasing; §2 requires modular CSS tokens (`var(--border-light)`). In `frontend/src/components/passage/PassageEditorialDesk.jsx` (lines 220, 231-267), the button displays `'AI Diagnostics'` and the panel uses 6 nested inline style dictionaries with hardcoded margins and internal score text `Score: {auditData.aamc_alignment_score}/100`. | Update button label to `'Passage Readability'`, extract inline style dictionaries into `.passage-diagnostics-card` and `.passage-diagnostics-meta` classes in `passage.css`, and decouple the score header to `Passage Alignment: Strong` (or `Needs Polish`). | `frontend/src/components/passage/PassageEditorialDesk.jsx`, `frontend/src/styles/passage.css` | High |

---

## Improve first

**Finding #1 (Passage Textarea Newsreader Serif Alignment)** is the highest-leverage improvement. The reading passage is the central cognitive artifact of the Passage Editorial Desk. Aligning the textarea typography (`font-size: 1.05rem`, `line-height: 1.68`, `letter-spacing: -0.01em`) to the exact medical journal contract in `DESIGN.md` §3.1 immediately improves editorial ergonomics, reduces cognitive fatigue, and harmonizes the editor with the rendered `SharedPassageCard`.
