"""List/export bounds, LIKE escaping, create-only batch endpoint and worker-save integrity."""

from __future__ import annotations

import uuid

import pytest
from app.repositories import _filters as filters
from app.repositories import (
    count_questions,
    get_questions,
    save_batch,
    save_question,
)
from app.repositories.question_mutations import BatchNotFoundError
from app.schemas import GenerationBatch
from factories import make_question

requires_db = pytest.mark.requires_db


def test_clamp_list_limit():
    assert filters.clamp_list_limit(None) == filters.MAX_LIST_LIMIT == 2000
    assert filters.clamp_list_limit(0) == 2000
    assert filters.clamp_list_limit(-1) == 2000
    assert filters.clamp_list_limit(25) == 25
    assert filters.clamp_list_limit(10**6) == 2000


def test_like_contains_escapes_wildcards():
    assert filters.like_contains("100%_x\\y") == "%100\\%\\_x\\\\y%"
    assert filters.like_contains("plain") == "%plain%"


@requires_db
async def test_search_treats_percent_and_underscore_literally():
    tag = uuid.uuid4().hex[:8]
    hit = make_question(question_stem=f"rate is 50%_{tag} of max")
    miss = make_question(question_stem=f"rate is 50xx{tag} of max")
    await save_question(hit)
    await save_question(miss)
    found = await get_questions(search=f"50%_{tag}", status=None)
    ids = {q.id for q in found}
    assert hit.id in ids
    assert miss.id not in ids
    assert await count_questions(search=f"50%_{tag}") >= 1
    # A bare wildcard must not match everything
    assert miss.id not in {q.id for q in await get_questions(search="%_%zz9", status=None)}


@requires_db
async def test_unlimited_list_is_clamped(monkeypatch):
    monkeypatch.setattr(filters, "MAX_LIST_LIMIT", 2)
    batch = GenerationBatch(id=str(uuid.uuid4()), section="chem_phys", status="completed")
    await save_batch(batch)
    for _ in range(3):
        await save_question(make_question(batch_id=batch.id, status="batch_only"))
    assert len(await get_questions(batch_id=batch.id, status=None)) == 2
    assert len(await get_questions(batch_id=batch.id, status=None, limit=1)) == 1


@requires_db
async def test_export_pages_through_the_whole_bank(client, monkeypatch):
    from app.api.v1 import questions as questions_api

    monkeypatch.setattr(questions_api, "_EXPORT_PAGE_SIZE", 2)
    tag = uuid.uuid4().hex
    for i in range(5):
        await save_question(make_question(question_stem=f"export {tag} {i}", status="in_bank"))
    res = await client.get("/api/export?format=json")
    assert res.status_code == 200
    assert sum(1 for q in res.json() if tag in q["question_stem"]) == 5
    csv_res = await client.get("/api/export?format=csv")
    assert csv_res.text.count(f"export {tag}") == 5


@requires_db
async def test_post_batches_is_create_only(client):
    bid = str(uuid.uuid4())
    body = {
        "id": bid,
        "section": "chem_phys",
        "status": "in_progress",
        "actual_count": 99,
        "total_tokens": 12345,
    }
    created = await client.post("/api/batches", json=body)
    assert created.status_code == 200
    stored = created.json()["batch"]
    assert stored["status"] == "completed"
    assert stored["actual_count"] == 0
    assert stored["total_tokens"] == 0

    again = await client.post("/api/batches", json={**body, "section": "psych_soc"})
    assert again.status_code == 409
    fetched = (await client.get(f"/api/batches/{bid}")).json()["batch"]
    assert fetched["section"] == "chem_phys"


@requires_db
async def test_job_question_never_fabricates_a_missing_batch():
    q = make_question(batch_id=str(uuid.uuid4()), job_id=str(uuid.uuid4()), status="batch_only")
    with pytest.raises(BatchNotFoundError):
        await save_question(q)
    from app.repositories import batch_exists

    assert not await batch_exists(q.batch_id)
