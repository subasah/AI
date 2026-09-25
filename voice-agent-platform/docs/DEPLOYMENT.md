# Secrets & continuous deployment

## How API tokens are stored

**Never commit tokens to git.** They are not in the repo.

| Secret | Where it lives | How the app reads it |
|--------|----------------|----------------------|
| `GOOGLE_API_KEY` | VPS file `voice-agent-platform/.env.docker` | Backend env → Gemini Live |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_PHONE_NUMBER` | same `.env.docker` | Outbound/inbound telephony |
| `DAILY_API_KEY` | same `.env.docker` | Optional WebRTC rooms |
| `ADMIN_ACCESS_TOKEN` | same `.env.docker` | Admin UI login |
| MySQL passwords | same `.env.docker` | Compose → MySQL + backend |
| `OPENAI_*` / `DEEPGRAM_*` / `CARTESIA_*` | same (only if classic pipeline) | Classic STT/TTS mode |

Flow:

```text
You paste keys once into /opt/aethervoice/voice-agent-platform/.env.docker on the VPS
        ↓
docker compose --env-file .env.docker up
        ↓
backend container receives them as environment variables
        ↓
VoiceBotSession / Twilio client / Gemini Live read os.getenv(...)
```

`.env.docker` is gitignored. GitHub Actions **does not** push your Twilio/Gemini keys; CD only SSHs in and rebuilds. Keys stay on the server.

Optional later upgrades (not required for demo):

- Docker secrets / a vault (Doppler, Infisical, AWS SSM)
- Separate `.env` per environment (staging vs prod)

---

## Continuous deployment (code here → VPS)

### One-time on the VPS

```bash
# SSH in as root (or sudo user)
export REPO_URL=https://github.com/subasah/AI.git
export BRANCH=main
# After merging the PR, BRANCH=main; until then use the feature branch name
bash -c "$(curl -fsSL https://raw.githubusercontent.com/subasah/AI/main/voice-agent-platform/scripts/bootstrap-vps.sh)" \
  || git clone https://github.com/subasah/AI.git /opt/aethervoice

cd /opt/aethervoice/voice-agent-platform
# If bootstrap created .env.docker from example:
nano .env.docker   # fill real keys + PUBLIC_BASE_URL=https://YOUR_IP_OR_DOMAIN
./scripts/deploy.sh
```

Create an SSH deploy key (ed25519) on your laptop, put the **public** key in VPS `~/.ssh/authorized_keys`, keep the **private** key for GitHub.

### One-time in GitHub → Settings → Secrets and variables → Actions

| Secret | Example |
|--------|---------|
| `VPS_HOST` | `203.0.113.10` (your VPS IP or hostname) |
| `VPS_USER` | `root` or `debian` |
| `VPS_SSH_KEY` | full private key PEM (`-----BEGIN OPENSSH PRIVATE KEY-----` …) |
| `VPS_PORT` | `22` (optional) |
| `VPS_APP_DIR` | `/opt/aethervoice` (optional) |
| `VPS_BRANCH` | `main` (optional) |

Do **not** put `GOOGLE_API_KEY` / Twilio / Daily into GitHub Secrets for this setup — they stay in server `.env.docker`.

### Ongoing

1. Merge / push to `main` (paths under `voice-agent-platform/`)
2. Workflow **Deploy AetherVoice to VPS** SSHs in → `git reset --hard` → `./scripts/deploy.sh`
3. Or run it manually: Actions → **Deploy AetherVoice to VPS** → Run workflow

### Manual deploy (no Actions)

```bash
ssh user@YOUR_VPS
cd /opt/aethervoice && git pull
cd voice-agent-platform && ./scripts/deploy.sh
```

---

## Security checklist for demos

- [ ] `.env.docker` mode `600` (`chmod 600 .env.docker`)
- [ ] Change `ADMIN_ACCESS_TOKEN` and MySQL passwords from defaults
- [ ] Firewall: allow `22`, `80`, `443` only
- [ ] Put HTTPS in front (Caddy / Cloudflare) and set `PUBLIC_BASE_URL` to `https://...`
- [ ] Twilio webhook = `https://YOUR_DOMAIN/voice/incoming`
