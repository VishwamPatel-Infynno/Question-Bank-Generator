"""Reading the engine's Server-Sent-Events text stream back into event dicts."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any


async def iter_sse_events(stream: AsyncIterator[str]) -> AsyncIterator[dict[str, Any]]:
    """Yields the JSON payload of every ``data:`` line; other lines and bad JSON are skipped."""
    async for raw_chunk in stream:
        line = raw_chunk.strip()
        if not line.startswith("data: "):
            continue
        try:
            yield json.loads(line[6:])
        except json.JSONDecodeError:
            continue
