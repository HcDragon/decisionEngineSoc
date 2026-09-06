import os
import pytest
from fastapi.testclient import TestClient

from decision_engine.api.routes import app

client = TestClient(app)

def test_get_model_info():
    response = client.get("/api/v1/model/info")
    assert response.status_code == 200
    data = response.json()
    assert data["model_type"] == "RandomForestClassifier"
    assert data["n_features"] == 73
    assert len(data["classes"]) >= 8
    assert data["is_ready"] is True

def test_predict_flow_sample():
    # Test with dummy features
    dummy_flow = {f"feat_{i}": 0.0 for i in range(73)}
    response = client.post("/api/v1/model/predict", json=dummy_flow)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_attack" in data
    assert "confidence" in data
    assert "class_probabilities" in data
    assert isinstance(data["class_probabilities"], dict)

def test_get_model_sample_and_predict():
    response = client.get("/api/v1/model/sample")
    if response.status_code == 200:
        sample = response.json()
        assert isinstance(sample, dict)
        pred_res = client.post("/api/v1/model/predict?feed_pipeline=true", json=sample)
        assert pred_res.status_code == 200
        pred_data = pred_res.json()
        assert "predicted_attack" in pred_data
        assert "decision" in pred_data
