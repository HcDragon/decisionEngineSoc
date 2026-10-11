"""Event bus + SSE endpoint tests (TC-EVENTS-*).

Unit-tests the EventBus directly (no live SSE wire format needed) and asserts the
stream route exists and advertises text/event-stream.
"""
from soc.backend.app.events.bus import EventBus
from soc.backend.app.main import app


def test_bus_publish_delivers_to_subscriber():
    """TC-EVENTS-BUS: publish() fans a {stage,payload} JSON line to a subscriber.
    Subscribed with no running loop -> publish delivers synchronously."""
    import json
    b = EventBus()
    q = b.subscribe()
    b.publish("capture", {"src_ip": "10.66.0.20", "proto": "TCP", "packets": 3})
    assert not q.empty()
    evt = json.loads(q.get_nowait())
    assert evt["stage"] == "capture"
    assert evt["payload"]["src_ip"] == "10.66.0.20"


def test_bus_unsubscribe_stops_delivery():
    """TC-EVENTS-UNSUB: after unsubscribe, publish no longer reaches the queue
    (guards against the SSE subscriber-queue leak on disconnect/reload)."""
    b = EventBus()
    q = b.subscribe()
    assert b.subscriber_count == 1
    b.unsubscribe(q)
    assert b.subscriber_count == 0
    b.publish("audit", {"incident_id": 1})
    assert q.empty()


def test_bus_publish_never_raises_on_bad_payload():
    """TC-EVENTS-SAFE: publish must never raise into the capture/decision path."""
    b = EventBus()
    b.subscribe()
    # A non-JSON-native object is handled by default=str, and any failure is
    # swallowed — either way this must not raise.
    b.publish("score", {"obj": object()})


def test_bus_bounded_queue_drops_when_full():
    """TC-EVENTS-FULL: a slow consumer's full queue drops events, never blocks."""
    b = EventBus()
    q = b.subscribe()
    for i in range(250):  # maxsize is 200
        b.publish("capture", {"n": i})
    # No exception, and the queue never exceeded its bound.
    assert q.qsize() <= 200


def test_stream_route_is_registered():
    """TC-EVENTS-ROUTE: the SSE endpoint is registered on the app.

    We assert registration via the OpenAPI schema rather than opening the live
    stream — the sync TestClient blocks forever on an infinite SSE generator.
    The content type is set in the endpoint (StreamingResponse media_type=
    'text/event-stream') and exercised live by the §3.4 manual lab run."""
    assert "/api/events/stream" in app.openapi()["paths"]
