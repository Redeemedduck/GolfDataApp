#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT_DIR}/.env"
  set +a
fi

if [[ -z "${SUPABASE_DB_URI:-}" ]]; then
  echo "SUPABASE_DB_URI is not set. Add it to your environment or .env file."
  exit 1
fi

exec npx -y @modelcontextprotocol/server-postgres "$SUPABASE_DB_URI"
