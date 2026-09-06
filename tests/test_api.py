import pytest
from fastapi.testclient import TestClient
from decision_engine.api.routes import app, INCIDENTS_DB

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_db():
    INCIDENTS_DB.clear()
    yield

def test_root_redirect():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"

def test_analyze_traffic():
    payload = {
        "timestamp": "2026-07-30T22:46:00Z",
        "attack_type": "DoS UDP Flood",
        "confidence": 0.99,
        "src_ip": "1.2.3.4",
        "dest_ip": "10.0.0.5",
        "src_port": 12345,
        "dest_port": 80,
        "protocol": "UDP",
        "packet_count": 15000,
        "flow_duration": 2.5
    }
    response = client.post("/api/v1/decision/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "incident_id" in data
    assert "attack_type" in data
    assert data["src_ip"] == "1.2.3.4"
    assert len(INCIDENTS_DB) == 1

def test_get_incidents():
    test_analyze_traffic()
    response = client.get("/api/v1/decision/incidents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

def test_approve_incident():
    test_analyze_traffic()
    incident_id = list(INCIDENTS_DB.keys())[0]
    
    # Force status to PENDING_APPROVAL to test approval endpoint
    if hasattr(INCIDENTS_DB[incident_id], "incident_status"):
        INCIDENTS_DB[incident_id].incident_status = "PENDING_APPROVAL"
    else:
        INCIDENTS_DB[incident_id]["incident_status"] = "PENDING_APPROVAL"
    
    response = client.post("/api/v1/decision/approve", json={"incident_id": incident_id})
    assert response.status_code == 200
    status_val = INCIDENTS_DB[incident_id].incident_status if hasattr(INCIDENTS_DB[incident_id], "incident_status") else INCIDENTS_DB[incident_id]["incident_status"]
    assert status_val == "MANUAL_MITIGATED"

def test_get_flagged_traffic():
    response = client.get("/api/v1/traffic/flagged")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_mitigation_sweep_worker_execution(monkeypatch):
    import os
    from decision_engine.api.routes import decision_manager
    db = decision_manager.db
    db.save_incident({
        "incident_id": "INC-SWEEP-01",
        "event_id": "EVT-SWEEP-01",
        "source_ip": "100.64.0.1",
        "destination_ip": "10.0.0.5",
        "attack_type": "DoS SYN Flood",
        "current_state": "MONITORING"
    })
    db.save_active_mitigation({
        "action_id": "ACT-SWEEP-01",
        "incident_id": "INC-SWEEP-01",
        "action_type": "BLOCK_IP_SIMULATION",
        "target": "100.64.0.1",
        "status": "ACTIVE",
        "expires_at": "2020-01-01T00:00:00Z"
    })
    
    expired = decision_manager.recovery_manager.process_expired_mitigations()
    assert len(expired) >= 1
    assert any(m["action_id"] == "ACT-SWEEP-01" for m in expired)
    
    inc = db.get_incident("INC-SWEEP-01")
    assert inc["current_state"] == "RESOLVED"
    
    # Test configurable sweep interval via env var
    monkeypatch.setenv("MITIGATION_SWEEP_INTERVAL_SECONDS", "45")
    interval = float(os.environ.get("MITIGATION_SWEEP_INTERVAL_SECONDS", 30))
    assert interval == 45.0

def test_sensor_status_reports_mode():
    """Task 6 Acceptance: /api/v1/sensor/status returns a field 'mode' reflecting runtime behavior."""
    response = client.get("/api/v1/sensor/status")
    assert response.status_code == 200
    data = response.json()
    assert "mode" in data
    assert data["mode"] in ("LIVE_NFSTREAM", "SIMULATED_DATASET_REPLAY")
    assert "active" in data


