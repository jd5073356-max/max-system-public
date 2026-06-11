import json
from fastapi.testclient import TestClient

from pi_service.app import app as pi_app
from common.security import create_token

client = TestClient(pi_app)

def test_process_endpoint():
    # generar token para un service_id ficticio
    token = create_token("test-service")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"action": "demo", "data": 123}
    response = client.post("/process", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "done"
    assert data["result"]["message"] == "processed"
    assert data["result"]["input"] == payload
