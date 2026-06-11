import asyncio
import os
import sys
from fastapi.testclient import TestClient

# Añadir el path del proyecto para importar módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dispatch.main import app as dispatch_app
from common.security import create_token, verify_token

client = TestClient(dispatch_app)

def test_register_service():
    response = client.post("/register", json={"service_name": "test", "url": "http://localhost"})
    assert response.status_code == 200
    data = response.json()
    assert "service_id" in data
    assert "token" in data

def test_jwt_creation_and_verification():
    token = create_token("service123", expires_hours=1)
    service_id = verify_token(token)
    assert service_id == "service123"
