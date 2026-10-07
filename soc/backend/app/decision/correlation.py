"""
Incident Correlation.

Collapses many alerts into a single incident keyed by ``(src_ip, family)`` within
a sliding time window (``correlation.window_s`` in policies.yaml). A DoS burst that
generates thousands of flows therefore produces ONE incident, not thousands of
alerts — the property Phase 5's ``dos_burst`` scenario checks.

Also computes the repeat-offender count: how many alerts this source has produced
inside the repeat-offender window, which feeds both the risk bonus and the
``repeat_count_gte`` rule condition.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from soc.backend.app.db.models import Alert, Incident, IncidentStatus
from soc.backend.app.policy.loader import PolicyBundle


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    """SQLite may hand back naive datetimes; treat them as UTC for comparison."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def correlate(
    db: Session,
    policy: PolicyBundle,
    *,
    src_ip: str,
    family: str,
    ts: Optional[datetime] = None,
    risk_score: float = 0.0,
) -> Incident:
    """
    Find an open incident for ``(src_ip, family)`` whose ``last_seen`` is within the
    correlation window and attach to it; otherwise open a new incident.

    The incident's ``alert_count`` and ``max_risk`` are updated, and ``last_seen`` is
    advanced. The caller is responsible for committing.
    """
    now = ts or _utcnow()
    window = timedelta(seconds=policy.correlation_window_s)

    existing = db.execute(
        select(Incident)
        .where(
            Incident.key_src_ip == src_ip,
            Incident.family == family,
            Incident.status == IncidentStatus.OPEN,
        )
        .order_by(Incident.last_seen.desc())
        .limit(1)
    ).scalar_one_or_none()

    if existing is not None and (now - _as_aware(existing.last_seen)) <= window:
        existing.alert_count += 1
        existing.last_seen = now
        existing.max_risk = max(existing.max_risk, risk_score)
        db.flush()
        return existing

    incident = Incident(
        key_src_ip=src_ip,
        family=family,
        first_seen=now,
        last_seen=now,
        alert_count=1,
        max_risk=risk_score,
        status=IncidentStatus.OPEN,
    )
    db.add(incident)
    db.flush()
    return incident


def repeat_count(db: Session, policy: PolicyBundle, *, src_ip: str, ts: Optional[datetime] = None) -> int:
    """Count prior alerts from ``src_ip`` within the repeat-offender window."""
    now = ts or _utcnow()
    since = now - timedelta(seconds=policy.repeat_offender.window_s)
    count = db.execute(
        select(func.count(Alert.id)).where(Alert.src_ip == src_ip, Alert.ts >= since)
    ).scalar_one()
    return int(count or 0)
