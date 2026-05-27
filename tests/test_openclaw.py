import json
from fastapi.testclient import TestClient

from openclaw.server import app as openclaw_app
from common.security import create_token

client = TestClient(openclaw_app)

def test_execute_action():
    token = <REDACTED>
    headers = {"Authorization": f"Bearer {token<REDACTED>
    payload = {"action": "demo", "value": 42}
    response = client.post("/claw/execute", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "executed"
    assert data["payload"] == payload
