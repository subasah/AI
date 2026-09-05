#!/usr/bin/env bash
# One-time VPS bootstrap for AetherVoice (Debian/Ubuntu).
# Usage (as root or sudo):
#   curl -fsSL ... | bash   OR   bash scripts/bootstrap-vps.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/aethervoice}"
REPO_URL="${REPO_URL:-https://github.com/subasah/AI.git}"
BRANCH="${BRANCH:-main}"

export DEBIAN_FRONTEND=noninteractive

echo "==> Installing Docker"
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ca-certificates curl git
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable --now docker
fi

echo "==> Cloning / updating repo into ${APP_DIR}"
mkdir -p "$(dirname "$APP_DIR")"
if [[ -d "${APP_DIR}/.git" ]]; then
  git -C "$APP_DIR" fetch origin
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
else
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

PLATFORM="${APP_DIR}/voice-agent-platform"
cd "$PLATFORM"

if [[ ! -f .env.docker ]]; then
  cp .env.docker.example .env.docker
  chmod 600 .env.docker
  echo ""
  echo "Created ${PLATFORM}/.env.docker — EDIT THIS FILE before first deploy:"
  echo "  GOOGLE_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER,"
  echo "  DAILY_API_KEY, PUBLIC_BASE_URL, ADMIN_ACCESS_TOKEN, MySQL passwords"
  echo ""
fi

chmod +x scripts/deploy.sh scripts/bootstrap-vps.sh 2>/dev/null || true
echo "==> Bootstrap done. Next:"
echo "  1) nano ${PLATFORM}/.env.docker"
echo "  2) ${PLATFORM}/scripts/deploy.sh"
echo "  3) Add GitHub Actions secrets for CD (see docs/DEPLOYMENT.md)"
