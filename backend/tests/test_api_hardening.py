"""API hardening: admin gate, image safety, safe defaults, write validation."""

import uuid
from types import SimpleNamespace

import pytest
from app.core.config import config
from app.schemas import ResolveDuplicatesRequest
from pydantic import ValidationError


def _question_payload(status="in_bank"):
    return {
        "id": str(uuid.uuid4()),
        "section": "CPBS",
        "section_label": "Chemical and Physical Foundations of Biological Systems",
        "subtopic": "Kinetics",
        "difficulty": "medium",
        "question_stem": "What happens to the rate?",
        "options": [{"id": "A", "text": "a"}, {"id": "B", "text": "b"}],
        "correct_answer_id": "A",
        "explanation": "Because.",
        "final_score": 95,
        "status": status,
    }


async def test_config_and_health_ignore_an_arbitrary_admin_header(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_API_KEY", "")
    for path in ("/api/config", "/api/health"):
        masked = (await client.get(path, headers={"x-admin-key": "anything"})).json()
        assert "default_text_model" not in masked, path


async def test_config_requires_the_matching_admin_key(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_API_KEY", "s3cret")
    wrong = (await client.get("/api/config", headers={"x-admin-key": "nope"})).json()
    right = (await client.get("/api/config", headers={"x-admin-key": "s3cret"})).json()
    assert "default_text_model" not in wrong
    assert "default_text_model" in right


def test_resolve_duplicates_defaults_to_the_recoverable_archive_action():
    assert ResolveDuplicatesRequest().action == "archive"
    with pytest.raises(ValidationError):
        ResolveDuplicatesRequest(action="foo")


@pytest.mark.parametrize(
    ("image_url", "expected"),
    [
        ("data:text/html;base64,PHNjcmlwdD4=", 415),
        ("javascript:alert(1)", 415),
        ("data:image/png;base64,iVBORw0KGgo=", 200),
        ("https://cdn.example.com/x.png", 307),
    ],
)
async def test_image_endpoint_only_serves_safe_types(client, monkeypatch, image_url, expected):
    import app.api.v1.questions as mod

    async def fake(_qid):
        return SimpleNamespace(image_url=image_url, image_svg=None)

    monkeypatch.setattr(mod, "get_question_by_id", fake)
    res = await client.get("/api/questions/x/image", follow_redirects=False)
    assert res.status_code == expected
    if expected == 200:
        assert "sandbox" in res.headers["content-security-policy"]


async def test_svg_image_is_sandboxed(client, monkeypatch):
    import app.api.v1.questions as mod

    async def fake(_qid):
        return SimpleNamespace(image_url=None, image_svg="<svg onload='x()'/>")

    monkeypatch.setattr(mod, "get_question_by_id", fake)
    res = await client.get("/api/questions/x/image")
    assert res.headers["content-type"].startswith("image/svg+xml")
    assert "sandbox" in res.headers["content-security-policy"]
    assert res.headers["x-content-type-options"] == "nosniff"


async def test_invalid_question_status_is_rejected_not_a_500(client):
    res = await client.post("/api/questions", json=_question_payload(status="bogus"))
    assert res.status_code == 422
    res = await client.post("/api/questions/batch", json=[_question_payload(status="bogus")])
    assert res.status_code == 422


async def test_bulk_question_save_is_bounded(client):
    payload = [_question_payload() for _ in range(501)]
    res = await client.post("/api/questions/batch", json=payload)
    assert res.status_code == 413


async def test_invalid_batch_status_is_rejected(client):
    body = {"id": str(uuid.uuid4()), "status": "bogus"}
    res = await client.post("/api/batches", json={**body, "name": "x"})
    assert res.status_code in (422,)


async def test_generation_ids_are_length_capped(client):
    res = await client.post(
        "/api/generate",
        json={"section": "CPBS", "subtopic": "Kinetics", "batch_id": "x" * 65},
    )
    assert res.status_code == 422


async def test_generation_rate_limit_returns_429_with_retry_after(client, monkeypatch):
    from app.api import security

    monkeypatch.setattr(config, "GENERATION_RATE_LIMIT_PER_MINUTE", 2)
    security._request_times.clear()
    body = {
        "section": "CPBS",
        "subtopic": "Kinetics",
        "batch_id": "x" * 65,
    }  # 422 after the limiter
    codes = [(await client.post("/api/generate", json=body)).status_code for _ in range(3)]
    assert codes[:2] == [422, 422]
    assert codes[2] == 429
    security._request_times.clear()


async def test_rate_limit_can_be_disabled(client, monkeypatch):
    from app.api import security

    monkeypatch.setattr(config, "GENERATION_RATE_LIMIT_PER_MINUTE", 0)
    security._request_times.clear()
    body = {"section": "CPBS", "subtopic": "Kinetics", "batch_id": "x" * 65}
    codes = {(await client.post("/api/generate", json=body)).status_code for _ in range(5)}
    assert codes == {422}


async def test_active_batch_cap_returns_429(client, monkeypatch):
    from app.api import security
    from app.services import batch_concurrency

    monkeypatch.setattr(config, "MAX_ACTIVE_BATCHES", 1)
    monkeypatch.setattr(config, "GENERATION_RATE_LIMIT_PER_MINUTE", 0)
    monkeypatch.setitem(batch_concurrency._active_batch_tasks, "busy", object())
    res = await client.post("/api/batches/start", json={"section": "CPBS", "subtopic": "Kinetics"})
    assert res.status_code == 429
    assert "already running" in res.json()["detail"]
    security._request_times.clear()
