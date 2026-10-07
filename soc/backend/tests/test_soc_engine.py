"""
Decision Engine contract tests (F0 core: policy loader, scoring, rules, audit,
correlation). Grows per phase as executors, guardrails, and playbooks land.

Test IDs are referenced by the master PRD (TC-SCORE-*, TC-RULE-*, TC-AUDIT-*,
TC-CORR-*). Adapt code to these assertions, not the other way around.
"""
from datetime import datetime, timedelta, timezone

import pytest

from soc.backend.app.policy.loader import load_policy_bundle, get_policy
from soc.backend.app.scoring.risk import compute_risk
from soc.backend.app.decision.rules import evaluate_rules
from soc.backend.app.decision.correlation import correlate, repeat_count
from soc.backend.app.audit.chain import (
    append_audit,
    verify_chain,
    compute_hash,
    GENESIS_HASH,
)
from soc.backend.app.db.models import Alert, IncidentStatus


def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Policy loader
# ---------------------------------------------------------------------------
def test_policy_loads_and_hashes():
    p = load_policy_bundle()
    assert p.version >= 1
    assert len(p.policy_hash) == 64
    # weights from policies.yaml
    assert p.weights.severity == pytest.approx(0.35)
    assert p.weights.confidence == pytest.approx(0.25)
    assert p.weights.asset == pytest.approx(0.25)
    assert p.weights.intel == pytest.approx(0.15)
    # family / member mapping
    assert p.family_for_label("DoS SYN Flood") == "dos_flood"
    assert p.family_for_label("MITM ARP Spoofing") == "mitm"
    assert p.family_for_label("Benign Traffic") == "benign"
    # at least the 6 playbooks referenced by rules are present
    assert "pb_contain_source" in p.playbooks
    assert len(p.playbooks) >= 6


def test_policy_hash_is_deterministic():
    assert load_policy_bundle().policy_hash == load_policy_bundle().policy_hash


def test_lookup_helpers():
    p = load_policy_bundle()
    assert p.asset_criticality("10.10.10.11") == pytest.approx(1.0)      # db-server-01
    assert p.asset_criticality("203.0.113.1") == pytest.approx(p.default_criticality)
    assert p.intel_score("10.66.0.5") == pytest.approx(1.0)              # known C2
    assert p.intel_score("10.10.10.11") == 0.0
    assert p.is_allowlisted("127.0.0.1") is True
    assert p.is_allowlisted("10.66.0.5") is False


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def test_score_benign_is_low():
    p = load_policy_bundle()
    r = compute_risk(p, family="benign", confidence=0.99, src_ip="10.0.0.15", dst_ip="10.10.10.10")
    assert r.tier == "LOW"
    assert r.score < p.tiers["medium"]


def test_score_critical_mitm_on_critical_asset():
    p = load_policy_bundle()
    # mitm severity 0.90, target db-server (crit 1.0), source is known-bad intel 1.0
    r = compute_risk(p, family="mitm", confidence=0.95, src_ip="10.66.0.5", dst_ip="10.10.10.11")
    # sev 100*.35*.9=31.5 + conf 100*.25*.95=23.75 + asset 100*.25*1=25 + intel 100*.15*1=15 = 95.25
    assert r.score == pytest.approx(95.25, abs=0.01)
    assert r.tier == "CRITICAL"
    assert r.intel_hit is True
    assert set(r.breakdown) == {"severity", "confidence", "asset", "intel", "repeat_bonus"}


def test_repeat_offender_bonus_capped():
    p = load_policy_bundle()
    r = compute_risk(p, family="recon", confidence=0.5, src_ip="10.66.0.5", dst_ip="10.10.10.10", repeat_count=100)
    assert r.breakdown["repeat_bonus"] == pytest.approx(p.repeat_offender.max_bonus)
    assert r.score <= 100.0


def test_tier_boundaries():
    p = load_policy_bundle()
    assert p.tier_for_score(0) == "LOW"
    assert p.tier_for_score(30) == "MEDIUM"
    assert p.tier_for_score(60) == "HIGH"
    assert p.tier_for_score(80) == "CRITICAL"
    assert p.tier_for_score(79.99) == "HIGH"


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------
def test_rule_crit_auto_fires_on_intel_and_high_score():
    p = load_policy_bundle()
    m = evaluate_rules(p, score=95.0, confidence=0.9, margin=0.4, family="mitm",
                       intel_hit=True, repeat_count=1)
    assert m.rule_id == "R-CRIT-AUTO"
    assert m.mode == "auto"
    assert m.playbook == "pb_contain_source"


def test_rule_crit_auto_blocked_by_low_margin_falls_through():
    p = load_policy_bundle()
    # high score + intel but margin below 0.30 -> R-CRIT-AUTO must NOT match
    m = evaluate_rules(p, score=95.0, confidence=0.9, margin=0.1, family="mitm",
                       intel_hit=True, repeat_count=1)
    assert m.rule_id != "R-CRIT-AUTO"
    assert m.rule_id == "R-MITM"


def test_rule_dos_recommend():
    p = load_policy_bundle()
    m = evaluate_rules(p, score=65.0, confidence=0.7, margin=0.2, family="dos_flood",
                       intel_hit=False, repeat_count=0)
    assert m.rule_id == "R-DOS"
    assert m.mode == "recommend"
    assert m.playbook == "pb_dos_mitigate"


def test_rule_default_fallback():
    p = load_policy_bundle()
    m = evaluate_rules(p, score=5.0, confidence=0.99, margin=0.9, family="benign",
                       intel_hit=False, repeat_count=0)
    assert m.rule_id == "R-DEFAULT"
    assert m.mode == "monitor"
    assert m.playbook == "pb_log_only"


def test_rule_trace_records_all_evaluated():
    p = load_policy_bundle()
    m = evaluate_rules(p, score=65.0, confidence=0.7, margin=0.2, family="dos_flood",
                       intel_hit=False, repeat_count=0)
    evaluated_ids = [e["rule_id"] for e in m.trace["evaluated"]]
    assert "R-CRIT-AUTO" in evaluated_ids   # evaluated before matching R-DOS
    assert m.trace["matched_rule"] == "R-DOS"


# ---------------------------------------------------------------------------
# Audit chain
# ---------------------------------------------------------------------------
def test_audit_chain_links_and_verifies(db_session):
    e1 = append_audit(db_session, event_type="ingest", entity_type="alert", entity_id="1",
                      payload={"a": 1})
    e2 = append_audit(db_session, event_type="decision", entity_type="decision", entity_id="1",
                      payload={"b": 2})
    db_session.commit()
    assert e1.prev_hash == GENESIS_HASH
    assert e2.prev_hash == e1.hash
    assert e1.hash == compute_hash(GENESIS_HASH, {"a": 1})
    result = verify_chain(db_session)
    assert result["valid"] is True
    assert result["count"] == 2


def test_audit_chain_detects_tampering(db_session):
    e1 = append_audit(db_session, event_type="ingest", entity_type="alert", entity_id="1",
                      payload={"a": 1})
    append_audit(db_session, event_type="decision", entity_type="decision", entity_id="1",
                 payload={"b": 2})
    db_session.commit()
    # Tamper with the first payload after the fact
    e1.payload = {"a": 999}
    db_session.commit()
    result = verify_chain(db_session)
    assert result["valid"] is False
    assert result["broken_at_id"] == e1.id


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------
def test_correlation_collapses_burst_into_one_incident(db_session):
    p = load_policy_bundle()
    now = utcnow()
    inc_ids = set()
    for i in range(50):
        inc = correlate(db_session, p, src_ip="10.66.0.5", family="dos_flood",
                        ts=now + timedelta(seconds=i), risk_score=90.0)
        inc_ids.add(inc.id)
    db_session.commit()
    assert len(inc_ids) == 1
    inc = next(iter(inc_ids))
    from soc.backend.app.db.models import Incident
    row = db_session.get(Incident, inc)
    assert row.alert_count == 50
    assert row.max_risk == pytest.approx(90.0)


def test_correlation_separates_by_family(db_session):
    p = load_policy_bundle()
    now = utcnow()
    a = correlate(db_session, p, src_ip="10.66.0.5", family="dos_flood", ts=now, risk_score=80)
    b = correlate(db_session, p, src_ip="10.66.0.5", family="recon", ts=now, risk_score=40)
    db_session.commit()
    assert a.id != b.id


def test_correlation_new_incident_after_window(db_session):
    p = load_policy_bundle()
    now = utcnow()
    a = correlate(db_session, p, src_ip="10.66.0.7", family="mitm", ts=now, risk_score=90)
    later = now + timedelta(seconds=p.correlation_window_s + 5)
    b = correlate(db_session, p, src_ip="10.66.0.7", family="mitm", ts=later, risk_score=90)
    db_session.commit()
    assert a.id != b.id


def test_repeat_count_within_window(db_session):
    p = load_policy_bundle()
    now = utcnow()
    for i in range(3):
        db_session.add(Alert(
            ts=now - timedelta(seconds=i * 10),
            src_ip="10.66.0.6", dst_ip="10.10.10.10", label="DoS SYN Flood",
            family="dos_flood", confidence=0.9, margin=0.4,
            probabilities={}, top_features=[], model_version="t",
        ))
    db_session.commit()
    assert repeat_count(db_session, p, src_ip="10.66.0.6", ts=now) == 3
    assert repeat_count(db_session, p, src_ip="10.0.0.1", ts=now) == 0
