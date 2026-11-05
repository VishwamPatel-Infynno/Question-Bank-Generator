"""Verified provider prices, model-based rate resolution, cache billing and image costs.

The defaults are checked on a Settings instance that ignores .env, so a developer's local
overrides cannot hide a wrong default (and CI, which has no .env, sees the same numbers).
"""

import logging

import pytest
from app.agents.base import calculate_token_cost
from app.agents.image_generator import openai_image_usage_cost
from app.core import pricing
from app.core.config import Settings, config

DEEPINFRA = "deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017"


@pytest.fixture
def defaults(monkeypatch):
    """A Settings object with the built-in defaults (no .env, no price env vars)."""
    for name in Settings.model_fields:
        if "COST" in name:
            monkeypatch.delenv(name, raising=False)
    return Settings(_env_file=None)


def test_built_in_defaults_are_the_verified_prices(defaults):
    assert (
        defaults.ANTHROPIC_COST_PER_MILLION_INPUT_TOKENS,
        defaults.ANTHROPIC_COST_PER_MILLION_OUTPUT_TOKENS,
    ) == (0.10, 0.50)
    assert (
        defaults.OPENAI_COST_PER_MILLION_INPUT_TOKENS,
        defaults.OPENAI_COST_PER_MILLION_OUTPUT_TOKENS,
    ) == (0.15, 0.60)
    # DeepInfra standard price (the 51% promo of $0.098 / $0.294 is opt-in through env)
    assert (
        defaults.DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS,
        defaults.DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS,
    ) == (0.20, 0.60)
    assert defaults.DEEPINFRA_IMAGE_COST_PER_UNIT == 0.014
    assert (
        defaults.OPENAI_IMAGE_COST_PER_MILLION_TEXT_INPUT_TOKENS,
        defaults.OPENAI_IMAGE_COST_PER_MILLION_IMAGE_INPUT_TOKENS,
        defaults.OPENAI_IMAGE_COST_PER_MILLION_OUTPUT_TOKENS,
    ) == (5.00, 8.00, 30.00)


def test_every_priced_model_documents_its_source():
    assert {"claude-haiku-5-5", "gpt-4o-mini", "gpt-image-2.5-flare"} <= {
        k.split(" ")[0] for k in pricing.PRICE_SOURCES
    }
    for key, source in pricing.PRICE_SOURCES.items():
        assert source["url"].startswith("https://"), key
        assert source["verified"] >= "2026-11-05", key


@pytest.mark.parametrize(
    ("model", "prompt", "completion", "expected"),
    [
        # short tier (prompt up to 100K tokens): $0.10 in / $0.50 out
        ("claude-haiku-5-5", 100_000, 1_000_000, 0.01 + 0.50),
        ("claude-haiku-5.5", 100_000, 1_000_000, 0.01 + 0.50),  # other spelling, same price
        ("anthropic/claude-haiku-5-5", 100_000, 0, 0.01),
        # long tier (prompt over 100K tokens): $0.50 in / $2.50 out
        ("claude-haiku-5-5", 100_001, 1_000_000, 100_001 * 0.50 / 1e6 + 2.50),
        ("claude-haiku-5-5", 1_000_000, 1_000_000, 0.50 + 2.50),
        ("gpt-4o-mini", 1_000_000, 1_000_000, 0.75),
        (DEEPINFRA, 1_000_000, 1_000_000, 0.80),
        (DEEPINFRA, 1000, 1000, 0.0008),
    ],
)
def test_text_costs_match_the_published_prices(model, prompt, completion, expected, monkeypatch):
    monkeypatch.setattr(config, "ACTIVE_LLM_PROVIDER", "deepinfra")
    for name in Settings.model_fields:  # a local .env must not change the numbers
        if "COST_PER_MILLION" in name and name.startswith(("ANTHROPIC", "OPENAI", "DEEPINFRA")):
            monkeypatch.setattr(config, name, getattr(Settings(_env_file=None), name))
    assert calculate_token_cost(prompt, completion, model=model) == pytest.approx(
        expected, abs=1e-7
    )


def test_cache_billing_per_provider(monkeypatch):
    for name in ("ANTHROPIC", "OPENAI", "DEEPINFRA"):
        monkeypatch.setattr(
            config,
            f"{name}_COST_PER_MILLION_INPUT_TOKENS",
            getattr(Settings(_env_file=None), f"{name}_COST_PER_MILLION_INPUT_TOKENS"),
        )
        monkeypatch.setattr(
            config,
            f"{name}_COST_PER_MILLION_OUTPUT_TOKENS",
            getattr(Settings(_env_file=None), f"{name}_COST_PER_MILLION_OUTPUT_TOKENS"),
        )
    # Haiku 5.5 short tier: 100K prompt tokens = 40K fresh + 40K cache read + 20K cache write (5 min)
    haiku = calculate_token_cost(
        100_000, 0, "claude-haiku-5-5", cache_read_tokens=40_000, cache_creation_tokens=20_000
    )
    assert haiku == pytest.approx(0.04 * 0.10 + 0.04 * 0.01 + 0.02 * 0.125, abs=1e-7)
    # the tier uses the whole prompt: cache tokens count towards the 100K threshold
    over = calculate_token_cost(
        150_000, 0, "claude-haiku-5-5", cache_read_tokens=100_000, cache_creation_tokens=0
    )
    assert over == pytest.approx(0.05 * 0.50 + 0.1 * 0.05, abs=1e-7)
    # gpt-4o-mini cached input is $0.075 (50%), DeepSeek cached is $0.006 (3% of $0.20)
    assert calculate_token_cost(
        1_000_000, 0, "gpt-4o-mini", cache_read_tokens=1_000_000
    ) == pytest.approx(0.075)
    assert calculate_token_cost(
        1_000_000, 0, DEEPINFRA, cache_read_tokens=1_000_000
    ) == pytest.approx(0.006)


def test_a_model_is_billed_by_its_own_provider_not_the_active_one(monkeypatch):
    monkeypatch.setattr(config, "ACTIVE_LLM_PROVIDER", "anthropic")
    di_in, di_out = config.get_default_pricing_rates(DEEPINFRA)
    assert (di_in, di_out) == (
        config.DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS,
        config.DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS,
    )
    oa_in, oa_out = config.get_default_pricing_rates("gpt-4o-mini")
    assert (oa_in, oa_out) == (
        config.OPENAI_COST_PER_MILLION_INPUT_TOKENS,
        config.OPENAI_COST_PER_MILLION_OUTPUT_TOKENS,
    )


def test_a_runtime_override_only_reprices_the_active_provider(monkeypatch):
    monkeypatch.setattr(config, "ACTIVE_LLM_PROVIDER", "anthropic")
    # Use the public setters and restore them: pytest's monkeypatch can delete a pydantic
    # private attribute when it undoes setattr on it, which breaks every later test
    config.COST_PER_MILLION_INPUT_TOKENS = 4.5
    config.COST_PER_MILLION_OUTPUT_TOKENS = 18.0
    try:
        assert config.get_default_pricing_rates("claude-haiku-5-5") == (4.5, 18.0)
        # a DeepInfra model keeps DeepInfra's rates while the Anthropic override is active
        assert config.get_default_pricing_rates(DEEPINFRA) == (
            config.DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS,
            config.DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS,
        )
    finally:
        config.COST_PER_MILLION_INPUT_TOKENS = None
        config.COST_PER_MILLION_OUTPUT_TOKENS = None


def test_unknown_models_are_priced_by_deepinfra_and_warned_about_once(caplog, monkeypatch):
    monkeypatch.setattr(config, "ACTIVE_LLM_PROVIDER", "deepinfra")
    pricing.warn_unpriced_model.cache_clear()
    with caplog.at_level(logging.WARNING, logger="app.core.pricing"):
        first = config.get_default_pricing_rates("some-org/mystery-model")
        config.get_default_pricing_rates("some-org/mystery-model")
    assert first == (
        config.DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS,
        config.DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS,
    )
    warnings = [r for r in caplog.records if "No price known" in r.getMessage()]
    assert len(warnings) == 1


def test_haiku_name_variants():
    for name in ("claude-haiku-5-5", "claude-haiku-5.5", "anthropic/claude-haiku-5-5"):
        assert pricing.is_haiku_5_5(name)
    assert not pricing.is_haiku_5_5("claude-3-5-haiku-20241022")


def test_openai_image_cost_comes_from_returned_usage():
    # 1,000 text tokens + 1,000 output tokens: 1000 * $5/M + 1000 * $30/M
    assert openai_image_usage_cost({"input_tokens": 1000, "output_tokens": 1000}) == pytest.approx(
        0.035
    )
    # input tokens split into text and image
    split = openai_image_usage_cost(
        {
            "input_tokens": 2000,
            "output_tokens": 0,
            "input_tokens_details": {"text_tokens": 1000, "image_tokens": 1000},
        }
    )
    assert split == pytest.approx(1000 * 5 / 1e6 + 1000 * 8 / 1e6)
    # legacy key names, and no usable usage at all
    assert openai_image_usage_cost(
        {"prompt_tokens": 20, "completion_tokens": 1000}
    ) == pytest.approx(0.0301)
    for empty in (None, {}, {"input_tokens": 0, "output_tokens": 0}, "x"):
        assert openai_image_usage_cost(empty) is None


def test_flux_klein_scales_with_area(monkeypatch):
    monkeypatch.setattr(config, "DEEPINFRA_IMAGE_COST_PER_UNIT", 0.014)
    model = "black-forest-labs/FLUX-2-klein-4b"
    assert config.calculate_image_cost(1024, 1024, model=model) == pytest.approx(0.014)
    assert config.calculate_image_cost(512, 512, model=model) == pytest.approx(0.0035)
    assert config.calculate_image_cost(2048, 2048, model=model) == pytest.approx(0.056)
