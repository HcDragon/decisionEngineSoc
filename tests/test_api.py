import pytest
from fastapi.testclient import TestClient
from api.router import app, INCIDENTS_DB
from models.enums import IncidentStatus

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
    INCIDENTS_DB[incident_id].incident_status = IncidentStatus.PENDING_APPROVAL
    
    response = client.post("/api/v1/decision/approve", json={"incident_id": incident_id})
    assert response.status_code == 200
    assert INCIDENTS_DB[incident_id].incident_status == IncidentStatus.MANUAL_MITIGATED
