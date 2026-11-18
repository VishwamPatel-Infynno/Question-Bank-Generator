from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.base import Base
from app.db.schema_migrations import (
    _ADD_COLUMN_RE,
    _CREATE_INDEX_RE,
    _DATA_STEPS,
    _REDUNDANT_INDEXES,
    _SCHEMA_STEPS,
    _TIMESTAMP_COLUMNS,
    _IdempotentConnection,
    _load_existing_schema,
    _step_backfill_batches,
    _step_backfill_passages,
    _step_composite_indexes,
    _step_dedup_columns,
    _step_drop_redundant_indexes,
    _step_fk_question_batch,
    _step_fk_question_job,
    _step_fk_question_passage,
    _step_fulltext_index,
    _step_job_tracking_columns,
    _step_matrix_columns,
    _step_passage_batch_indexes,
    _step_pgvector_columns,
    _step_reconcile_question_status,
    _step_retry_tracking_columns,
    _step_run_batch_columns,
    _step_soft_delete_columns,
    _step_taxonomy_columns,
    _step_token_columns,
    _timestamptz_migration_sql,
    run_schema_migrations,
)
from app.models.batch import GenerationBatchModel
from app.models.job import GenerationJobModel
from app.models.passage import PassageModel
from app.models.question import QuestionModel

__all__ = [
    "_ADD_COLUMN_RE",
    "_CREATE_INDEX_RE",
    "_DATA_STEPS",
    "_REDUNDANT_INDEXES",
    "_SCHEMA_STEPS",
    "_TIMESTAMP_COLUMNS",
    "GenerationBatchModel",
    "GenerationJobModel",
    "PassageModel",
    "QuestionModel",
    "_IdempotentConnection",
    "_load_existing_schema",
    "_step_backfill_batches",
    "_step_backfill_passages",
    "_step_composite_indexes",
    "_step_dedup_columns",
    "_step_drop_redundant_indexes",
    "_step_fk_question_batch",
    "_step_fk_question_job",
    "_step_fk_question_passage",
    "_step_fulltext_index",
    "_step_job_tracking_columns",
    "_step_matrix_columns",
    "_step_passage_batch_indexes",
    "_step_pgvector_columns",
    "_step_reconcile_question_status",
    "_step_retry_tracking_columns",
    "_step_run_batch_columns",
    "_step_soft_delete_columns",
    "_step_taxonomy_columns",
    "_step_token_columns",
    "_timestamptz_migration_sql",
    "init_db_schema",
    "run_schema_migrations",
]

logger = logging.getLogger(__name__)


async def init_db_schema(engine: AsyncEngine) -> None:
    """Initializes PostgreSQL tables, verifies schema columns, backfills passages/batches, and ensures FTS indexes."""
    async with engine.begin() as conn:
        # Enable pgvector extension before creating models that use the Vector type
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception as e:
            logger.debug("Could not enable pgvector extension before create_all (%s).", e)
        await conn.run_sync(Base.metadata.create_all)

    await run_schema_migrations(engine)
    logger.info(
        "PostgreSQL tables verified / created successfully with passages, batches, matrix columns, FKs, and FTS."
    )
