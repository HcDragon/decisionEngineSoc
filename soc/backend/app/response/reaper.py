"""
Virtual-firewall TTL reaper.

Expires active VirtualFirewall entries whose ``ttl_at`` has passed: flips the DB
row to inactive, removes the real nft rule when the lab executor is armed, and
appends a hash-chained audit record. Runs as a daemon thread started in the app
lifespan; also callable directly for tests.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone

from soc.backend.app.audit.chain import append_audit
from soc.backend.app.db.models import VirtualFirewall
from soc.backend.app.db.session import SessionLocal
from soc.backend.app.response import firewall

logger = logging.getLogger("soc.reaper")


def _as_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def expire_due(db) -> int:
    """Expire all due blocks in one pass; returns how many were expired."""
    now = datetime.now(timezone.utc)
    rows = (
        db.query(VirtualFirewall)
        .filter(VirtualFirewall.active.is_(True), VirtualFirewall.ttl_at.isnot(None))
        .all()
    )
    expired = 0
    for vf in rows:
        if _as_aware(vf.ttl_at) > now:
            continue
        removal = None
        if firewall.is_lab_enabled():
            removal = firewall.remove_block(vf.target)
        vf.active = False
        append_audit(
            db,
            event_type="firewall.expired",
            entity_type="virtual_firewall",
            entity_id=vf.id,
            payload={"target": vf.target, "kind": vf.kind.value, "removal": removal},
        )
        expired += 1
    if expired:
        db.commit()
        logger.info("Reaper expired %d firewall entr%s", expired, "y" if expired == 1 else "ies")
    return expired


def _loop(stop: threading.Event, interval: float) -> None:
    while not stop.is_set():
        try:
            db = SessionLocal()
            try:
                expire_due(db)
            finally:
                db.close()
        except Exception as e:  # never let the reaper thread die
            logger.warning("Reaper pass failed: %s", e)
        stop.wait(timeout=interval)


_stop = threading.Event()
_thread = None


def start(interval: float = 15.0) -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, args=(_stop, interval), daemon=True, name="soc-reaper")
    _thread.start()
    logger.info("Firewall TTL reaper started (interval=%.0fs)", interval)


def stop() -> None:
    _stop.set()
