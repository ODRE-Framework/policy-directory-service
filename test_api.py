from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_policy():
    response = client.post("/api/policy/", json={"odrl_policy": {"uid": "policy:123"}})
    assert response.status_code == 201
    assert response.json()["odrl_policy"]["uid"] == "policy:123"

def test_get_policy():
    response = client.get("/api/policy/policy:123")
    assert response.status_code == 200
    assert response.json()["uid"] == "policy:123"

def test_evaluate_policy():
    response = client.get("/api/policy/evaluate/policy:123")
    assert response.status_code == 200


#pytest test_api.py
