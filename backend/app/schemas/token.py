from __future__ import annotations

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(0, description="Input tokens processed")
    completion_tokens: int = Field(0, description="Output tokens generated")
    total_tokens: int = Field(0, description="Sum of prompt and completion tokens")
    cost_usd: float = Field(
        0.0, description="Estimated total cost in USD based on official pricing"
    )
    duration_ms: int | None = Field(
        None, description="Wall-clock latency of the LLM call in milliseconds, retries included"
    )
    calls: int = Field(0, description="Number of LLM calls this usage covers (0 for mock results)")


def sum_usage(usages: list[TokenUsage], parallel: bool = False) -> TokenUsage:
    """Combines several calls' usage into one.

    Tokens and cost always add up (every call is billed). Latency adds up for sequential calls
    but is the slowest call for calls that ran concurrently (``parallel=True``).
    """
    durations = [u.duration_ms or 0 for u in usages]
    duration = (max(durations, default=0) if parallel else sum(durations)) or None
    return TokenUsage(
        prompt_tokens=sum(u.prompt_tokens for u in usages),
        completion_tokens=sum(u.completion_tokens for u in usages),
        total_tokens=sum(u.total_tokens for u in usages),
        cost_usd=round(sum(u.cost_usd for u in usages), 7),
        duration_ms=duration,
        calls=sum(u.calls for u in usages),
    )
