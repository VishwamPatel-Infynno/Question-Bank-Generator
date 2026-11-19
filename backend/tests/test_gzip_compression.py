from __future__ import annotations

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_large_response_gzip_compression():
    """Verify that responses exceeding 1KB are compressed with gzip when requested."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request with gzip accept-encoding
        resp = await client.get("/api/taxonomy", headers={"accept-encoding": "gzip"})
        assert resp.status_code == 200
        # GZipMiddleware sets Content-Encoding header
        assert resp.headers.get("content-encoding") == "gzip"

        # httpx automatically handles decompression on resp.content / resp.json()
        data = resp.json()
        assert isinstance(data, dict)
        assert len(data) > 0


@pytest.mark.asyncio
async def test_small_response_not_compressed():
    """Verify that responses below the 1KB threshold are not compressed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health", headers={"accept-encoding": "gzip"})
        assert resp.status_code == 200
        # Health check is small (< 1000 bytes), so minimum_size prevents compression
        assert resp.headers.get("content-encoding") != "gzip"


@pytest.mark.asyncio
async def test_no_gzip_header_returns_uncompressed():
    """Verify that requests without accept-encoding: gzip return uncompressed data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/taxonomy", headers={"accept-encoding": "identity"})
        assert resp.status_code == 200
        assert resp.headers.get("content-encoding") != "gzip"
        data = resp.json()
        assert isinstance(data, dict)
