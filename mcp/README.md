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
- Use the generated JSON from `scripts/mcp_supabase_config.py` and merge it into your Codex MCP config.
- Start the MCP server with:
  ```bash
  scripts/start_mcp_supabase.sh
  ```
  Keep it running while Codex connects and issues SQL queries.

## What This Provides
- MCP server config using `@modelcontextprotocol/server-postgres`
- Direct SQL access to Supabase tables for AI agents
