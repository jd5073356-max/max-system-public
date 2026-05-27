# MAX · Sistema de IA Distribuido

Segundo cerebro y socio estratégico de Juan David. Sistema multi-agente desplegado en AWS EC2 con memoria persistente, canal de entrada por Telegram y agente local en Windows.

## Arquitectura
```
Telegram → Nginx → Dispatch (Claude) → Pi (Ollama Cloud) → OpenClaw
                                     ↕
                               Supabase (memoria)
                                     ↕
                          Agente local (Windows PC)
```

## Motores

| Servicio | Puerto | Rol | Modelos |
|---|---|---|---|
| Dispatch | 8001 | Cerebro · coordinador | Claude Haiku / Sonnet / Opus |
| Pi Service | 8000 | Generador de código | minimax · qwen · kimi · gpt-oss:120b |
| OpenClaw | 8002 | Ejecutor de comandos | — |

## Niveles de complejidad

| Nivel | Trigger | Modelos usados | Costo |
|---|---|---|---|
| 1 Simple | 1 acción, mensaje corto | Pi minimax | $0 |
| 2 Normal | Genera código conocido | Pi qwen / glm / gpt-oss | $0 |
| 3 Complejo | Múltiples pasos, archivos | Pi kimi + Claude Haiku | ~$0.003 |
| 4 Muy complejo | Autónomo, 3+ acciones | Pi gpt-oss + Claude Sonnet | ~$0.01 |

## Stack

- **Nube**: AWS EC2 · Ubuntu 24 · Docker Compose
- **Seguridad**: Nginx reverse proxy · API Key · JWT
- **Memoria**: Supabase PostgreSQL + pgvector
- **Canal**: Telegram Bot (polling)
- **Agente local**: Python · Windows · ejecuta tareas remotas

## Variables de entorno
```env
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
DISPATCH_SECRET<REDACTED>
TELEGRAM_TOKEN<REDACTED>
OLLAMA_API_KEY=
OLLAMA_CLOUD_URL=https://api.ollama.com
```

## Inicio rápido
```bash
git clone https://github.com/jd5073356-max/max-system.git
cd max-system
cp .env.example .env  # completar con tus keys
docker compose up -d
```

## Autor

Juan David · Bogotá, Colombia · [@jd5073356-max](https://github.com/jd5073356-max)
