# Docker Compose — AetherVoice

Full-stack MVP hosting: **Nginx + React (static) + FastAPI + MySQL**.

## Prerequisites

- Docker Engine 24+
- Docker Compose v2 (`docker compose`)

## Configure

```bash
cp .env.docker.example .env.docker
```

Important variables:

| Variable | Purpose |
|----------|---------|
| `MYSQL_ROOT_PASSWORD` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE` | DB credentials |
| `ADMIN_ACCESS_TOKEN` | Admin UI login token |
| `HTTP_PORT` | Host port mapped to Nginx (default `80`) |
| `GOOGLE_API_KEY` | Gemini Live (optional until demos) |
| `TWILIO_*` | Phone demos (optional until demos) |
| `PUBLIC_BASE_URL` | Public URL Twilio should call (e.g. `https://your.domain`) |

## Build & start

```bash
docker compose --env-file .env.docker up -d --build
```

## Stop

```bash
docker compose --env-file .env.docker down
```

## Verify

```bash
curl -s http://localhost/api/health
# → {"status":"ok","service":"voice-agent-platform"}
```

Open http://localhost and sign in with `ADMIN_ACCESS_TOKEN`.

## Call debugging (MySQL)

Transcripts and tool I/O are stored in MySQL (`calls`, `call_turns`, `call_tool_io`, `call_events`).

```bash
curl -s http://localhost/api/calls | jq .
curl -s http://localhost/api/calls/<call_id> | jq .
```

Or open **Call debug** in the admin UI.
