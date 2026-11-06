# Contributing to Infynno MCAT Question Bank Generator v2.0

Engineered by **[Infynno Solutions LLP](https://infynno.com/)** (*"Infinite Innovations"*).

Thank you for your interest in contributing to the **Infynno MCAT Question Bank Generator** multi-agent AI system!

---

## 🛠️ Development Environment Setup

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 24** & **pnpm 10** (pinned by `packageManager`; Vitest/jsdom need Node 22.12+)
- **Docker & Docker Compose** (for PostgreSQL 16)
- High-Throughput Inference Gateway credentials

### 2. Local Database
```bash
docker compose up -d
```
Verifies that PostgreSQL 16 is running on port `5432` with database `mcat_db`.

### 3. Backend Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
cp .env.example .env
```
Run FastAPI dev server:
```bash
PYTHONPATH=backend uvicorn app.main:app --port 8000 --reload
```

### 4. Frontend Setup
```bash
pnpm install
pnpm dev
```

---

## 🧪 Testing & Verification Guidelines

Before submitting any code changes, ensure all verification suites pass with zero defects (see [`docs/TESTING_AND_QA.md`](docs/TESTING_AND_QA.md) for full test specifications):

```bash
# 1. Backend pytest suite (346 deterministic unit & integration tests across 55 modules; 266 pass offline, 80 DB tests skip cleanly without PostgreSQL; 356 total backend tests)
ACTIVE_LLM_PROVIDER=deepinfra pytest backend/tests -v -m "not live_e2e"

# 2. Backend Python linter and formatting checks (enforcing SIM, RET, B, C4, E, W, F, I, UP)
ruff check .
ruff format --check .

# 3. Frontend Oxlint linter (0 errors, 0 warnings policy across all frontend sources)
pnpm --dir frontend lint

# 4. Frontend production build (compiles cleanly via Vite 8)
pnpm --dir frontend build
pnpm --dir frontend run test        # Vitest unit tests for the pure helpers
pnpm run lint:all                   # ruff (backend) + oxlint (frontend)
pnpm run test:all                   # pytest (backend) + Vitest (frontend)
pnpm --dir frontend run check:css   # fails on CSS classes nothing uses
```

---

## 📐 Multi-Agent Architectural Principles

1. **Strict Quality Threshold**: Questions scoring $\le 90$ must be regenerated up to 3 times by the Re-Generator agent. If still below 90, the workflow must halt and reject the question from the Question Bank. Always compare through `config.passes_quality_gate()` / `config.PASSING_SCORE_THRESHOLD`; never hardcode 90.
   - **Fail Closed**: A question is never accepted unchecked. Reviewer and Blind Solver errors raise `QualityCheckUnavailableError`; mock/heuristic fixtures are used only in offline mode (`LLMNotConfiguredError`, no credentials). Tests that simulate offline mode must raise `LLMNotConfiguredError`.
   - **Deterministic First**: `agents/validators.py` structural checks (4 unique options, valid key, forbidden dashes, ...) run before any LLM review.
2. **Blind-Solver Dual Validation**: Every candidate question is solved blindly without knowing the author's key or explanation. Any key discrepancy or confidence $< 88\%$ triggers automatic remediation to ensure question keys are incontrovertible.
3. **Review Queue Withholding Guarantee**: Questions produced during background batches are held safely in `batch_only` status while the batch is in progress to prevent partial/draft questions from leaking into the reviewer queue. High-scoring items (>90) are atomically promoted to `ai_validated` upon batch completion.
4. **Soft-Deletion & Batch Integrity**: Calling delete on questions sets `is_deleted = true` without decrementing batch progress metrics (`actual_count`), ensuring generation monitoring history remains intact. Questions and linked passages can be restored via `POST /api/questions/{id}/restore`. Soft-deleting a passage cascade-updates all associated questions.
5. **Autonomous 3-Trials Retry Policy**: Background batch runs execute in-flight replenishment retries up to 3 trials per set (`trial_count <= 3`). Manual retry controls are strictly reserved as "Resume Sets" for manually paused runs under 3 trials, returning HTTP 400 when all trials are exhausted.
6. **Custom Authoring Instructions Enforcement**: Educator directives (`additional_instructions`) supplied via Step 3 must be injected into prompt builders with high-priority pedagogical mandate across passage drafting, question drafting, and remediation critique cycles.
7. **Deterministic Token & Cost Math**: All costs must be computed accurately across dual first-class providers:
   - DeepInfra: $0.20 input / $0.60 output per 1M tokens (standard price; cached input 3%). Rates follow the model's own provider: see `docs/TOKEN_TRACKING.md` and `app/core/pricing.py`.
   - Anthropic: Claude Haiku 5.5 ($0.10 in / $0.50 out per 1M), Claude 3.5 Sonnet, Claude 3 Opus, and prompt cache read/write rates.
   - Image: FLUX-2-klein $0.014 per image (scaled by $(\text{width}/1024) \times (\text{height}/1024)$); gpt-image-2.5-flare is token-billed from the returned usage.
8. **Modular Layer Separation**:
   - Routing: `backend/app/api/v1/` (39 endpoint operations)
   - Business/Agent Logic: `backend/app/agents/` (Generator, Blind Solver, Reviewer, Regenerator, Visuals)
   - Data Access Layer: `backend/app/repositories/`
   - Database Entities: `backend/app/models/`
   - Background Services: `backend/app/services/` (`batch_runner.py` with global job semaphores)
   - Frontend: Top-level views (`views/`) with feature-based component directories (`wizard/`, `question/`, `passage/`, `bank/`, `batch/`, `validated/`, `layout/`, `modals/`, `common/`) and centralized hooks/constants.
9. **Multi-Agent Pipeline & Cognitive Fusion**: Step 01 fuses item authoring and 100-point rubric self-critique (`Drafting & Review`) into a single pass. Step 02 executes independent dual validation (`Answer Check`). Step 03 executes remediation (`Question Polish`) for drafts scoring $\le 90$ or failing verification, while Step 04 renders visual stimuli (`Figures & Diagrams`).
10. **AAMC Dual Split-Pane Reading Mode**: Ensures dense scientific research passages and CARS essays are presented side-by-side with sticky scrolling and synchronized candidate review.
11. **Option Symmetry & Anti-AI Standard**: Enforce option length parity (within 3 words, or 20% of the average for longer options; `agents/standards.py`) across strictly 4 options ($A, B, C, D$) and single hyphens (`-`) only; em dashes (`—`) and en dashes (`–`) are strictly forbidden across prompts and generation output.

---

## 📬 Pull Request Workflow

1. Fork the repository and create your branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your commits using standard conventional commit messages:
   - `feat:` new feature or capability
   - `fix:` bug fix
   - `docs:` documentation improvements
   - `refactor:` code restructuring without changing behavior
   - `test:` adding or improving tests
3. Push to your fork and submit a Pull Request targeting `main`.
