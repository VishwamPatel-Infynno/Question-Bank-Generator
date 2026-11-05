"""Optional shared-secret gate and request input limits."""

import pytest
from app.core.config import config
from app.schemas import GenerationRequest
from pydantic import ValidationError


async def test_mutating_routes_open_when_no_access_key_is_configured(client, monkeypatch):
    monkeypatch.setattr(config, "API_ACCESS_KEY", "")
    res = await client.post("/api/batches/cancel-all")
    assert res.status_code != 401


async def test_mutating_routes_require_the_key_when_configured(client, monkeypatch):
    monkeypatch.setattr(config, "API_ACCESS_KEY", "gate-secret")

    assert (await client.post("/api/batches/cancel-all")).status_code == 401
    wrong = await client.post("/api/batches/cancel-all", headers={"x-api-key": "nope"})
    assert wrong.status_code == 401
    ok = await client.post("/api/batches/cancel-all", headers={"x-api-key": "gate-secret"})
    assert ok.status_code != 401

    # Reads and the read-only duplicate check stay open
    assert (await client.get("/api/health")).status_code == 200
    dup = await client.post(
        "/api/questions/check-duplicate", json={"question_stem": "Which is correct?"}
    )
    assert dup.status_code != 401


def test_request_inputs_are_length_limited():
    base = {"section": "CP", "subtopic": "Kinetics", "difficulty": "Medium"}
    GenerationRequest(**base, additional_instructions="x" * 4000)
    for field, size in (
        ("additional_instructions", 4001),
        ("custom_prompt", 4001),
        ("subtopic", 301),
        ("shared_stimulus", 20001),
    ):
        payload = {**base, field: "x" * size}
        with pytest.raises(ValidationError):
            GenerationRequest(**payload)


def test_api_key_is_not_shown_in_repr():
    req = GenerationRequest(section="CP", subtopic="K", difficulty="Medium", api_key="sk-secret")
    assert "sk-secret" not in repr(req)


async def test_batch_list_is_paginated_and_omits_payloads(client):
    res = await client.get("/api/batches?limit=2&offset=0")
    assert res.status_code == 200
    body = res.json()
    assert len(body["batches"]) <= 2
    assert all(b.get("request_payload") is None for b in body["batches"])
    assert (await client.get("/api/batches?limit=0")).status_code == 422


async def test_unhandled_errors_return_a_consistent_body_without_internals(monkeypatch):
    import app.api.v1.batches as batches_mod
    from app.main import core_app
    from httpx import ASGITransport, AsyncClient

    async def boom(**_kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(batches_mod, "get_batches", boom)
    transport = ASGITransport(app=core_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/batches")
    assert res.status_code == 500
    assert res.json() == {"detail": "Internal server error.", "code": "internal_error"}


async def test_security_headers_are_present_on_normal_and_error_responses(client):
    for path in ("/api/health", "/api/does-not-exist"):
        res = await client.get(path)
        assert res.headers["x-content-type-options"] == "nosniff"
        assert res.headers["x-frame-options"] == "DENY"
        assert res.headers["referrer-policy"] == "strict-origin-when-cross-origin"
