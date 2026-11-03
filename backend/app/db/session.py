from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import config
from app.db.init_db import init_db_schema

logger = logging.getLogger(__name__)

# Native PostgreSQL 16 engine via asyncpg with production connection pooling
engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=config.DB_POOL_SIZE,
    max_overflow=config.DB_MAX_OVERFLOW,
    pool_timeout=config.DB_POOL_TIMEOUT,
    pool_recycle=config.DB_POOL_RECYCLE,
)

# Standard async session factory bound to PostgreSQL engine
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initializes PostgreSQL database tables, migrations, and indexes."""
    logger.info("Initializing PostgreSQL schema and connections...")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
        await init_db_schema(engine)
        logger.info("PostgreSQL database schema initialized successfully.")
    except Exception as e:
        logger.warning(
            f"PostgreSQL initialization deferred or unavailable ({e}). "
            "Backend operating in offline / disconnected mode."
        )


async def check_db_health() -> dict[str, Any]:
    """Probes PostgreSQL database connection health for readiness/liveness checks."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1;"))
            return {"connected": True, "status": "ready", "engine": "postgresql"}
    except Exception as e:
        logger.error(f"PostgreSQL connection check failed: {e}")
        return {
            "connected": False,
            "status": "unavailable",
            "engine": "postgresql",
            "error": str(e),
        }
