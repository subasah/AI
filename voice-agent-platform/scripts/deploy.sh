#!/usr/bin/env bash
# Run on the VPS after git pull. Rebuilds and restarts the stack.
# Secrets stay in .env.docker on the server — never committed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env.docker ]]; then
  echo "ERROR: $ROOT/.env.docker is missing."
  echo "Copy .env.docker.example → .env.docker and fill GOOGLE_API_KEY, TWILIO_*, DAILY_API_KEY, etc."
  exit 1
fi

echo "==> Pulling images / building services"
docker compose --env-file .env.docker pull || true
docker compose --env-file .env.docker up -d --build --remove-orphans

echo "==> Pruning dangling images"
docker image prune -f >/dev/null || true

echo "==> Health check"
sleep 3
curl -fsS "http://127.0.0.1:${HTTP_PORT:-80}/api/health" || {
  echo "Health check failed — showing backend logs:"
  docker compose --env-file .env.docker logs --tail=80 backend
  exit 1
}

echo "==> Deploy complete"
docker compose --env-file .env.docker ps
