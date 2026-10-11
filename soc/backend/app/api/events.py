"""Server-Sent Events endpoint for the live Pipeline Mesh.

One-way, server→dashboard feed of pipeline-stage events. SSE (not WebSocket) is
sufficient and simpler for a single-instance lab. Each client gets its own
subscriber queue; the queue is unsubscribed when the client disconnects so
repeated dashboard reloads during a demo don't leak subscriber queues.
"""
import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from soc.backend.app.events.bus import bus

router = APIRouter(prefix="/api", tags=["Events"])


@router.get("/events/stream")
async def stream_events(request: Request):
    q = bus.subscribe()

    async def gen():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream")
