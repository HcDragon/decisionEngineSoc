"""
Decision Pipeline — the wire that connects detection to the backend.

Takes one classified flow and runs the full F0 decision core against it:

    classify-map -> gate -> score -> correlate -> rule -> persist -> (apply) -> audit

Produces durable DB records (Alert, Incident, Decision, optional Action /
VirtualFirewall / Case) and a hash-chained AuditLog entry, so the dashboard's
incident / alert / decision / block counters reflect real traffic instead of
staying empty.

Safety: nothing here touches a real network. Actions are only ever recorded in
the database. A VirtualFirewall row is written only under the ``simulated``
executor (DB-tracked, TTL rollback); ``dry_run`` records the intent with no
side effect; the real ``lab`` executor is never invoked from this module.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from soc.backend.app.audit.chain import append_audit
from soc.backend.app.config import settings
from soc.backend.app.db.models import (
    Action,
    Alert,
    Case,
    Decision,
    DecisionMode,
    DecisionStatus,
    Incident,
    VirtualFirewall,
    VirtualFirewallKind,
)
from soc.backend.app.decision.correlation import correlate, repeat_count
from soc.backend.app.decision.rules import evaluate_rules
from soc.backend.app.policy.loader import PolicyBundle
from soc.backend.app.scoring.risk import compute_risk

logger = logging.getLogger("soc.pipeline")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _norm_confidence(confidence: float) -> float:
    """Flows may carry confidence as a percentage (88.5) or a fraction (0.88).
    Normalize to [0, 1]."""
    c = float(confidence)
    if c > 1.0:
        c = c / 100.0
    return max(0.0, min(1.0, c))


def _effective_mode(rule_mode: str, global_mode: str) -> str:
    """Apply the global automation kill-switch to a rule's requested mode.

    - off            -> everything is monitor-only
    - recommend_only -> an 'auto' rule is downgraded to 'recommend'
    - auto           -> rule mode is honoured as-is
    """
    if global_mode == "off":
        return "monitor"
    if rule_mode == "auto" and global_mode != "auto":
        return "recommend"
    return rule_mode


_MODE_TO_STATUS = {
    "monitor": DecisionStatus.MONITORED,
    "recommend": DecisionStatus.PENDING_APPROVAL,
    "auto": DecisionStatus.EXECUTED,
}
_MODE_TO_ENUM = {
    "monitor": DecisionMode.MONITOR,
    "recommend": DecisionMode.RECOMMEND,
    "auto": DecisionMode.AUTO,
}

# playbook action -> virtual-firewall kind (containment actions only)
_ACTION_TO_VF = {
    "block_ip": VirtualFirewallKind.BLOCK,
    "isolate_host": VirtualFirewallKind.ISOLATE,
    "rate_limit": VirtualFirewallKind.RATE_LIMIT,
}


def _render(value: Any, ctx: Dict[str, Any]) -> Any:
    """Minimal ``{{ incident.src_ip }}`` / ``{{ decision.tier }}`` substitution."""
    if isinstance(value, str) and "{{" in value:
        out = value
        for token, repl in ctx.items():
            out = out.replace("{{ " + token + " }}", str(repl)).replace("{{" + token + "}}", str(repl))
        return out
    if isinstance(value, dict):
        return {k: _render(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_render(v, ctx) for v in value]
    return value


def _apply_playbook(
    db: Session,
    policy: PolicyBundle,
    *,
    decision: Decision,
    incident: Incident,
    playbook_id: Optional[str],
    execute: bool,
    executor: str,
) -> List[Dict[str, Any]]:
    """Record the playbook's steps as Action rows and, when executing under the
    simulated executor, materialise containment as VirtualFirewall rows. Returns a
    summary of what was recorded (never performs real network changes)."""
    if not playbook_id:
        return []
    pb = policy.playbooks.get(playbook_id)
    if not pb:
        logger.warning("Decision referenced unknown playbook '%s'", playbook_id)
        return []

    ctx = {
        "incident.src_ip": incident.key_src_ip,
        "decision.tier": decision.tier,
    }
    dry_run = executor != "lab"
    summary: List[Dict[str, Any]] = []

    for step in pb.get("steps", []):
        action_name = step.get("action", "noop")
        params = _render(step.get("params", {}) or {}, ctx)

        # Guardrail: never act on an allowlisted target.
        target = params.get("target")
        enforce_result = None
        if target and policy.is_allowlisted(target):
            status = "skipped_allowlisted"
        elif execute:
            # simulated -> DB only; lab -> real nft (if armed+in-CIDR); dry_run -> nothing
            status = {"simulated": "simulated", "lab": "enforced", "dry_run": "dry_run"}.get(
                executor, "dry_run"
            )
        else:
            status = "proposed"

        vf_kind = _ACTION_TO_VF.get(action_name)

        # Dedupe: if this (target, kind) already has an active block, don't
        # re-apply. A brute-force burst produces many alerts, but the source
        # should be blocked once, not once per alert.
        already_blocked = False
        if vf_kind and target:
            already_blocked = (
                db.query(VirtualFirewall)
                .filter(
                    VirtualFirewall.target == str(target),
                    VirtualFirewall.kind == vf_kind,
                    VirtualFirewall.active.is_(True),
                )
                .first()
                is not None
            )

        # Real enforcement under the lab executor (guarded inside firewall.*).
        if execute and executor == "lab" and vf_kind and target and status == "enforced" \
                and not already_blocked:
            from soc.backend.app.response import firewall
            enforce_result = firewall.apply_block(str(target), kind=action_name)
            if not enforce_result.get("enforced"):
                # Guard refused (not armed / outside CIDR / no nft): record honestly.
                status = "recorded_only"
        elif already_blocked and vf_kind:
            status = "already_blocked"

        action = Action(
            decision_id=decision.id,
            step_id=step.get("id", "s?"),
            action=action_name,
            params=params,
            executor=executor,
            dry_run=dry_run,
            status=status,
            result=enforce_result,
            started_at=_utcnow(),
            finished_at=_utcnow() if execute else None,
        )
        db.add(action)
        db.flush()

        # Materialise containment in the DB virtual-firewall for both simulated
        # and lab executors (lab additionally applied the real rule above).
        # Skip if the target already has an active block (dedupe).
        if execute and executor in ("simulated", "lab") and vf_kind and target \
                and not already_blocked \
                and status in ("simulated", "enforced", "recorded_only"):
            ttl_s = int(params.get("ttl_s", settings.DEFAULT_BLOCK_TTL_S))
            db.add(
                VirtualFirewall(
                    kind=vf_kind,
                    target=str(target),
                    ttl_at=_utcnow() + timedelta(seconds=ttl_s),
                    action_id=action.id,
                    active=True,
                )
            )
        elif action_name == "open_case":
            db.add(
                Case(
                    incident_id=incident.id,
                    title=str(params.get("title", f"Incident {incident.id}")),
                    priority=str(params.get("priority", decision.tier)),
                    status="open",
                )
            )

        summary.append({"step": step.get("id"), "action": action_name, "status": status})

    return summary


def process_flow(
    db: Session,
    policy: PolicyBundle,
    *,
    src_ip: str,
    dst_ip: str,
    src_port: Optional[int] = None,
    dst_port: Optional[int] = None,
    label: str,
    confidence: float,
    margin: float = 0.0,
    probabilities: Optional[Dict[str, float]] = None,
    top_features: Optional[List[Dict[str, Any]]] = None,
    model_version: str = "live-monitor",
    raw_features: Optional[Dict[str, Any]] = None,
    ts: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """Run the decision core for one classified flow.

    Returns a summary dict when an alert was raised, or ``None`` when the flow was
    benign / below the alert-confidence gate / allowlisted (telemetry only).
    The caller owns nothing: this function commits its own unit of work.
    """
    ts = ts or _utcnow()
    family = policy.family_for_label(label)
    conf = _norm_confidence(confidence)

    # --- Gates: things that never raise an alert ---------------------------
    if policy.is_allowlisted(src_ip):
        return None
    if family is None or family == "benign":
        return None
    if conf < policy.min_alert_confidence:
        return None

    try:
        # --- Score -----------------------------------------------------------
        rc = repeat_count(db, policy, src_ip=src_ip, ts=ts)
        score = compute_risk(
            policy,
            family=family,
            confidence=conf,
            src_ip=src_ip,
            dst_ip=dst_ip,
            repeat_count=rc,
        )

        # --- Correlate into an incident -------------------------------------
        incident = correlate(
            db, policy, src_ip=src_ip, family=family, ts=ts, risk_score=score.score
        )

        # --- Persist the alert ----------------------------------------------
        alert = Alert(
            ts=ts,
            src_ip=src_ip,
            dst_ip=dst_ip,
            src_port=src_port,
            dst_port=dst_port,
            label=label,
            family=family,
            confidence=conf,
            margin=float(margin),
            probabilities=probabilities or {label: conf},
            top_features=top_features or [],
            model_version=model_version,
            incident_id=incident.id,
            raw_features=raw_features,
        )
        db.add(alert)
        db.flush()

        # --- Rule evaluation -------------------------------------------------
        match = evaluate_rules(
            policy,
            score=score.score,
            confidence=conf,
            margin=float(margin),
            family=family,
            intel_hit=score.intel_hit,
            repeat_count=rc,
        )
        eff_mode = _effective_mode(match.mode, settings.AUTOMATION_MODE)
        status = _MODE_TO_STATUS.get(eff_mode, DecisionStatus.MONITORED)

        decision = Decision(
            incident_id=incident.id,
            ts=ts,
            risk_score=score.score,
            tier=score.tier,
            score_breakdown=score.breakdown,
            rule_id=match.rule_id,
            rule_trace=match.trace,
            policy_hash=policy.policy_hash,
            mode=_MODE_TO_ENUM.get(eff_mode, DecisionMode.MONITOR),
            playbook_id=match.playbook,
            status=status,
            guardrail_results={
                "requested_mode": match.mode,
                "effective_mode": eff_mode,
                "automation_mode": settings.AUTOMATION_MODE,
                "executor": settings.SOC_EXECUTOR,
                "lab_mode": settings.SOC_LAB_MODE,
            },
            explanation={"score_inputs": score.inputs},
        )
        db.add(decision)
        db.flush()

        # --- Apply (record only) --------------------------------------------
        # Execute = auto mode. Recommend/monitor only record proposed steps.
        execute = eff_mode == "auto"
        action_summary: List[Dict[str, Any]] = []
        if eff_mode in ("recommend", "auto"):
            action_summary = _apply_playbook(
                db,
                policy,
                decision=decision,
                incident=incident,
                playbook_id=match.playbook,
                execute=execute,
                executor=settings.SOC_EXECUTOR,
            )

        # --- Audit (hash-chained) -------------------------------------------
        append_audit(
            db,
            event_type="decision.created",
            entity_type="decision",
            entity_id=decision.id,
            payload={
                "incident_id": incident.id,
                "alert_id": alert.id,
                "src_ip": src_ip,
                "family": family,
                "risk_score": score.score,
                "tier": score.tier,
                "rule_id": match.rule_id,
                "mode": eff_mode,
                "playbook": match.playbook,
                "policy_hash": policy.policy_hash,
            },
        )

        db.commit()
        return {
            "incident_id": incident.id,
            "alert_id": alert.id,
            "decision_id": decision.id,
            "family": family,
            "risk_score": score.score,
            "tier": score.tier,
            "rule_id": match.rule_id,
            "mode": eff_mode,
            "playbook": match.playbook,
            "actions": action_summary,
        }
    except Exception:
        db.rollback()
        raise
