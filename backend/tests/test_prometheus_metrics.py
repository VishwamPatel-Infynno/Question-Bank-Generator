from __future__ import annotations

import pytest
from app.core.config import config
from app.main import app
from app.services.metrics import normalize_metric_path, telemetry_store
from httpx import ASGITransport, AsyncClient


def test_metric_path_normalization():
    assert (
        normalize_metric_path("/api/questions/e2a39281-b51c-4b6b-88a2-11e2f389a9c1")
        == "/api/questions/{id}"
    )
    assert normalize_metric_path("/api/batches/12345/jobs/67890") == "/api/batches/{id}/jobs/{id}"
    assert normalize_metric_path("/api/sections/") == "/api/sections"
    assert normalize_metric_path("/api/health") == "/api/health"


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoints():
    telemetry_store.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test root /metrics endpoint
        root_resp = await client.get("/metrics")
        assert root_resp.status_code == 200
        assert "text/plain" in root_resp.headers["content-type"]
        assert "version=0.0.4" in root_resp.headers["content-type"]
        body = root_resp.text

        assert "# HELP mcat_up" in body
        assert "# TYPE mcat_up gauge" in body
        assert "mcat_up 1" in body
        assert "mcat_database_connected" in body
        assert "mcat_batches_active" in body
        assert "mcat_worker_jobs_active" in body
        assert "mcat_global_max_concurrent_jobs" in body
        assert "mcat_global_max_concurrent_llm_calls" in body

        # 2. Test /api/metrics endpoint for dual route symmetry
        api_resp = await client.get("/api/metrics")
        assert api_resp.status_code == 200
        assert "mcat_up 1" in api_resp.text


@pytest.mark.asyncio
async def test_telemetry_middleware_tracks_requests():
    telemetry_store.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send requests to live and ready endpoints
        live_resp = await client.get("/api/health/live")
        assert live_resp.status_code == 200

        # Scrape metrics and verify counter increment
        metrics_resp = await client.get("/metrics")
        assert metrics_resp.status_code == 200
        body = metrics_resp.text

        assert (
            'mcat_http_requests_total{endpoint="/api/health/live",method="GET",status="200"}'
            in body
        )
        assert (
            'mcat_http_request_duration_seconds_count{endpoint="/api/health/live",method="GET"}'
            in body
        )


@pytest.mark.asyncio
async def test_metrics_admin_key_protection(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_API_KEY", "prod-secret")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Standard scraper without admin header succeeds (public by default)
        resp_public = await client.get("/metrics")
        assert resp_public.status_code == 200

        # Explicit invalid admin header is rejected
        resp_invalid = await client.get("/metrics", headers={"x-admin-key": "wrong"})
        assert resp_invalid.status_code == 403

        # Valid admin header succeeds
        resp_valid = await client.get("/metrics", headers={"x-admin-key": "prod-secret"})
        assert resp_valid.status_code == 200
