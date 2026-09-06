import pytest
from decision_engine.decision.decision_manager import DecisionManager
from decision_engine.models.threat_event import ThreatEvent
from decision_engine.policy.policy_engine import PolicyEngine
from decision_engine.actions.simulation_executor import SimulationExecutor

@pytest.fixture
def manager():
    return DecisionManager()

def test_decision_manager_process_model(manager):
    event = ThreatEvent(
        timestamp="2026-07-30T22:46:00Z",
        attack_type="Dictionary Brute Force",
        confidence=0.99,
        src_ip="192.168.1.100",
        dest_ip="10.0.0.5",
        src_port=52172,
        dest_port=22,
        protocol="TCP",
        packet_count=502,
        flow_duration=3618.0
    )
    
    decision = manager.process(event)
    assert decision.attack_type == "Dictionary Brute Force"
    assert decision.src_ip == "192.168.1.100"
    assert isinstance(decision.incident_id, str)
    assert isinstance(decision.risk_score, float)
    assert decision.risk_score > 0
    assert isinstance(decision.recommended_action, str)

def test_decision_manager_process_dict(manager):
    pred_dict = {
        "attack_type": "DoS SYN Flood",
        "confidence": 98.5,
        "source_ip": "192.168.1.100",
        "destination_ip": "10.0.0.5",
        "packet_count": 150000
    }
    decision = manager.process_prediction(pred_dict)
    assert decision.attack_type == "DoS SYN Flood"
    assert decision.automation_level in (4, 5)
    assert decision.incident_status in ("AUTO_MITIGATED", "CONTAINED")
    # Supports both attribute and subscript access
    assert decision["automation_level"] in (4, 5)

def test_decision_manager_benign_traffic(manager):
    pred_dict = {
        "attack_type": "Benign Traffic",
        "confidence": 95.0,
        "source_ip": "198.51.100.1",
        "destination_ip": "10.0.0.5",
        "packet_count": 50
    }
    decision = manager.process_prediction(pred_dict)
    assert decision.automation_level == 0
    assert decision.incident_status in ("LOGGED", "CONTAINED")
    assert decision.analyst_required is False

def test_policy_engine_loading():
    pe = PolicyEngine()
    policies = pe.loader.reload()
    assert len(policies) >= 5
    assert any("SYN" in p.policy_id for p in policies)

def test_executor_actions():
    executor = SimulationExecutor()
    results = executor.execute_actions(["BLOCK_SOURCE_IP", "SYN_PROTECTION"], "192.168.1.50")
    assert len(results) == 2
    assert all(r["status"] == "SUCCESS" for r in results)
