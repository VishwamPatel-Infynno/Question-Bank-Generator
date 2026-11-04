from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas import GenerationRequest
from app.workflow import run_workflow_stream

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Multi-Agent Generation"])


@router.post("/generate")
async def generate_mcat_question(req: GenerationRequest):
    """
    Triggers the multi-agent workflow (Generator -> Reviewer -> Re-Generator -> Image Generator)
    and streams live progress events via Server-Sent Events (SSE).
    """
    return StreamingResponse(
        run_workflow_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
