## Summary of Changes
Provide a brief summary of what this pull request introduces or fixes.

## Related Issues
Fixes #(issue number)

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Architectural refactoring / cleanup
- [ ] Documentation update
- [ ] CI / Build configuration

## Quality Gate & Testing Checklist
These mirror the jobs in `.github/workflows/ci.yml`:
- [ ] Python linting passes: `ruff check .`
- [ ] Python formatting passes: `ruff format --check .`
- [ ] Pytest test suite passes: `pytest -v` (tests marked `requires_db` need PostgreSQL; note if they were skipped)
- [ ] Frontend linting passes: `pnpm --dir frontend lint`
- [ ] Frontend unit tests pass: `pnpm --dir frontend run test`
- [ ] No unused CSS classes: `pnpm --dir frontend run check:css`
- [ ] Frontend builds cleanly: `pnpm --dir frontend build`
- [ ] Adheres to the strict psychometric quality benchmark (> 80 passing threshold; `PASSING_SCORE_THRESHOLD=80`)
- [ ] No sensitive API keys or credentials committed
- [ ] Applicable documentation updated in `docs/`
