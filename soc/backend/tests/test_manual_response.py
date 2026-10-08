"""
Manual (analyst-driven) response contract tests.

Covers the dashboard "Manual defence" path: an incident is raised by the
pipeline, then an analyst approves containment via POST /api/incidents/{id}/respond
(simulated executor -> DB virtual-firewall only, no real network changes), and
later lifts it via /release.
"""
from datetime import datetime, timezone

import pytest

from soc.backend.app.config import settings
from soc.backend.app.decision.pipeline import process_flow
from soc.backend.app.policy.loader import get_policy
from soc.backend.app.db.models import IncidentStatus, VirtualFirewall


def _raise_incident(db):
    """Drive one malicious flow through the pipeline to create an incident."""
    policy = get_policy()
    summary = process_flow(
        db,
        policy,
        src_ip="10.66.0.20",
        dst_ip="10.66.0.10",
        src_port=44444,
        dst_port=22,
        label="Dictionary Brute Force",
        confidence=0.95,
    )
    assert summary is not None
    return summary["incident_id"]


def test_manual_respond_contains_incident(client, db_session, monkeypatch):
    # Manual defence => recommend_only global mode, simulated executor (DB-only).
    monkeypatch.setattr(settings, "AUTOMATION_MODE", "recommend_only")
    monkeypatch.setattr(settings, "SOC_EXECUTOR", "simulated")

    incident_id = _raise_incident(db_session)

    r = client.post(f"/api/incidents/{incident_id}/respond", json={"action": "block_ip"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "contained"
    assert body["target"] == "10.66.0.20"
    assert body["enforcement"] == "simulated"

    # Incident is now contained and a virtual-firewall block exists.
    inc_detail = client.get(f"/api/incidents/{incident_id}").json()
    assert inc_detail["status"] == IncidentStatus.CONTAINED.value
    fw = client.get("/api/firewall").json()
    assert any(e["target"] == "10.66.0.20" and e["active"] for e in fw["entries"])


def test_manual_respond_is_idempotent(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "SOC_EXECUTOR", "simulated")
    incident_id = _raise_incident(db_session)

    first = client.post(f"/api/incidents/{incident_id}/respond", json={"action": "block_ip"})
    assert first.json()["status"] == "contained"
    second = client.post(f"/api/incidents/{incident_id}/respond", json={"action": "block_ip"})
    assert second.json()["status"] == "already_blocked"

    active = [e for e in client.get("/api/firewall").json()["entries"] if e["target"] == "10.66.0.20"]
    assert len(active) == 1


def test_manual_release_lifts_containment(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "SOC_EXECUTOR", "simulated")
    incident_id = _raise_incident(db_session)
    client.post(f"/api/incidents/{incident_id}/respond", json={"action": "block_ip"})

    r = client.post(f"/api/incidents/{incident_id}/release")
    assert r.status_code == 200, r.text
    assert r.json()["released"] >= 1

    active = [e for e in client.get("/api/firewall").json()["entries"] if e["active"]]
    assert all(e["target"] != "10.66.0.20" for e in active)


def test_manual_respond_refuses_allowlisted(client, db_session, monkeypatch):
    """Guardrail: never block an allowlisted source even on explicit request."""
    monkeypatch.setattr(settings, "SOC_EXECUTOR", "simulated")
    policy = get_policy()
    # Build an incident whose source is allowlisted by hand (pipeline would gate it).
    from soc.backend.app.db.models import Incident, Decision, DecisionMode, DecisionStatus

    inc = Incident(key_src_ip="127.0.0.1", family="recon", alert_count=1, max_risk=40.0)
    db_session.add(inc)
    db_session.flush()
    db_session.add(Decision(
        incident_id=inc.id, risk_score=40.0, tier="low", rule_id="R-TEST",
        policy_hash=policy.policy_hash, mode=DecisionMode.RECOMMEND,
        status=DecisionStatus.PENDING_APPROVAL,
    ))
    db_session.commit()

    r = client.post(f"/api/incidents/{inc.id}/respond", json={"action": "block_ip"})
    assert r.status_code == 409


def test_respond_unknown_incident_404(client):
    r = client.post("/api/incidents/999999/respond", json={"action": "block_ip"})
    assert r.status_code == 404
