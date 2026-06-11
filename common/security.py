import jwt
import os
from datetime import datetime, timedelta

DISPATCH_SECRET = os.getenv("DISPATCH_SECRET") or "dev-secret-key"

def create_token(service_id: str, expires_hours: int = 1) -> str:
    payload = {
        "sub": service_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
    }
    return jwt.encode(payload, DISPATCH_SECRET, algorithm="HS256")

def verify_token(token: str) -> str:
    try:
        data = jwt.decode(token, DISPATCH_SECRET, algorithms=["HS256"])
        return data.get("sub")
    except jwt.PyJWTError as e:
        raise Exception("Invalid token") from e
