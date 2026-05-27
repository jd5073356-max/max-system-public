import jwt
import os
from datetime import datetime, timedelta

DISPATCH_SECRET = <REDACTED> or "dev-secret-key"

def create_token<REDACTED> str, expires_hours: int = 1) -> str:
    payload = {
        "sub": service_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=expires_hours),
    }
    return jwt.encode(payload, DISPATCH_SECRET<REDACTED> algorithm="HS256")

def verify_token<REDACTED> str) -> str:
    try:
        data = jwt.decode(token<REDACTED> DISPATCH_SECRET<REDACTED> algorithms=["HS256"])
        return data.get("sub")
    except jwt.PyJWTError as e:
        raise Exception("Invalid token<REDACTED> from e
