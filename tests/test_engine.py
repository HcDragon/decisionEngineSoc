import pytest
from core.engine import DecisionManager
from api.schemas import TrafficPrediction, NetworkFlow

@pytest.fixture
def manager():
    return DecisionManager()

def test_decision_manager_auto_mitigate(manager):
    flow = NetworkFlow(
        timestamp="2026-07-30T22:46:00Z",
        src_ip="192.168.1.100",
        dest_ip="10.0.0.5",
        src_port=52172,
        dest_port=22,
        protocol="TCP",
        packet_count=502,
        flow_duration=3618.0
    )
    prediction = TrafficPrediction(
        attack_type="Dictionary Brute Force",
        confidence=0.99,
        flow_context=flow
    )
    
    decision = manager.process(prediction)
    assert decision.attack_type == "Dictionary Brute Force"
    assert decision.src_ip == "192.168.1.100"
    assert isinstance(decision.incident_id, str)
    assert isinstance(decision.risk_score, float)
    assert isinstance(decision.recommended_action, str)
