import os, httpx, asyncio, logging
from datetime import datetime, timedelta
import jwt

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
DISPATCH_SECRET = os.getenv("DISPATCH_SECRET", "dev-secret-key")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("telegram")

def get_internal_token() -> str:
    payload = {
        "sub": "telegram-bridge",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, DISPATCH_SECRET, algorithm="HS256")

async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text[:4000],
            "parse_mode": "Markdown"
        })

async def send_typing(chat_id: int):
    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API}/sendChatAction", json={
            "chat_id": chat_id,
            "action": "typing"
        })

async def process_message(chat_id: int, text: str):
    if text.startswith("/start"):
        await send_message(chat_id, "MAX activo. Habla.")
        return

    await send_typing(chat_id)

    try:
        token = get_internal_token()
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "http://localhost:8001/dispatch",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={"message": text}
            )
            result = resp.json()
            reply = result.get("reply", "Sin respuesta")
            level = result.get("level", "?")
            models = result.get("models_used", {})
            pi = models.get("pi", "?")
            claude = models.get("claude", "none")

            footer = f"\n\n_Nivel {level} · {pi}_"
            if claude != "none":
                footer += f" · {claude}"

            await send_message(chat_id, reply + footer)

    except Exception as e:
        await send_message(chat_id, f"Error: {str(e)[:100]}")
        log.error(f"Error procesando mensaje: {e}")

async def poll_telegram():
    offset = 0
    log.info("Telegram polling iniciado")

    while True:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                resp = await client.get(
                    f"{TELEGRAM_API}/getUpdates",
                    params={"offset": offset, "timeout": 30, "limit": 10}
                )
                data = resp.json()

                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        message = update.get("message", {})
                        chat_id = message.get("chat", {}).get("id")
                        text = message.get("text", "")
                        if chat_id and text:
                            log.info(f"Mensaje de {chat_id}: {text[:50]}")
                            asyncio.create_task(process_message(chat_id, text))

        except Exception as e:
            log.error(f"Polling error: {e}")
            await asyncio.sleep(5)
