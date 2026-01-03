#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SUPABASE_DB_URI:-}" ]]; then
  echo "SUPABASE_DB_URI is not set. Add it to your environment or .env file."
  exit 1
fi

exec npx -y @modelcontextprotocol/server-postgres "$SUPABASE_DB_URI"
