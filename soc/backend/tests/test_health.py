"""
Tests for health and system status endpoints.
"""
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "automation_mode" in data
    assert "timestamp" in data


def test_system_status(client):
    response = client.get("/system/status")
    assert response.status_code == 200
    data = response.json()
    assert "environment" in data
    assert "automation_mode" in data
    assert "executor" in data
    assert "lab_mode" in data
    assert data["config_dir_exists"] is True


def test_system_mode_update(client):
    # Set to 'off'
    response = client.post("/system/mode", json={"automation": "off"})
    assert response.status_code == 200
    assert response.json()["automation"] == "off"

    # Verify through health check
    health_resp = client.get("/health")
    assert health_resp.json()["automation_mode"] == "off"

    # Set back to 'recommend_only'
    response = client.post("/system/mode", json={"automation": "recommend_only"})
    assert response.status_code == 200
    assert response.json()["automation"] == "recommend_only"
