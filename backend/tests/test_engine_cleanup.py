"""The workflow stream must not leak worker tasks when its consumer stops reading."""

import asyncio

import pytest
from app.schemas import Difficulty, GenerationRequest, MCATSection
from app.workflow import run_workflow_stream

_ENGINE_TASKS = ("_staggered_worker", "_worker", "_monitor_tasks")


def _leaked_engine_tasks():
    return [
        t
        for t in asyncio.all_tasks()
        if not t.done() and getattr(t.get_coro(), "__name__", "") in _ENGINE_TASKS
    ]


@pytest.mark.asyncio
async def test_closing_the_stream_cancels_all_workers():
    req = GenerationRequest(
        section=MCATSection.CHEM_PHYS,
        subtopic="Kinetics",
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=4,
    )
    stream = run_workflow_stream(req)
    # Read events until the workers are running, then abandon the run mid-flight.
    for _ in range(40):
        await stream.__anext__()
        if _leaked_engine_tasks():
            break
    assert _leaked_engine_tasks(), "expected live worker tasks while the run is in progress"

    await stream.aclose()
    await asyncio.sleep(0.05)
    assert _leaked_engine_tasks() == []
