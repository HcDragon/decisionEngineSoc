"""In-process pub/sub for the live Pipeline Mesh event stream.

A single-instance lab needs no broker: each SSE subscriber gets its own bounded
``asyncio.Queue`` and ``publish()`` fans out to all of them. ``publish()`` is
called synchronously from the capture worker thread (inside ``process_flow`` /
``_record_native_flow``), so it must never block, await, or do I/O.

Thread-safety note: an ``asyncio.Queue`` is not thread-safe and its consumer
(the SSE coroutine awaiting ``q.get()``) runs on the event loop, while
``publish()`` runs on a worker thread. So we capture the loop at ``subscribe()``
time and hand items over with ``loop.call_soon_threadsafe`` — that both wakes the
awaiting consumer promptly and keeps the queue mutation on the loop thread. When
there is no running loop (e.g. a unit test), we fall back to a direct
``put_nowait`` so the bus is still testable in isolation.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("soc.events")


def _safe_put(q: "asyncio.Queue", data: str) -> None:
    try:
        q.put_nowait(data)
    except asyncio.QueueFull:
        pass  # slow consumer — drop, never block the pipeline


class EventBus:
    def __init__(self) -> None:
        # (queue, loop-that-owns-it). loop is None when subscribed without a
        # running event loop (unit tests).
        self._subscribers: List[Tuple[asyncio.Queue, Optional[asyncio.AbstractEventLoop]]] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        try:
            loop: Optional[asyncio.AbstractEventLoop] = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        self._subscribers.append((q, loop))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers = [(qq, lp) for (qq, lp) in self._subscribers if qq is not q]

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def publish(self, stage: str, payload: Dict[str, Any]) -> None:
        """Fan a {stage, payload} event out to every subscriber. Never raises."""
        try:
            data = json.dumps({"stage": stage, "payload": payload}, default=str)
        except Exception:  # pragma: no cover - defensive; payloads are small/simple
            return
        for q, loop in list(self._subscribers):
            try:
                if loop is not None and loop.is_running():
                    loop.call_soon_threadsafe(_safe_put, q, data)
                else:
                    _safe_put(q, data)
            except Exception:
                pass  # a dead/closed loop must never break the capture path


bus = EventBus()
