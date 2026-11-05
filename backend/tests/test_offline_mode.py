"""Mocks are an explicit opt-in: no credentials without OFFLINE_MODE must fail loudly."""

import json

import pytest
from app.agents import blind_solver, generator, reviewer
from app.agents.base import LLMNotConfiguredError
from app.core.config import config
from app.workflow import run_workflow_stream
from factories import make_draft, make_request


def _draft():
    return make_draft(
        question_stem="Which is correct?",
        options=[f"Option {i} text" for i in "ABCD"],
        explanation="Option A is right. Option B no. Option C no. Option D no.",
    )


@pytest.fixture
def strict_no_keys(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", False)  # conftest enables it for offline tests


async def test_agents_raise_instead_of_returning_mock_results(strict_no_keys):
    with pytest.raises(LLMNotConfiguredError):
        await generator.generate_question_with_self_critique(make_request())
    with pytest.raises(LLMNotConfiguredError):
        await generator.generate_question(make_request())
    with pytest.raises(LLMNotConfiguredError):
        await reviewer.review_question(_draft(), make_request())
    with pytest.raises(LLMNotConfiguredError):
        await blind_solver.blind_solve_question(_draft(), make_request())


async def test_offline_mode_still_provides_fixtures_and_tags_the_run(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE_MODE", True)
    draft, _, _ = await generator.generate_question_with_self_critique(make_request())
    assert len(draft.options) == 4

    result = None
    async for chunk in run_workflow_stream(make_request()):
        evt = json.loads(chunk.strip()[len("data: ") :])
        if evt["event_type"] == "workflow_complete":
            result = evt["data"]["question"]
    assert result["stage_outcomes"]["offline_mode"] is True


async def test_run_without_credentials_fails_fast_with_a_clear_message(strict_no_keys):
    events = []
    async for chunk in run_workflow_stream(make_request()):
        events.append(json.loads(chunk.strip()[len("data: ") :]))
    errors = [e for e in events if e["event_type"] == "workflow_error"]
    assert errors and "API Key is required" in errors[-1]["message"]
    # Fail fast: a configuration error is not retried three times
    assert sum(1 for e in events if e["event_type"] == "batch_progress") <= 1
