import pytest
import os
import pandas as pd
from decision_engine.integrations.ids_bridge import IDSBridge
from decision_engine.decision.decision_manager import DecisionManager
from decision_engine.models.threat_event import ThreatEvent
from decision_engine.models.decision import SecurityDecision

@pytest.fixture
def ids_bridge():
    return IDSBridge()

@pytest.fixture
def decision_manager():
    return DecisionManager()

def test_ids_bridge_artifact_loading(ids_bridge):
    """Verifies that all ML artifacts and transformers are properly loaded."""
    assert ids_bridge.is_ready is True
    assert ids_bridge.model is not None
    assert ids_bridge.encoder is not None
    assert ids_bridge.scaler is not None
    assert len(ids_bridge.feature_names) == 73
    assert len(ids_bridge.encoder.classes_) == 10

def test_ids_bridge_flow_prediction(ids_bridge):
    """Verifies inference on real sample rows from the dataset."""
    df_samples = ids_bridge.load_dataset_samples(n_per_class=2)
    assert len(df_samples) > 0
    
    first_row = df_samples.iloc[0]
    pred_class, confidence, actual = ids_bridge.predict_flow(first_row)
    
    assert isinstance(pred_class, str)
    assert pred_class in ids_bridge.encoder.classes_
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0

def test_ids_bridge_threat_event_conversion(ids_bridge):
    """Verifies conversion of a flow into a validated ThreatEvent."""
    df_samples = ids_bridge.load_dataset_samples(n_per_class=1)
    first_row = df_samples.iloc[0]
    
    event = ids_bridge.flow_to_threat_event(first_row)
    assert isinstance(event, ThreatEvent)
    assert event.source.ip != ""
    assert event.destination.ip.startswith("10.0.0.")
    assert event.detection.attack_type in ids_bridge.encoder.classes_
    assert 0.0 <= event.detection.confidence <= 1.0
    assert event.network.packet_count >= 1

def test_all_10_attack_classes_end_to_end(ids_bridge, decision_manager):
    """
    Verifies that all 10 attack classes from the IDS model are successfully
    processed by the Decision Engine and match specific security policies.
    """
    classes = list(ids_bridge.encoder.classes_)
    assert len(classes) == 10
    
    for attack_type in classes:
        # Create a synthetic or mapped event for each class
        mock_payload = {
            "source": {"ip": "198.51.100.50", "port": 45120},
            "destination": {"ip": "10.0.0.5", "port": 80},
            "network": {
                "protocol": "TCP",
                "packet_count": 5000 if "Flood" in attack_type else 50,
                "flow_duration": 1.5,
                "bytes": 320000 if "Flood" in attack_type else 3200,
                "packets_per_second": 3333.0 if "Flood" in attack_type else 33.3
            },
            "detection": {
                "model": "RandomForestClassifier-IDS",
                "attack_type": attack_type,
                "confidence": 0.95,
                "confidence_level": "HIGH"
            },
            "sensor": {"source": "CICIDS2017-NFStream-Sensor", "mode": "LIVE"}
        }
        
        event = ThreatEvent(**mock_payload)
        decision = decision_manager.process(event)
        
        assert isinstance(decision, SecurityDecision)
        assert decision.attack_type == attack_type
        assert decision.incident_id.startswith("INC-")
        assert decision.risk_score >= 0.0
        assert decision.policy_id != ""
        assert decision.explanation != ""
        
        # Verify policy mapping logic
        if attack_type == "Benign Traffic":
            assert decision.automation_level == 0
            assert decision.decision.value == "ALLOW"
        elif "Flood" in attack_type:
            assert decision.automation_level in (4, 5)
            assert decision.decision.value == "CONTAIN"
        elif attack_type == "MITM ARP Spoofing":
            assert decision.automation_level == 4
            assert decision.decision.value == "CONTAIN"
        elif "Recon" in attack_type:
            assert decision.automation_level in (2, 3)
