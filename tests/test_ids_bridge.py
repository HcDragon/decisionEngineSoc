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
def decision_manager(tmp_path):
    from decision_engine.storage.db import Database
    db_file = str(tmp_path / "test_ids_bridge.db")
    return DecisionManager(db=Database(db_path=db_file))

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

def test_all_monitored_assets_have_non_default_criticality():
    """Task 4 Acceptance: Every IP in IDSBridge.MONITORED_ASSETS must resolve to non-default criticality in ContextEnricher."""
    from decision_engine.integrations.ids_bridge import MONITORED_ASSETS
    from decision_engine.context.context_enricher import ContextEnricher
    from decision_engine.models.threat_event import ThreatEvent

    enricher = ContextEnricher()
    for asset in MONITORED_ASSETS:
        ip = asset["ip"]
        assert ip in enricher.asset_registry, f"Asset IP {ip} missing from ContextEnricher asset_registry"
        crit = enricher.asset_registry[ip]["criticality"]
        # Default in risk engine is 50; all registered monitored assets must have explicit non-default criticality
        assert crit != 50, f"Asset IP {ip} has default criticality 50"
        assert 0 <= crit <= 100

        # Verify through full ContextEnricher.enrich()
        test_payload = {
            "source": {"ip": "198.51.100.50", "port": 45120},
            "destination": {"ip": ip, "port": 80},
            "network": {
                "protocol": "TCP",
                "packet_count": 100,
                "flow_duration": 1.0,
                "bytes": 5000,
                "packets_per_second": 100.0
            },
            "detection": {
                "model": "RandomForestClassifier-IDS",
                "attack_type": "DoS SYN Flood",
                "confidence": 0.95,
                "confidence_level": "HIGH"
            }
        }
        event = ThreatEvent(**test_payload)
        ctx = enricher.enrich(event)
        assert ctx.configured.asset_criticality == crit
        assert ctx.configured.asset_criticality != 50

def test_persistent_attacker_correlation(ids_bridge, decision_manager):
    """Task 5 Acceptance: Reusing persistent attacker IPs triggers incident correlation (event_count > 1)."""
    has_correlation = False
    for threat_event, meta in ids_bridge.stream_dataset(n_samples=50, delay_seconds=0):
        decision = decision_manager.process(threat_event)
        inc = decision_manager.db.get_incident(decision.incident_id)
        if inc and inc.get("event_count", 1) > 1:
            has_correlation = True
            break
    assert has_correlation is True

def test_ids_bridge_fails_fast_on_invalid_path(monkeypatch, tmp_path):
    """Task 11 Acceptance: Windows-only paths removed and IDSBridge fails fast on missing artifacts."""
    import inspect
    from decision_engine.integrations.ids_bridge import IDSBridge

    # Ensure hardcoded Windows drive path is not in source
    source = inspect.getsource(IDSBridge.__init__)
    assert "L:\\" not in source
    assert "L:\\\\" not in source

    # Point to empty directory
    empty_dir = str(tmp_path / "empty_aiml")
    os.makedirs(empty_dir, exist_ok=True)
    with pytest.raises(FileNotFoundError) as exc_info:
        IDSBridge(ids_project_dir=empty_dir)
    assert "IDS_PROJECT_DIR" in str(exc_info.value)


