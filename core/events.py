"""
In-memory event bus for SSE streaming.

Each running analysis gets an asyncio.Queue. The background debate task
pushes typed events; the SSE endpoint reads and forwards them to the client.

Design notes:
- Works for single-process deployments (FastAPI BackgroundTasks).
- If scaling to multi-process (Celery), replace with Redis pub/sub.
- Queues are created at analysis submission time so no events are missed
  even if the client connects slightly after the debate starts.
"""

import asyncio
import json
from typing import Any
from uuid import UUID

_queues: dict[str, asyncio.Queue] = {}

# Sentinel pushed when the debate is complete (or failed).
_DONE = object()


def create_queue(analysis_id: UUID) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _queues[str(analysis_id)] = q
    return q


def get_queue(analysis_id: UUID) -> asyncio.Queue | None:
    return _queues.get(str(analysis_id))


def drop_queue(analysis_id: UUID) -> None:
    _queues.pop(str(analysis_id), None)


async def push(analysis_id: UUID, event: str, data: Any) -> None:
    q = _queues.get(str(analysis_id))
    if q:
        await q.put({"event": event, "data": data})


async def push_done(analysis_id: UUID) -> None:
    q = _queues.get(str(analysis_id))
    if q:
        await q.put(_DONE)


def is_done_sentinel(item: Any) -> bool:
    return item is _DONE


def format_sse(event: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"
