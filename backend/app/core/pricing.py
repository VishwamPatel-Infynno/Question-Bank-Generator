"""Model price lookup helpers (USD per one million tokens).

The configured provider rates live in ``Settings``; this module holds the fallback tables and the
LiteLLM registry lookup so the pricing logic is data, not a long if-chain inside the settings class.
"""

from __future__ import annotations

import functools
import logging
import re
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
    cache_write: float  # 5-minute TTL (the only TTL the app requests)
    cache_write_1h: float = 0.0  # 1-hour TTL; informational, the app never asks for it


# Claude Haiku 5.5 is billed in two tiers by prompt size (official Anthropic pricing). The
# prompt length counts ALL input tokens, including cache reads and writes.
HAIKU_5_5_LONG_PROMPT_TOKENS = 100_000
HAIKU_5_5_SHORT_RATES = CachedRates(0.10, 0.50, 0.01, 0.125, 0.20)
HAIKU_5_5_LONG_RATES = CachedRates(0.50, 2.50, 0.05, 0.625, 1.00)

# Cached-input multipliers of the base input rate, per provider
ANTHROPIC_CACHE_READ_FACTOR = 0.10  # Claude models without their own table: read = 10% of input
ANTHROPIC_CACHE_WRITE_FACTOR = 1.25  # 5-minute cache write = 125% of input
OPENAI_CACHED_INPUT_FACTOR = 0.50  # gpt-4o-mini: $0.075 cached vs $0.15 input
DEEPINFRA_CACHED_INPUT_FACTOR = 0.03  # DeepSeek V4.1 Flash: $0.006 cached vs $0.20 input

# Where the built-in prices come from. Re-check these pages when updating any default rate
# (config.py defaults, .env.example, docs/TOKEN_TRACKING.md): docs and a test keep them in step.
PRICE_SOURCES: dict[str, dict[str, str]] = {
    "claude-haiku-5-5": {
        "url": "https://platform.claude.com/docs/en/about-claude/pricing",
        "verified": "2026-11-05",
        "note": "USD/MTok; tiers at 100K prompt tokens; cache read/write per the tier table",
    },
    "gpt-4o-mini": {
        "url": "https://developers.openai.com/api/docs/pricing",
        "verified": "2026-11-05",
        "note": "$0.15 in / $0.075 cached / $0.60 out",
    },
    "deepseek-v4.1-flash-1017 (DeepInfra)": {
        "url": "https://deepinfra.com/deepseek-ai/DeepSeek-V4.1-Flash-1017",
        "verified": "2026-11-05",
        "note": "standard $0.20 in / $0.006 cached / $0.60 out; the page also shows a 51% promo "
        "($0.098 / $0.294) with no end date: set the DEEPINFRA_* rates to use it",
    },
    "gpt-image-2.5-flare": {
        "url": "https://developers.openai.com/api/docs/models/gpt-image-2.5-flare",
        "verified": "2026-11-05",
        "note": "token billed: text in $5, image in $8, image out $30 per MTok (batch half); "
        "no per-image price: cost = returned usage tokens",
    },
    "FLUX-2-klein-4b (DeepInfra)": {
        "url": "https://deepinfra.com/black-forest-labs/FLUX-2-klein-4b",
        "verified": "2026-11-05",
        "note": "$0.014 x (width / 1024) x (height / 1024) per image",
    },
}


def haiku_5_5_rates(prompt_tokens: int) -> CachedRates:
    """Tiered rates for Claude Haiku 5.5: prompts above 100K tokens cost more per token."""
    if prompt_tokens > HAIKU_5_5_LONG_PROMPT_TOKENS:
        return HAIKU_5_5_LONG_RATES
    return HAIKU_5_5_SHORT_RATES


_HAIKU_5_5 = re.compile(r"haiku-5[-.]5")


def is_haiku_5_5(target: str) -> bool:
    """True for any spelling of Claude Haiku 5.5 (claude-haiku-5-5, claude-haiku-5.5, prefixed)."""
    return bool(_HAIKU_5_5.search(target.lower()))


@functools.lru_cache(maxsize=256)
def warn_unpriced_model(target: str, assumed_provider: str) -> None:
    """Logs once per model that no price is known, so a wrong estimate is visible in the logs."""
    logger.warning(
        "No price known for model '%s'; costing it with the %s provider's configured rates. "
        "Set the provider's *_COST_PER_MILLION_* values or add the model to core/pricing.py.",
        target,
        assumed_provider,
    )


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
