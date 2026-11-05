"""
_mock_tokens.py — Mock fallback token budgets for offline / LLM-unavailable scenarios.

When a live LLM call fails (no API key, network error, rate-limit), each agent
falls back to a heuristic result and needs plausible token usage numbers for cost
tracking continuity.  All per-agent constants live here so they are maintained in
one place rather than scattered as magic numbers across agent modules.
"""

from __future__ import annotations

# ── Passage Generator ─────────────────────────────────────────────────────────
PASSAGE_GENERATOR_MOCK_PROMPT_TOKENS: int = 380
PASSAGE_GENERATOR_MOCK_COMPLETION_TOKENS: int = 290

# ── Question Generator (single-pass and fused draft-and-critique) ─────────────
QUESTION_GENERATOR_MOCK_PROMPT_TOKENS: int = 450
QUESTION_GENERATOR_MOCK_COMPLETION_TOKENS: int = 320

# ── Reviewer ──────────────────────────────────────────────────────────────────
REVIEWER_MOCK_PROMPT_TOKENS: int = 380
REVIEWER_MOCK_COMPLETION_TOKENS: int = 210

# ── Re-Generator ──────────────────────────────────────────────────────────────
REGENERATOR_MOCK_PROMPT_TOKENS: int = 510
REGENERATOR_MOCK_COMPLETION_TOKENS: int = 390

# ── Blind-Solver ──────────────────────────────────────────────────────────────
BLIND_SOLVER_MOCK_PROMPT_TOKENS: int = 280
BLIND_SOLVER_MOCK_COMPLETION_TOKENS: int = 160


def mock_usage(prompt_tokens: int, completion_tokens: int):
    """Plausible ``TokenUsage`` for a mock/heuristic result, priced like a real call.

    Imported lazily so this constants module stays free of heavy imports.
    """
    from app.agents.base import calculate_token_cost
    from app.schemas import TokenUsage

    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost_usd=calculate_token_cost(prompt_tokens, completion_tokens),
    )
