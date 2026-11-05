from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.security import limit_generation_requests
from app.schemas import GenerationRequest
from app.workflow import run_workflow_stream

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Multi-Agent Generation"])

SSE_KEEPALIVE_SECONDS = 15.0


async def with_keepalive(
    source: AsyncIterator[str], interval: float = SSE_KEEPALIVE_SECONDS
) -> AsyncIterator[str]:
    """Yields the source's events and an SSE comment line whenever it is quiet for ``interval``.

    LLM stages can take a minute or more with no events; proxies and browsers drop idle
    connections, so a periodic ``: keepalive`` comment keeps the stream open. Comment lines are
    ignored by SSE clients, so the event payloads are unchanged.
    """
    pending = asyncio.ensure_future(source.__anext__())
    try:
        while True:
            done, _ = await asyncio.wait({pending}, timeout=interval)
            if not done:
                yield ": keepalive\n\n"
                continue
            try:
                item = pending.result()
            except StopAsyncIteration:
                return
            yield item
            pending = asyncio.ensure_future(source.__anext__())
    finally:
        # Stop any in-flight read first, then close the source so its own cleanup runs.
        if not pending.done():
            pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        aclose = getattr(source, "aclose", None)
        if aclose is not None:
            await aclose()


@router.post("/generate", dependencies=[Depends(limit_generation_requests)])
async def generate_mcat_question(req: GenerationRequest):
    """
    Triggers the multi-agent workflow (Generator -> Reviewer -> Re-Generator -> Image Generator)
    and streams live progress events via Server-Sent Events (SSE).
    """
    return StreamingResponse(
        with_keepalive(run_workflow_stream(req)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
