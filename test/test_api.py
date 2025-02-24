from fastapi.testclient import TestClient
from app.app import app
import json

client = TestClient(app)


#Positive enforcement
def test_positive_enforcement_create():
    policy_datetime_lt = """
    {
        "@context": "http://www.w3.org/ns/odrl.jsonld",
        "@type": "Offer",
        "uid": "https://helio.auroral.linkeddata.es/policy/2",
        "permission": [{
           "target": "https://helio.auroral.linkeddata.es/api/luminosity/data",
           "action": "distribute",
           "constraint": [{
               "leftOperand": "dateTime",
               "operator": "lt",
               "rightOperand":  { "@value": "2040-01-01T09:00:01", "@type": "xsd:dateTime" }
           }]
       }]
    }
    """
    response = client.post("/api/policy/", json={"odrl_policy": json.loads(policy_datetime_lt)})

    assert response.status_code == 201
    assert response.json()["odrl_policy"]["uid"] == "policy:2"

def test_get_policy():
    response = client.get("/api/policy/policy:123")
    assert response.status_code == 200
    assert response.json()["uid"] == "policy:123"

def test_evaluate_policy():
    response = client.get("/api/policy/evaluate/policy:123")
    assert response.status_code == 200

def test_policy_not_found():
    response = client.get("/api/policy/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Política no encontrada"}

def test_invalid_content_type():
    response = client.post(
        "/api/policy/evaluate",
        json={"policy": {
        "@context": "http://www.w3.org/ns/odrl.jsonld",
        "@type": "Offer",
        "uid": "http://example.com/policy:6165",
        "profile": "http://example.com/odrl:profile:10",
        "permission": [{
            "target": "http://example.com/document:1234",
            "assigner": "http://example.com/org:616",
            "action": "distribute",
            "constraint": [{
                "leftOperand": "dateTime",
                "operator": "lt",
                "rightOperand": { "@value": "2025-01-01", "@type": "xsd:date" }
            }, {
                "leftOperand": { "@value": "{{token}}", "@type": "xsd:string" },
                "operator": "eq",
                "rightOperand": { "@value": "AAA", "@type": "xsd:string" }
            }]
        }]
    }},
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported MIME type, only supported application/ld+json"}



#pytest test_api.py
