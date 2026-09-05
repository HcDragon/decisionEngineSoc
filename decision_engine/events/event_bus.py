import asyncio
import threading
from typing import Callable, Dict, List, Any, Optional
from datetime import datetime, timezone

class EventBus:
    """
    Real-Time Internal Event Bus for publishing and subscribing to Decision Engine lifecycle events.
    Supports asynchronous subscribers, thread-safe sync dispatch, and queue broadcasting for SSE/WebSockets.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventBus, cls).__new__(cls)
                cls._instance._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
                cls._instance._queues: List[asyncio.Queue] = []
                cls._instance._history: List[Dict[str, Any]] = []
                cls._instance._max_history = 200
            return cls._instance

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe a synchronous callback to an event type (or '*' for all events)."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def register_queue(self) -> asyncio.Queue:
        """Register an asyncio.Queue for real-time streaming (SSE/WebSocket)."""
        q = asyncio.Queue()
        self._queues.append(q)
        return q

    def unregister_queue(self, q: asyncio.Queue):
        """Unregister an asyncio.Queue when a client disconnects."""
        if q in self._queues:
            self._queues.remove(q)

    def publish(self, event_type: str, payload: Dict[str, Any]):
        """
        Publishes an event to all subscribers and active streaming queues.
        """
        event_message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": payload
        }
        
        # Save to circular history
        self._history.append(event_message)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Notify direct callbacks
        callbacks = list(self._subscribers.get(event_type, [])) + list(self._subscribers.get("*", []))
        for cb in callbacks:
            try:
                cb(event_message)
            except Exception as e:
                # Event delivery error shouldn't crash the pipeline
                pass

        # Push to async queues for dashboard streaming
        for q in list(self._queues):
            try:
                q.put_nowait(event_message)
            except Exception:
                pass

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent events in chronological order."""
        return self._history[-limit:]
