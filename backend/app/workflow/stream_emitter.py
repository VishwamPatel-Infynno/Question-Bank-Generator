"""
stream_emitter.py - Asynchronous event queue consumer and SSE framing for workflow streams.

Encapsulates bounded queue polling, consumer timeout handling, backpressure enforcement,
JSON data framing for Server-Sent Events (SSE), and terminal event construction.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Callable
from typing import Any

from app.core.config import config
from app.schemas import GenerationRequest, WorkflowEvent

__all__ = [
    "build_terminal_workflow_event",
    "drain_event_queue",
    "format_sse_event",
]


def format_sse_event(event: WorkflowEvent | dict[str, Any]) -> str:
    """Formats a WorkflowEvent model or dictionary into an SSE data frame."""
    if hasattr(event, "model_dump_json"):
        return f"data: {event.model_dump_json()}\n\n"
    return f"data: {json.dumps(event)}\n\n"


async def drain_event_queue(
    event_queue: asyncio.Queue[WorkflowEvent | None],
    monitor_done: asyncio.Event,
    poll_timeout: float = 1.0,
) -> AsyncGenerator[str, None]:
    """
    Drains a bounded asyncio.Queue of WorkflowEvents, formatting each as SSE data chunks.

    Exits cleanly when a None sentinel is received or when monitor_done is set
    and the event queue has been completely drained.
    """
    while True:
        try:
            evt = await asyncio.wait_for(event_queue.get(), timeout=poll_timeout)
        except TimeoutError:
            if monitor_done.is_set() and event_queue.empty():
                break
            continue
        if evt is None:
            break
        yield format_sse_event(evt)


def build_terminal_workflow_event(
    *,
    make_event: Callable[..., WorkflowEvent],
    layout: Any,
    req: GenerationRequest,
    total_qty: int,
    all_staged_questions: list[dict[str, Any]],
    outcomes_rejections: list[dict[str, Any]],
    outcomes_errors: list[str],
    usage_totals: dict[str, Any],
    all_agent_usage: list[dict[str, Any]],
    passage_state: Any,
    batch_id: str,
    shared_passage_id: str | None,
    is_single_passage_set: bool,
    shared_passage_payload_fn: Callable[[Any, Any], dict[str, Any]],
    complete_message_fn: Callable[[Any, list[dict[str, Any]], dict[str, Any]], str],
) -> WorkflowEvent:
    """
    Constructs the terminal workflow event (workflow_complete, workflow_rejected, or workflow_error).
    """
    if not all_staged_questions:
        if outcomes_rejections:
            rej_msg = (
                f"All {total_qty} questions in the run were rejected by the Quality Gate "
                f"(score <= {req.passing_threshold or config.PASSING_SCORE_THRESHOLD})."
            )
            return make_event(
                event_type="workflow_rejected",
                agent_name="Quality Gate",
                message=rej_msg,
                data={
                    "rejections": outcomes_rejections,
                    "total_rejected": len(outcomes_rejections),
                    "cumulative_usage": usage_totals,
                },
            )
        error_msg = f"All {total_qty} questions in the run failed to generate after retries."
        if outcomes_errors:
            error_msg += f" Last error: {outcomes_errors[-1]}"
        return make_event(
            event_type="workflow_error",
            agent_name="System",
            message=error_msg,
            data={
                "error": outcomes_errors[-1] if outcomes_errors else error_msg,
                "errors": outcomes_errors,
                "cumulative_usage": usage_totals,
            },
        )

    return make_event(
        event_type="workflow_complete",
        agent_name="System",
        message=complete_message_fn(layout, all_staged_questions, usage_totals),
        data={
            "questions": all_staged_questions,
            "question": all_staged_questions[0] if all_staged_questions else None,
            "batch_id": batch_id,
            "passage_id": shared_passage_id if is_single_passage_set else None,
            **shared_passage_payload_fn(layout, passage_state),
            "cumulative_usage": usage_totals,
            "usage_breakdown": all_agent_usage,
        },
    )
