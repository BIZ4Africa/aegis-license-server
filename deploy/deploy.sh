#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/deploy/docker-compose.prod.yml"
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE="${ROOT_DIR}/.env.example"
KEY_ID_DEFAULT="aegis-2026-01"

log() { printf '\n[%s] %s\n' "$(date +'%H:%M:%S')" "$*"; }
fail() { printf '\n[ERROR] %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
AEGIS easy deployment helper

Usage:
  deploy/deploy.sh [--key-id <id>] [--skip-keygen] [--no-build]

Options:
  --key-id <id>   Key ID for signing keys (default: ${KEY_ID_DEFAULT})
  --skip-keygen   Do not generate keys automatically when missing
  --no-build      Skip docker image rebuild
  -h, --help      Show this help
EOF
}

KEY_ID="${KEY_ID_DEFAULT}"
SKIP_KEYGEN=false
NO_BUILD=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --key-id)
      KEY_ID="${2:-}"
      [[ -n "$KEY_ID" ]] || fail "--key-id requires a value"
      shift 2
      ;;
    --skip-keygen)
      SKIP_KEYGEN=true
      shift
      ;;
    --no-build)
      NO_BUILD=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

command -v docker >/dev/null 2>&1 || fail "docker is required"
docker compose version >/dev/null 2>&1 || fail "docker compose plugin is required"

if [[ ! -f "$ENV_FILE" ]]; then
  [[ -f "$ENV_EXAMPLE" ]] || fail "Missing ${ENV_EXAMPLE}"
  log "No .env found. Creating one from .env.example"
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  log "Please review ${ENV_FILE} and replace CHANGE_ME values before production usage"
fi

KEY_DIR="${ROOT_DIR}/keys"
PRIVATE_KEY="${KEY_DIR}/${KEY_ID}.private.pem"
PUBLIC_KEY="${KEY_DIR}/${KEY_ID}.public.pem"

if [[ ! -f "$PRIVATE_KEY" || ! -f "$PUBLIC_KEY" ]]; then
  if [[ "$SKIP_KEYGEN" == "true" ]]; then
    fail "Missing signing keys in ${KEY_DIR} and --skip-keygen was set"
  fi
  log "Generating Ed25519 keypair (key-id=${KEY_ID})"
  mkdir -p "$KEY_DIR"
  python3 "$ROOT_DIR/scripts/generate_keys.py" --key-id "$KEY_ID"
fi

if [[ "$NO_BUILD" == "true" ]]; then
  log "Starting services without rebuilding image"
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
else
  log "Building image and starting services"
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
fi

log "Deployment status"
docker compose -f "$COMPOSE_FILE" ps

log "Health check (API)"
if curl -fsS "http://localhost:${API_PORT:-8000}/health" >/dev/null; then
  log "API is healthy"
else
  fail "API health check failed. Check logs with: docker compose -f deploy/docker-compose.prod.yml logs api"
fi

log "Done. API docs: http://localhost:${API_PORT:-8000}/docs"
