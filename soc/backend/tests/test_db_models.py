"""
Tests for all 10 SQLAlchemy database models.
"""
from datetime import datetime, timezone
import pytest
from soc.backend.app.db.models import (
    Alert,
    Incident,
    IncidentStatus,
    Decision,
    DecisionMode,
    DecisionStatus,
    Action,
    Approval,
    ApprovalVerdict,
    Case,
    VirtualFirewall,
    VirtualFirewallKind,
    AuditLog,
    Counter,
    Feedback,
)


def test_incident_and_alert_creation(db_session):
    now = datetime.now(timezone.utc)
    incident = Incident(
        key_src_ip="10.66.0.5",
        family="dos_flood",
        first_seen=now,
        last_seen=now,
        alert_count=1,
        max_risk=85.0,
        status=IncidentStatus.OPEN,
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    assert incident.id is not None
    assert incident.key_src_ip == "10.66.0.5"

    alert = Alert(
        ts=now,
        src_ip="10.66.0.5",
        dst_ip="10.10.10.10",
        src_port=44332,
        dst_port=80,
        label="DoS SYN Flood",
        family="dos_flood",
        confidence=0.95,
        margin=0.45,
        probabilities={"DoS SYN Flood": 0.95, "Benign Traffic": 0.05},
        top_features=[{"feature": "SYN Flag Count", "contribution": 0.42}],
        model_version="rf_v1_hash",
        incident_id=incident.id,
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    assert alert.id is not None
    assert alert.incident_id == incident.id
    assert len(incident.alerts) == 1


def test_decision_and_action_pipeline(db_session):
    now = datetime.now(timezone.utc)
    incident = Incident(
        key_src_ip="10.66.0.6",
        family="brute_force",
        first_seen=now,
        last_seen=now,
        alert_count=3,
        max_risk=75.0,
    )
    db_session.add(incident)
    db_session.commit()

    decision = Decision(
        incident_id=incident.id,
        ts=now,
        risk_score=75.0,
        tier="HIGH",
        score_breakdown={"severity": 24.5, "confidence": 20.0, "asset": 12.5, "intel": 15.0},
        rule_id="R-BRUTE",
        rule_trace={"matched": True, "condition": "family == brute_force"},
        policy_hash="abc123policyhash",
        mode=DecisionMode.AUTO,
        playbook_id="pb_bruteforce_lockout",
        status=DecisionStatus.EXECUTED,
    )
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)

    assert decision.id is not None
    assert decision.tier == "HIGH"

    action = Action(
        decision_id=decision.id,
        step_id="s1",
        action="block_ip",
        params={"target": "10.66.0.6", "ttl_s": 900},
        executor="simulated",
        dry_run=False,
        status="success",
        started_at=now,
    )
    db_session.add(action)
    db_session.commit()
    db_session.refresh(action)

    assert action.id is not None
    assert len(decision.actions) == 1

    vf = VirtualFirewall(
        kind=VirtualFirewallKind.BLOCK,
        target="10.66.0.6",
        ttl_at=now,
        action_id=action.id,
        active=True,
        created_at=now,
    )
    db_session.add(vf)
    db_session.commit()
    db_session.refresh(vf)

    assert vf.id is not None
    assert vf.kind == VirtualFirewallKind.BLOCK


def test_approval_case_feedback(db_session):
    now = datetime.now(timezone.utc)
    incident = Incident(
        key_src_ip="10.66.0.7",
        family="mitm",
        first_seen=now,
        last_seen=now,
    )
    db_session.add(incident)
    db_session.commit()

    alert = Alert(
        ts=now,
        src_ip="10.66.0.7",
        dst_ip="10.10.10.11",
        label="MITM ARP Spoofing",
        family="mitm",
        confidence=0.88,
        margin=0.35,
        probabilities={"MITM ARP Spoofing": 0.88},
        top_features=[],
        model_version="v1",
        incident_id=incident.id,
    )
    db_session.add(alert)

    decision = Decision(
        incident_id=incident.id,
        ts=now,
        risk_score=90.0,
        tier="CRITICAL",
        score_breakdown={},
        rule_id="R-MITM",
        rule_trace={},
        policy_hash="p123",
        mode=DecisionMode.RECOMMEND,
        playbook_id="pb_mitm_isolate",
        status=DecisionStatus.PENDING_APPROVAL,
    )
    db_session.add(decision)
    db_session.commit()

    approval = Approval(
        decision_id=decision.id,
        analyst="analyst_alice",
        verdict=ApprovalVerdict.APPROVE,
        comment="Confirmed ARP spoofing attack pattern",
        ts=now,
    )
    db_session.add(approval)

    case = Case(
        incident_id=incident.id,
        title="MITM ARP Spoofing Incident",
        priority="CRITICAL",
        status="open",
        created_at=now,
    )
    db_session.add(case)

    feedback = Feedback(
        alert_id=alert.id,
        analyst="analyst_alice",
        true_label="MITM ARP Spoofing",
        ts=now,
    )
    db_session.add(feedback)
    db_session.commit()

    assert approval.id is not None
    assert case.id is not None
    assert feedback.id is not None


def test_audit_log_and_counter(db_session):
    now = datetime.now(timezone.utc)
    audit = AuditLog(
        ts=now,
        actor="system",
        event_type="policy_reload",
        entity_type="config",
        entity_id="policies.yaml",
        payload={"hash": "abcdef"},
        prev_hash="0000000000000000000000000000000000000000000000000000000000000000",
        hash="1111111111111111111111111111111111111111111111111111111111111111",
    )
    db_session.add(audit)

    counter = Counter(
        ts_bucket=now,
        label="Benign Traffic",
        count=42,
    )
    db_session.add(counter)
    db_session.commit()

    assert audit.id is not None
    assert counter.id is not None
    assert counter.count == 42
