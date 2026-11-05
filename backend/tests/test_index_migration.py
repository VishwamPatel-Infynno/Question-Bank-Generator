"""The redundant single-column question indexes are dropped, covering composites stay."""

import pytest
from app.db.session import engine, init_db
from sqlalchemy import text

pytestmark = pytest.mark.requires_db

DROPPED = {"ix_questions_status", "ix_questions_section", "ix_questions_batch_id"}
KEPT = {"ix_questions_status_created", "ix_questions_section_status", "ix_questions_batch_job"}


async def test_redundant_indexes_dropped_and_idempotent():
    await init_db()
    await init_db()  # a second run must be a no-op: nothing re-created, nothing failing
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'questions'")
        )
        names = {r[0] for r in res.fetchall()}
    assert not (DROPPED & names)
    assert names >= KEPT
