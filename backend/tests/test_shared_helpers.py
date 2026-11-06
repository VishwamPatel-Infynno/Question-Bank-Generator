"""Shared helpers extracted during cleanup keep their exact semantics."""

import pytest
from app.agents import generator
from app.agents._mock_tokens import QUESTION_GENERATOR_MOCK_PROMPT_TOKENS, mock_usage
from app.agents.base import calculate_token_cost
from app.agents.standards import is_cars
from app.schemas import GenerationRequest, TokenUsage
from app.schemas.token import sum_usage
from app.workflow._section_utils import is_cars_section


def _u(tokens, cost, ms=None):
    return TokenUsage(
        prompt_tokens=tokens,
        completion_tokens=0,
        total_tokens=tokens,
        cost_usd=cost,
        duration_ms=ms,
    )


def test_sum_usage_adds_tokens_and_cost_and_picks_latency_by_concurrency():
    parts = [_u(10, 0.001, 100), _u(20, 0.002, 300)]
    sequential = sum_usage(parts)
    assert sequential.total_tokens == 30 and sequential.cost_usd == 0.003
    assert sequential.duration_ms == 400
    assert sum_usage(parts, parallel=True).duration_ms == 300
    assert sum_usage([_u(1, 0.0)]).duration_ms is None


def test_mock_usage_is_priced_like_a_real_call():
    usage = mock_usage(QUESTION_GENERATOR_MOCK_PROMPT_TOKENS, 100)
    assert usage.total_tokens == QUESTION_GENERATOR_MOCK_PROMPT_TOKENS + 100
    assert usage.cost_usd == calculate_token_cost(QUESTION_GENERATOR_MOCK_PROMPT_TOKENS, 100)


@pytest.mark.parametrize("section", ["CARS", "cars", "Cars"])
def test_workflow_and_agent_cars_helpers_agree(section):
    assert is_cars(section) and is_cars_section(section)
    assert not is_cars("chem_phys") and not is_cars_section("chem_phys")


def test_passage_prompt_differs_between_cars_and_science(patch_llm):
    """Regression: a variable rename once made every passage prompt use the CARS text."""
    captured = []

    async def fake_call(prompt, system_prompt, **kwargs):
        captured.append(prompt)
        return "A passage.", _u(10, 0.0)

    patch_llm(fake_call)

    async def run(section):
        await generator.generate_passage_stimulus(
            GenerationRequest(section=section, subtopic="Topic", difficulty="Medium")
        )

    import asyncio

    asyncio.run(run("CARS"))
    asyncio.run(run("CP"))
    assert len(captured) == 2 and captured[0] != captured[1]
    assert "CARS" in captured[0] and "CARS" not in captured[1]
