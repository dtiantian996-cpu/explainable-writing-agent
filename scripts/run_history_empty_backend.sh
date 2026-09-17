#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT_DIR/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env.local"
  set +a
elif [[ -f "$ROOT_DIR/.env.example" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env.example"
  set +a
fi

DB_NAME="${YASI_HISTORY_EMPTY_DATABASE:-yasi_history_empty}"
BACKEND_PORT="${YASI_HISTORY_EMPTY_BACKEND_PORT:-8101}"
MYSQL_PORT="${MYSQL_PORT:-19306}"
MYSQL_USER="${MYSQL_USER:-yasi}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-yasi}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-root}"

"$ROOT_DIR/scripts/docker-compose-local.sh" up -d mysql >/dev/null

docker exec yasi-mysql sh -lc "mysql -uroot -p\"$MYSQL_ROOT_PASSWORD\" -e \"DROP DATABASE IF EXISTS \\\`$DB_NAME\\\`; CREATE DATABASE \\\`$DB_NAME\\\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; GRANT ALL PRIVILEGES ON \\\`$DB_NAME\\\`.* TO '$MYSQL_USER'@'%'; FLUSH PRIVILEGES;\""

export DATABASE_URL="mysql+asyncmy://$MYSQL_USER:$MYSQL_PASSWORD@127.0.0.1:${MYSQL_PORT}/${DB_NAME}"
export YASI_USE_MOCK_AI="${YASI_USE_MOCK_AI:-true}"
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-replace-me}"

cd "$ROOT_DIR/backend"
./.venv/bin/python -m alembic -c alembic.ini upgrade head >/dev/null

exec ./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT"
