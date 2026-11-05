"""Client-supplied API keys must never be persisted or returned."""

import uuid

import pytest
from app.db.session import async_session_factory
from app.models.batch import GenerationBatchModel
from app.repositories import (
    get_batch_by_id,
    get_batches,
    save_batch,
    scrub_stored_request_secrets,
)
from app.schemas import GenerationBatch, GenerationRequest

pytestmark = pytest.mark.requires_db


def _batch(batch_id: str, payload: dict) -> GenerationBatch:
    return GenerationBatch(
        id=batch_id,
        section="chem_phys",
        subtopic="Kinetics",
        difficulty="medium",
        target_count=5,
        request_payload=payload,
    )


@pytest.mark.asyncio
async def test_saved_and_returned_payloads_never_contain_api_key():
    bid = str(uuid.uuid4())
    await save_batch(_batch(bid, {"api_key": "sk-secret", "subtopic": "Kinetics"}))

    fetched = await get_batch_by_id(bid)
    assert fetched.request_payload == {"subtopic": "Kinetics"}

    listed = next(b for b in await get_batches() if b.id == bid)
    assert listed.request_payload is None  # list rows omit the payload entirely


@pytest.mark.asyncio
async def test_startup_scrub_removes_keys_stored_by_older_versions():
    bid = str(uuid.uuid4())
    async with async_session_factory() as session:  # bypass save_batch to simulate legacy data
        session.add(
            GenerationBatchModel(
                id=bid,
                section="chem_phys",
                subtopic="Kinetics",
                difficulty="medium",
                target_count=5,
                request_payload={"api_key": "sk-legacy", "subtopic": "Kinetics"},
            )
        )
        await session.commit()

    assert await scrub_stored_request_secrets() >= 1
    assert (await get_batch_by_id(bid)).request_payload == {"subtopic": "Kinetics"}


def test_request_payload_dump_for_persistence_excludes_api_key():
    req = GenerationRequest(section="CP", subtopic="K", difficulty="Medium", api_key="sk-x")
    assert "api_key" not in req.model_dump(exclude={"api_key"})
