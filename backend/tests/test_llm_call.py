"""Tests for call_llm request construction and retry behavior (provider mocked)."""

import asyncio
from types import SimpleNamespace

from app.agents import base
from app.core.config import config


def _response(content="{}", finish_reason="stop"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish_reason)
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


async def test_anthropic_system_prompt_is_marked_cacheable(monkeypatch):
    captured = {}

    async def fake_completion(**kwargs):
        captured.update(kwargs)
        return _response()

    monkeypatch.setattr(base.litellm, "acompletion", fake_completion)
    monkeypatch.setattr(config, "ENABLE_PROMPT_CACHING", True)
    await base.call_llm("hi", "STATIC SYSTEM", model="claude-haiku-5-5", api_key="k")

    system = captured["messages"][0]["content"]
    assert system[0]["text"] == "STATIC SYSTEM"
    assert system[0]["cache_control"] == {"type": "ephemeral"}


async def test_non_anthropic_system_prompt_stays_plain_text(monkeypatch):
    captured = {}

    async def fake_completion(**kwargs):
        captured.update(kwargs)
        return _response()

    monkeypatch.setattr(base.litellm, "acompletion", fake_completion)
    await base.call_llm("hi", "STATIC SYSTEM", model="deepinfra/some-model", api_key="k")
    assert captured["messages"][0]["content"] == "STATIC SYSTEM"
    assert captured["num_retries"] == 0


async def test_truncated_completion_is_retried_with_larger_budget(monkeypatch):
    budgets = []

    async def fake_completion(**kwargs):
        budgets.append(kwargs["max_tokens"])
        return _response("cut", "length") if len(budgets) == 1 else _response('{"ok": 1}')

    monkeypatch.setattr(base.litellm, "acompletion", fake_completion)
    content, _ = await base.call_llm(
        "hi", "sys", model="deepinfra/some-model", api_key="k", max_tokens=1000
    )
    assert content == '{"ok": 1}'
    assert budgets == [1000, 2000]


async def test_llm_slot_is_released_while_backing_off(monkeypatch):
    sem_free_during_sleep = []
    calls = {"n": 0}
    sem = asyncio.Semaphore(1)
    monkeypatch.setattr(base, "get_global_llm_semaphore", lambda: sem)

    async def fake_completion(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("HTTP 503 service unavailable")
        return _response()

    async def fake_sleep(_secs):
        sem_free_during_sleep.append(not sem.locked())

    monkeypatch.setattr(base.litellm, "acompletion", fake_completion)
    monkeypatch.setattr(base.asyncio, "sleep", fake_sleep)
    await base.call_llm("hi", "sys", model="deepinfra/some-model", api_key="k")
    assert calls["n"] == 2
    assert sem_free_during_sleep == [True]
