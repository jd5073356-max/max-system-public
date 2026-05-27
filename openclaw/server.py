from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os, httpx, jwt, asyncio, subprocess, uuid
from typing import Dict

app = FastAPI(title="OpenClaw")

DISPATCH_SECRET = <REDACTED> "dev-secret-key")
DISPATCH_URL = os.getenv("DISPATCH_URL", "http://dispatch:8001")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

security = HTTPBearer()

def verify_jwt(token: <REDACTED>
    try:
        return jwt.decode(token<REDACTED> DISPATCH_SECRET<REDACTED> algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token<REDACTED>

async def log_to_supabase(service: str, level: str, message: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{SUPABASE_URL}/rest/v1/system_logs",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            json={"service": service, "level": level, "message": message}
        )

@app.on_event("startup")
async def startup():
    await asyncio.sleep(3)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{DISPATCH_URL}/register", json={
                "service_name": "openclaw",
                "url": "http://openclaw:8002"
            })
    except Exception:
        pass

@app.post("/execute")
async def execute(
    payload: Dict = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    verify_jwt(credentials.credentials)

    command = payload.get("command", "")
    task_id = payload.get("task_id", str(uuid.uuid4()))

    if not command:
        raise HTTPException(status_code=422, detail="command requerido")

    await log_to_supabase("openclaw", "info", f"Ejecutando: {command[:100]}")

    try:
        proc = subprocess.run(
            command, shell=True, capture_output=True,
            text=True, timeout=60
        )
        output = proc.stdout or proc.stderr
        status = "done" if proc.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        output = "Timeout: comando tardó más de 60 segundos"
        status = "failed"
    except Exception as e:
        output = str(e)
        status = "failed"

    await log_to_supabase("openclaw", "info" if status == "done" else "error", output[:500])

    return {
        "task_id": task_id,
        "status": status,
        "output": output
    }

@app.get("/status")
async def status():
    return {"status": "ok"}
