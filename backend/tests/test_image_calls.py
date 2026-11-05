"""Retry behaviour and response handling of the provider image calls (HTTP mocked)."""

import httpx
import pytest
from app.agents import image_generator as ig


@pytest.fixture
def no_sleep(monkeypatch):
    sleeps = []

    async def fake_sleep(secs):
        sleeps.append(secs)

    monkeypatch.setattr(ig.asyncio, "sleep", fake_sleep)
    return sleeps


def _mock_http(monkeypatch, handler):
    real = httpx.AsyncClient
    monkeypatch.setattr(
        ig.httpx,
        "AsyncClient",
        lambda **kw: real(transport=httpx.MockTransport(handler), **kw),
    )


async def test_empty_attempts_are_retried_with_growing_backoff(no_sleep):
    calls = []

    async def attempt(_client):
        calls.append(1)
        return ("data:image/png;base64,AAA", 0.02) if len(calls) == 3 else (None, None)

    assert await ig._retry_image_call("test", 5.0, attempt) == ("data:image/png;base64,AAA", 0.02)
    assert len(calls) == 3
    assert no_sleep == [1.0, 2.0]


async def test_exceptions_are_retried_then_give_up(no_sleep):
    calls = []

    async def attempt(_client):
        calls.append(1)
        raise RuntimeError("network down")

    assert await ig._retry_image_call("test", 5.0, attempt) == (None, None)
    assert len(calls) == ig._IMAGE_MAX_RETRIES + 1


async def test_openai_image_returns_a_data_uri_and_reported_cost(monkeypatch, no_sleep):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.content.decode()
        return httpx.Response(
            200,
            json={
                "data": [{"b64_json": "QUJD"}],
                "usage": {"input_tokens": 1_000_000, "output_tokens": 0},
            },
        )

    _mock_http(monkeypatch, handler)
    img, cost = await ig.call_openai_image_api("a diagram", 1024, 1024, "sk-test", "gpt-image-x")
    assert img == "data:image/png;base64,QUJD"
    assert cost == 5.0  # 1M input tokens at $5/M
    assert seen["auth"] == "Bearer sk-test"
    assert '"model":"gpt-image-x"' in seen["body"].replace(" ", "")


async def test_openai_image_falls_back_to_the_calculated_cost_and_url_payloads(
    monkeypatch, no_sleep
):
    _mock_http(
        monkeypatch,
        lambda request: httpx.Response(200, json={"data": [{"url": "https://cdn.example/x.png"}]}),
    )
    img, cost = await ig.call_openai_image_api("p", 1024, 1024, "sk-test", "gpt-image-x")
    assert img == "https://cdn.example/x.png"
    assert cost and cost > 0


async def test_openai_error_status_is_retried_and_fails_cleanly(monkeypatch, no_sleep):
    attempts = []

    def handler(request):
        attempts.append(1)
        return httpx.Response(500, text="server exploded")

    _mock_http(monkeypatch, handler)
    assert await ig.call_openai_image_api("p", 1024, 1024, "sk-test") == (None, None)
    assert len(attempts) == ig._IMAGE_MAX_RETRIES + 1
