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
