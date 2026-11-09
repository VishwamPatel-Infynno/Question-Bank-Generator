from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from collections.abc import Callable
from typing import Any, TypeVar

import json_repair

from app.core import pricing
from app.core.config import config
from app.schemas import TokenUsage
from app.schemas.token import sum_usage

logger = logging.getLogger(__name__)

T = TypeVar("T")

_litellm_module: Any = None


def _get_litellm() -> Any:
    """Imports litellm on first use (it is slow to import and not needed to boot or run tests)."""
    global _litellm_module
    if _litellm_module is None:
        os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
        os.environ.setdefault("LITELLM_TELEMETRY", "False")
        import litellm

        litellm.suppress_debug_info = True
        litellm.drop_params = True
        litellm.local_model_cost_map = True
        _litellm_module = litellm
    return _litellm_module


def __getattr__(name: str) -> Any:
    # Keeps `app.agents.base.litellm` working (tests patch it) without an eager import
    if name == "litellm":
        return _get_litellm()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_global_llm_semaphore: asyncio.Semaphore | None = None


def get_global_llm_semaphore() -> asyncio.Semaphore:
    """Returns the singleton global LLM concurrency semaphore, lazily initialized."""
    global _global_llm_semaphore
    if _global_llm_semaphore is None:
        _global_llm_semaphore = asyncio.Semaphore(config.GLOBAL_MAX_CONCURRENT_LLM_CALLS)
    return _global_llm_semaphore


def clean_json_text(text: str) -> str:
    """
    Extract and sanitize a JSON payload from LLM output.

    Handles markdown code fences (```json ... ``` or bare ``` ... ```),
    strips leading/trailing non-JSON text, and locates the outermost
    ``{...}`` or ``[...]`` structure.

    Args:
        text: Raw LLM response string that may contain surrounding prose
            or markdown formatting.

    Returns:
        A cleaned string ready for ``json.loads`` or ``json_repair.loads``.
    """
    text = text.strip()

    # Check for markdown code fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()
    elif text.startswith("```"):
        lines = text.splitlines()
        if len(lines) > 1 and lines[0].startswith("```"):
            text = "\n".join(lines[1:]).strip()

    # Try to locate the outermost { ... } or [ ... ]
    start_brace = text.find("{")
    start_bracket = text.find("[")

    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        end_brace = text.rfind("}")
        if end_brace != -1 and end_brace > start_brace:
            text = text[start_brace : end_brace + 1]
    elif start_bracket != -1:
        end_bracket = text.rfind("]")
        if end_bracket != -1 and end_bracket > start_bracket:
            text = text[start_bracket : end_bracket + 1]

    return text


def safe_json_loads(text: str) -> Any:
    """
    Safely parses JSON from LLM outputs with multi-stage resilient parsing:
    1. Standard json.loads with strict=False (handles unescaped control characters like literal \\n and \\t inside strings)
    2. json_repair on cleaned text (fixes missing quotes, unescaped quotes, trailing commas, truncated brackets)
    3. json_repair on raw uncleaned text
    4. Sanitization of non-printable control characters (< 0x20 except \\t, \\n, \\r) with strict=False retry
    """
    cleaned = clean_json_text(text)

    # 1. Primary: json.loads with strict=False
    try:
        return json.loads(cleaned, strict=False)
    except ValueError as e1:
        logger.debug("Primary json.loads failed: %s. Attempting resilient fallbacks...", e1)
        # 2. Resilient fallback: json_repair (on the cleaned text, then on the raw text)
        for candidate_text, label in ((cleaned, "cleaned"), (text, "raw")):
            try:
                res = json_repair.loads(candidate_text)
                if isinstance(res, (dict, list)) and res:
                    return res
            except Exception as repair_err:  # third-party parser: any failure means "try the next"
                logger.debug("json_repair on %s text failed: %s", label, repair_err)

        # 3. Clean low ASCII control characters (0x00-0x08, 0x0B, 0x0C, 0x0E-0x1F) and retry
        try:
            sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
            return json.loads(sanitized, strict=False)
        except ValueError as sanitize_err:
            logger.debug("json.loads after control-char sanitization failed: %s", sanitize_err)

        raise e1


def _usage_from_response(
    response: Any, model: str, *, duration_ms: int | None = None
) -> TokenUsage:
    """Billed usage of one completion, cache tokens included (also for a truncated retry)."""
    usage_obj = getattr(response, "usage", None)
    prompt_tokens = int(getattr(usage_obj, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage_obj, "completion_tokens", 0) or 0)
    total_tokens = int(
        getattr(usage_obj, "total_tokens", prompt_tokens + completion_tokens)
        or (prompt_tokens + completion_tokens)
    )
    cache_read_tokens, cache_creation_tokens = _cache_tokens_from_usage(usage_obj)
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd=calculate_token_cost(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            cache_read_tokens=cache_read_tokens,
            cache_creation_tokens=cache_creation_tokens,
        ),
        duration_ms=duration_ms,
        calls=1,
    )


def normalize_model_for_litellm(model: str) -> str:
    """
    Normalizes Anthropic model identifiers so LiteLLM provider detection never fails.
    e.g. 'claude-3-5-sonnet-20241022' -> 'anthropic/claude-3-5-sonnet-20241022',
    while preserving bare names that LiteLLM already knows natively (like 'claude-haiku-5-5').
    """
    m = model.strip()
    if config.is_anthropic_model(m):
        if m.startswith(("anthropic/", "anthropic.")):
            return m
        try:
            _get_litellm().get_llm_provider(m)
            return m
        except Exception:
            return f"anthropic/{m}"
    if config.is_openai_model(m):
        if m.startswith(("openai/", "openai.")):
            return m
        try:
            _get_litellm().get_llm_provider(m)
            return m
        except Exception:
            return f"openai/{m}"
    return m


def calculate_token_cost(
    prompt_tokens: int,
    completion_tokens: int,
    model: str | None = None,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    """
    Calculate USD expenditure based on exact provider rates:
    - Claude Haiku 5.5 Tiered Rates (from official Anthropic pricing):
        - <= 100K prompt tokens: $0.10 in / $0.50 out / $0.01 cache read / $0.125 cache write
        - > 100K prompt tokens: $0.50 in / $2.50 out / $0.05 cache read / $0.625 cache write
    - Other Claude Models (Sonnet, Opus, etc.):
        - Rates from config.get_default_pricing_rates(target_model)
        - Universal Anthropic prompt caching:
            - Cache Read: 10% of base in_rate
            - Cache Write: 125% of base in_rate
    - OpenAI Models (gpt-4o-mini, gpt-4o, o3-mini, o1):
        - Rates from config.get_default_pricing_rates(target_model)
        - Universal OpenAI prompt caching: 50% discount on cached prompt tokens
    - DeepInfra / Custom Rates:
        - Rates from config.get_default_pricing_rates(target_model): the configured DeepInfra
          rates ($0.20 in / $0.60 out per 1M tokens standard price)
        - Cached prompt tokens at 3% of the input rate (DeepSeek V4.1 Flash cached $0.006)
    Rates follow the model's provider, never the active provider (see core/pricing.py for sources).
    """
    target_model = model or config.DEFAULT_TEXT_MODEL
    # Billing follows the model's own provider; a runtime override only re-prices the active one
    has_rate_override = config.rate_override_applies(target_model)
    provider = config.get_active_provider(target_model)
    per_million = 1_000_000.0

    if provider == "anthropic":
        if pricing.is_haiku_5_5(target_model) and not has_rate_override:
            tier = pricing.haiku_5_5_rates(prompt_tokens)
            in_rate, out_rate = tier.input, tier.output
            cache_read_rate, cache_creation_rate = tier.cache_read, tier.cache_write
        else:
            in_rate, out_rate = config.get_default_pricing_rates(target_model)
            cache_read_rate = in_rate * pricing.ANTHROPIC_CACHE_READ_FACTOR
            cache_creation_rate = in_rate * pricing.ANTHROPIC_CACHE_WRITE_FACTOR

        base_prompt_tokens = max(0, prompt_tokens - cache_read_tokens - cache_creation_tokens)
        return round(
            (base_prompt_tokens / per_million) * in_rate
            + (completion_tokens / per_million) * out_rate
            + (cache_read_tokens / per_million) * cache_read_rate
            + (cache_creation_tokens / per_million) * cache_creation_rate,
            7,
        )

    in_rate, out_rate = config.get_default_pricing_rates(target_model)
    # OpenAI and DeepInfra bill cached prompt tokens at a discount and report no cache writes
    cached_factor = (
        pricing.OPENAI_CACHED_INPUT_FACTOR
        if provider == "openai"
        else pricing.DEEPINFRA_CACHED_INPUT_FACTOR
    )
    cached_tokens = min(max(0, cache_read_tokens), prompt_tokens)
    return round(
        ((prompt_tokens - cached_tokens) / per_million) * in_rate
        + (cached_tokens / per_million) * in_rate * cached_factor
        + (completion_tokens / per_million) * out_rate,
        7,
    )


class LLMNotConfiguredError(ValueError):
    """No API credentials are configured, so the agents may fall back to offline heuristics."""


def require_offline_mode(err: LLMNotConfiguredError) -> None:
    """Call inside ``except LLMNotConfiguredError``: re-raises unless OFFLINE_MODE allows fixtures."""
    if not config.OFFLINE_MODE:
        raise err


class QualityCheckUnavailableError(RuntimeError):
    """A quality-control agent (reviewer or blind solver) could not produce a trustworthy result.

    The pipeline fails closed on this error: an item must never be accepted unchecked.
    """


def _system_content(model: str, system_prompt: str) -> str | list[dict[str, Any]]:
    """Marks the static system prompt as cacheable for Anthropic models.

    System prompts are identical across calls, so cached reads cost a fraction of normal input
    tokens. Providers with automatic prefix caching (OpenAI, DeepInfra) need no marker. Prompts
    below the provider's minimum cacheable size are simply not cached, which is harmless.
    """
    if config.ENABLE_PROMPT_CACHING and config.is_anthropic_model(model):
        return [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
    return system_prompt


def _resolve_api_key(model: str, explicit_key: str | None) -> str:
    """
    Resolves the API key for the requested model.

    Priority order:
    1. Explicitly passed ``explicit_key`` (caller override)
    2. Anthropic key from Settings / environment if model is Anthropic
    3. DeepInfra key from Settings / environment if model is DeepInfra
    4. Raises ValueError if corresponding key is not configured.
    """
    if explicit_key:
        return explicit_key

    if config.is_anthropic_model(model):
        key = config.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise LLMNotConfiguredError(
                "Anthropic API Key is required. Please set ANTHROPIC_API_KEY in your .env file."
            )
        return key

    if config.is_openai_model(model):
        key = config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        if not key:
            raise LLMNotConfiguredError(
                "OpenAI API Key is required. Please set OPENAI_API_KEY in your .env file."
            )
        return key

    key = config.DEEPINFRA_API_KEY or os.getenv("DEEPINFRA_API_KEY")
    if not key:
        raise LLMNotConfiguredError(
            "AI Gateway API Key is required. Please configure it in Settings or set the server environment key."
        )
    return key


def _as_token_count(raw: Any) -> int:
    """A provider token counter as an int; anything that is not a plain number counts as zero."""
    return int(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else 0


def _cache_tokens_from_usage(usage_obj: Any) -> tuple[int, int]:
    """(cache-read, cache-creation) prompt tokens reported by the provider, zero when absent.

    Anthropic reports ``cache_read_input_tokens``/``cache_creation_input_tokens``; OpenAI-style
    providers report ``prompt_tokens_details.cached_tokens`` (an object or a dict).
    """
    cache_read = _as_token_count(getattr(usage_obj, "cache_read_input_tokens", 0))
    details = getattr(usage_obj, "prompt_tokens_details", None)
    if details is not None and type(details).__name__ not in ("MagicMock", "Mock"):
        cached_val = (
            details.get("cached_tokens", 0)
            if isinstance(details, dict)
            else getattr(details, "cached_tokens", 0)
        )
        cache_read = cache_read or _as_token_count(cached_val)
    cache_creation = _as_token_count(getattr(usage_obj, "cache_creation_input_tokens", 0))
    return cache_read, cache_creation


def _classify_llm_error(err: Exception) -> str | None:
    """How a failed LLM call should be retried.

    ``"transient"`` (rate limit, overloaded provider, timeout) backs off exponentially,
    ``"connection"`` retries once after a short pause, ``None`` is not retried.
    """
    err_str = str(err).lower()
    is_rate_limit = "429" in err_str or "rate limit" in err_str or "too many requests" in err_str
    is_overloaded = (
        re.search(r"\b(500|502|503|504|529)\b", err_str) is not None
        or "service unavailable" in err_str
        or "bad gateway" in err_str
        or "internal server error" in err_str
        or "overloaded" in err_str
    )
    is_timeout = (
        "timeout" in err_str
        or "timed out" in err_str
        or isinstance(err, (asyncio.TimeoutError, TimeoutError))
    )
    if is_rate_limit or is_overloaded or is_timeout:
        return "transient"
    if "connection" in err_str:
        return "connection"
    return None


def _get_available_fallback_models(primary_model: str) -> list[str]:
    """Builds an ordered list of candidate models for which valid API credentials exist."""
    candidates = [primary_model]
    cascade = config.get_effective_cascade(primary_model)
    for model_name in cascade:
        if model_name != primary_model and model_name not in candidates:
            try:
                if _resolve_api_key(model_name, None):
                    candidates.append(model_name)
            except Exception as key_err:
                logger.debug("Skipping fallback model '%s': %s", model_name, key_err)
                continue
    return candidates


async def call_llm(
    prompt: str,
    system_prompt: str,
    model: str | None = None,
    api_key: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> tuple[str, TokenUsage]:
    """Universal LLM caller via LiteLLM targeting DeepInfra or Anthropic models with global throttling & backoff."""
    initial_model = model or config.DEFAULT_TEXT_MODEL
    effective_max_tokens = max_tokens if max_tokens is not None else config.DEFAULT_MAX_TOKENS
    effective_temperature = temperature if temperature is not None else config.DEFAULT_TEMPERATURE

    # If caller explicitly provided an api_key, stick to that specific model
    candidate_models = [initial_model] if api_key else _get_available_fallback_models(initial_model)

    last_error: Exception | None = None
    semaphore = get_global_llm_semaphore()
    call_started = time.perf_counter()

    for candidate in candidate_models:
        try:
            resolved_key = _resolve_api_key(candidate, api_key)
        except Exception as key_err:
            last_error = key_err
            continue

        kwargs: dict[str, Any] = {
            "model": normalize_model_for_litellm(candidate),
            "messages": [
                {"role": "system", "content": _system_content(candidate, system_prompt)},
                {"role": "user", "content": prompt},
            ],
            "temperature": effective_temperature,
            "max_tokens": effective_max_tokens,
            "request_timeout": max(60.0, effective_max_tokens / 25),
            "num_retries": 0,  # retries are handled once, by the loop below
        }
        if resolved_key:
            kwargs["api_key"] = resolved_key
        if config.is_anthropic_model(candidate):
            kwargs["thinking"] = {"type": "disabled"}

        max_retries = config.LLM_MAX_RETRIES
        # Usage of truncated completions that were retried: those calls were billed too
        truncated_usage: list[TokenUsage] = []
        for attempt in range(max_retries + 1):
            try:
                # Hold a global LLM slot only for the call itself, never while backing off.
                async with semaphore:
                    response = await _get_litellm().acompletion(**kwargs)
                content = (response.choices[0].message.content or "").strip()
                if not content:
                    finish_reason = getattr(response.choices[0], "finish_reason", "unknown")
                    raise ValueError(
                        f"Model {candidate} returned empty content (finish_reason: {finish_reason})"
                    )

                # A cut-off completion is never trustworthy: json_repair would silently
                # "complete" a truncated explanation. Retry with a larger budget instead.
                if getattr(response.choices[0], "finish_reason", None) == "length":
                    current_max = int(kwargs["max_tokens"])
                    ceiling = config.LLM_MAX_TOKENS_CEILING
                    if current_max < ceiling:
                        truncated_usage.append(_usage_from_response(response, candidate))
                        kwargs["max_tokens"] = min(ceiling, current_max * 2)
                        logger.warning(
                            "Output truncated at %s tokens on '%s'. Retrying with max_tokens=%s.",
                            current_max,
                            candidate,
                            kwargs["max_tokens"],
                        )
                        continue
                    raise ValueError(
                        f"Model {candidate} output was truncated at {current_max} tokens"
                    )

                usage = _usage_from_response(
                    response,
                    candidate,
                    duration_ms=int((time.perf_counter() - call_started) * 1000),
                )
                provider_label = config.get_active_provider(candidate).capitalize()
                logger.info(
                    "LLM Call Succeeded [%s via %s]: %s in + %s out = %s tokens ($%.5f)",
                    candidate,
                    provider_label,
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.total_tokens,
                    usage.cost_usd,
                )
                if truncated_usage:
                    usage = sum_usage([*truncated_usage, usage])
                return content, usage
            except Exception as err:
                last_error = err
                retry_kind = _classify_llm_error(err)

                if retry_kind == "transient" and attempt < max_retries:
                    base_backoff = config.LLM_BASE_BACKOFF_SECONDS
                    backoff_secs = base_backoff * (2**attempt) + random.uniform(0.1, 0.5)
                    logger.warning(
                        "Transient LLM error (%s) on candidate '%s'. Backing off for %.2fs (attempt %s/%s)...",
                        err,
                        candidate,
                        backoff_secs,
                        attempt + 1,
                        max_retries + 1,
                    )
                    await asyncio.sleep(backoff_secs)
                    continue
                if retry_kind == "connection" and attempt < max_retries:
                    backoff_secs = 1.0 + random.uniform(0.1, 0.4)
                    logger.warning(
                        "Connection error (%s) on '%s'. Retrying in %.2fs...",
                        err,
                        candidate,
                        backoff_secs,
                    )
                    await asyncio.sleep(backoff_secs)
                    continue

                logger.warning(
                    "LLM error on model '%s' attempt %s: %s", candidate, attempt + 1, err
                )
                break

    logger.error("LLM call failed for prompt. Last error: %s", last_error)
    if isinstance(last_error, ValueError):
        raise last_error
    raise RuntimeError(
        f"AI Generation Failed: Model unreachable or encountered errors. Details: {last_error}"
    )


_PARSE_ERRORS = (ValueError, KeyError, TypeError, AttributeError)


async def call_llm_validated(
    prompt: str,
    system_prompt: str,
    parse: Callable[[str], T],
    **llm_kwargs: Any,
) -> tuple[T, TokenUsage]:
    """Calls the model and parses its reply, with one repair attempt on invalid output.

    ``parse`` must raise on any structural problem (missing fields, wrong types, bad JSON). On
    failure the model is shown its own reply and the error and asked once, at temperature 0, for a
    corrected JSON object; both calls are billed. A second failure raises ``ValueError``, so
    nothing malformed ever turns into a fabricated default. Provider errors (including
    ``LLMNotConfiguredError``) propagate untouched.
    """
    raw, usage = await call_llm(prompt=prompt, system_prompt=system_prompt, **llm_kwargs)
    try:
        return parse(raw), usage
    except _PARSE_ERRORS as first_error:
        logger.warning("LLM output failed validation (%s); requesting one repair.", first_error)
        repair_prompt = (
            f"{prompt}\n\n--- YOUR PREVIOUS REPLY WAS INVALID ---\n"
            f"Problem: {first_error}\n"
            f"Previous reply (truncated):\n{raw[:4000]}\n\n"
            "Return ONLY the corrected, complete JSON object in the required schema."
        )
        repair_kwargs = {**llm_kwargs, "temperature": 0.0}
        raw2, usage2 = await call_llm(
            prompt=repair_prompt, system_prompt=system_prompt, **repair_kwargs
        )
        total = sum_usage([usage, usage2])
        try:
            return parse(raw2), total
        except _PARSE_ERRORS as second_error:
            raise ValueError(f"LLM output invalid after repair: {second_error}") from second_error
