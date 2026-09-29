"""
Tests for Traffic Monitoring and NFStream integration endpoints.
"""
from fastapi.testclient import TestClient
from soc.backend.app.main import create_app


def test_traffic_status_endpoint():
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/traffic/status")
        assert res.status_code == 200
        data = res.json()
        assert "monitored_port" in data
        assert "engine_mode" in data
        assert "status" in data
        assert "protocol_distribution" in data


def test_traffic_port_switch():
    app = create_app()
    with TestClient(app) as client:
        # Switch to port 443
        res = client.post("/api/traffic/port", json={"port": 443})
        assert res.status_code == 200
        data = res.json()
        assert data["monitored_port"] == 443

        # Check status reflects the port
        status_res = client.get("/api/traffic/status")
        assert status_res.status_code == 200
        assert status_res.json()["monitored_port"] == 443


def test_traffic_flows_endpoint():
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/traffic/flows?limit=10")
        assert res.status_code == 200
        flows = res.json()
        assert isinstance(flows, list)


def test_dashboard_overview():
    app = create_app()
    with TestClient(app) as client:
        res = client.get("/api/dashboard/overview")
        assert res.status_code == 200
        data = res.json()
        assert "system" in data
        assert "stats" in data
        assert "traffic" in data
