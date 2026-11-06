import pytest
from app.agents.base import (
    _resolve_api_key,
    calculate_token_cost,
    call_llm,
    normalize_model_for_litellm,
)
from app.api.v1.config import get_runtime_settings
from app.api.v1.health import health_check
from app.core.config import config
from factories import make_completion


async def test_anthropic_model_detection_and_settings():
    """Verify that settings correctly identify Anthropic models, active providers, and rate cards."""
    assert config.is_anthropic_model("claude-haiku-5-5") is True
    assert config.is_anthropic_model("anthropic/claude-haiku-5-5") is True
    assert config.is_anthropic_model("claude-3-5-haiku-20241022") is True
    assert config.is_anthropic_model("deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017") is False

    assert config.get_active_provider("claude-haiku-5-5") == "anthropic"
    assert (
        config.get_active_provider("deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017") == "deepinfra"
    )

    haiku_in, haiku_out = config.get_default_pricing_rates("claude-haiku-5-5")
    assert haiku_in == 0.10
    assert haiku_out == 0.50

    di_in, di_out = config.get_default_pricing_rates(
        "deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017"
    )
    # a DeepInfra model is billed at DeepInfra's rates even while Anthropic is the active provider
    assert di_in == config.DEEPINFRA_COST_PER_MILLION_INPUT_TOKENS
    assert di_out == config.DEEPINFRA_COST_PER_MILLION_OUTPUT_TOKENS


async def test_provider_switcher_via_settings(monkeypatch):
    """Verify switching providers via ACTIVE_LLM_PROVIDER toggle."""
    monkeypatch.setattr(config, "ACTIVE_LLM_PROVIDER", "anthropic")
    assert config.get_active_provider() == "anthropic"

    monkeypatch.setattr(config, "ACTIVE_LLM_PROVIDER", "deepinfra")
    assert config.get_active_provider() == "deepinfra"


async def test_anthropic_strict_api_key_enforcement(monkeypatch):
    """Verify that calling an Anthropic model without ANTHROPIC_API_KEY raises an informative ValueError."""
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Anthropic API Key is required"):
        _resolve_api_key("claude-haiku-5-5", explicit_key=None)

    # Explicit key overrides environment requirement
    resolved = _resolve_api_key("claude-haiku-5-5", explicit_key="sk-ant-explicit-test")
    assert resolved == "sk-ant-explicit-test"

    # Setting key succeeds
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-ant-test-key-123")
    assert _resolve_api_key("claude-haiku-5-5", explicit_key=None) == "sk-ant-test-key-123"


async def test_deepinfra_key_enforcement_preservation(monkeypatch):
    """Verify that DeepInfra key resolution remains fully intact."""
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)

    with pytest.raises(ValueError, match="AI Gateway API Key is required"):
        _resolve_api_key("deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017", explicit_key=None)


async def test_claude_haiku_pricing_standard_tier():
    """
    Test standard prompt pricing (<= 100K tokens) for Claude Haiku 5.5:
    - Input: $0.10 / 1M tokens ($0.00000010/token)
    - Output: $0.50 / 1M tokens ($0.00000050/token)
    """
    cost = calculate_token_cost(
        prompt_tokens=1000,
        completion_tokens=1000,
        model="claude-haiku-5-5",
    )
    assert cost == 0.00060

    cost_100k = calculate_token_cost(
        prompt_tokens=100_000,
        completion_tokens=10_000,
        model="claude-haiku-5-5",
    )
    assert cost_100k == 0.015


async def test_claude_haiku_pricing_extended_tier():
    """
    Test extended prompt pricing (> 100K tokens) for Claude Haiku 5.5:
    - Input: $0.50 / 1M tokens ($0.00000050/token)
    - Output: $2.50 / 1M tokens ($0.00000250/token)
    """
    cost_extended = calculate_token_cost(
        prompt_tokens=150_000,
        completion_tokens=20_000,
        model="claude-haiku-5-5",
    )
    assert cost_extended == 0.125


async def test_claude_sonnet_pricing_auto_detection():
    """Verify Claude 3.5 Sonnet auto-detects $3.00 in / $15.00 out per 1M tokens with prompt cache math."""
    cost = calculate_token_cost(
        prompt_tokens=1000,
        completion_tokens=1000,
        model="claude-3-5-sonnet-20241022",
    )
    assert cost == 0.018

    # With prompt caching: 400 cache read, 200 cache creation, 400 base in
    cost_cached = calculate_token_cost(
        prompt_tokens=1000,
        completion_tokens=1000,
        model="claude-3-5-sonnet-20241022",
        cache_read_tokens=400,
        cache_creation_tokens=200,
    )
    assert cost_cached == 0.01707


async def test_claude_opus_pricing_auto_detection():
    """Verify Claude 3 Opus auto-detects $15.00 in / $75.00 out per 1M tokens."""
    cost = calculate_token_cost(
        prompt_tokens=1000,
        completion_tokens=1000,
        model="claude-3-opus-20240229",
    )
    assert cost == 0.090


async def test_custom_env_pricing_override(monkeypatch):
    """An explicit COST_PER_MILLION_* override re-prices the active provider's models."""
    monkeypatch.setattr(config, "ACTIVE_LLM_PROVIDER", "anthropic")  # the override is scoped to it
    monkeypatch.setattr(config, "COST_PER_MILLION_INPUT_TOKENS", 4.50)
    monkeypatch.setattr(config, "COST_PER_MILLION_OUTPUT_TOKENS", 18.00)

    cost = calculate_token_cost(
        prompt_tokens=1000,
        completion_tokens=1000,
        model="claude-custom-unreleased-model",
    )
    assert cost == 0.0225


async def test_model_normalization_for_litellm():
    """Verify normalize_model_for_litellm properly prefixes bare Anthropic models."""
    assert (
        normalize_model_for_litellm("claude-3-5-sonnet-20241022")
        == "anthropic/claude-3-5-sonnet-20241022"
    )
    assert normalize_model_for_litellm("claude-haiku-5-5") == "claude-haiku-5-5"
    assert (
        normalize_model_for_litellm("anthropic/claude-3-opus-20240229")
        == "anthropic/claude-3-opus-20240229"
    )
    assert (
        normalize_model_for_litellm("deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017")
        == "deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017"
    )


async def test_mock_llm_call_anthropic(monkeypatch):
    """Verify call_llm correctly formats Anthropic payload with disabled thinking and computes usage."""
    import litellm

    captured_kwargs = []

    async def mock_acompletion(**kwargs):
        captured_kwargs.append(kwargs)
        return make_completion(
            '{"result": "anthropic_success"}', prompt_tokens=1000, completion_tokens=1000
        )

    monkeypatch.setattr(litellm, "acompletion", mock_acompletion)
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-ant-mock-key")

    content, usage = await call_llm(
        prompt="Generate an MCAT biology scenario",
        system_prompt="You are an MCAT author",
        model="claude-haiku-5-5",
    )

    assert content == '{"result": "anthropic_success"}'
    assert len(captured_kwargs) == 1
    assert captured_kwargs[0]["model"] == "claude-haiku-5-5"
    assert captured_kwargs[0]["api_key"] == "sk-ant-mock-key"
    assert captured_kwargs[0]["thinking"] == {"type": "disabled"}
    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 1000
    assert usage.cost_usd == 0.00060


async def test_health_and_config_endpoints_anthropic_reporting(monkeypatch):
    """Verify /config and /health endpoints report has_anthropic_key, active_provider, and dynamic pricing."""
    # DEFAULT_TEXT_MODEL is a property with a public setter; restore it by hand (monkeypatch
    # would delete the private attribute behind it when undoing)
    orig_model = config.DEFAULT_TEXT_MODEL
    monkeypatch.setattr(config, "ACTIVE_LLM_PROVIDER", "anthropic")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-ant-live")
    config.DEFAULT_TEXT_MODEL = "claude-haiku-5-5"
    try:
        cfg_data = await get_runtime_settings()
        assert cfg_data["default_text_model"] == "claude-haiku-5-5"
        assert cfg_data["active_provider"] == "anthropic"
        assert cfg_data["has_anthropic_key"] is True
        assert cfg_data["cost_per_million_input"] == 0.10
        assert cfg_data["cost_per_million_output"] == 0.50

        hlth_data = await health_check()
        assert hlth_data["default_text_model"] == "claude-haiku-5-5"
        assert hlth_data["active_provider"] == "anthropic"
        assert hlth_data["has_anthropic_key"] is True
        assert hlth_data["cost_per_million_input"] == 0.10
        assert hlth_data["cost_per_million_output"] == 0.50
    finally:
        config.DEFAULT_TEXT_MODEL = orig_model
