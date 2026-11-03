from unittest.mock import MagicMock

import pytest
from app.core.config import config
from app.schemas import (
    Difficulty,
    GenerationRequest,
    MCATSection,
)
from app.workflow.graph import (
    generator_node,
    reviewer_node,
)


@pytest.mark.asyncio
async def test_deepinfra_model_configuration(monkeypatch):
    monkeypatch.setattr(config, "ACTIVE_LLM_PROVIDER", "deepinfra")
    assert "deepinfra" in config.DEFAULT_TEXT_MODEL.lower()
    assert "DeepSeek-V4.1-Flash-1017" in config.DEFAULT_TEXT_MODEL
    assert config.COST_PER_MILLION_INPUT_TOKENS == 0.098
    assert config.COST_PER_MILLION_OUTPUT_TOKENS == 0.294


@pytest.mark.asyncio
async def test_token_and_cost_calculation(monkeypatch):
    from app.agents.base import calculate_token_cost

    monkeypatch.setattr(config, "ACTIVE_LLM_PROVIDER", "deepinfra")
    monkeypatch.setattr(config, "COST_PER_MILLION_INPUT_TOKENS", 0.098)
    monkeypatch.setattr(config, "COST_PER_MILLION_OUTPUT_TOKENS", 0.294)

    # 1,000 prompt tokens @ $0.098/1M = $0.000098
    # 1,000 completion tokens @ $0.294/1M = $0.000294
    # Total = $0.000392
    cost = calculate_token_cost(
        prompt_tokens=1000,
        completion_tokens=1000,
        model="deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017",
    )
    assert cost == 0.000392

    # 1,000,000 input tokens = $0.098
    cost_in = calculate_token_cost(
        prompt_tokens=1_000_000,
        completion_tokens=0,
        model="deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017",
    )
    assert cost_in == 0.098

    # 1,000,000 output tokens = $0.294
    cost_out = calculate_token_cost(
        prompt_tokens=0,
        completion_tokens=1_000_000,
        model="deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017",
    )
    assert cost_out == 0.294


@pytest.mark.asyncio
async def test_workflow_token_accumulation(monkeypatch):
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)
    req = GenerationRequest(section=MCATSection.BIO_BIOCHEM, difficulty=Difficulty.MEDIUM)
    init_state = {
        "request": req.model_dump(),
        "iteration_count": 1,
        "iterations_history": [],
        "total_tokens": 0,
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_cost_usd": 0.0,
        "agent_usage_breakdown": [],
    }
    # Test generator_node returns token usage
    gen_res = await generator_node(init_state)
    assert "total_tokens" in gen_res
    assert gen_res["total_tokens"] > 0
    assert gen_res["total_cost_usd"] > 0.0
    assert len(gen_res["agent_usage_breakdown"]) == 1

    # Merge into state and run reviewer_node
    init_state.update(gen_res)
    rev_res = await reviewer_node(init_state)
    assert rev_res["total_tokens"] > gen_res["total_tokens"]
    assert rev_res["total_cost_usd"] > gen_res["total_cost_usd"]
    assert len(rev_res["agent_usage_breakdown"]) == 2


@pytest.mark.asyncio
async def test_deepinfra_strict_api_key_enforcement(monkeypatch):
    from app.agents.base import call_llm

    monkeypatch.setattr(config, "ACTIVE_LLM_PROVIDER", "deepinfra")
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)

    with pytest.raises(ValueError, match="AI Gateway API Key is required"):
        await call_llm(
            prompt="test prompt",
            system_prompt="test system",
            model="deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017",
        )


@pytest.mark.asyncio
async def test_max_tokens_settings_and_config_endpoint():
    """Verify that DEFAULT_MAX_TOKENS and REVIEWER_MAX_TOKENS are properly set in config and returned by /config."""
    from app.api.v1.config import get_settings

    assert config.DEFAULT_MAX_TOKENS == 3000
    assert config.REVIEWER_MAX_TOKENS == 1800

    settings_data = await get_settings()
    assert settings_data["default_max_tokens"] == 3000
    assert settings_data["reviewer_max_tokens"] == 1800
    assert settings_data["default_temperature"] == 0.2
    assert settings_data["generator_temperature"] == 0.2
    assert settings_data["reviewer_temperature"] == 0.1
    assert settings_data["blind_solver_temperature"] == 0.1
    assert "fast_model_cascade" in settings_data
    assert isinstance(settings_data["fast_model_cascade"], list)
    assert len(settings_data["fast_model_cascade"]) >= 1


@pytest.mark.asyncio
async def test_call_llm_effective_max_tokens_and_temperature(monkeypatch):
    """Verify call_llm uses config.DEFAULT_MAX_TOKENS and config.DEFAULT_TEMPERATURE by default and respects explicit overrides."""
    import litellm
    from app.agents.base import call_llm

    captured_kwargs = []

    async def mock_acompletion(**kwargs):
        captured_kwargs.append(kwargs)
        mock_resp = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"result": "ok"}'
        mock_resp.choices = [mock_choice]
        mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        return mock_resp

    monkeypatch.setattr(litellm, "acompletion", mock_acompletion)

    # 1. Default invocation (max_tokens=None, temperature=None) should use config defaults
    await call_llm(
        prompt="test prompt",
        system_prompt="test system",
        model="deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017",
        api_key="mock_key",
    )
    assert len(captured_kwargs) == 1
    assert captured_kwargs[0]["max_tokens"] == config.DEFAULT_MAX_TOKENS
    assert captured_kwargs[0]["max_tokens"] == 3000
    assert captured_kwargs[0]["temperature"] == config.DEFAULT_TEMPERATURE
    assert captured_kwargs[0]["temperature"] == 0.2

    # 2. Explicit invocation with custom max_tokens & temperature
    await call_llm(
        prompt="test prompt 2",
        system_prompt="test system 2",
        model="deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017",
        api_key="mock_key",
        temperature=config.REVIEWER_TEMPERATURE,
        max_tokens=config.REVIEWER_MAX_TOKENS,
    )
    assert len(captured_kwargs) == 2
    assert captured_kwargs[1]["max_tokens"] == 1800
    assert captured_kwargs[1]["temperature"] == 0.1
