import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import Receive, Scope, Send

from app.api.router import api_router
from app.core.config import config
from app.core.logging import configure_logging
from app.db.session import init_db
from app.repositories.batch_repository import reconcile_interrupted_batches

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    configure_logging()
    logger.info("Initializing Infynno MCAT Question Bank Generator backend...")
    await init_db()
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


core_app = FastAPI(
    title="Infynno MCAT Question Bank Generator API",
    description="AI Question Writing & Verification System | An Infynno Solutions LLP Product",
    version="2.0.0",
    lifespan=lifespan,
)


# Security Headers Middleware
@core_app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    return response


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
