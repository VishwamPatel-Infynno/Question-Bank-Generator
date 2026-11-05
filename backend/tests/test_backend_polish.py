"""Difficulty alias filtering, OpenAPI generation and the narrowed JSON parsing."""

import uuid

import pytest
from app.agents.base import safe_json_loads
from app.repositories import get_questions, save_question
from factories import make_question


def _q(difficulty, marker):
    return make_question(difficulty=difficulty, subtopic=marker)


@pytest.mark.requires_db
@pytest.mark.asyncio
@pytest.mark.parametrize("filter_value", ["hard", "HIGH", " High "])
async def test_difficulty_filter_treats_every_spelling_of_a_level_alike(filter_value):
    marker = f"alias-{uuid.uuid4()}"
    saved = [await save_question(_q(d, marker)) for d in ("high", "Hard", "low", "medium")]
    ids = {q.id for q in saved}
    found = await get_questions(difficulty=filter_value, limit=None)
    got = {q.id for q in found} & ids
    assert got == {saved[0].id, saved[1].id}


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_difficulty_sort_orders_low_then_medium_then_high():
    marker = f"sort-{uuid.uuid4()}"
    saved = [await save_question(_q(d, marker)) for d in ("Hard", "easy", "Standard")]
    found = await get_questions(sort_by="difficulty", limit=None)
    order = [q.id for q in found if q.id in {s.id for s in saved}]
    assert order == [saved[1].id, saved[2].id, saved[0].id]


def test_openapi_schema_builds_with_the_annotated_routes():
    from app.main import core_app

    schema = core_app.openapi()
    assert "/api/questions" in schema["paths"] and "/api/batches" in schema["paths"]


def test_malformed_json_still_raises_a_value_error():
    assert safe_json_loads('{"a": 1}') == {"a": 1}
    with pytest.raises(ValueError):
        safe_json_loads("definitely not json at all")
