"""One source of truth for authoring numbers; DDL helper that never locks migrated tables."""

import re

import pytest
from app.agents import prompt_builder, prompts, regenerator, standards
from app.db.init_db import _IdempotentConnection
from app.schemas import GenerationRequest
from sqlalchemy import text


def test_option_spread_limit_scales_with_option_length():
    assert standards.option_spread_limit(4) == 3
    assert standards.option_spread_limit(12) == 3
    assert standards.option_spread_limit(25) == 5
    assert standards.option_spread_limit(40) == 8


def test_every_prompt_quotes_the_shared_numbers_and_no_stale_ones():
    texts = {
        "generator": prompts.GENERATOR_SYSTEM_PROMPT,
        "fused": prompts.FUSED_GENERATOR_SYSTEM_PROMPT,
        "reviewer": prompts.REVIEWER_SYSTEM_PROMPT,
        "regenerator": prompts.REGENERATOR_SYSTEM_PROMPT,
    }
    for name, body in texts.items():
        assert "<<" not in body, f"{name} prompt has an unresolved placeholder"
        for stale in ("1-2 words", "1-3 words", "2-4 words", "within 1 to 3", "±15%"):
            assert stale not in body, f"{name} prompt still says {stale!r}"
        assert "250-400" not in body and "320-450" not in body
    assert standards.OPTION_PARITY_TEXT in prompts.REVIEWER_SYSTEM_PROMPT
    assert "300-500" in prompts.GENERATOR_SYSTEM_PROMPT
    assert "500-600" in prompts.GENERATOR_SYSTEM_PROMPT


def test_user_prompts_use_the_same_option_rule():
    req = GenerationRequest(section="CP", subtopic="K", difficulty="Medium")
    for fused in (True, False):
        built = prompt_builder._build_generator_user_prompt(req, fused=fused)
        assert standards.OPTION_PARITY_TEXT in built
        assert not re.search(r"within 1 to 3|2-4 words|±15%", built)
    assert (
        standards.OPTION_PARITY_TEXT
        in regenerator.regenerate_question.__globals__["OPTION_PARITY_TEXT"]
    )


def test_is_cars_helper_accepts_enums_and_strings():
    assert standards.is_cars("CARS") and standards.is_cars("cars")
    assert not standards.is_cars("chem_phys")


class _FakeConn:
    def __init__(self):
        self.executed = []

    async def execute(self, stmt, *a, **k):
        self.executed.append(stmt.text)


@pytest.mark.asyncio
async def test_existing_columns_and_indexes_are_not_re_issued():
    fake = _FakeConn()
    conn = _IdempotentConnection(fake, {("questions", "total_tokens")}, {"ix_questions_status"})
    await conn.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS total_tokens INTEGER"))
    await conn.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS brand_new INTEGER"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_status ON questions (status)"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_new ON questions (topic)"))
    await conn.execute(text("UPDATE questions SET status = 'in_bank' WHERE status IS NULL"))
    assert [s.split()[0] for s in fake.executed] == ["ALTER", "CREATE", "UPDATE"]
    assert "brand_new" in fake.executed[0] and "ix_new" in fake.executed[1]
