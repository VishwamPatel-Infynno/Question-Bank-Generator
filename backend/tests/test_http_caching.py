from __future__ import annotations

import pytest
from app.core.config import config
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_sections_endpoint_caching_and_etag():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Initial request
        resp1 = await client.get("/api/sections")
        assert resp1.status_code == 200
        assert "etag" in resp1.headers
        assert "cache-control" in resp1.headers
        assert "public, max-age=3600" in resp1.headers["cache-control"]
        etag = resp1.headers["etag"]

        # Conditional request with matching If-None-Match
        resp2 = await client.get("/api/sections", headers={"if-none-match": etag})
        assert resp2.status_code == 304
        assert resp2.headers["etag"] == etag
        assert not resp2.content

        # Conditional request with mismatching If-None-Match
        resp3 = await client.get("/api/sections", headers={"if-none-match": '"mismatched-etag"'})
        assert resp3.status_code == 200
        assert resp3.headers["etag"] == etag


@pytest.mark.asyncio
async def test_taxonomy_endpoint_caching_and_etag():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Initial request
        resp1 = await client.get("/api/taxonomy")
        assert resp1.status_code == 200
        assert "etag" in resp1.headers
        assert "cache-control" in resp1.headers
        assert "public, max-age=3600" in resp1.headers["cache-control"]
        etag = resp1.headers["etag"]

        # Conditional request with matching If-None-Match
        resp2 = await client.get("/api/taxonomy", headers={"if-none-match": etag})
        assert resp2.status_code == 304
        assert resp2.headers["etag"] == etag
        assert not resp2.content


@pytest.mark.asyncio
async def test_config_endpoint_caching_and_etag(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_API_KEY", "test-secret")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Public non-admin request
        resp1 = await client.get("/api/config")
        assert resp1.status_code == 200
        assert "etag" in resp1.headers
        assert "cache-control" in resp1.headers
        assert "public, max-age=300" in resp1.headers["cache-control"]
        etag = resp1.headers["etag"]

        # Conditional request with matching If-None-Match
        resp2 = await client.get("/api/config", headers={"if-none-match": etag})
        assert resp2.status_code == 304
        assert resp2.headers["etag"] == etag
        assert not resp2.content

        # Admin request returns private, no-cache
        resp_admin = await client.get("/api/config", headers={"x-admin-key": "test-secret"})
        assert resp_admin.status_code == 200
        assert resp_admin.headers["cache-control"] == "private, no-cache"


@pytest.mark.asyncio
async def test_single_batch_endpoint_caching_and_etag():
    import uuid

    from app.repositories import save_batch
    from app.schemas import BatchStatus, GenerationBatch

    uid = uuid.uuid4().hex[:8]
    batch = GenerationBatch(
        id=f"batch-etag-{uid}",
        section="chem_phys",
        subtopic="Thermodynamics",
        difficulty="medium",
        passage_mode="independent",
        target_count=5,
        actual_count=0,
        total_jobs=1,
        completed_jobs=0,
        status=BatchStatus.IN_PROGRESS,
    )
    await save_batch(batch)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Initial request: returns 200 with ETag
        resp1 = await client.get(f"/api/batches/{batch.id}")
        assert resp1.status_code == 200
        assert "etag" in resp1.headers
        etag = resp1.headers["etag"]
        data1 = resp1.json()
        assert data1["batch"]["id"] == batch.id

        # Conditional request with matching If-None-Match: returns 304 with no body
        resp2 = await client.get(f"/api/batches/{batch.id}", headers={"if-none-match": etag})
        assert resp2.status_code == 304
        assert resp2.headers["etag"] == etag
        assert not resp2.content

        # Conditional request with stale / mismatched ETag: returns 200
        resp3 = await client.get(
            f"/api/batches/{batch.id}", headers={"if-none-match": '"stale-etag"'}
        )
        assert resp3.status_code == 200
        assert resp3.headers["etag"] == etag


@pytest.mark.asyncio
async def test_batch_etag_changes_when_a_question_is_soft_deleted(client):
    import uuid

    from app.repositories import delete_question, save_batch, save_question
    from app.schemas import BatchStatus, GenerationBatch
    from factories import make_question

    batch = GenerationBatch(
        id=str(uuid.uuid4()),
        section="chem_phys",
        subtopic="K",
        difficulty="medium",
        target_count=5,
        total_jobs=1,
        status=BatchStatus.COMPLETED,
    )
    await save_batch(batch)
    q = make_question(batch_id=batch.id, status="batch_only")
    await save_question(q)

    first = await client.get(f"/api/batches/{batch.id}")
    etag = first.headers["etag"]
    assert (
        await client.get(f"/api/batches/{batch.id}", headers={"if-none-match": etag})
    ).status_code == 304

    await delete_question(q.id)  # soft delete never touches the batch row
    after = await client.get(f"/api/batches/{batch.id}", headers={"if-none-match": etag})
    assert after.status_code == 200
    assert after.headers["etag"] != etag
