"""Optional shared-secret gate and request input limits."""

import pytest
from app.core.config import config
from app.schemas import GenerationRequest
from pydantic import ValidationError


async def test_mutating_routes_open_when_no_access_key_is_configured(client, monkeypatch):
    monkeypatch.setattr(config, "API_ACCESS_KEY", "")
    res = await client.post("/api/batches/cancel-all")
    assert res.status_code != 401


@pytest.mark.requires_db
async def test_mutating_routes_require_the_key_when_configured(client, monkeypatch):
    monkeypatch.setattr(config, "API_ACCESS_KEY", "gate-secret")

    assert (await client.post("/api/batches/cancel-all")).status_code == 401
    wrong = await client.post("/api/batches/cancel-all", headers={"x-api-key": "nope"})
    assert wrong.status_code == 401
    ok = await client.post("/api/batches/cancel-all", headers={"x-api-key": "gate-secret"})
    assert ok.status_code != 401

    # Reads stay open; the read-only duplicate check is exempt from the key (but rate limited)
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
        ("subtopic", 301),
        ("shared_stimulus", 20001),
    ):
        payload = {**base, field: "x" * size}
        with pytest.raises(ValidationError):
            GenerationRequest(**payload)


def test_api_key_is_not_shown_in_repr():
    req = GenerationRequest(section="CP", subtopic="K", difficulty="Medium", api_key="sk-secret")
    assert "sk-secret" not in repr(req)


@pytest.mark.requires_db
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


async def test_check_duplicate_is_rate_limited_but_exempt_from_the_api_key(client, monkeypatch):
    import app.api.security as sec

    monkeypatch.setattr(config, "API_ACCESS_KEY", "gate-secret")
    monkeypatch.setattr(config, "GENERATION_RATE_LIMIT_PER_MINUTE", 2)
    sec._request_times.clear()
    codes = []
    for _ in range(3):
        res = await client.post("/api/questions/check-duplicate", content=b"not json")
        codes.append(res.status_code)
    sec._request_times.clear()
    assert 401 not in codes  # no key needed
    assert codes[:2] != [429, 429]
    assert codes[2] == 429


def test_duplicate_check_request_fields_are_length_limited():
    from app.schemas.question import DuplicateCheckRequest

    DuplicateCheckRequest(question_stem="x" * 5000)
    with pytest.raises(ValidationError):
        DuplicateCheckRequest(question_stem="x" * 5001)
    with pytest.raises(ValidationError):
        DuplicateCheckRequest(question_stem="q", subtopic="x" * 301)
    with pytest.raises(ValidationError):
        DuplicateCheckRequest(question_stem="q", options=[{"id": "A", "text": "x" * 2001}])


def test_rate_limit_identity_ignores_forwarded_header_and_buckets_ipv6():
    from app.api.security import _client_key
    from starlette.requests import Request

    def make(host, xff=""):
        return Request(
            {
                "type": "http",
                "headers": [(b"x-forwarded-for", xff.encode())],
                "client": (host, 1),
            }
        )

    assert _client_key(make("10.0.0.5", "1.2.3.4")) == "10.0.0.5"
    assert _client_key(make("2001:db8::1")) == _client_key(make("2001:db8::ffff"))
    assert _client_key(make("2001:db8::1")) != _client_key(make("2001:db9::1"))


async def test_active_batch_cap_reserves_slots_atomically(monkeypatch):
    import app.api.security as sec
    from fastapi import HTTPException

    monkeypatch.setattr(config, "MAX_ACTIVE_BATCHES", 2)
    monkeypatch.setattr(sec, "get_active_batch_metrics", lambda: {"active_running_batches": 0})
    gens = [sec.limit_active_batches() for _ in range(3)]
    await gens[0].__anext__()
    await gens[1].__anext__()
    with pytest.raises(HTTPException) as exc:
        await gens[2].__anext__()
    assert exc.value.status_code == 429
    await gens[0].aclose()  # a finished launch frees its reservation
    again = sec.limit_active_batches()
    await again.__anext__()
    await again.aclose()
    await gens[1].aclose()
    assert sec._pending_batch_launches == 0


async def test_streamed_body_over_the_limit_gets_413(monkeypatch):
    from app.main import core_app
    from httpx import ASGITransport, AsyncClient

    monkeypatch.setattr(config, "MAX_REQUEST_BODY_MB", 1)

    async def chunks():  # no Content-Length: sent chunked
        for _ in range(3):
            yield b"x" * (512 * 1024)

    transport = ASGITransport(app=core_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/api/questions/check-duplicate", content=chunks())
    assert res.status_code == 413
    assert res.json()["code"] == "payload_too_large"


def test_generation_request_limits():
    base = {"section": "CP", "subtopic": "Kinetics", "difficulty": "Medium"}
    GenerationRequest(**base, passing_threshold=100, model_name="deepinfra/org/Model-1.0")
    for bad in (
        {"passing_threshold": 101},
        {"passing_threshold": -1},
        {"thematic_angle": "x" * 2001},
        {"topic": "x" * 301},
        {"subject": "x" * 201},
        {"content_domains": ["x"] * 31},
        {"content_domains": ["x" * 201]},
        {"model_name": "bad model; rm -rf"},
        {"model_name": "../etc/passwd"},
    ):
        with pytest.raises(ValidationError):
            GenerationRequest(**base, **bad)


def test_unconfigured_model_is_refused_on_server_keys_unless_caller_brings_a_key():
    from app.agents.base import LLMNotConfiguredError, _ensure_model_allowed

    _ensure_model_allowed(None, None)
    _ensure_model_allowed(config.DEFAULT_TEXT_MODEL, None)
    _ensure_model_allowed("some/expensive-model", "client-key")
    with pytest.raises(LLMNotConfiguredError):
        _ensure_model_allowed("some/expensive-model", None)


def test_ai_copilot_free_form_payloads_are_size_capped():
    from app.api.v1.ai import RefineQuestionRequest, StudyGuideRequest

    RefineQuestionRequest(question={"question_stem": "ok"}, instruction="shorten it")
    with pytest.raises(ValidationError):
        RefineQuestionRequest(question={"blob": "x" * 60_000}, instruction="shorten it")
    with pytest.raises(ValidationError):
        StudyGuideRequest(questions=[{"blob": "x" * 60_000}])
    with pytest.raises(ValidationError):
        StudyGuideRequest(questions=[{"blob": "x" * 40_000}] * 9)


def test_terminal_error_event_never_carries_raw_provider_text():
    from app.schemas import WorkflowEvent
    from app.workflow.stream_emitter import build_terminal_workflow_event

    secret = "401 from https://api.x.com/v1?key=abc api_key=sk-LEAKLEAKLEAK1234"

    def make_event(**kw):
        return WorkflowEvent(**kw)

    req = GenerationRequest(section="CP", subtopic="K", difficulty="Medium")
    evt = build_terminal_workflow_event(
        make_event=make_event,
        layout=None,
        req=req,
        total_qty=1,
        all_staged_questions=[],
        outcomes_rejections=[],
        outcomes_errors=[secret],
        usage_totals={},
        all_agent_usage=[],
        passage_state=None,
        batch_id="b",
        shared_passage_id=None,
        is_single_passage_set=False,
        shared_passage_payload_fn=lambda *_: {},
        complete_message_fn=lambda *_: "",
    )
    blob = evt.model_dump_json()
    assert "sk-LEAKLEAKLEAK1234" not in blob
    assert "key=abc" not in blob


def test_proxy_config_overwrites_forwarded_for_and_trusts_no_wildcard():
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    nginx = (root / "frontend" / "nginx.conf").read_text()
    assert "X-Forwarded-For $remote_addr;" in nginx
    assert "proxy_add_x_forwarded_for" not in nginx
    assert 'proxy_set_header X-API-Key "${API_ACCESS_KEY}"' in nginx
    dockerfile = (root / "backend" / "Dockerfile").read_text()
    assert "--forwarded-allow-ips" not in dockerfile  # uvicorn reads FORWARDED_ALLOW_IPS instead
    assert "VITE_API_ACCESS_KEY" not in (root / "frontend" / "Dockerfile").read_text()
    assert "VITE_API_ACCESS_KEY" not in (root / "docker-compose.yml").read_text()
