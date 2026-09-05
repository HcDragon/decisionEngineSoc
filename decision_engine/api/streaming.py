import asyncio
import json
from fastapi import Request
from fastapi.responses import StreamingResponse
from decision_engine.events.event_bus import EventBus

async def sse_event_generator(request: Request, event_bus: EventBus):
    """
    Asynchronous Server-Sent Events (SSE) generator streaming live Decision Engine events.
    """
    queue = event_bus.register_queue()
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                # Wait for next event with a periodic keep-alive ping
                event_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(event_data)}\n\n"
            except asyncio.TimeoutError:
                # Keep-alive ping comment to prevent client timeout
                yield ": ping\n\n"
    finally:
        event_bus.unregister_queue(queue)
