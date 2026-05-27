import asyncio, httpx, json, os
from datetime import datetime, timedelta
import jwt

DISPATCH_SECRET = <REDACTED> "dev-secret-key")
DISPATCH_URL = "http://dispatch:8001"
TELEGRAM_TOKEN = <REDACTED>
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6778293636")

def create_jwt():
    payload = {
        "sub": "scheduler",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=2)
    }
    return jwt.encode(payload, DISPATCH_SECRET<REDACTED> algorithm="HS256")

async def send_telegram(message: str):
    if not TELEGRAM_TOKEN<REDACTED>
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN<REDACTED>
                json={"chat_id": TELEGRAM_CHAT_ID, "text": message[:4000]}
            )
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

async def dispatch_message(message: str) -> str:
    try:
        token = <REDACTED>
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{DISPATCH_URL}/dispatch",
                headers={
                    "Authorization": f"Bearer {token<REDACTED>
                    "Content-Type": "application/json"
                },
                json={"message": message}
            )
            return resp.json().get("reply", "Sin respuesta")
    except Exception as e:
        return f"Error: {str(e)}"

async def decide_and_execute(task: dict) -> bool:
    decision_prompt = (
        f"MAX modo autonomo - DECISION PREVIA.\n"
        f"Tarea programada: {task['name']}\n"
        f"Descripcion: {task['prefix']}\n"
        f"Hora actual Colombia: {get_bogota_time()}\n\n"
        f"Antes de ejecutar esta tarea, analiza:\n"
        f"1. ¿Vale la pena ejecutarla ahora dado el contexto actual?\n"
        f"2. ¿Hay algo en la memoria reciente que haga esta tarea redundante?\n"
        f"3. ¿Cual es la mejor estrategia para ejecutarla?\n\n"
        f"Responde en este formato JSON exacto:\n"
        f'{{"ejecutar": true/false, "razon": "por que si o no", "estrategia": "como ejecutarla mejor", "prioridad": "alta/media/baja"}}'
    )

    decision_raw = await dispatch_message(decision_prompt)

    try:
        import re
        match = re.search(r'\{.*\}', decision_raw, re.DOTALL)
        if match:
            decision = json.loads(match.group())
            ejecutar = decision.get("ejecutar", True)
            razon = decision.get("razon", "")
            estrategia = decision.get("estrategia", "")
            prioridad = decision.get("prioridad", "media")

            print(f"[DECISION] {task['name']}: ejecutar={ejecutar} prioridad={prioridad}")
            print(f"[DECISION] Razon: {razon}")

            if not ejecutar:
                await send_telegram(f"⏭️ MAX decidió omitir: {task['prefix']}\n💭 {razon}")
                return False

            task["estrategia"] = estrategia
            task["prioridad"] = prioridad
            return True
    except Exception as e:
        print(f"[DECISION ERROR] {e}")

    return True

def get_bogota_time():
    now = datetime.utcnow()
    bogota = now - timedelta(hours=5)
    return bogota.strftime("%Y-%m-%d %H:%M")

async def run_task(task: dict):
    task_name = task["name"]
    print(f"[SCHEDULER] Evaluando: {task_name}")

    should_run = await decide_and_execute(task)
    if not should_run:
        return

    estrategia = task.get("estrategia", "")
    mensaje_final = task["message"]
    if estrategia:
        mensaje_final = f"{task['message']}\n\nEstrategia sugerida: {estrategia}"

    await send_telegram(f"🔄 Ejecutando: {task['prefix']}...")
    reply = await dispatch_message(mensaje_final)
    await send_telegram(f"{task['prefix']}\n\n{reply[:3000]}")
    print(f"[SCHEDULER] Completado: {task_name}")

async def get_custom_tasks() -> list:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{os.getenv('SUPABASE_URL')}/rest/v1/scheduled_tasks?status=eq.active",
                headers={
                    "apikey": os.getenv("SUPABASE_KEY"),
                    "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}"
                }
            )
            return resp.json() if resp.status_code == 200 else []
    except Exception:
        return []

DAILY_TASKS = [
    {
        "name": "reporte_proyectos",
        "hour": 22,
        "minute": 0,
        "days": [0,1,2,3,4,5,6],
        "message": "MAX modo autonomo: analiza el estado de todos mis proyectos activos (javascript fundamentos, max-agent, automatizacion youtube n8n) y dame un reporte con que avance hoy, que falta, y cual es la proxima accion mas importante para cada uno. Se especifico y directo.",
        "prefix": "📊 Reporte nocturno de proyectos"
    },
    {
        "name": "ruta_aprendizaje",
        "hour": 22,
        "minute": 15,
        "days": [0,1,2,3,4,5,6],
        "message": "MAX modo autonomo: revisa mi ruta de aprendizaje de JavaScript. Estoy en que nivel segun mi CLAUDE.md, que deberia estudiar manana, y dame un ejercicio especifico para practicar.",
        "prefix": "📚 Ruta de aprendizaje"
    },
    {
        "name": "tendencias_ia",
        "hour": 22,
        "minute": 30,
        "days": [0,2,4],
        "message": "MAX modo autonomo: busca en internet las 3 tendencias mas importantes de automatizacion con IA de los ultimos 3 dias. Dame solo lo relevante para freelancing con automatizaciones. Incluye oportunidades de negocio concretas.",
        "prefix": "🤖 Tendencias IA"
    },
    {
        "name": "monitor_servidor",
        "hour": 22,
        "minute": 45,
        "days": [0,1,2,3,4,5,6],
        "message": "MAX modo autonomo: revisa el estado del servidor EC2. Ejecuta df -h, free -h, docker ps, y docker logs dispatch --tail 5. Dame un resumen de si todo esta bien o si hay algo que arreglar.",
        "prefix": "🖥️ Estado del servidor"
    },
    {
        "name": "buscar_trabajos",
        "hour": 22,
        "minute": 0,
        "days": [1,4],
        "message": "MAX modo autonomo: busca trabajos actuales en Fiverr y Workana de automatizacion con IA, n8n, make.com, chatbots. Filtra los que puedo hacer con mi perfil (18 anos, SENA, automatizacion IA). Dame los 5 mejores con precio y por que aplico.",
        "prefix": "💼 Trabajos disponibles"
    },
    {
        "name": "analisis_n8n",
        "hour": 23,
        "minute": 0,
        "days": [3,6],
        "message": "MAX modo autonomo: analiza el estado de mi pipeline de automatizacion de YouTube en n8n. La generacion de imagenes funciona pero la generacion de video final esta incompleta. Dame ideas especificas de como completarlo para que genere ingresos.",
        "prefix": "⚡ Analisis n8n"
    },
]

last_run = {}

async def scheduler_loop():
    print("[SCHEDULER] MAX Task Scheduler con decision inteligente iniciado")
    await send_telegram(
        "🚀 MAX Task Scheduler activo\n"
        "✅ Decisiones inteligentes activadas\n"
        "📋 Tareas programadas esta noche:\n"
        "• 10:00pm Reporte proyectos\n"
        "• 10:15pm Ruta aprendizaje\n"
        "• 10:30pm Tendencias IA\n"
        "• 10:45pm Monitor servidor\n"
        "• 11:00pm Análisis n8n (jue/dom)"
    )

    while True:
        now = datetime.utcnow()
        bogota = now - timedelta(hours=5)
        bogota_hour = bogota.hour
        bogota_minute = bogota.minute
        weekday = bogota.weekday()

        custom_tasks = await get_custom_tasks()

        all_tasks = DAILY_TASKS + [
            {
                "name": f"custom_{t['id']}",
                "hour": t.get("hour", 22),
                "minute": t.get("minute", 0),
                "days": t.get("days", [0,1,2,3,4,5,6]),
                "message": t.get("message", ""),
                "prefix": f"⚙️ {t.get('title', 'Tarea personalizada')}"
            }
            for t in custom_tasks
        ]

        for task in all_tasks:
            key = f"{task['name']}_{bogota.date()}"
            if (
                bogota_hour == task["hour"] and
                bogota_minute == task["minute"] and
                weekday in task["days"] and
                key not in last_run
            ):
                last_run[key] = True
                asyncio.create_task(run_task(task))

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(scheduler_loop())
