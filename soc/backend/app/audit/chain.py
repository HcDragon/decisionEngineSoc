"""
Hash-Chained Audit Trail.

Every critical state transition (alert ingested, decision made, action executed,
approval recorded, mode change, policy reload) appends a tamper-evident record:

    hash = sha256(prev_hash + canonical_json(payload))

The chain starts from a fixed genesis hash (64 zeros). Any modification to a past
payload breaks every subsequent hash, so the chain can be verified end-to-end.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from soc.backend.app.db.models import AuditLog

GENESIS_HASH = "0" * 64


def canonical_json(payload: Any) -> str:
    """Deterministic JSON encoding used for hashing (sorted keys, no whitespace)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(prev_hash: str, payload: Any) -> str:
    return hashlib.sha256((prev_hash + canonical_json(payload)).encode("utf-8")).hexdigest()


def _latest_hash(db: Session) -> str:
    row = db.execute(
        select(AuditLog.hash).order_by(AuditLog.id.desc()).limit(1)
    ).scalar_one_or_none()
    return row or GENESIS_HASH


def append_audit(
    db: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: Dict[str, Any],
    actor: str = "system",
    flush: bool = True,
) -> AuditLog:
    """Append one record to the chain. Caller controls the surrounding transaction;
    we flush (not commit) so the row participates in the caller's unit of work."""
    prev = _latest_hash(db)
    h = compute_hash(prev, payload)
    entry = AuditLog(
        actor=actor,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id),
        payload=payload,
        prev_hash=prev,
        hash=h,
    )
    db.add(entry)
    if flush:
        db.flush()
    return entry


def verify_chain(db: Session) -> Dict[str, Any]:
    """Recompute the whole chain and report the first break, if any."""
    rows: List[AuditLog] = list(
        db.execute(select(AuditLog).order_by(AuditLog.id.asc())).scalars()
    )
    prev = GENESIS_HASH
    for row in rows:
        if row.prev_hash != prev:
            return {"valid": False, "broken_at_id": row.id, "reason": "prev_hash mismatch"}
        expected = compute_hash(prev, row.payload)
        if row.hash != expected:
            return {"valid": False, "broken_at_id": row.id, "reason": "hash mismatch"}
        prev = row.hash
    return {"valid": True, "count": len(rows), "head": prev}
