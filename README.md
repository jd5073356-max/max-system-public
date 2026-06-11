# MAX · Sistema de IA Distribuido

![status](https://img.shields.io/badge/status-hibernando-blue)
![Python](https://img.shields.io/badge/Python-3.x-3776ab?logo=python)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ed?logo=docker)
![AWS](https://img.shields.io/badge/deploy-AWS_EC2-orange?logo=amazonec2)
![Supabase](https://img.shields.io/badge/Supabase-pgvector-3ecf8e?logo=supabase)

Segundo cerebro y socio estratégico de Juan David. Sistema multi-agente desplegado en AWS EC2 con memoria persistente, canal de entrada por Telegram y agente local en Windows.

> Copia pública sanitizada de `max-system` (secretos removidos). Ver [Estado del proyecto](#estado-del-proyecto).

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
DISPATCH_SECRET=
TELEGRAM_TOKEN=
OLLAMA_API_KEY=
OLLAMA_CLOUD_URL=https://api.ollama.com
```

## Inicio rápido
```bash
git clone https://github.com/jd5073356-max/max-system-public.git
cd max-system-public
cp .env.example .env  # completar con tus keys
docker compose up -d
```

## Estado del proyecto

**En hibernación activa.** El sistema estuvo desplegado en producción sobre AWS EC2 (Docker Compose,
Nginx, Supabase). La pausa responde a una migración planificada hacia un homelab propio con costo de
operación mínimo. El código queda como referencia de arquitectura de un sistema multi-agente distribuido.

## Autor

Juan David · Bogotá, Colombia · [@jd5073356-max](https://github.com/jd5073356-max)
