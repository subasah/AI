# AetherVoice — Industry-Agnostic Voice Agent Platform

Multi-tenant platform to **create voice agents once**, customize per industry, and **deliver them to customer companies** while you retain ownership of:

- Conversation **flows** (state machines)
- **Prompts** / brand voice
- **Skills** & **agents** (swarm handoffs)
- **MCP** attachments
- **Tool calling** into the customer’s internal services

Inspired by the architecture taught in [agenticvoiceagent.github.io](https://github.com/agenticvoiceagent/agenticvoiceagent.github.io) (tools → skills → agents → swarm → MCP) and the Pipecat realtime pipeline pattern.

> Note: `https://github.com/llmevalcore/voice-agent/` was not publicly resolvable at build time; patterns were taken from the agentic voice course + local Pipecat starter in this repo.

---

## Layout

```text
voice-agent-platform/
├── docker-compose.yml        # Nginx + React + FastAPI + MySQL
├── nginx/                    # Reverse proxy + static React build
├── mysql/init.sql            # DB schema bootstrap
├── library/                  # Shared brain (reusable across all customers)
├── incoming_call_handler/    # Inbound Twilio / WebRTC webhooks
├── outgoing_call_handler/    # Outbound dial campaigns
├── backend/                  # FastAPI control plane (Python)
├── frontend/                 # React admin UI (create & sell agents)
├── configs/examples/         # Sample deployments
└── industries/               # Per-industry notes / overrides
```

Python package folders use underscores (`incoming_call_handler`) so imports work; conceptually these are your **incoming-call-handler** and **outgoing-call-handler**.

---

## Production stack with Docker Compose

Orchestrates **Nginx** (serves React + proxies `/api` and `/voice`), **FastAPI**, and **MySQL** (persistent volume) on an internal Docker network.

### Build, start, and stop

```bash
cd voice-agent-platform
cp .env.docker.example .env.docker
# Edit MySQL passwords / ADMIN_ACCESS_TOKEN / GOOGLE_API_KEY / TWILIO_* as needed

# Build images and start everything in the background
docker compose --env-file .env.docker up -d --build

# Check status
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs -f

# Stop (containers removed; MySQL data volume kept)
docker compose --env-file .env.docker down

# Stop and delete the MySQL volume too
docker compose --env-file .env.docker down -v
```

Open **http://localhost** (or `http://localhost:$HTTP_PORT`).  
Login token: value of `ADMIN_ACCESS_TOKEN` in `.env.docker` (default `dev-admin-token`).

| Service | Container | Role |
|---------|-----------|------|
| `nginx` | `aethervoice-nginx` | Public port 80 — React static + reverse proxy |
| `backend` | `aethervoice-backend` | FastAPI on internal `8080` |
| `mysql` | `aethervoice-mysql` | MySQL 8 with volume `aethervoice-mysql-data` |

Nginx routes:

- `/` → React SPA  
- `/api/` → FastAPI  
- `/voice/` → FastAPI (Twilio / sessions)

### Call I/O in MySQL (debugging)

Docker Compose sets `STORE_BACKEND=mysql`. Every call persists:

| Table | What |
|-------|------|
| `calls` | Session metadata (direction, numbers, pipeline, status) |
| `call_turns` | Caller input + agent output text |
| `call_tool_io` | Tool arguments + results (success/failure, latency) |
| `call_events` | Handoffs, session_start/end, other structured events |

Inspect in the admin UI under **Call debug**, or:

```bash
curl -s http://localhost/api/calls
curl -s http://localhost/api/calls/<call_id>
```

JSON file store remains only as a **local-dev fallback for company/deployment config** when MySQL is not running. Call transcripts are not meant to live in JSON.

---

## Continuous deployment & API tokens

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for the full guide.

**Tokens (Twilio, Gemini, Daily, etc.):** live only in `/opt/aethervoice/voice-agent-platform/.env.docker` on the VPS. Never committed. Docker Compose injects them into the backend container.

**CD:** GitHub Actions workflow `.github/workflows/deploy-aethervoice-vps.yml` SSHs to your VPS on push to `main`, pulls code, and runs `scripts/deploy.sh`. One-time: bootstrap the VPS, create `.env.docker`, add `VPS_HOST` / `VPS_USER` / `VPS_SSH_KEY` as GitHub Actions secrets.

### Local development (without Docker)

#### 1. API tokens (later)

```bash
cp voice-agent-platform/.env.example voice-agent-platform/.env
# Fill GOOGLE_API_KEY, TWILIO_*, DAILY_API_KEY, etc.
```

#### 2. Backend

```bash
cd voice-agent-platform
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
export PYTHONPATH=$PWD
# Optional: STORE_BACKEND=mysql with local MySQL; default is JSON files
uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 --reload
```

#### 3. Frontend (local)

```bash
cd voice-agent-platform/frontend
npm install
npm run dev
```

Open http://localhost:5173 — access token default: `dev-admin-token`.

#### 4. Frontend on GitHub Pages

The admin UI can also be published at **https://subasah.github.io/AI/**.

```bash
cd voice-agent-platform/frontend
npm run build:pages
# Or: npm run deploy:pages
```

For Pages-only hosting, set Actions variable `VITE_API_BASE` to your API URL. Docker Compose does not need that — the UI and API share the same origin via Nginx.

---

## How selling a voice agent works

1. **Create a company** (the customer you sell to).
2. **Create a deployment** from an industry template (restaurant, car dealer, mortgage servicing).
3. You own/edit **agents, prompts, flows, skills**.
4. **Attach MCP** and/or **HTTP tools** pointing at *their* APIs (loyalty, DMS, LOS, POS…).
5. **Activate** → map phone numbers → inbound/outbound handlers load that deployment.
6. Tomorrow, attach another service with `POST /api/deployments/{id}/tools` or the UI — no rewrite of the swarm.

Tool execution order (seamless failover while keys are pending):

1. Local handler  
2. MCP binding (`server_id/tool_name`)  
3. Customer HTTP endpoint  
4. `mock_response` (safe dry-run)

---

## API surface (control plane)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health |
| CRUD | `/api/companies` | Customer companies |
| CRUD | `/api/deployments` | Voice agent packages |
| POST | `/api/deployments/{id}/mcp` | Attach MCP server |
| POST | `/api/deployments/{id}/tools` | Attach / replace a tool |
| POST | `/api/deployments/{id}/activate` | Go live |
| GET | `/api/templates` | Industry templates |
| POST | `/voice/incoming` | Twilio inbound |
| POST | `/voice/incoming/web` | WebRTC/session bootstrap |
| POST | `/voice/outgoing` | Place outbound call |

---

## Industry templates

| Industry | Swarm | Example tools |
|----------|-------|----------------|
| Restaurant | greeter → reservations / info | `check_availability`, `create_reservation` |
| Car dealer | greeter → sales / service | `search_inventory`, `schedule_test_drive` |
| Mortgage servicing | greeter → verification → payment / loan_info | `verify_identity`, `make_payment`, escalate |

---

## Live voice

### Default: Gemini Live Flash (speech → speech)

Caller audio goes straight into Gemini; Gemini returns audio. **No Deepgram or Cartesia.**

```bash
pip install "pipecat-ai[google,daily,silero]"
# set GOOGLE_API_KEY in .env
```

Per deployment: `voice.pipeline_mode = "gemini_live"` (default), pick `gemini_voice` / `gemini_model` in the admin UI.

### Optional: classic cascade

`voice.pipeline_mode = "classic"` → Deepgram STT → OpenAI LLM → Cartesia TTS.

```bash
pip install "pipecat-ai[daily,deepgram,cartesia,openai,silero]"
```

Until keys are set, sessions run in **mock mode** and still exercise tools/MCP config.

---

## Auth note

The React UI uses a shared access token (`ADMIN_ACCESS_TOKEN`) as a placeholder. Replace with SSO / RBAC before production.
