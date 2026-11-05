---
name: mcat-git-workflow
description: Commit, branch and pull-request conventions for the Question Bank Generator. Use when the user asks to commit, push, create a branch, write a commit message, open or describe a PR, or says "ship it". Ensures verification ran, conventional-commit style is used, and secrets stay out of git.
---

# Git workflow

- Default branch `main`; work on `feature/<name>` or `fix/<name>` branches and PR into `main`.
- Conventional commits, matching history: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`. Subject in imperative mood; body lists the main areas touched (recent commits are broad refactor summaries, but prefer smaller focused commits).
- Before committing, run the mcat-verify gate and include doc updates (mcat-docs-sync) in the same commit.
- Stage specific files, not `git add -A`: `.env`, `.venv`, `node_modules`, `.playwright-mcp`, caches and `testsprite_tests` outputs must not be committed. Check `git status` first.
- Only commit or push when the user asks. Never force-push `main`.
- PRs follow `.github/PULL_REQUEST_TEMPLATE.md`: read it and fill every section; CI runs lint, backend tests (with Postgres 16) and the frontend build.
