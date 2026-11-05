"""Model price lookup helpers (USD per one million tokens).

The configured provider rates live in ``Settings``; this module holds the fallback tables and the
LiteLLM registry lookup so the pricing logic is data, not a long if-chain inside the settings class.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)

Rate = tuple[float, float]  # (input, output) USD per 1M tokens

# Substring -> rate, checked in order (first match wins). Used when LiteLLM has no entry.
ANTHROPIC_FAMILY_RATES: tuple[tuple[str, Rate], ...] = (
    ("sonnet", (3.00, 15.00)),
    ("opus", (15.00, 75.00)),
    ("haiku", (0.80, 4.00)),
)
ANTHROPIC_DEFAULT_RATE: Rate = (3.00, 15.00)

OPENAI_FAMILY_RATES: tuple[tuple[str, Rate], ...] = (
    ("gpt-4o", (2.50, 10.00)),
    ("o3-mini", (1.10, 4.40)),
    ("o1-mini", (3.00, 12.00)),
    ("o1", (15.00, 60.00)),
    ("gpt-4", (10.00, 30.00)),
    ("gpt-3.5", (0.50, 1.50)),
)

DEEPSEEK_REASONER_RATE: Rate = (0.55, 2.19)


class CachedRates(NamedTuple):
    """USD per 1M tokens including the prompt-cache read and write rates."""

    input: float
    output: float
    cache_read: float
    cache_write: float


# Claude Haiku 5.5 is billed in two tiers by prompt size (official Anthropic pricing).
HAIKU_5_5_LONG_PROMPT_TOKENS = 100_000
HAIKU_5_5_SHORT_RATES = CachedRates(0.10, 0.50, 0.01, 0.125)
HAIKU_5_5_LONG_RATES = CachedRates(0.50, 2.50, 0.05, 0.625)


def haiku_5_5_rates(prompt_tokens: int) -> CachedRates:
    """Tiered rates for Claude Haiku 5.5: prompts above 100K tokens cost more per token."""
    if prompt_tokens > HAIKU_5_5_LONG_PROMPT_TOKENS:
        return HAIKU_5_5_LONG_RATES
    return HAIKU_5_5_SHORT_RATES


def family_rate(target: str, table: tuple[tuple[str, Rate], ...]) -> Rate | None:
    """First table entry whose key appears in the model name, or None."""
    for key, rate in table:
        if key in target:
            return rate
    return None


def is_deepseek_reasoner(target: str) -> bool:
    return (
        "deepseek-r1" in target or "deepseek-reasoner" in target or target.endswith("/deepseek-r1")
    )


def litellm_rate(target: str, provider: str) -> Rate | None:
    """Looks the model up in LiteLLM's cost registry (per-token prices scaled to per-million)."""
    try:
        import litellm

        bare = target.replace(f"{provider}/", "").replace(f"{provider}.", "")
        candidates = [target, bare, f"{provider}/{bare}"]
        if provider == "anthropic":
            candidates.append(f"anthropic.{bare}")
        for cand in candidates:
            info = litellm.model_cost.get(cand)
            if info and "input_cost_per_token" in info and "output_cost_per_token" in info:
                return (
                    round(float(info["input_cost_per_token"]) * 1_000_000.0, 4),
                    round(float(info["output_cost_per_token"]) * 1_000_000.0, 4),
                )
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        logger.debug("litellm pricing lookup failed for %s: %s", target, exc)
    return None
