"""
Decision Engine API — reads the records the pipeline produces.

Surfaces incidents, alerts, decisions, the virtual firewall, the hash-chained
audit trail, and the active policy version to the dashboard and analysts.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from soc.backend.app.audit.chain import append_audit, verify_chain
from soc.backend.app.config import settings
from soc.backend.app.db.models import (
    Action,
    Alert,
    Approval,
    ApprovalVerdict,
    AuditLog,
    Case,
    Decision,
    DecisionStatus,
    Incident,
    IncidentStatus,
    VirtualFirewall,
    VirtualFirewallKind,
)
from soc.backend.app.db.session import get_db
from soc.backend.app.policy.loader import get_policy

# playbook/containment action -> virtual-firewall kind
_ACTION_TO_VF = {
    "block_ip": VirtualFirewallKind.BLOCK,
    "isolate_host": VirtualFirewallKind.ISOLATE,
    "rate_limit": VirtualFirewallKind.RATE_LIMIT,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

router = APIRouter(prefix="/api", tags=["Decision Engine"])


def _decision_dict(d: Decision) -> Dict[str, Any]:
    return {
        "id": d.id,
        "incident_id": d.incident_id,
        "ts": d.ts.isoformat(),
        "risk_score": d.risk_score,
        "tier": d.tier,
        "score_breakdown": d.score_breakdown,
        "rule_id": d.rule_id,
        "mode": d.mode.value,
        "status": d.status.value,
        "playbook_id": d.playbook_id,
        "policy_hash": d.policy_hash,
    }


def _alert_dict(a: Alert) -> Dict[str, Any]:
    return {
        "id": a.id,
        "ts": a.ts.isoformat(),
        "src_ip": a.src_ip,
        "dst_ip": a.dst_ip,
        "src_port": a.src_port,
        "dst_port": a.dst_port,
        "label": a.label,
        "family": a.family,
        "confidence": a.confidence,
        "incident_id": a.incident_id,
    }


@router.get("/incidents")
async def list_incidents(
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status: open|contained|closed"),
    db: Session = Depends(get_db),
):
    """List incidents, newest first, each with its latest decision."""
    q = select(Incident).order_by(Incident.last_seen.desc()).limit(limit)
    incidents = db.execute(q).scalars().all()
    out = []
    for inc in incidents:
        if status and inc.status.value != status:
            continue
        latest = (
            db.execute(
                select(Decision)
                .where(Decision.incident_id == inc.id)
                .order_by(Decision.ts.desc())
                .limit(1)
            ).scalar_one_or_none()
        )
        out.append(
            {
                "id": inc.id,
                "src_ip": inc.key_src_ip,
                "family": inc.family,
                "first_seen": inc.first_seen.isoformat(),
                "last_seen": inc.last_seen.isoformat(),
                "alert_count": inc.alert_count,
                "max_risk": inc.max_risk,
                "status": inc.status.value,
                "latest_decision": _decision_dict(latest) if latest else None,
            }
        )
    return {"count": len(out), "incidents": out}


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: int, db: Session = Depends(get_db)):
    """Full incident detail: alerts, decisions (with traces), and cases."""
    inc = db.get(Incident, incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    alerts = db.execute(
        select(Alert).where(Alert.incident_id == incident_id).order_by(Alert.ts.desc())
    ).scalars().all()
    decisions = db.execute(
        select(Decision).where(Decision.incident_id == incident_id).order_by(Decision.ts.desc())
    ).scalars().all()
    cases = db.execute(
        select(Case).where(Case.incident_id == incident_id)
    ).scalars().all()

    decisions_full = []
    for d in decisions:
        base = _decision_dict(d)
        base["rule_trace"] = d.rule_trace
        base["guardrail_results"] = d.guardrail_results
        base["explanation"] = d.explanation
        actions = db.execute(
            select(Action).where(Action.decision_id == d.id)
        ).scalars().all()
        base["actions"] = [
            {
                "id": a.id,
                "step_id": a.step_id,
                "action": a.action,
                "params": a.params,
                "executor": a.executor,
                "dry_run": a.dry_run,
                "status": a.status,
            }
            for a in actions
        ]
        decisions_full.append(base)

    return {
        "id": inc.id,
        "src_ip": inc.key_src_ip,
        "family": inc.family,
        "first_seen": inc.first_seen.isoformat(),
        "last_seen": inc.last_seen.isoformat(),
        "alert_count": inc.alert_count,
        "max_risk": inc.max_risk,
        "status": inc.status.value,
        "alerts": [_alert_dict(a) for a in alerts],
        "decisions": decisions_full,
        "cases": [
            {"id": c.id, "title": c.title, "priority": c.priority, "status": c.status}
            for c in cases
        ],
    }


@router.get("/alerts")
async def list_alerts(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Recent alerts, newest first."""
    alerts = db.execute(
        select(Alert).order_by(Alert.ts.desc()).limit(limit)
    ).scalars().all()
    return {"count": len(alerts), "alerts": [_alert_dict(a) for a in alerts]}


@router.get("/decisions")
async def list_decisions(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Recent decisions, newest first."""
    decisions = db.execute(
        select(Decision).order_by(Decision.ts.desc()).limit(limit)
    ).scalars().all()
    return {"count": len(decisions), "decisions": [_decision_dict(d) for d in decisions]}


@router.get("/firewall")
async def list_firewall(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Virtual firewall entries (simulated containment; no real network changes)."""
    q = select(VirtualFirewall).order_by(VirtualFirewall.created_at.desc())
    rows = db.execute(q).scalars().all()
    out = [
        {
            "id": vf.id,
            "kind": vf.kind.value,
            "target": vf.target,
            "active": vf.active,
            "ttl_at": vf.ttl_at.isoformat() if vf.ttl_at else None,
            "created_at": vf.created_at.isoformat(),
        }
        for vf in rows
        if (vf.active or not active_only)
    ]
    return {"count": len(out), "entries": out}


@router.get("/audit/verify")
async def audit_verify(db: Session = Depends(get_db)):
    """Recompute and verify the hash-chained audit trail."""
    return verify_chain(db)


class RespondRequest(BaseModel):
    """Manual (analyst-driven) response request from the dashboard."""
    action: str = Field("block_ip", description="block_ip | isolate_host | rate_limit")
    ttl_s: Optional[int] = Field(None, ge=10, le=86400, description="Block lifetime; defaults to policy TTL")
    analyst: str = Field("dashboard", description="Who approved the action")
    comment: Optional[str] = Field(None, description="Optional analyst note")


@router.post("/incidents/{incident_id}/respond")
async def respond_to_incident(
    incident_id: int,
    payload: Optional[RespondRequest] = None,
    db: Session = Depends(get_db),
):
    """Manually apply a containment action to an incident (the "Block" button).

    Used when defence is set to MANUAL: the analyst reviews the incident and
    approves the response here. Honours the same executor guardrails as the
    automatic pipeline — ``simulated`` / ``dry_run`` only write DB-tracked
    virtual-firewall rows; the real ``lab`` executor additionally applies an nft
    rule (and only for in-CIDR targets). Idempotent per (target, kind).
    """
    req = payload or RespondRequest()
    inc = db.get(Incident, incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    target = inc.key_src_ip
    policy = get_policy()
    if policy.is_allowlisted(target):
        raise HTTPException(status_code=409, detail=f"{target} is allowlisted; refusing to block")

    vf_kind = _ACTION_TO_VF.get(req.action)
    if vf_kind is None:
        raise HTTPException(status_code=400, detail=f"Unsupported action '{req.action}'")

    latest = db.execute(
        select(Decision).where(Decision.incident_id == inc.id).order_by(Decision.ts.desc()).limit(1)
    ).scalar_one_or_none()
    if latest is None:
        raise HTTPException(status_code=409, detail="Incident has no decision to act on")

    # Dedupe: already contained?
    existing = (
        db.query(VirtualFirewall)
        .filter(
            VirtualFirewall.target == str(target),
            VirtualFirewall.kind == vf_kind,
            VirtualFirewall.active.is_(True),
        )
        .first()
    )
    if existing is not None:
        return {"status": "already_blocked", "incident_id": inc.id, "target": target, "firewall_id": existing.id}

    executor = settings.SOC_EXECUTOR
    enforce_result = None
    status = {"simulated": "simulated", "lab": "enforced", "dry_run": "dry_run"}.get(executor, "dry_run")
    if executor == "lab":
        from soc.backend.app.response import firewall
        enforce_result = firewall.apply_block(str(target), kind=req.action)
        if not enforce_result.get("enforced"):
            status = "recorded_only"

    ttl_s = int(req.ttl_s or settings.DEFAULT_BLOCK_TTL_S)

    # Record analyst approval of the decision.
    db.add(Approval(
        decision_id=latest.id,
        analyst=req.analyst,
        verdict=ApprovalVerdict.APPROVE,
        comment=req.comment or f"Manual {req.action} via dashboard",
    ))

    action = Action(
        decision_id=latest.id,
        step_id="manual",
        action=req.action,
        params={"target": target, "ttl_s": ttl_s},
        executor=executor,
        dry_run=executor != "lab",
        status=status,
        result=enforce_result,
        started_at=_utcnow(),
        finished_at=_utcnow(),
    )
    db.add(action)
    db.flush()

    vf = VirtualFirewall(
        kind=vf_kind,
        target=str(target),
        ttl_at=_utcnow() + timedelta(seconds=ttl_s),
        action_id=action.id,
        active=True,
    )
    db.add(vf)

    latest.status = DecisionStatus.EXECUTED
    inc.status = IncidentStatus.CONTAINED

    append_audit(
        db,
        event_type="response.manual",
        entity_type="incident",
        entity_id=inc.id,
        payload={
            "action": req.action,
            "target": target,
            "executor": executor,
            "status": status,
            "ttl_s": ttl_s,
            "analyst": req.analyst,
            "decision_id": latest.id,
        },
    )
    db.commit()
    db.refresh(vf)
    return {
        "status": "contained",
        "incident_id": inc.id,
        "target": target,
        "action": req.action,
        "executor": executor,
        "enforcement": status,
        "firewall_id": vf.id,
        "ttl_at": vf.ttl_at.isoformat(),
        "enforce_result": enforce_result,
    }


@router.post("/incidents/{incident_id}/release")
async def release_incident(
    incident_id: int,
    analyst: str = Query("dashboard"),
    db: Session = Depends(get_db),
):
    """Lift all active containment on an incident's source (the "Release" button)."""
    inc = db.get(Incident, incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    target = inc.key_src_ip
    rows = (
        db.query(VirtualFirewall)
        .filter(VirtualFirewall.target == str(target), VirtualFirewall.active.is_(True))
        .all()
    )
    nft_result = None
    if settings.SOC_EXECUTOR == "lab":
        from soc.backend.app.response import firewall
        nft_result = firewall.remove_block(str(target))

    for vf in rows:
        vf.active = False
    if rows:
        inc.status = IncidentStatus.OPEN

    append_audit(
        db,
        event_type="response.release",
        entity_type="incident",
        entity_id=inc.id,
        payload={"target": target, "released": len(rows), "analyst": analyst, "nft": nft_result},
    )
    db.commit()
    return {"status": "released", "incident_id": inc.id, "target": target, "released": len(rows)}


@router.get("/policy")
async def policy_info():
    """Active policy version, hash, attack families, and rule summary."""
    p = get_policy()
    return {
        "version": p.version,
        "policy_hash": p.policy_hash,
        "min_alert_confidence": p.min_alert_confidence,
        "correlation_window_s": p.correlation_window_s,
        "tiers": p.tiers,
        "weights": {
            "severity": p.weights.severity,
            "confidence": p.weights.confidence,
            "asset": p.weights.asset,
            "intel": p.weights.intel,
        },
        "families": {k: {"severity": f.severity, "members": f.members} for k, f in p.families.items()},
        "rules": [
            {"id": r.id, "priority": r.priority, "mode": r.mode, "playbook": r.playbook}
            for r in p.rules
        ],
    }
