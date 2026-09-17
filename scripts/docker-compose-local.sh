#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

set -a
source .env.example
if [ -f .env.local ]; then
  source .env.local
fi
set +a

export YASI_DOCKER_API_BASE_URL="${YASI_DOCKER_API_BASE_URL:-http://127.0.0.1:${YASI_DOCKER_BACKEND_PORT:-19080}}"

compose_env_files=(--env-file .env.example)
if [ -f .env.local ]; then
  compose_env_files+=(--env-file .env.local)
fi

exec docker compose "${compose_env_files[@]}" "$@"
