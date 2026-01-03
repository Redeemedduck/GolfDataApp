# MCP Supabase Connector

This folder provides a ready-to-use MCP connector configuration for accessing Supabase Postgres directly from MCP-enabled clients (Claude Desktop, Cursor, etc.).

## Requirements
- `node` + `npx`
- Supabase Postgres connection string (transaction pooler recommended)

## Quick Setup
1. Set `SUPABASE_DB_URI` in your environment or `.env`:
   ```env
   SUPABASE_DB_URI="postgresql://postgres.[ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
   ```
2. Generate the connector config:
   ```bash
   python scripts/mcp_supabase_config.py
   ```
3. Copy the generated file into your MCP client config:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\\Claude\\claude_desktop_config.json`

## Codex CLI Notes
- Codex stores MCP config at `~/.codex/config.toml` (per Codex MCP docs).
- Use the generated snippet from `scripts/mcp_supabase_config.py`:
  - `mcp/codex_config.supabase.generated.toml`
- Ensure `SUPABASE_DB_URI` is in your environment, then start the server:
  ```bash
  scripts/start_mcp_supabase.sh
  ```
- The script will also load `.env` from the repo root if present.
- You can also add the server via CLI:
  ```bash
  codex mcp add supabase-golf-data -- bash scripts/start_mcp_supabase.sh
  ```

## What This Provides
- MCP server config using `@modelcontextprotocol/server-postgres`
- Direct SQL access to Supabase tables for AI agents
