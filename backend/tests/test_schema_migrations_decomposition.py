from __future__ import annotations

import pytest
from app.db import init_db, schema_migrations
from sqlalchemy import text


def test_schema_migrations_step_counts():
    """Verify that schema and data migration sequences contain the expected steps."""
    assert len(schema_migrations._SCHEMA_STEPS) == 13
    assert len(schema_migrations._DATA_STEPS) == 6

    for step in schema_migrations._SCHEMA_STEPS:
        assert callable(step)
    for step in schema_migrations._DATA_STEPS:
        assert callable(step)


def test_init_db_facade_reexports():
    """Verify that init_db facade maintains 100% parity with schema_migrations exports."""
    symbols = [
        "_ADD_COLUMN_RE",
        "_CREATE_INDEX_RE",
        "_DATA_STEPS",
        "_REDUNDANT_INDEXES",
        "_SCHEMA_STEPS",
        "_TIMESTAMP_COLUMNS",
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
        "run_schema_migrations",
    ]
    for sym in symbols:
        assert hasattr(init_db, sym), f"init_db missing re-export of {sym}"
        assert getattr(init_db, sym) is getattr(schema_migrations, sym), f"{sym} identity mismatch"


@pytest.mark.asyncio
async def test_idempotent_connection_filter():
    """Verify that _IdempotentConnection skips statements whose effect already exists."""

    class FakeConn:
        def __init__(self):
            self.executed = []

        async def execute(self, statement, *args, **kwargs):
            self.executed.append(statement)
            return "EXECUTED"

    fake = FakeConn()
    columns = {("questions", "status"), ("passages", "text")}
    indexes = {"ix_questions_status", "ix_passages_section"}
    proxy = schema_migrations._IdempotentConnection(fake, columns, indexes)

    # Already existing column -> should be bypassed (return None, not appended to executed)
    res1 = await proxy.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS status VARCHAR(32);")
    )
    assert res1 is None
    assert len(fake.executed) == 0

    # New column -> should be executed
    res2 = await proxy.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS new_col TEXT;"))
    assert res2 == "EXECUTED"
    assert len(fake.executed) == 1

    # Already existing index -> should be bypassed
    res3 = await proxy.execute(
        text("CREATE INDEX IF NOT EXISTS ix_questions_status ON questions (status);")
    )
    assert res3 is None
    assert len(fake.executed) == 1

    # New index -> should be executed
    res4 = await proxy.execute(text("CREATE INDEX IF NOT EXISTS ix_new ON questions (new_col);"))
    assert res4 == "EXECUTED"
    assert len(fake.executed) == 2


def test_timestamptz_migration_sql_generation():
    """Verify that _timestamptz_migration_sql produces a valid PostgreSQL DO block."""
    sql = schema_migrations._timestamptz_migration_sql()
    assert sql.startswith("DO $$")
    assert sql.endswith("END $$;")

    for table, col, _ in schema_migrations._TIMESTAMP_COLUMNS:
        assert f"table_name = '{table}'" in sql
        assert f"column_name = '{col}'" in sql
