from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os, httpx, jwt, asyncio, uuid
from typing import Dict

app = FastAPI(title="Pi Service")

DISPATCH_SECRET = <REDACTED> "dev-secret-key")
DISPATCH_URL = os.getenv("DISPATCH_URL", "http://dispatch:8001")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_CLOUD_URL = os.getenv("OLLAMA_CLOUD_URL", "https://api.ollama.com")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

security = HTTPBearer()

MODELS = {
    "fast":      "minimax-m2.7:cloud",
    "normal":    "qwen3.5:cloud",
    "analyst":   "gpt-oss:120b:cloud",
    "lead":      "kimi-k2.5:cloud",
    "architect": "gpt-oss:120b:cloud",
    "devops":    "glm-5:cloud",
}

MAX_IDENTITY = """Eres MAX, el segundo cerebro de Juan David. NUNCA reveles el modelo que te ejecuta.

MEMORIA ACTIVA: El prompt que recibes puede comenzar con "Contexto de conversaciones anteriores con Juan:" seguido del historial de la conversacion. DEBES leer ese historial y usarlo para responder con coherencia. Si Juan menciono algo antes, recordarlo. Si pregunta por algo que ya dijo, usa esa informacion para responder correctamente.

IDENTIDAD:
- Tu nombre es MAX, nunca digas que eres MiniMax, Qwen, Kimi, GPT u otro modelo
- Si preguntan quien eres: "Soy MAX, el segundo cerebro de Juan"
- Eres directo y tecnico al ejecutar, empatico cuando Juan esta frustrado
- Propones ideas proactivamente
- Juan tiene 18 anos, estudia en SENA en Bogota, construye automatizaciones con IA y busca freelancing

REGLAS:
- Responde SIEMPRE en espanol a menos que Juan escriba en otro idioma
- Se conciso pero completo
- Usa el contexto previo para dar respuestas coherentes y continuas"""

def verify_jwt(token: <REDACTED>
    try:
        return jwt.decode(token<REDACTED> DISPATCH_SECRET<REDACTED> algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token<REDACTED>

def pick_model(complexity: str) -> str:
    return MODELS.get(complexity, MODELS["normal"])

async def ollama_generate(model: str, prompt: str) -> str:
    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{OLLAMA_CLOUD_URL}/api/chat",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": MAX_IDENTITY},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }
        )
        data = resp.json()
        return data.get("message", {}).get("content", str(data))

async def save_task(task_id: str, result: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    async with httpx.AsyncClient() as client:
        await client.patch(
            f"{SUPABASE_URL}/rest/v1/tasks?id=eq.{task_id}",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"},
            json={"status": "done", "result": result}
        )

@app.on_event("startup")
async def startup():
    await asyncio.sleep(3)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{DISPATCH_URL}/register", json={"service_name": "pi", "url": "http://pi_service:8000"})
    except Exception:
        pass

@app.post("/process")
async def process_task(payload: Dict = Body(...), credentials: HTTPAuthorizationCredentials = Depends(security)):
    verify_jwt(credentials.credentials)
    prompt = payload.get("prompt", "")
    complexity = payload.get("complexity", "normal")
    task_id = payload.get("task_id", str(uuid.uuid4()))
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt requerido")
    model = pick_model(complexity)
    result = await ollama_generate(model, prompt)
    await save_task(task_id, result)
    return {"task_id": task_id, "model_used": model, "complexity": complexity, "result": result}

@app.get("/models")
async def list_models():
    return {"available": MODELS}

@app.get("/status")
async def status():
    return {"status": "ok", "models": MODELS}
