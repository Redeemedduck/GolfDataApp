# Claude Desktop Setup Guide

To connect **Claude Desktop** to your Supabase Postgres database, you need to configure the [Postgres MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres).

## Prerequisite
You need your **Supabase Connection String**.
1. Go to Supabase Dashboard -> **Connect** button (top right).
2. Select **Transaction Pooler** (port 6543) for best compatibility.
3. Copy the URI. It looks like: `postgresql://postgres.[ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres`

## Configuration File
Can be found at:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### `claude_desktop_config.json`
Create or edit this file to include the following:

```json
{
  "mcpServers": {
    "supabase-golf-data": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://postgres.[YOUR_REF]:[YOUR_PASSWORD]@[HOST]:6543/postgres"
      ]
    }
  }
}
```

> [!IMPORTANT]
> Replace the connection string above with your actual Supabase connection string.
> Ensure you have `node` and `npx` installed on your machine.

## Usage
1. Restart Claude Desktop.
2. Look for the 🔌 icon. You should see "supabase-golf-data".
3. Ask Claude: *"Show me the tables in my golf database"* or *"Calculated the average carry distance from the shots table"*.

## Optional: Auto-generate Config
If you store your Supabase connection string in `SUPABASE_DB_URI`, you can generate
a ready-to-copy config file:

```bash
python scripts/mcp_supabase_config.py
```

It writes: `mcp/claude_desktop_config.supabase.generated.json`
