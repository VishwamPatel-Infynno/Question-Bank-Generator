import pytest
from app.agents.base import _resolve_api_key
from app.agents.generator import get_mock_draft
from app.agents.image_generator import (
    calculate_image_cost,
    call_openai_image_api,
    generate_image_stimulus,
)
from app.core.config import config
from app.main import app
from app.schemas import Difficulty, GenerationRequest, MCATSection
from httpx import ASGITransport, AsyncClient


def test_openai_provider_detection():
    """Verifies that model provider classification functions identify OpenAI models correctly."""
    assert config.is_openai_model("gpt-4o-mini") is True
    assert config.is_openai_model("gpt-4o") is True
    assert config.is_openai_model("o3-mini") is True
    assert config.is_openai_model("o1") is True
    assert config.is_openai_model("openai/gpt-4o-mini") is True
    assert config.is_openai_model("claude-haiku-5-5") is False
    assert config.is_openai_model("deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017") is False

    assert config.is_openai_image_model("gpt-image-2.5-flare") is True
    assert config.is_openai_image_model("gpt-image-2.5-sunburst") is True
    assert config.is_openai_image_model("openai/gpt-image-2.5-flare") is True
    assert config.is_openai_image_model("black-forest-labs/FLUX-2-klein-4b") is False


def test_openai_key_resolution(monkeypatch):
    """Verifies that _resolve_api_key handles OpenAI models and enforces key presence."""
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OpenAI API Key is required"):
        _resolve_api_key("gpt-4o-mini", None)

    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-proj-test12345")
    assert _resolve_api_key("gpt-4o-mini", None) == "sk-proj-test12345"
    assert _resolve_api_key("gpt-4o-mini", "explicit-key-override") == "explicit-key-override"


def test_openai_image_pricing_matrix():
    """Verifies mathematical rate cards for GPT Image 2.5, DALL-E 3, and DALL-E 2 tiers."""
    # Flare default rate: $0.020 for 1024x1024
    assert calculate_image_cost(1024, 1024, model="gpt-image-2.5-flare") == 0.020
    assert config.calculate_image_cost(1024, 1024, model="gpt-image-2.5-flare") == 0.020

    # Sunburst high-precision tier: $0.060 for 1024x1024
    assert calculate_image_cost(1024, 1024, model="gpt-image-2.5-sunburst") == 0.060

    # Resolution scaling (512x512 = 0.25x area)
    assert calculate_image_cost(512, 512, model="gpt-image-2.5-flare") == 0.005
    assert calculate_image_cost(512, 512, model="gpt-image-2.5-sunburst") == 0.015

    # DALL-E 3: Standard vs HD, Square vs Rectangular
    assert config.calculate_image_cost(1024, 1024, model="dall-e-3", quality="standard") == 0.040
    assert config.calculate_image_cost(1024, 1024, model="dall-e-3", quality="hd") == 0.080
    assert config.calculate_image_cost(1024, 1792, model="dall-e-3", quality="standard") == 0.080
    assert config.calculate_image_cost(1024, 1792, model="dall-e-3", quality="hd") == 0.120

    # DALL-E 2: 1024x1024, 512x512, 256x256
    assert config.calculate_image_cost(1024, 1024, model="dall-e-2") == 0.020
    assert config.calculate_image_cost(512, 512, model="dall-e-2") == 0.018
    assert config.calculate_image_cost(256, 256, model="dall-e-2") == 0.016


async def test_call_openai_image_api_token_metered_costing(monkeypatch):
    """Verifies that call_openai_image_api extracts usage tokens ($5/1M in, $30/1M out) when reported."""
    import httpx

    class MockResponseWithUsage:
        status_code = 200

        def json(self):
            return {
                "created": 1720000000,
                "data": [
                    {
                        "b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
                    }
                ],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 1000,
                    "total_tokens": 1020,
                },
            }

    async def mock_post(self, url, *args, **kwargs):
        return MockResponseWithUsage()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    _img, cost = await call_openai_image_api(
        prompt="Test figure",
        width=1024,
        height=1024,
        api_key="sk-mock-key",
        model="gpt-image-2.5-flare",
    )
    # 20 in @ $5.00/1M = $0.000100 + 1000 out @ $30.00/1M = $0.030000 => Total = $0.030100
    assert cost == 0.0301


async def test_openai_image_generator_missing_key(monkeypatch):
    """Verifies strict error reporting when ACTIVE_IMAGE_PROVIDER is 'openai' and key is missing."""
    monkeypatch.setattr(config, "ACTIVE_IMAGE_PROVIDER", "openai")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")

    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        difficulty=Difficulty.MEDIUM,
        require_image=True,
    )
    draft = get_mock_draft(req)

    img_url, img_svg, _desc, usage = await generate_image_stimulus(draft, req)
    assert img_url is None
    assert img_svg is None
    assert usage["agent_name"] == "Image Generator"
    assert usage["details"]["provider"] == "infynno"
    assert "Visual Studio" in usage["details"]["error"]


async def test_openai_image_generator_success(monkeypatch):
    """Verifies successful OpenAI GPT Image 2.5 generation and cost accumulation with proprietary masking."""
    monkeypatch.setattr(config, "ACTIVE_IMAGE_PROVIDER", "openai")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-proj-mock-key")
    monkeypatch.setattr(config, "OPENAI_IMAGE_MODEL", "gpt-image-2.5-flare")

    from app.agents import image_generator

    async def mock_call_openai(*_args, **_kwargs):
        return ("data:image/png;base64,mock_openai_b64_payload", None)

    monkeypatch.setattr(image_generator, "call_openai_image_api", mock_call_openai)

    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.HARD,
        require_image=True,
    )
    draft = get_mock_draft(req)

    img_url, img_svg, _desc, usage = await generate_image_stimulus(draft, req)
    assert img_url == "data:image/png;base64,mock_openai_b64_payload"
    assert img_svg is None
    assert usage["details"]["provider"] == "infynno"
    assert usage["model"] == "Infynno Visual Studio v2"
    assert usage["cost_usd"] == 0.020


async def test_call_openai_image_api_network_mock(monkeypatch):
    """Verifies call_openai_image_api correctly posts to OpenAI endpoint and parses b64_json."""
    import httpx

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "created": 1720000000,
                "data": [
                    {
                        "b64_json": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
                        "revised_prompt": "Medical test figure with clear labels",
                    }
                ],
            }

    async def mock_post(self, url, *args, **kwargs):
        assert "api.openai.com/v1/images/generations" in url
        payload = kwargs.get("json", {})
        assert payload.get("model") == "gpt-image-2.5-flare"
        assert payload.get("response_format") == "b64_json"
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    img_data, _cost = await call_openai_image_api(
        prompt="Enzyme kinetics curve",
        width=1024,
        height=1024,
        api_key="sk-mock-key",
        model="gpt-image-2.5-flare",
    )
    assert img_data is not None
    assert img_data.startswith("data:image/png;base64,")


async def test_api_config_and_health_branded_masking(monkeypatch):
    """Verifies that /api/config and /api/health endpoints report proprietary branding without leaking model/provider identities."""
    monkeypatch.setattr(config, "ACTIVE_IMAGE_PROVIDER", "openai")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-proj-test")
    monkeypatch.setattr(config, "OPENAI_IMAGE_MODEL", "gpt-image-2.5-flare")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        cfg_res = await ac.get("/api/config")
        assert cfg_res.status_code == 200
        cfg_data = cfg_res.json()
        assert cfg_data["engine"] == "Infynno Cognitive Architecture v2.0"
        assert cfg_data["visual_engine"] == "Infynno Visual Studio v2.0"
        assert cfg_data["ai_engine_ready"] is True
        # Ensure zero vendor leaks in public config payload
        assert "default_text_model" not in cfg_data
        assert "default_image_model" not in cfg_data
        assert "openai_model" not in cfg_data
        assert "openai_image_model" not in cfg_data
        assert "has_openai_key" not in cfg_data
        assert "has_anthropic_key" not in cfg_data
        assert "has_deepinfra_key" not in cfg_data

        health_res = await ac.get("/api/health")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert health_data["engine"] == "Infynno Cognitive Architecture v2.0"
        assert health_data["visual_engine"] == "Infynno Visual Studio v2.0"
        assert health_data["ai_engine_ready"] is True
        # Ensure zero vendor leaks in health payload
        assert "default_text_model" not in health_data
        assert "default_image_model" not in health_data
        assert "active_provider" not in health_data
        assert "active_image_provider" not in health_data
