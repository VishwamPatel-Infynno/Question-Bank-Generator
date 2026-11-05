from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.router import api_router
from app.core.config import config
from app.core.logging import configure_logging
from app.db.session import engine, init_db
from app.repositories import reconcile_interrupted_batches, scrub_stored_request_secrets
from app.services.batch_concurrency import cancel_all_background_batches

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    configure_logging()
    logger.info("Initializing Infynno MCAT Question Bank Generator backend...")
    await init_db()
    try:
        scrubbed = await scrub_stored_request_secrets()
        if scrubbed:
            logger.info(f"Removed stored API keys from {scrubbed} batch request payload(s).")
    except Exception as exc:
        logger.warning(f"Request payload scrub skipped: {exc}")
    try:
        await reconcile_interrupted_batches()
    except Exception as exc:
        logger.warning(f"Batch startup reconciliation skipped or deferred: {exc}")
    try:
        yield
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        logger.info("Shutting down backend...")
        # Stop running batches gracefully so progress is saved and no LLM spend is orphaned.
        try:
            stopped = await asyncio.wait_for(cancel_all_background_batches(), timeout=15)
            if stopped:
                logger.info(f"Gracefully stopped {stopped} running batch(es) before shutdown.")
        except Exception as exc:
            logger.warning(f"Batch shutdown drain incomplete: {exc}")
        try:
            await engine.dispose()
        except Exception as exc:
            logger.warning(f"Database engine disposal failed: {exc}")


core_app = FastAPI(
    title="Infynno MCAT Question Bank Generator API",
    description="AI Question Writing & Verification System | An Infynno Solutions LLP Product",
    version="2.0.0",
    lifespan=lifespan,
)


@core_app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Consistent error body for unexpected failures; details stay in the server log only."""
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=exc)
    return JSONResponse(
        status_code=500, content={"detail": "Internal server error.", "code": "internal_error"}
    )


_SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"x-xss-protection", b"1; mode=block"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"permissions-policy", b"geolocation=(), camera=(), microphone=()"),
)


class SecurityHeadersMiddleware:
    """Adds security headers to every HTTP response.

    A plain ASGI middleware instead of ``@app.middleware("http")``: the decorator form wraps each
    response in ``BaseHTTPMiddleware``, which adds a copy of the body stream and complicates SSE
    streaming and client-disconnect cancellation. This one only touches the response start message.
    """

    def __init__(self, app: ASGIApp):
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in _SECURITY_HEADERS:
                    headers.append(name.decode(), value.decode())
            await send(message)

        await self._app(scope, receive, send_with_headers)


core_app.add_middleware(SecurityHeadersMiddleware)


# Enable hardened CORS - origins sourced from Settings (localhost defaults + env overrides)
core_app.add_middleware(
    CORSMiddleware,
    allow_origins=config.effective_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)

# Mount versioned API routes under /api
core_app.include_router(api_router)


class CleanLifespanMiddleware:
    """Wraps the ASGI application to gracefully handle cancellation on shutdown without traceback noise."""

    def __init__(self, app: FastAPI):
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "lifespan":

            async def safe_receive():
                try:
                    return await receive()
                except (asyncio.CancelledError, KeyboardInterrupt):
                    return {"type": "lifespan.shutdown"}

            await self._app(scope, safe_receive, send)
        else:
            await self._app(scope, receive, send)

    def __getattr__(self, name: str):
        return getattr(self._app, name)


app: FastAPI = CleanLifespanMiddleware(core_app)  # type: ignore[assignment]
