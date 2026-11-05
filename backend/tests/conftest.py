"""
Shared pytest fixtures for the MCAT Question Bank Generator backend test suite.

Fixtures defined here are automatically discovered and available to all tests
in this directory without explicit import.
"""

import asyncio
import socket
from urllib.parse import urlparse

import asyncpg
import pytest
from app.core.config import config
from app.main import app
from httpx import ASGITransport, AsyncClient


def is_postgres_available(timeout: float = 1.0) -> bool:
    """Probes whether PostgreSQL is listening AND accepts the configured credentials."""
    db_url = config.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    parsed = urlparse(db_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432

    # Fast TCP socket pre-check to fail immediately if the port is not open
    try:
        with socket.create_connection((host, port), timeout=0.2):
            pass
    except OSError:
        return False

    async def _try_connect() -> bool:
        try:
            conn = await asyncpg.connect(
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip("/"),
                host=host,
                port=port,
                timeout=timeout,
            )
            await conn.execute("SELECT 1;")
            await conn.close()
            return True
        except Exception:
            return False

    try:
        return asyncio.run(_try_connect())
    except Exception:
        return False


POSTGRES_AVAILABLE = is_postgres_available()


@pytest.fixture(autouse=True)
def auto_skip_db_tests(request):
    """Automatically skips tests marked with @pytest.mark.requires_db if PostgreSQL is not reachable or unauthenticated."""
    if request.node.get_closest_marker("requires_db") and not POSTGRES_AVAILABLE:
        pytest.skip(
            "PostgreSQL database on localhost:5432 is offline or credentials for mcat_user failed. "
            "Skipping database-dependent test."
        )


@pytest.fixture(autouse=True)
def neutralize_llm_credentials(request, monkeypatch):
    """
    Ensures all non-live unit/integration tests run completely offline and free of cost.
    Strips external provider API credentials unless explicitly marked with @pytest.mark.live_e2e.
    """
    if request.node.get_closest_marker("live_e2e"):
        return

    from app.core.config import config

    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(config, "DEEPINFRA_API_KEY", "")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    # Offline tests rely on mock fixtures, which require the explicit opt-in
    monkeypatch.setattr(config, "OFFLINE_MODE", True)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPINFRA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture(autouse=True, scope="session")
async def ensure_db_initialized():
    """Automatically initializes the database schema if PostgreSQL is reachable."""
    if POSTGRES_AVAILABLE:
        try:
            from app.db.session import init_db

            await init_db()
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning("Failed to auto-init DB in test session: %s", e)


@pytest.fixture(scope="session")
async def client():
    """
    Async HTTP test client bound to the FastAPI application.

    Uses HTTPX's ASGITransport to exercise the full ASGI stack (middleware,
    routing, dependency injection) without starting a real server.

    Scope is ``session`` so the client (and underlying lifespan) is shared
    across the entire test session, avoiding repeated DB init overhead.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture(scope="session")
def anyio_backend():
    """Tells anyio (used by pytest-asyncio) to use the asyncio backend."""
    return "asyncio"


@pytest.fixture
def patch_llm(monkeypatch):
    """Replaces the LLM call used by every agent.

    Agents call ``call_llm_validated``, which resolves ``call_llm`` in ``app.agents.base``, so
    that is the single place to patch. Usage: ``patch_llm(fake_async_fn)``.
    """
    import app.agents.base as base_mod

    def _patch(fake):
        monkeypatch.setattr(base_mod, "call_llm", fake)

    return _patch
