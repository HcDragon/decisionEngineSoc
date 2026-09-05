import pytest
from core.engine import DecisionManager
from api.schemas import TrafficPrediction
from models.enums import IncidentStatus
from intelligence.policy_engine import PolicyEngine
from core.executor import SimulationExecutor

@pytest.fixture
def manager():
    return DecisionManager()

def test_decision_manager_process_model(manager):
    prediction = TrafficPrediction(
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
    
    decision = manager.process(prediction)
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
    assert decision.automation_level == 5
    assert decision.incident_status == IncidentStatus.AUTO_MITIGATED
    # Supports both attribute and subscript access
    assert decision["automation_level"] == 5

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
    assert decision.incident_status == IncidentStatus.LOGGED
    assert decision.analyst_required is False

def test_policy_engine_loading():
    pe = PolicyEngine()
    assert len(pe.policies) >= 5
    matched, is_exact = pe.evaluate(risk_score=90.0, attack_type="DoS SYN Flood", confidence=0.95)
    assert is_exact is True
    assert matched["policy_id"] == "POL-NET-004-SYN"

def test_executor_actions():
    executor = SimulationExecutor()
    results = executor.execute_actions(["BLOCK_SOURCE_IP", "SYN_PROTECTION"], "192.168.1.50")
    assert len(results) == 2
    assert all(r["status"] == "SUCCESS" for r in results)
