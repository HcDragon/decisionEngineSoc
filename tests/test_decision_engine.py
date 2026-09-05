import pytest
import os
import time
from datetime import datetime, timezone
from pydantic import ValidationError

from decision_engine.models.threat_event import ThreatEvent
from decision_engine.models.context import EnrichedContext
from decision_engine.models.risk import RiskAssessment, RiskSeverity
from decision_engine.models.policy import PolicyDefinition, PolicyMatchResult
from decision_engine.models.decision import SecurityDecision, DecisionType
from decision_engine.models.action import ActionResult, ActionStatus, ExecutionMode
from decision_engine.models.verification import VerificationResult, VerificationStatus
from decision_engine.models.incident import IncidentRecord, IncidentState

from decision_engine.storage.db import Database
from decision_engine.events.event_bus import EventBus
from decision_engine.audit.audit_logger import AuditLogger
from decision_engine.context.context_enricher import ContextEnricher
from decision_engine.risk.risk_engine import RiskEngine
from decision_engine.policy.policy_engine import PolicyEngine
from decision_engine.actions.adapters.simulation_adapter import SimulationAdapter
from decision_engine.actions.action_executor import SOARActionExecutor
from decision_engine.playbooks.playbook_engine import PlaybookEngine
from decision_engine.verification.verification_engine import VerificationEngine
from decision_engine.recovery.recovery_manager import RecoveryManager
from decision_engine.incidents.incident_manager import IncidentManager
from decision_engine.decision.decision_manager import DecisionManager

from fastapi.testclient import TestClient
from decision_engine.api.routes import app

# ---------------------------------------------------------
# Test Fixtures (Isolated for unit testing only)
# ---------------------------------------------------------
@pytest.fixture
def mock_threat_event_nested():
    return {
        "event_id": "EVT-TEST-001",
        "timestamp": "2026-09-06T00:00:00Z",
        "source": {"ip": "192.168.1.100", "port": 52172},
        "destination": {"ip": "10.0.0.5", "port": 80},
        "network": {
            "protocol": "TCP",
            "packet_count": 150000,
            "flow_duration": 2.5,
            "bytes": 9600000,
            "packets_per_second": 60000.0
        },
        "detection": {
            "model": "RandomForest",
            "attack_type": "DoS SYN Flood",
            "confidence": 0.98,
            "confidence_level": "HIGH"
        },
        "sensor": {"source": "NFStream", "mode": "LIVE"}
    }

@pytest.fixture
def mock_threat_event_flat():
    return {
        "timestamp": "2026-09-06T00:00:00Z",
        "attack_type": "DoS UDP Flood",
        "confidence": 0.95,
        "src_ip": "192.168.1.200",
        "dest_ip": "10.0.0.10",
        "src_port": 12345,
        "dest_port": 53,
        "protocol": "UDP",
        "packet_count": 8000,
        "flow_duration": 1.2
    }

# ---------------------------------------------------------
# 1. Threat Event Validation Tests
# ---------------------------------------------------------
def test_threat_event_validation_nested(mock_threat_event_nested):
    event = ThreatEvent(**mock_threat_event_nested)
    assert event.event_id == "EVT-TEST-001"
    assert event.src_ip == "192.168.1.100"
    assert event.dest_ip == "10.0.0.5"
    assert event.attack_type == "DoS SYN Flood"
    assert event.confidence == 0.98

def test_threat_event_validation_flat(mock_threat_event_flat):
    event = ThreatEvent(**mock_threat_event_flat)
    assert event.src_ip == "192.168.1.200"
    assert event.dest_ip == "10.0.0.10"
    assert event.attack_type == "DoS UDP Flood"
    assert event.confidence == 0.95
    assert event.network.protocol == "UDP"

def test_threat_event_malformed_rejection():
    # Missing source IP and required fields
    with pytest.raises(Exception):
        ThreatEvent(source=None)

# ---------------------------------------------------------
# 2. Context Enrichment Tests
# ---------------------------------------------------------
def test_context_enrichment(mock_threat_event_nested):
    enricher = ContextEnricher()
    event = ThreatEvent(**mock_threat_event_nested)
    context: EnrichedContext = enricher.enrich(event)
    
    # Verify Observed Data
    assert context.observed.source_ip == "192.168.1.100"
    assert context.observed.destination_ip == "10.0.0.5"
    assert context.observed.packets_per_second == 60000.0
    
    # Verify Configured Data (10.0.0.5 is Tier 1 database)
    assert context.configured.asset_criticality == 95
    assert context.configured.destination_role == "Core Production Database"
    
    # Verify Derived Data
    assert isinstance(context.derived.repeated_detections_count, int)

# ---------------------------------------------------------
# 3. Risk Calculation & Normalization Tests
# ---------------------------------------------------------
def test_risk_calculation(mock_threat_event_nested):
    enricher = ContextEnricher()
    event = ThreatEvent(**mock_threat_event_nested)
    context = enricher.enrich(event)
    
    engine = RiskEngine()
    assessment: RiskAssessment = engine.assess_risk(context)
    
    assert 0.0 <= assessment.risk_score <= 100.0
    assert assessment.severity in (RiskSeverity.HIGH, RiskSeverity.CRITICAL)
    assert len(assessment.factors) == 5
    assert all(f.contribution >= 0.0 for f in assessment.factors)

# ---------------------------------------------------------
# 4. Risk Boundary Condition Tests
# ---------------------------------------------------------
def test_risk_boundary_benign():
    benign_event = ThreatEvent(
        source={"ip": "10.0.0.50", "port": 1234},
        destination={"ip": "10.0.0.10", "port": 80},
        network={"protocol": "TCP", "packet_count": 10, "flow_duration": 1.0, "bytes": 640, "packets_per_second": 10.0},
        detection={"model": "RandomForest", "attack_type": "Benign Traffic", "confidence": 0.01, "confidence_level": "LOW"}
    )
    enricher = ContextEnricher()
    context = enricher.enrich(benign_event)
    engine = RiskEngine()
    assessment = engine.assess_risk(context)
    assert assessment.risk_score <= 25.0
    assert assessment.severity in (RiskSeverity.INFORMATIONAL, RiskSeverity.LOW)

# ---------------------------------------------------------
# 5. Policy Matching Tests
# ---------------------------------------------------------
def test_policy_matching(mock_threat_event_nested):
    enricher = ContextEnricher()
    event = ThreatEvent(**mock_threat_event_nested)
    context = enricher.enrich(event)
    risk_engine = RiskEngine()
    risk = risk_engine.assess_risk(context)
    
    policy_engine = PolicyEngine()
    result: PolicyMatchResult = policy_engine.evaluate(context, risk)
    assert result.selected_policy.policy_id == "DOS-SYN-001"
    assert result.selected_policy.playbook_id == "PB-DOS-SYN"

# ---------------------------------------------------------
# 6. Policy Priority & Conflict Resolution Tests
# ---------------------------------------------------------
def test_policy_priority_conflict():
    policy_engine = PolicyEngine()
    # Ensure policies are sorted by priority
    policies = policy_engine.loader.reload()
    priorities = [p.priority for p in policies]
    assert priorities == sorted(priorities, reverse=True)

# ---------------------------------------------------------
# 7. No Policy Fallback Test
# ---------------------------------------------------------
def test_no_policy_fallback():
    weird_event = ThreatEvent(
        source={"ip": "1.2.3.4", "port": 1234},
        destination={"ip": "10.0.0.99", "port": 80},
        network={"protocol": "TCP", "packet_count": 1, "flow_duration": 1.0, "bytes": 64, "packets_per_second": 1.0},
        detection={"model": "RandomForest", "attack_type": "Unknown Obscure Vector", "confidence": 0.1, "confidence_level": "LOW"}
    )
    enricher = ContextEnricher()
    context = enricher.enrich(weird_event)
    risk = RiskAssessment(risk_score=10.0, severity=RiskSeverity.INFORMATIONAL, factors=[], summary_explanation="")
    
    policy_engine = PolicyEngine()
    res = policy_engine.evaluate(context, risk)
    assert res.selected_policy.policy_id == "DEFAULT-FALLBACK"

# ---------------------------------------------------------
# 8. Decision Generation Tests
# ---------------------------------------------------------
def test_decision_generation(mock_threat_event_nested):
    manager = DecisionManager()
    decision: SecurityDecision = manager.process(mock_threat_event_nested)
    assert decision.decision == DecisionType.CONTAIN
    assert decision.policy_id == "DOS-SYN-001"
    assert decision.automation_level == 5
    assert len(decision.explanation) > 0

# ---------------------------------------------------------
# 9. Automation Level Enforcement Tests
# ---------------------------------------------------------
def test_automation_level_enforcement():
    executor = SOARActionExecutor()
    # Level 0 cannot execute block
    res_l0 = executor.execute_step(action="BLOCK_IP_SIMULATION", target="1.2.3.4", automation_level=0)
    assert res_l0.status == ActionStatus.SKIPPED
    
    # Level 2 requires approval
    res_l2 = executor.execute_step(action="BLOCK_IP_SIMULATION", target="1.2.3.4", automation_level=2, approved=False)
    assert res_l2.status == ActionStatus.WAITING_APPROVAL

    # Level 5 executes directly
    res_l5 = executor.execute_step(action="BLOCK_IP_SIMULATION", target="1.2.3.4", automation_level=5)
    assert res_l5.status == ActionStatus.SUCCESS

# ---------------------------------------------------------
# 10. Playbook Execution Tests
# ---------------------------------------------------------
def test_playbook_execution():
    pb_engine = PlaybookEngine()
    record = pb_engine.execute_playbook(
        playbook_id="PB-DOS-SYN",
        target="192.168.1.100",
        automation_level=5,
        incident_id="INC-UNIT-01"
    )
    assert record.status == "COMPLETED"
    assert record.total_steps >= 4

# ---------------------------------------------------------
# 11. Action Safety & Allowlist Tests
# ---------------------------------------------------------
def test_action_allowlist_rejection():
    adapter = SimulationAdapter()
    res = adapter.execute_action(action="DROP_DATABASE_CMD", target="1.2.3.4")
    assert res.status == ActionStatus.FAILED
    assert "not in the security allowlist" in res.message

# ---------------------------------------------------------
# 12 & 13. Verification Success and Failure Tests
# ---------------------------------------------------------
def test_verification_success():
    ver = VerificationEngine()
    res = ver.verify_mitigation(
        incident_id="INC-V1",
        target="1.2.3.4",
        baseline_pps=50000.0,
        observed_pps=200.0
    )
    assert res.status == VerificationStatus.SUCCESS
    assert res.reduction_percentage >= 90.0

def test_verification_failure():
    ver = VerificationEngine()
    res = ver.verify_mitigation(
        incident_id="INC-V2",
        target="1.2.3.4",
        baseline_pps=50000.0,
        observed_pps=45000.0
    )
    assert res.status == VerificationStatus.FAILED

# ---------------------------------------------------------
# 14. Recovery Expiration Tests
# ---------------------------------------------------------
def test_recovery_expiry():
    db = Database()
    rec = RecoveryManager(db=db)
    # Inject expired mitigation
    db.save_active_mitigation({
        "action_id": "ACT-EXP-01",
        "incident_id": "INC-EXP-01",
        "action_type": "BLOCK_IP_SIMULATION",
        "target": "1.2.3.4",
        "status": "ACTIVE",
        "expires_at": "2020-01-01T00:00:00Z" # Past
    })
    expired = rec.process_expired_mitigations()
    assert len(expired) >= 1
    assert any(m["action_id"] == "ACT-EXP-01" for m in expired)

# ---------------------------------------------------------
# 15. Escalation on Verification Failure Test
# ---------------------------------------------------------
def test_escalation_logic():
    db = Database()
    rec = RecoveryManager(db=db)
    db.save_incident({
        "incident_id": "INC-ESC-01",
        "event_id": "EVT-ESC-01",
        "source_ip": "1.2.3.4",
        "destination_ip": "10.0.0.5",
        "attack_type": "DoS SYN Flood",
        "current_state": "RESPONSE_STARTED"
    })
    updated = rec.escalate_incident("INC-ESC-01", "Traffic rate still above threshold")
    assert updated["current_state"] == IncidentState.ESCALATED.value
    assert updated["severity"] == "CRITICAL"

# ---------------------------------------------------------
# 16. Incident Deduplication & Correlation Window Test
# ---------------------------------------------------------
def test_incident_deduplication(mock_threat_event_nested):
    mgr = IncidentManager(correlation_window_seconds=10)
    data = dict(mock_threat_event_nested)
    data["source"] = {"ip": "172.16.50.99", "port": 4444}
    data["destination"] = {"ip": "10.0.0.99", "port": 80}
    event = ThreatEvent(**data)
    
    inc1, is_new1 = mgr.get_or_create_incident(event)
    assert is_new1 is True
    
    # Immediate subsequent event from same source/dest
    inc2, is_new2 = mgr.get_or_create_incident(event)
    assert is_new2 is False
    assert inc2.incident_id == inc1.incident_id
    assert inc2.event_count >= 2

# ---------------------------------------------------------
# 17. Audit Logging & Trail Reconstruction Test
# ---------------------------------------------------------
def test_audit_logging():
    db = Database()
    logger = AuditLogger(db=db)
    logger.log(
        event_type="TEST_AUDIT",
        details="Forensic audit entry test",
        incident_id="INC-AUD-01",
        component="UNIT_TEST"
    )
    trail = logger.get_trail("INC-AUD-01")
    assert len(trail) >= 1
    assert any(entry["event_type"] == "TEST_AUDIT" for entry in trail)

# ---------------------------------------------------------
# 18. REST API Endpoints Test
# ---------------------------------------------------------
def test_api_endpoints(mock_threat_event_nested):
    client = TestClient(app)
    
    # 1. Health check
    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "HEALTHY"
    
    # 2. Analyze threat event
    res_analyze = client.post("/api/v1/decision/analyze", json=mock_threat_event_nested)
    assert res_analyze.status_code == 200
    data = res_analyze.json()
    assert "incident_id" in data
    assert "decision" in data
    assert data["decision"] == "CONTAIN"
    
    # 3. List incidents
    res_list = client.get("/api/v1/incidents")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1
    
    # 4. Get events
    res_events = client.get("/api/v1/events")
    assert res_events.status_code == 200
    assert len(res_events.json()) >= 1

# ---------------------------------------------------------
# 19. Event Bus Pub/Sub Test
# ---------------------------------------------------------
def test_event_bus():
    bus = EventBus()
    received = []
    
    def on_event(msg):
        received.append(msg)
        
    bus.subscribe("TEST_EVENT", on_event)
    bus.publish("TEST_EVENT", {"payload": "val"})
    assert len(received) == 1
    assert received[0]["data"]["payload"] == "val"

# ---------------------------------------------------------
# 20. End-to-End Decision Engine Pipeline Test
# ---------------------------------------------------------
def test_end_to_end_pipeline(mock_threat_event_nested):
    manager = DecisionManager()
    decision = manager.process(mock_threat_event_nested)
    
    # Verify complete pipeline resolution
    assert decision.incident_id.startswith("INC-")
    assert decision.decision == DecisionType.CONTAIN
    assert decision.risk_score > 70.0
    assert decision.policy_id == "DOS-SYN-001"
    assert len(decision.actions) > 0
    assert len(decision.reasons) > 0
    
    # Verify DB state
    inc = manager.db.get_incident(decision.incident_id)
    assert inc is not None
    assert inc["current_state"] in ("CONTAINED", "RESPONSE_STARTED")
    
    # Verify audit log trail
    audit_trail = manager.audit.get_trail(decision.incident_id)
    event_types = [entry["event_type"] for entry in audit_trail]
    assert "THREAT_RECEIVED" in event_types
    assert "RISK_CALCULATED" in event_types
    assert "POLICY_MATCHED" in event_types
    assert "DECISION_CREATED" in event_types
