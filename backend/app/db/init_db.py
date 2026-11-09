from __future__ import annotations

import logging
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import config
from app.db.base import Base
from app.models.batch import GenerationBatchModel  # noqa: F401 - Registered for Base.metadata
from app.models.job import GenerationJobModel  # noqa: F401 - Registered for Base.metadata
from app.models.passage import PassageModel  # noqa: F401 - Registered for Base.metadata
from app.models.question import QuestionModel  # noqa: F401 - Registered for Base.metadata

logger = logging.getLogger(__name__)


_ADD_COLUMN_RE = re.compile(
    r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\s+(\w+)", re.IGNORECASE
)
_CREATE_INDEX_RE = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+IF\s+NOT\s+EXISTS\s+(\w+)", re.IGNORECASE
)


class _IdempotentConnection:
    """Skips DDL whose effect already exists instead of re-running it.

    ``ADD COLUMN IF NOT EXISTS`` and ``CREATE INDEX IF NOT EXISTS`` are no-ops when the object
    exists, but PostgreSQL still takes a table lock first (ACCESS EXCLUSIVE for ALTER TABLE). Run on
    every start or test, that lock deadlocks against queries from running batch tasks. Checking the
    catalog first means a fully migrated database is never locked.
    """

    def __init__(self, conn, columns: set[tuple[str, str]], indexes: set[str]):
        self._conn = conn
        self._columns = columns
        self._indexes = indexes

    async def execute(self, statement, *args, **kwargs):
        sql = getattr(statement, "text", None)
        if isinstance(sql, str):
            m = _ADD_COLUMN_RE.search(sql)
            if m and (m.group(1).lower(), m.group(2).lower()) in self._columns:
                return None
            m = _CREATE_INDEX_RE.search(sql)
            if m and m.group(1).lower() in self._indexes:
                return None
        return await self._conn.execute(statement, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._conn, name)


async def _load_existing_schema(conn) -> tuple[set[tuple[str, str]], set[str]]:
    cols = await conn.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema()"
        )
    )
    idx = await conn.execute(
        text("SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()")
    )
    return (
        {(r[0].lower(), r[1].lower()) for r in cols.fetchall()},
        {r[0].lower() for r in idx.fetchall()},
    )


async def _step_token_columns(conn) -> None:
    """Token tracking columns."""
    # Safe schema update for token tracking columns (PostgreSQL)
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS total_tokens INTEGER DEFAULT 0;")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS prompt_tokens INTEGER DEFAULT 0;")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS completion_tokens INTEGER DEFAULT 0;")
    )
    await conn.execute(
        text(
            "ALTER TABLE questions ADD COLUMN IF NOT EXISTS cost_usd DOUBLE PRECISION DEFAULT 0.0;"
        )
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS token_usage_details JSONB;")
    )


async def _step_matrix_columns(conn) -> None:
    """Manager combination matrix columns."""
    # Safe schema update for Manager Combination Matrix columns
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS combination_id VARCHAR(64);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS content_domain VARCHAR(128);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS question_type VARCHAR(128);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS interaction_type VARCHAR(64);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS primary_trap VARCHAR(128);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS passage_required VARCHAR(16);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS passage_mode VARCHAR(32);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS passage_id VARCHAR(64);")
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_questions_passage_id ON questions (passage_id);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS passage_questions INTEGER;")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS visual_type VARCHAR(64);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS visual_medical_category VARCHAR(64);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS visual_clinical_description TEXT;")
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_questions_visual_medical_category ON questions (visual_medical_category);"
        )
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS mcat_scaled_score INTEGER;")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS aamc_skill VARCHAR(128);")
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_questions_mcat_scaled_score ON questions (mcat_scaled_score);"
        )
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_questions_aamc_skill ON questions (aamc_skill);")
    )
    await conn.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS stage_outcomes JSONB;"))


async def _step_taxonomy_columns(conn) -> None:
    """Granular dependent taxonomy hierarchy columns."""
    # Safe schema update for Granular Dependent Taxonomy Hierarchy
    await conn.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS subject VARCHAR(128);"))
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_questions_subject ON questions (subject);")
    )
    await conn.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS unit VARCHAR(128);"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_unit ON questions (unit);"))
    await conn.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS topic VARCHAR(128);"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_topic ON questions (topic);"))
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS subskill VARCHAR(256);")
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_questions_subskill ON questions (subskill);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS likely_mistake_pattern TEXT;")
    )


async def _step_dedup_columns(conn) -> None:
    """Deduplication and collision metadata columns."""
    # Safe schema update for Deduplication & Collision Metadata
    await conn.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS duplicate_info JSONB;"))
    await conn.execute(
        text(
            "ALTER TABLE questions ADD COLUMN IF NOT EXISTS is_duplicate_override BOOLEAN DEFAULT FALSE;"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_questions_section_subtopic ON questions (section, subtopic);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_questions_is_duplicate_override ON questions (is_duplicate_override);"
        )
    )


# (table, column, defaults to NOW()) timestamp columns that older schemas stored as text
_TIMESTAMP_COLUMNS: tuple[tuple[str, str, bool], ...] = (
    ("questions", "created_at", True),
    ("questions", "updated_at", False),
    ("passages", "created_at", True),
    ("passages", "updated_at", False),
    ("generation_batches", "created_at", True),
    ("generation_batches", "updated_at", False),
    ("generation_jobs", "created_at", True),
    ("generation_jobs", "started_at", False),
    ("generation_jobs", "completed_at", False),
)


def _timestamptz_migration_sql() -> str:
    """One DO block converting every text timestamp column to TIMESTAMPTZ (idempotent)."""
    blocks = []
    for table, column, default_now in _TIMESTAMP_COLUMNS:
        fallback = "NOW()" if default_now else "NULL"
        set_default = (
            f"\n                    ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT NOW();"
            if default_now
            else ""
        )
        blocks.append(
            f"""
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = '{table}' AND column_name = '{column}' AND data_type = 'character varying'
                ) THEN
                    ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE USING (
                        CASE WHEN {column} IS NOT NULL AND {column} != '' THEN {column}::timestamptz ELSE {fallback} END
                    );{set_default}
                END IF;"""
        )
    return "DO $$\nBEGIN" + "".join(blocks) + "\nEND $$;"


async def _step_run_batch_columns(conn) -> None:
    """Run and batch UUID columns and timestamps."""
    # Safe schema update for Run and Batch UUID columns and timestamps
    await conn.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS run_id VARCHAR(64);"))
    await conn.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS batch_id VARCHAR(64);"))
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;")
    )
    await conn.execute(text(_timestamptz_migration_sql()))
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_questions_run_id ON questions (run_id);")
    )
    await conn.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS job_id VARCHAR(64);"))
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_questions_job_id ON questions (job_id);")
    )


async def _step_retry_tracking_columns(conn) -> None:
    """Autonomous set retry tracking."""
    # Safe schema update for autonomous set retry tracking
    await conn.execute(
        text("ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS trial_count INTEGER DEFAULT 1;")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'in_bank';")
    )
    await conn.execute(text("UPDATE questions SET status = 'in_bank' WHERE status IS NULL;"))


async def _step_soft_delete_columns(conn) -> None:
    """Soft-deletion support."""
    # Safe schema update for soft-deletion support
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;")
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_questions_is_deleted ON questions (is_deleted);")
    )
    await conn.execute(
        text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;")
    )
    await conn.execute(
        text("ALTER TABLE passages ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;")
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_passages_is_deleted ON passages (is_deleted);")
    )
    await conn.execute(
        text("ALTER TABLE passages ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;")
    )


async def _step_composite_indexes(conn) -> None:
    """Composite indexes for repository filtering, metrics and pagination."""
    # Composite indexes for accelerated repository filtering, metrics, and pagination
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_questions_status_is_del_created "
            "ON questions (status, is_deleted, created_at DESC);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_questions_section_status ON questions (section, status);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_batches_status_created "
            "ON generation_batches (status, created_at DESC);"
        )
    )


async def _step_job_tracking_columns(conn) -> None:
    """Batch job tracking columns."""
    # Safe schema update for batch job tracking columns
    await conn.execute(
        text(
            "ALTER TABLE generation_batches ADD COLUMN IF NOT EXISTS total_jobs INTEGER DEFAULT 10;"
        )
    )
    await conn.execute(
        text(
            "ALTER TABLE generation_batches ADD COLUMN IF NOT EXISTS completed_jobs INTEGER DEFAULT 0;"
        )
    )
    await conn.execute(
        text(
            "ALTER TABLE generation_batches ADD COLUMN IF NOT EXISTS failed_jobs INTEGER DEFAULT 0;"
        )
    )
    await conn.execute(
        text("ALTER TABLE generation_batches ADD COLUMN IF NOT EXISTS error_message TEXT;")
    )
    await conn.execute(
        text("ALTER TABLE generation_batches ADD COLUMN IF NOT EXISTS request_payload JSONB;")
    )


async def _step_passage_batch_indexes(conn) -> None:
    """Indexes and image columns for passages and batches."""
    # Safe indexes and image columns for passages and batches
    await conn.execute(text("ALTER TABLE passages ADD COLUMN IF NOT EXISTS image_url TEXT;"))
    await conn.execute(text("ALTER TABLE passages ALTER COLUMN image_url TYPE TEXT;"))
    await conn.execute(text("ALTER TABLE passages ADD COLUMN IF NOT EXISTS image_svg TEXT;"))
    await conn.execute(
        text("ALTER TABLE passages ADD COLUMN IF NOT EXISTS image_description TEXT;")
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_passages_section ON passages (section);")
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_passages_created_at ON passages (created_at);")
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_batches_created_at ON generation_batches (created_at);")
    )


async def _step_fulltext_index(conn) -> None:
    """GIN full-text search index on questions."""
    # GIN Full-Text Search index on questions
    await conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_questions_fts ON questions USING gin (
                to_tsvector('english',
                    coalesce(question_stem, '') || ' ' ||
                    coalesce(stimulus_text, '') || ' ' ||
                    coalesce(subtopic, '') || ' ' ||
                    coalesce(explanation, '')
                )
            );
            """
        )
    )


async def _step_backfill_passages(conn) -> None:
    """Backfill passages from existing questions."""
    # 1. Backfill passages from existing questions having passage_id & stimulus_text
    await conn.execute(
        text(
            """
            INSERT INTO passages (id, text, section, subtopic, created_at, updated_at)
            SELECT DISTINCT ON (passage_id)
                passage_id,
                stimulus_text,
                section,
                subtopic,
                created_at,
                updated_at
            FROM questions
            WHERE passage_id IS NOT NULL AND stimulus_text IS NOT NULL AND trim(stimulus_text) != ''
            ON CONFLICT (id) DO NOTHING;
            """
        )
    )

    # Ensure any other orphaned passage_id is covered before setting FK
    await conn.execute(
        text(
            """
            INSERT INTO passages (id, text, created_at)
            SELECT DISTINCT q.passage_id, coalesce(q.stimulus_text, ''), q.created_at
            FROM questions q
            LEFT JOIN passages p ON q.passage_id = p.id
            WHERE q.passage_id IS NOT NULL AND p.id IS NULL
            ON CONFLICT (id) DO NOTHING;
            """
        )
    )


async def _step_backfill_batches(conn) -> None:
    """Backfill generation_batches from existing questions."""
    # 2. Backfill generation_batches from existing questions having batch_id
    await conn.execute(
        text(
            """
            INSERT INTO generation_batches (
                id, section, subtopic, difficulty, passage_mode,
                actual_count, total_tokens, cost_usd, status, created_at, updated_at
            )
            SELECT
                batch_id,
                max(section) as section,
                max(subtopic) as subtopic,
                max(difficulty) as difficulty,
                max(passage_mode) as passage_mode,
                count(id) as actual_count,
                coalesce(sum(total_tokens), 0) as total_tokens,
                coalesce(sum(cost_usd), 0.0) as cost_usd,
                'completed' as status,
                min(created_at) as created_at,
                max(updated_at) as updated_at
            FROM questions
            WHERE batch_id IS NOT NULL
            GROUP BY batch_id
            ON CONFLICT (id) DO NOTHING;
            """
        )
    )

    # Ensure any orphaned batch_id is covered before setting FK
    await conn.execute(
        text(
            """
            INSERT INTO generation_batches (id, created_at)
            SELECT DISTINCT q.batch_id, q.created_at
            FROM questions q
            LEFT JOIN generation_batches b ON q.batch_id = b.id
            WHERE q.batch_id IS NOT NULL AND b.id IS NULL
            ON CONFLICT (id) DO NOTHING;
            """
        )
    )


async def _step_fk_question_passage(conn) -> None:
    """Foreign key questions.passage_id -> passages.id."""
    # 3. Safe Foreign Key: questions.passage_id -> passages.id
    await conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'fk_questions_passage_id'
                ) THEN
                    ALTER TABLE questions
                    ADD CONSTRAINT fk_questions_passage_id
                    FOREIGN KEY (passage_id) REFERENCES passages(id) ON DELETE SET NULL;
                END IF;
            END $$;
            """
        )
    )


async def _step_fk_question_batch(conn) -> None:
    """Foreign key questions.batch_id -> generation_batches.id."""
    # 4. Safe Foreign Key: questions.batch_id -> generation_batches.id
    await conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'fk_questions_batch_id'
                ) THEN
                    ALTER TABLE questions
                    ADD CONSTRAINT fk_questions_batch_id
                    FOREIGN KEY (batch_id) REFERENCES generation_batches(id) ON DELETE SET NULL;
                END IF;
            END $$;
            """
        )
    )


async def _step_fk_question_job(conn) -> None:
    """Foreign key questions.job_id -> generation_jobs.id."""
    # 5. Safe Foreign Key: questions.job_id -> generation_jobs.id
    await conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'fk_questions_job_id'
                ) THEN
                    ALTER TABLE questions
                    ADD CONSTRAINT fk_questions_job_id
                    FOREIGN KEY (job_id) REFERENCES generation_jobs(id) ON DELETE SET NULL;
                END IF;
            END $$;
            """
        )
    )


async def _step_reconcile_question_status(conn) -> None:
    """Reconcile question status for the two-tier quality thresholds."""
    # 6. Reconcile question status for the two-tier quality thresholds. The numbers come from
    # config (never literals) so this SQL cannot drift from determine_question_status:
    # > PASSING -> ai_validated, (BATCH, PASSING] -> batch_only, <= BATCH -> below_threshold.
    thresholds = {
        "passing": int(config.PASSING_SCORE_THRESHOLD),
        "batch": int(config.BATCH_PASSING_SCORE_THRESHOLD),
    }
    await conn.execute(
        text(
            """
            UPDATE questions
            SET status = 'batch_only'
            WHERE status = 'ai_validated'
              AND final_score > :batch AND final_score <= :passing;
            """
        ),
        thresholds,
    )
    await conn.execute(
        text(
            """
            UPDATE questions
            SET status = 'below_threshold'
            WHERE status = 'ai_validated' AND final_score <= :batch;
            """
        ),
        thresholds,
    )


# Single-column indexes made redundant by a composite whose leading column is the same: the
# composite serves every query the single-column index could (and the batch_id one still backs the
# generation_batches foreign key). Dropped only when the covering composite really exists.
_REDUNDANT_INDEXES = (
    ("ix_questions_status", "ix_questions_status_created"),
    ("ix_questions_section", "ix_questions_section_status"),
    ("ix_questions_batch_id", "ix_questions_batch_job"),
)


async def _step_drop_redundant_indexes(conn) -> None:
    """Drop single-column question indexes that a composite index already covers."""
    result = await conn.execute(
        text("SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()")
    )
    existing = {row[0].lower() for row in result.fetchall()}
    for redundant, covering in _REDUNDANT_INDEXES:
        if redundant in existing and covering in existing:
            await conn.execute(text(f"DROP INDEX IF EXISTS {redundant};"))


# Ordered, idempotent migration steps. Schema steps run through the lock-avoiding connection;
# data steps (backfills, foreign keys, status reconciliation) run in a second transaction.
_SCHEMA_STEPS = (
    _step_token_columns,
    _step_matrix_columns,
    _step_taxonomy_columns,
    _step_dedup_columns,
    _step_run_batch_columns,
    _step_retry_tracking_columns,
    _step_soft_delete_columns,
    _step_composite_indexes,
    _step_job_tracking_columns,
    _step_passage_batch_indexes,
    _step_fulltext_index,
    _step_drop_redundant_indexes,
)
_DATA_STEPS = (
    _step_backfill_passages,
    _step_backfill_batches,
    _step_fk_question_passage,
    _step_fk_question_batch,
    _step_fk_question_job,
    _step_reconcile_question_status,
)


async def init_db_schema(engine: AsyncEngine):
    """Initializes PostgreSQL tables, verifies schema columns, backfills passages/batches, and ensures FTS indexes."""
    async with engine.begin() as raw_conn:
        await raw_conn.run_sync(Base.metadata.create_all)
        # Read the catalog AFTER create_all so freshly created tables are included
        columns, indexes = await _load_existing_schema(raw_conn)
        conn = _IdempotentConnection(raw_conn, columns, indexes)
        for step in _SCHEMA_STEPS:
            await step(conn)

    # Data backfill, foreign key constraints and status reconciliation
    async with engine.begin() as conn:
        for step in _DATA_STEPS:
            await step(conn)

    logger.info(
        "PostgreSQL tables verified / created successfully with passages, batches, matrix columns, FKs, and FTS."
    )
