# Local setup guide (macOS)

Run AetherVoice on your Mac **before** deploying to a VPS.  
Two paths: **Docker (recommended)** or **native Python + Node**.

---

## What you get locally

| Piece | URL |
|-------|-----|
| Admin UI | http://localhost (Docker) or http://localhost:5173 (native) |
| API health | http://localhost/api/health or http://localhost:8080/api/health |
| API docs | http://localhost/docs or http://localhost:8080/docs |
| Login token | `ADMIN_ACCESS_TOKEN` (default `dev-admin-token`) |

API keys (Gemini, Twilio, Daily) are **optional** for UI/config demos.  
Without them you can still create companies/agents and exercise mock tools.  
Add keys when you want live voice or phone calls.

---

## Option A — Docker Compose (recommended on Mac)

Easiest: Nginx + React + FastAPI + MySQL in one command.

### 1. Prerequisites

1. Install **[Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)**
2. Open Docker Desktop and wait until it says **Engine running**
3. Confirm in Terminal:

```bash
docker --version
docker compose version
```

### 2. Clone and enter the project

```bash
git clone https://github.com/subasah/AI.git
cd AI/voice-agent-platform
```

(If you already have the repo, just `cd` into `voice-agent-platform`.)

### 3. Create your local env file

```bash
cp .env.docker.example .env.docker
```

Edit `.env.docker` (TextEdit, VS Code, or `nano`):

```bash
nano .env.docker
```

**Minimum for local UI demos** (no paid keys yet):

```env
HTTP_PORT=80
PUBLIC_BASE_URL=http://localhost
CORS_ORIGINS=http://localhost,http://127.0.0.1
ADMIN_ACCESS_TOKEN=dev-admin-token

MYSQL_ROOT_PASSWORD=local_root_pass
MYSQL_DATABASE=aethervoice
MYSQL_USER=aethervoice
MYSQL_PASSWORD=local_db_pass
```

**When you have keys**, add them to the same file:

```env
GOOGLE_API_KEY=your_gemini_key
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
DAILY_API_KEY=...
```

> Never commit `.env.docker`. It is gitignored.

### 4. Start everything

```bash
docker compose --env-file .env.docker up -d --build
```

First build can take several minutes (Node + Python images).

### 5. Verify

```bash
docker compose --env-file .env.docker ps
curl -s http://localhost/api/health
```

Expected: `{"status":"ok","service":"voice-agent-platform"}`

### 6. Open the app

1. Browser → **http://localhost**
2. Access token → `dev-admin-token` (or whatever you set in `.env.docker`)
3. Try **Companies** → **Create & Sell** → **Call debug**

### 7. Useful commands

```bash
# Logs (follow)
docker compose --env-file .env.docker logs -f

# Backend logs only
docker compose --env-file .env.docker logs -f backend

# Restart after editing .env.docker
docker compose --env-file .env.docker up -d

# Stop (keeps MySQL data)
docker compose --env-file .env.docker down

# Stop and wipe MySQL volume
docker compose --env-file .env.docker down -v
```

### Mac tips / common issues

| Issue | Fix |
|-------|-----|
| Port 80 in use | Set `HTTP_PORT=8088` in `.env.docker`, then open http://localhost:8088 |
| `docker` not found | Start Docker Desktop; reopen Terminal |
| Build fails / disk full | Docker Desktop → Settings → Resources; free disk space |
| Apple Silicon | Docker Desktop handles `linux/arm64`; no extra flags needed |
| Permission on scripts | `chmod +x scripts/*.sh` |

---

## Option B — Native Mac (no Docker for the app)

Use this if you want hot-reload while coding. MySQL is still recommended via Docker for call logs; without MySQL, config uses a local JSON fallback and call I/O won’t persist to DB.

### 1. Prerequisites

```bash
# Homebrew: https://brew.sh
brew install python@3.12 node git

python3 --version   # 3.12+
node --version      # 20+ or 22+
npm --version
```

Optional MySQL for real call debugging:

```bash
brew install mysql
brew services start mysql
# create DB/user, or run only the mysql service from docker compose
```

Or run **only MySQL** with Docker while developing the app natively:

```bash
cd voice-agent-platform
cp .env.docker.example .env.docker
docker compose --env-file .env.docker up -d mysql
```

### 2. Backend

```bash
cd voice-agent-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env
# Edit .env — at least ADMIN_ACCESS_TOKEN; add GOOGLE_API_KEY later
```

If using Docker MySQL from above:

```bash
# add to .env
STORE_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=aethervoice
MYSQL_USER=aethervoice
MYSQL_PASSWORD=aethervoice_pass_change_me   # match .env.docker
CALL_LOG_MYSQL=true
```

Start API:

```bash
export PYTHONPATH=$PWD
uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 --reload
```

Health: http://localhost:8080/api/health

### 3. Frontend (second Terminal)

```bash
cd voice-agent-platform/frontend
npm install
npm run dev
```

Open **http://localhost:5173**  
Login: `dev-admin-token` (or `VITE_ADMIN_TOKEN` / `ADMIN_ACCESS_TOKEN`)

Vite proxies `/api` and `/voice` to `http://localhost:8080` automatically.

### 4. Stop native

- Ctrl+C in both Terminals  
- If MySQL via Docker: `docker compose --env-file .env.docker stop mysql`

---

## Quick smoke test (either option)

1. Log into the admin UI  
2. **Companies** → add a test company (e.g. restaurant)  
3. **Create & Sell** → create a deployment from a template  
4. Open the agent → confirm pipeline is **Gemini Live**  
5. (Optional) `curl` a web session:

```bash
# Docker (port 80) or native API (port 8080)
curl -s -X POST http://localhost:8080/voice/incoming/web \
  -H 'Content-Type: application/json' \
  -d '{"deployment_id":"YOUR_DEPLOYMENT_ID"}' | python3 -m json.tool
```

6. Check **Call debug** (needs MySQL) for the new `call_id`

---

## Optional: live Gemini / Twilio on localhost

| Goal | What to do |
|------|------------|
| Gemini Live voice | Set `GOOGLE_API_KEY` in `.env.docker` or `.env` |
| Twilio phone webhooks to your laptop | Use [ngrok](https://ngrok.com/): `ngrok http 80` (or 8080), set `PUBLIC_BASE_URL` to the ngrok HTTPS URL, point Twilio Voice webhook to `https://xxxx.ngrok.io/voice/incoming` |

You do **not** need Twilio/Gemini to explore the control plane UI.

---

## Project layout (where to look)

```text
voice-agent-platform/
├── docker-compose.yml      # Full local/prod stack
├── .env.docker.example     # Copy → .env.docker (Docker)
├── .env.example            # Copy → .env (native backend)
├── backend/                # FastAPI
├── frontend/               # React (Vite)
├── library/                # Agents, tools, Gemini/classic pipelines
├── docs/DEPLOYMENT.md      # VPS + CD + secrets
└── docs/LOCAL_SETUP.md     # This file
```

---

## Next steps after local works

1. Keep developing on Mac  
2. When ready for the demo VPS, follow [DEPLOYMENT.md](./DEPLOYMENT.md)  
3. Same `.env.docker` pattern on the server — just use real keys + public HTTPS URL  

---

## Help

- Compose issues → [DOCKER.md](../DOCKER.md)  
- Server / CD / where tokens live → [DEPLOYMENT.md](./DEPLOYMENT.md)  
- Product overview → [README.md](../README.md)
