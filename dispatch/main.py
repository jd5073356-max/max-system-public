from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os, uuid, httpx, asyncio, json, re
from datetime import datetime, timedelta
from typing import Dict, Optional
import jwt
import anthropic
from supabase import create_client
from ddgs import DDGS
from bs4 import BeautifulSoup

app = FastAPI(title="MAX Dispatch")

DISPATCH_SECRET = os.getenv("DISPATCH_SECRET", "dev-secret-key")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_CLOUD_URL = os.getenv("OLLAMA_CLOUD_URL", "https://api.ollama.com")
PI_URL = "http://pi_service:8000"
OPENCLAW_URL = "http://openclaw:8002"

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
db = create_client(SUPABASE_URL, SUPABASE_KEY)

security = HTTPBearer()
registered_services: Dict[str, str] = {}

CLAUDE_MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-20250514",
    "opus":   "claude-opus-4-20250514",
}

PI_MODELS = {
    "fast":      "minimax-m2.7:cloud",
    "normal":    "qwen3.5:cloud",
    "analyst":   "gpt-oss:120b:cloud",
    "lead":      "kimi-k2.5:cloud",
    "architect": "gpt-oss:120b:cloud",
    "devops":    "glm-5:cloud",
}

CLASSIFIER_PROMPT = (
    "Eres el clasificador de MAX, el sistema IA de Juan David (18 anos, Bogota, SENA).\n"
    "Analiza el mensaje y responde SOLO con JSON.\n\n"
    "NIVELES:\n"
    "1 = Respuesta directa, simple, una accion\n"
    "2 = Generar contenido, buscar info, crear algo\n"
    "3 = Multiples pasos, analizar, coordinar\n"
    "4 = Tarea autonoma muy compleja, toda la noche\n\n"
    "MODELOS PI:\n"
    "nivel 1: fast | nivel 2 codigo: normal | nivel 2 analisis: analyst | nivel 3: lead | nivel 4: architect\n\n"
    "CLAUDE:\n"
    "nivel 1-2: none | nivel 3: haiku | nivel 4: sonnet\n\n"
    "PATRONES DE JUAN — como habla y que significa:\n"
    "- 'abre X' → needs_local_pc=true, accion shell (abrir programa)\n"
    "- 'organiza X' → needs_local_pc=true, accion claude_code\n"
    "- 'crea una carpeta/archivo/pdf/excel' → needs_local_pc=true\n"
    "- 'ejecuta/corre/lanza X' → needs_local_pc=true, accion shell\n"
    "- 'revisa mi proyecto/codigo' → needs_local_pc=true, accion claude_code\n"
    "- 'busca en mi pc/computador' → needs_local_pc=true, accion claude_code\n"
    "- 'en que voy en X' → needs_local_pc=true, accion claude_code\n"
    "- 'busca en internet/fiverr/google' → needs_search=true\n"
    "- 'lee la pagina de/precio de' → needs_scrape=true\n"
    "- 'agrega tarea/recuerdame/programa que' → needs_schedule=true\n"
    "- 'hazme una guia/explicame/dame' → nivel 2, respuesta directa\n"
    "- 'que es/como funciona/por que' → nivel 1-2, respuesta directa\n"
    "- 'arreglalo/por que no funciona/que esta pasando' → nivel 2-3, debug\n"
    "- 'hazlo automatico/que funcione solo' → nivel 3-4\n"
    "- 'conecta/integra/une esto con' → nivel 3-4\n"
    "- 'analiza todo/organiza todo/resuelve todo' → nivel 4\n\n"
    "REGLA CRITICA — needs_local_pc=true cuando:\n"
    "- menciona su PC, computador, escritorio, carpeta local\n"
    "- pide abrir programas (obsidian, vscode, tiktok, chrome)\n"
    "- pide crear archivos fisicos en su maquina\n"
    "- pide revisar/buscar algo en sus archivos locales\n"
    "- pide ejecutar algo en su sistema\n\n"
    "needs_unknown=true cuando el mensaje es completamente ambiguo y no encaja en ningun patron.\n\n"
    "Responde SOLO con JSON:\n"
    '{"level": 1, "pi": "fast", "claude": "none", "needs_claw": false, "needs_search": false, "needs_scrape": false, "needs_local_pc": false, "needs_schedule": false, "needs_unknown": false}'
)

LOCAL_TASK_PROMPT = (
    "Eres el generador de tareas locales de MAX. Juan pidio algo en su PC Windows.\n"
    "Genera el JSON exacto para ejecutar la tarea.\n\n"
    "Acciones:\n"
    "- claude_code: revisar/analizar/editar proyectos de codigo. Campos: prompt, workdir, complexity (fast/normal/complex)\n"
    "- mkdir: crear carpeta. Campos: folder_name, base\n"
    "- write_file: crear archivo texto. Campos: path, content\n"
    "- pdf: crear PDF. Campos: path, content\n"
    "- docx: crear Word. Campos: path, content, title\n"
    "- xlsx: crear Excel. Campos: path, headers (lista), rows (lista de listas)\n"
    "- pptx: crear PowerPoint. Campos: path, slides\n"
    "- csv: crear CSV. Campos: path, headers, rows\n"
    "- shell: comando Windows. Campos: payload\n"
    "- vscode: abrir VS Code. Campos: path\n"
    "- browser: abrir URL. Campos: url\n"
    "- download: descargar. Campos: url\n"
    "- playwright: navegar web. Campos: browser_action, url\n\n"
    "USA claude_code cuando Juan pida revisar/analizar/mejorar/debuggear su codigo o proyectos.\n\n"
    "Rutas de proyectos de Juan:\n"
    "- JavaScript SENA: C:/Users/USUARIO/Trabajo/max/Proyectos/GitHub/javascript-fundamentos\n"
    "- MAX agent: C:/Users/USUARIO/Trabajo/max/max-agent\n"
    "- General: C:/Users/USUARIO/Trabajo\n\n"
    "Ejemplos:\n\n"
    "Revisar proyecto javascript:\n"
    '{"action": "claude_code", "prompt": "revisa el proyecto y dime en que ejercicio voy", "workdir": "C:/Users/USUARIO/Trabajo/max/Proyectos/GitHub/javascript-fundamentos", "complexity": "normal"}\n\n'
    "Crear carpeta:\n"
    '{"action": "mkdir", "folder_name": "mi carpeta", "base": "C:/Users/USUARIO/Desktop"}\n\n'
    "Crear Excel:\n"
    '{"action": "xlsx", "path": "C:/Users/USUARIO/Desktop/datos.xlsx", "headers": ["nombre", "edad", "ciudad"], "rows": [["Juan", 18, "Bogota"], ["Maria", 25, "Medellin"]]}\n\n'
    "Multiples pasos:\n"
    '[{"action": "mkdir", "folder_name": "proyecto", "base": "C:/Users/USUARIO/Desktop"}, {"action": "pdf", "path": "C:/Users/USUARIO/Desktop/proyecto/doc.pdf", "content": "hola"}]\n\n'
    "Responde SOLO con JSON valido sin explicaciones."
)

def create_jwt(service_id: str, hours: int = 24) -> str:
    payload = {"sub": service_id, "iat": datetime.utcnow(), "exp": datetime.utcnow() + timedelta(hours=hours)}
    return jwt.encode(payload, DISPATCH_SECRET, algorithm="HS256")

def verify_jwt(token: str) -> str:
    try:
        payload = jwt.decode(token, DISPATCH_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def classify_with_ai(message: str) -> dict:
    try:
        headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{OLLAMA_CLOUD_URL}/api/chat",
                headers=headers,
                json={
                    "model": "kimi-k2.5:cloud",
                    "messages": [
                        {"role": "system", "content": CLASSIFIER_PROMPT},
                        {"role": "user", "content": message}
                    ],
                    "stream": False
                }
            )
            content = resp.json().get("message", {}).get("content", "")
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                return json.loads(match.group())
    except Exception as e:
        print(f"Clasificador falló: {type(e).__name__}: {e}")
    return {"level": 1, "pi": "fast", "claude": "none", "needs_claw": False, "needs_search": False, "needs_scrape": False, "needs_local_pc": False}

async def parse_local_task_with_ai(message: str) -> list:
    try:
        headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{OLLAMA_CLOUD_URL}/api/chat",
                headers=headers,
                json={
                    "model": "kimi-k2.5:cloud",
                    "messages": [
                        {"role": "system", "content": LOCAL_TASK_PROMPT},
                        {"role": "user", "content": message}
                    ],
                    "stream": False
                }
            )
            content = resp.json().get("message", {}).get("content", "")
            content = content.strip()
            if content.startswith("["):
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    return json.loads(match.group())
            else:
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    return [json.loads(match.group())]
    except Exception as e:
        print(f"Parse local task falló: {e}")
    return [{"action": "shell", "payload": message}]

def web_search(query: str, max_results: int = 4) -> list:
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({"title": r["title"], "url": r["href"], "snippet": r["body"][:300]})
        return results
    except Exception as e:
        print(f"Busqueda falló: {e}")
        return []

async def scrape_url(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return ""
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in text.splitlines() if len(l) > 40]
            return "\n".join(lines[:80])
    except Exception as e:
        print(f"Scrape falló {url}: {e}")
        return ""

async def research_web(query: str, scrape: bool = False) -> str:
    results = web_search(query)
    if not results:
        return ""
    context = "Resultados de busqueda web:\n"
    for i, r in enumerate(results[:3]):
        context += f"\n[{i+1}] {r['title']}\nURL: {r['url']}\n{r['snippet']}\n"
        if scrape:
            content = await scrape_url(r["url"])
            if content:
                context += f"Contenido:\n{content[:600]}\n"
    return context

async def create_local_tasks(message: str) -> list:
    task_configs = await parse_local_task_with_ai(message)
    task_ids = []
    for config in task_configs:
        try:
            result = db.table("tasks").insert({
                "title": message[:100],
                "status": "pending",
                "service": "local_pc",
                "metadata": config
            }).execute()
            if result.data:
                task_ids.append(result.data[0]["id"])
        except Exception as e:
            print(f"Error creando tarea local: {e}")
    return task_ids

async def wait_for_local_results(task_ids: list, timeout: int = 60) -> str:
    if not task_ids:
        return ""
    start = datetime.utcnow()
    while (datetime.utcnow() - start).seconds < timeout:
        await asyncio.sleep(3)
        try:
            results = db.table("tasks").select("id, status, result").in_("id", task_ids).execute()
            if not results.data:
                continue
            done = [r for r in results.data if r["status"] in ["done", "failed"]]
            if len(done) == len(task_ids):
                outputs = []
                for r in done:
                    outputs.append(f"[{r['status']}] {r.get('result', '')}")
                return "\n".join(outputs)
        except Exception:
            pass
    return "Tareas enviadas al agente local"

def get_memory(limit: int = 8) -> str:
    try:
        knowledge = ""
        try:
            k = db.table("knowledge").select("category, content").execute()
            if k.data:
                knowledge = "CONOCIMIENTO PERMANENTE DE JUAN:\n"
                for item in k.data:
                    knowledge += f"[{item['category']}] {item['content']}\n"
                knowledge += "\n"
        except Exception:
            pass
        result = db.table("conversations").select("role, content").order("created_at", desc=True).limit(limit).execute()
        memoria = ""
        if result.data:
            memoria = "CONVERSACIONES RECIENTES:\n"
            memoria += "\n".join([f"{r['role']}: {r['content'][:200]}" for r in reversed(result.data)])
        return f"{knowledge}{memoria}\n\nUSA esta memoria para dar contexto a tu respuesta."
    except Exception:
        return ""

def save_memory(role: str, content: str):
    try:
        db.table("conversations").insert({"engine": "dispatch", "role": role, "content": content}).execute()
    except Exception:
        pass

def log_system(level: str, message: str, metadata: dict = {}):
    try:
        db.table("system_logs").insert({"service": "dispatch", "level": level, "message": message, "metadata": metadata}).execute()
    except Exception:
        pass

async def call_pi(prompt: str, pi_model: str, token: str, memory: str = "") -> str:
    full_prompt = prompt
    if memory:
        full_prompt = f"Contexto de conversaciones anteriores con Juan:\n{memory}\n\nMensaje actual: {prompt}"
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{PI_URL}/process",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"prompt": full_prompt, "complexity": pi_model, "task_id": str(uuid.uuid4())}
            )
            return resp.json().get("result", "Pi no respondio")
    except Exception as e:
        return f"Error en Pi: {str(e)}"

async def call_openclaw(command: str, token: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{OPENCLAW_URL}/execute",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"command": command, "task_id": str(uuid.uuid4())}
            )
            return resp.json().get("output", "OpenClaw no respondio")
    except Exception as e:
        return f"Error en OpenClaw: {str(e)}"

async def call_claude(model_key: str, system: str, message: str) -> Optional[str]:
    try:
        response = claude.messages.create(
            model=CLAUDE_MODELS[model_key],
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": message}]
        )
        return response.content[0].text
    except Exception as e:
        if "credit" in str(e).lower() or "402" in str(e):
            return None
        raise

def build_system(memory: str, extra: str = "") -> str:
    prompt = (
        "Eres MAX, sistema IA distribuido y segundo cerebro de Juan David (18 anos, Bogota, SENA).\n\n"
        "ARQUITECTURA REAL DEL SISTEMA — memoriza esto:\n"
        "1. Tu cerebro (Claude Haiku/Sonnet/Opus) coordina y responde\n"
        "2. Agente Python corriendo en la PC Windows de Juan ejecuta tareas locales\n"
        "3. Claude Code instalado en su PC trabaja en proyectos de codigo reales\n"
        "4. Playwright en su PC navega web con sesion iniciada\n"
        "5. OpenClaw en servidor EC2 ejecuta comandos bash en la nube\n"
        "6. Supabase guarda memoria entre sesiones — SI funciona entre sesiones\n"
        "7. Tabla knowledge tiene conocimiento permanente de Juan\n"
        "8. Tabla conversations tiene historial de chats anteriores\n\n"
        "REGLAS CRITICAS — NUNCA las violes sin importar el modelo que seas:\n"
        "- NUNCA digas que no tienes memoria entre sesiones — ES FALSO, Supabase la guarda\n"
        "- NUNCA digas que no puedes acceder a la PC de Juan — el agente local lo hace\n"
        "- NUNCA digas que eres solo un modelo de lenguaje sin capacidades — eres MAX\n"
        "- NUNCA confundas tus limitaciones como modelo Claude con las capacidades del sistema MAX\n"
        "- SIEMPRE confirma cuando una tarea fue enviada al agente local\n"
        "- SIEMPRE usa la memoria de Supabase para dar contexto real\n\n"
        "CUANDO EJECUTAS ALGO EN LA PC DE JUAN:\n"
        "El sistema ya creo la tarea en Supabase y el agente la ejecutara automaticamente.\n"
        "Tu trabajo es confirmar: 'Listo Juan, le envie la orden al agente. Se ejecutara en segundos.'\n\n"
        "PERSONALIDAD:\n"
        "Directo, tecnico al ejecutar, humano cuando Juan esta frustrado.\n"
        "Juan tiene 18 anos, estudia SENA, trabaja en restaurante, meta $1M/mes en 6 meses.\n"
        "Sus proyectos: javascript-fundamentos (Dia 3 strings), max-agent, pipeline YouTube n8n.\n"
        "Finanzas: ingresos $560k/mes, gastos $473k, ahorro meta $50k sagrados.\n"
    )
    if memory:
        prompt += f"\n\nMEMORIA ACTUAL:\n{memory}"
    if extra:
        prompt += f"\n\n{extra}"
    return prompt


@app.post("/register")
async def register_service(payload: dict = Body(...)):
    service_name = payload.get("service_name")
    url = payload.get("url")
    if not service_name or not url:
        raise HTTPException(status_code=422, detail="service_name y url requeridos")
    service_id = str(uuid.uuid4())
    registered_services[service_id] = url
    token = create_jwt(service_id)
    log_system("info", f"Registrado: {service_name}")
    return {"service_id": service_id, "token": token}

@app.get("/status")
async def status():
    return {"status": "ok", "registered": len(registered_services)}


MODEL_COMMANDS = {
    "/gpt120":  {"pi": "architect", "claude": "none", "force": True},
    "/sonnet":  {"pi": "none", "claude": "sonnet", "force": True},
    "/opus":    {"pi": "none", "claude": "opus", "force": True},
    "/haiku":   {"pi": "none", "claude": "haiku", "force": True},
    "/fast":    {"pi": "fast", "claude": "none", "force": True},
}

def parse_model_command(message: str) -> tuple:
    msg = message.strip()
    for cmd, config in MODEL_COMMANDS.items():
        if msg.lower().startswith(cmd):
            clean_message = msg[len(cmd):].strip()
            return clean_message, config
    return message, None

@app.post("/dispatch")
async def dispatch_task(task: Dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    verify_jwt(credentials.credentials)
    message = task.get("message", "")
    if not message:
        raise HTTPException(status_code=422, detail="message requerido")

    memory = get_memory()

    message, forced_model = parse_model_command(message)
    if forced_model:
        classification = {
            "level": 4 if forced_model.get("claude") in ["sonnet", "opus"] else 2,
            "pi": forced_model.get("pi", "fast"),
            "claude": forced_model.get("claude", "none"),
            "needs_claw": False,
            "needs_search": False,
            "needs_scrape": False,
            "needs_local_pc": False,
            "needs_schedule": False
        }
        log_system("info", f"Modelo forzado: {forced_model}")
    else:
        classification = await classify_with_ai(message)
    level = classification.get("level", 1)
    pi_model = classification.get("pi", "fast")
    claude_model = classification.get("claude", "none")
    needs_claw = classification.get("needs_claw", False)
    needs_search = classification.get("needs_search", False)
    needs_scrape = classification.get("needs_scrape", False)
    needs_local_pc = classification.get("needs_local_pc", False)
    internal_token = create_jwt("dispatch-internal", hours=1)

    save_memory("user", message)
    log_system("info", f"Nivel {level} Pi:{pi_model} LocalPC:{needs_local_pc}", {"msg": message[:80]})

    local_results = ""
    if needs_local_pc:
        log_system("info", "Creando tareas para agente local")
        task_ids = await create_local_tasks(message)
        if task_ids:
            local_results = await wait_for_local_results(task_ids, timeout=120)
            log_system("info", f"Resultado local: {local_results[:100]}")

    web_context = ""
    if needs_search or needs_scrape:
        web_context = await research_web(message, scrape=needs_scrape)

    enriched_message = message
    if web_context:
        enriched_message += f"\n\n{web_context}"
    if local_results:
        enriched_message += f"\n\nResultado del agente local:\n{local_results}"

    pi_result = ""
    claw_result = ""
    reply = ""

    if needs_local_pc and local_results:
        system = build_system(memory)
        claude_reply = await call_claude("haiku", system, enriched_message)
        if claude_reply:
            reply = claude_reply
        else:
            reply = "Listo Juan, ejecute la tarea en tu PC." if "done" in local_results else f"Problema: {local_results}"

    elif level <= 2:
        pi_result = await call_pi(enriched_message, pi_model, internal_token, memory)
        if needs_claw:
            claw_result = await call_openclaw(pi_result, internal_token)
        pi_context = claw_result if claw_result else pi_result
        extra = f"Pi respondio:\n{pi_context}" if pi_context else ""
        system = build_system(memory, extra)
        claude_reply = await call_claude("haiku", system, enriched_message)
        reply = claude_reply if claude_reply else pi_context

    elif level == 3:
        pi_result = await call_pi(enriched_message, pi_model, internal_token, memory)
        if needs_claw:
            claw_result = await call_openclaw(pi_result, internal_token)
        extra = f"Pi respondio:\n{pi_result}"
        if claw_result:
            extra += f"\n\nOpenClaw ejecuto:\n{claw_result}"
        system = build_system(memory, extra)
        claude_reply = await call_claude("haiku", system, message)
        reply = claude_reply if claude_reply else f"[Sin creditos Claude]\n\n{pi_result}"

    else:
        pi_result = await call_pi(enriched_message, pi_model, internal_token, memory)
        if needs_claw:
            claw_result = await call_openclaw(pi_result, internal_token)
        extra = f"gpt-oss:120b analizo:\n{pi_result}"
        if claw_result:
            extra += f"\n\nOpenClaw ejecuto:\n{claw_result}"
        system = build_system(memory, extra)
        claude_reply = await call_claude(claude_model, system, message)
        if claude_reply:
            reply = claude_reply
        else:
            fallback = await call_pi(f"Responde como MAX a: {message}", "architect", internal_token, memory)
            reply = f"[Sin creditos Claude]\n\n{fallback}"

    save_memory("assistant", reply)
    log_system("info", f"Respuesta nivel {level}")

    return {
        "task_id": str(uuid.uuid4()),
        "status": "done",
        "level": level,
        "models_used": {"pi": pi_model, "claude": claude_model},
        "reply": reply
    }

from telegram import poll_telegram

@app.on_event("startup")
async def start_telegram():
    if os.getenv("TELEGRAM_TOKEN"):
        asyncio.create_task(poll_telegram())
