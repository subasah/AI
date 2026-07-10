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
├── library/                  # Shared brain (reusable across all customers)
│   ├── agents/               # BaseAgent + config-driven agents
│   ├── tools/                # ToolDispatcher (handler → MCP → HTTP → mock)
│   ├── skills/               # Skill configs
│   ├── flows/                # FSM runtime
│   ├── mcp/                  # MCP client manager (plug new services easily)
│   ├── prompts/              # Voice-first prompt helpers
│   ├── swarm/                # Handoff orchestrator
│   ├── observability/        # call_id structured logging
│   ├── industries/           # Restaurant / dealer / mortgage templates
│   └── bot_core.py           # Session + optional Pipecat assembly
├── incoming_call_handler/    # Inbound Twilio / WebRTC webhooks
├── outgoing_call_handler/    # Outbound dial campaigns
├── backend/                  # FastAPI control plane (Python)
├── frontend/                 # React admin UI (create & sell agents)
├── configs/examples/         # Sample deployments
└── industries/               # Per-industry notes / overrides
```

Python package folders use underscores (`incoming_call_handler`) so imports work; conceptually these are your **incoming-call-handler** and **outgoing-call-handler**.

---

## Quick start

### 1. API tokens (later)

```bash
cp voice-agent-platform/.env.example voice-agent-platform/.env
# Fill OPENAI_API_KEY, DEEPGRAM_API_KEY, CARTESIA_API_KEY, TWILIO_*, DAILY_API_KEY, etc.
```

### 2. Backend

```bash
cd voice-agent-platform
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
export PYTHONPATH=$PWD
uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 3. Frontend

```bash
cd voice-agent-platform/frontend
npm install
npm run dev
```

Open http://localhost:5173 — access token default: `dev-admin-token` (see `ADMIN_ACCESS_TOKEN`).

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

## Live voice (optional)

When keys are ready, install:

```bash
pip install "pipecat-ai[daily,deepgram,cartesia,openai,silero]" twilio mcp
```

`VoiceBotSession.build_pipecat_pipeline()` assembles STT → LLM → TTS. Until then, sessions run in **mock mode** and still exercise tools/MCP config.

---

## Auth note

The React UI uses a shared access token (`ADMIN_ACCESS_TOKEN`) as a placeholder. Replace with SSO / RBAC before production.
