"""
test_stream_emitter.py - Unit tests for stream_emitter.py SSE consumer and terminal assembly.
"""

from __future__ import annotations

import asyncio

import pytest
from app.schemas import Difficulty, GenerationRequest, MCATSection, WorkflowEvent
from app.workflow.stream_emitter import (
    build_terminal_workflow_event,
    drain_event_queue,
    format_sse_event,
)


def _dummy_make_event(event_type: str, agent_name: str, message: str, data: dict) -> WorkflowEvent:
    return WorkflowEvent(
        event_type=event_type,
        agent_name=agent_name,
        message=message,
        data=data,
    )


def test_format_sse_event_model():
    evt = WorkflowEvent(
        event_type="test_event",
        agent_name="System",
        message="Hello World",
        data={"key": "val"},
    )
    formatted = format_sse_event(evt)
    assert formatted.startswith("data: ")
    assert formatted.endswith("\n\n")
    assert '"event_type":"test_event"' in formatted
    assert '"message":"Hello World"' in formatted


def test_format_sse_event_dict():
    payload = {"event": "custom", "num": 42}
    formatted = format_sse_event(payload)
    assert formatted.startswith("data: ")
    assert formatted.endswith("\n\n")
    assert '"event": "custom"' in formatted
    assert '"num": 42' in formatted


@pytest.mark.asyncio
async def test_drain_event_queue_clean_exit_sentinel():
    queue: asyncio.Queue[WorkflowEvent | None] = asyncio.Queue()
    monitor_done = asyncio.Event()

    evt1 = _dummy_make_event("step_1", "Agent1", "Message 1", {})
    evt2 = _dummy_make_event("step_2", "Agent2", "Message 2", {})
    await queue.put(evt1)
    await queue.put(evt2)
    await queue.put(None)  # Sentinel

    chunks: list[str] = []
    async for chunk in drain_event_queue(queue, monitor_done, poll_timeout=0.1):
        chunks.append(chunk)

    assert len(chunks) == 2
    assert "step_1" in chunks[0]
    assert "step_2" in chunks[1]


@pytest.mark.asyncio
async def test_drain_event_queue_exit_via_monitor_done():
    queue: asyncio.Queue[WorkflowEvent | None] = asyncio.Queue()
    monitor_done = asyncio.Event()

    evt1 = _dummy_make_event("step_1", "Agent1", "Message 1", {})
    await queue.put(evt1)
    monitor_done.set()  # Monitor finishes without putting sentinel

    chunks: list[str] = []
    async for chunk in drain_event_queue(queue, monitor_done, poll_timeout=0.05):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert "step_1" in chunks[0]


def test_build_terminal_workflow_event_complete():
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=1,
    )
    staged = [{"id": "q1", "stem": "Test question stem"}]
    evt = build_terminal_workflow_event(
        make_event=_dummy_make_event,
        layout=None,
        req=req,
        total_qty=1,
        all_staged_questions=staged,
        outcomes_rejections=[],
        outcomes_errors=[],
        usage_totals={"total_tokens": 500},
        all_agent_usage=[],
        passage_state=None,
        batch_id="batch-123",
        shared_passage_id=None,
        is_single_passage_set=False,
        shared_passage_payload_fn=lambda _layout, _state: {},
        complete_message_fn=lambda _layout, _qs, _usage: "Run completed successfully.",
    )
    assert evt.event_type == "workflow_complete"
    assert evt.data["batch_id"] == "batch-123"
    assert len(evt.data["questions"]) == 1


def test_build_terminal_workflow_event_rejected():
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=1,
    )
    rejections = [{"score": 65, "reason": "Weak distractors"}]
    evt = build_terminal_workflow_event(
        make_event=_dummy_make_event,
        layout=None,
        req=req,
        total_qty=1,
        all_staged_questions=[],
        outcomes_rejections=rejections,
        outcomes_errors=[],
        usage_totals={"total_tokens": 400},
        all_agent_usage=[],
        passage_state=None,
        batch_id="batch-123",
        shared_passage_id=None,
        is_single_passage_set=False,
        shared_passage_payload_fn=lambda _layout, _state: {},
        complete_message_fn=lambda _layout, _qs, _usage: "",
    )
    assert evt.event_type == "workflow_rejected"
    assert evt.agent_name == "Quality Gate"
    assert evt.data["total_rejected"] == 1


def test_build_terminal_workflow_event_error():
    req = GenerationRequest(
        section=MCATSection.BIO_BIOCHEM,
        difficulty=Difficulty.MEDIUM,
        questions_to_generate=1,
    )
    evt = build_terminal_workflow_event(
        make_event=_dummy_make_event,
        layout=None,
        req=req,
        total_qty=1,
        all_staged_questions=[],
        outcomes_rejections=[],
        outcomes_errors=["LLM timeout on generation attempt 3"],
        usage_totals={"total_tokens": 300},
        all_agent_usage=[],
        passage_state=None,
        batch_id="batch-123",
        shared_passage_id=None,
        is_single_passage_set=False,
        shared_passage_payload_fn=lambda _layout, _state: {},
        complete_message_fn=lambda _layout, _qs, _usage: "",
    )
    assert evt.event_type == "workflow_error"
    assert "LLM timeout on generation attempt 3" in evt.message
    assert evt.data["error"] == "LLM timeout on generation attempt 3"
