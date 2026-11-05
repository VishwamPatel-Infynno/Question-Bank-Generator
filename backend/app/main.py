from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.router import api_router
from app.core.config import config
from app.core.logging import bind_log_context, configure_logging
from app.db.session import engine, init_db
from app.repositories import reconcile_interrupted_batches, scrub_stored_request_secrets
from app.services.batch_concurrency import cancel_all_background_batches

logger = logging.getLogger(__name__)


async def _post_init_maintenance() -> None:
    """Startup work that needs a ready database."""
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


async def _retry_db_init(first_delay: float = 5.0, max_delay: float = 60.0) -> None:
    """Retries schema initialization with backoff until the database is reachable."""
    delay = first_delay
    while True:
        await asyncio.sleep(delay)
        if await init_db():
            logger.info("Database became available; schema initialized.")
            await _post_init_maintenance()
            return
        delay = min(max_delay, delay * 2)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    configure_logging()
    logger.info("Initializing Infynno MCAT Question Bank Generator backend...")
    db_ready = await init_db()
    retry_task: asyncio.Task[None] | None = None
    if db_ready:
        await _post_init_maintenance()
    else:
        # The database may simply start later than the API (compose, orchestrators): keep trying
        # instead of leaving every route broken until a manual restart.
        retry_task = asyncio.create_task(_retry_db_init())
    try:
        yield
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        if retry_task is not None and not retry_task.done():
            retry_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await retry_task
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


_REQUEST_ID_OK = re.compile(r"^[A-Za-z0-9._\-]{1,64}$")


class RequestContextMiddleware:
    """Request id for log correlation plus a request body size limit.

    - Accepts a caller-supplied ``X-Request-ID`` (when it is a short safe token) or creates one,
      binds it to every log line produced while handling the request, and echoes it back.
    - Rejects bodies whose declared ``Content-Length`` exceeds MAX_REQUEST_BODY_MB with HTTP 413
      before any work happens.
    """

    def __init__(self, app: ASGIApp):
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        supplied = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = supplied if _REQUEST_ID_OK.match(supplied) else uuid.uuid4().hex[:16]

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append("x-request-id", request_id)
            await send(message)

        limit = config.MAX_REQUEST_BODY_MB * 1024 * 1024
        declared = headers.get(b"content-length", b"0")
        if limit and declared.isdigit() and int(declared) > limit:
            response = JSONResponse(
                status_code=413,
                content={
                    "detail": f"Request body exceeds {config.MAX_REQUEST_BODY_MB} MB.",
                    "code": "payload_too_large",
                },
            )
            await response(scope, receive, send_with_id)
            return

        with bind_log_context(request_id=request_id):
            await self._app(scope, receive, send_with_id)


core_app.add_middleware(SecurityHeadersMiddleware)
core_app.add_middleware(RequestContextMiddleware)


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
