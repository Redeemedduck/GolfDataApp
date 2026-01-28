# Golf Data App Setup Guide
## Local-First with Optional Supabase Cloud Sync

This guide walks you through setting up the Golf Data App for local development, optional cloud sync with Supabase, and advanced AI integration via MCP.

---

## Architecture

```
┌─────────────────┐
│  Uneekor Portal │
│  (Shot Data)    │
└────────┬────────┘
         │
         v
┌─────────────────┐      ┌──────────────────┐
│  automation/    │─────>│  SQLite (local)  │
│  (Playwright)   │      │  golf_stats.db   │
└─────────────────┘      └────────┬─────────┘
                                  │  (optional sync)
                                  │  scripts/migrate_to_supabase.py
                                  v
                         ┌─────────────────┐
                         │    Supabase     │
                         │  (PostgreSQL)   │
                         └────────┬────────┘
                                  │
                         ┌────────┴────────┐
                         v                 v
                   Streamlit App     MCP Connectors
                   (Dashboard)       (Claude Desktop)
```

---

## Prerequisites

- Python 3.10+
- Node.js and `npx` (for MCP server, optional)
- Supabase account (optional, for cloud sync)

---

## Step 1: Local Environment Setup

### 1.1 Clone the Repository

```bash
git clone <repository-url>
cd GolfDataApp
```

### 1.2 Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 1.3 Install Dependencies

```bash
pip install -r requirements.txt
```

### 1.4 Configure Environment Variables

Create a `.env` file in the project root (use `.env.example` as a template):

```env
# Required for Gemini AI Coach
GEMINI_API_KEY="your-gemini-api-key"

# Optional: Supabase cloud sync
SUPABASE_URL="https://xxxxx.supabase.co"
SUPABASE_KEY="your-anon-key-here"

# Optional: Force Supabase reads (useful when SQLite is empty)
# USE_SUPABASE_READS="1"

# Optional: Structured logging
# GOLFDATA_LOGGING="1"

# Optional: Slack alerts for automation
# SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

The app works fully offline with just SQLite. Supabase variables are only needed for cloud sync.

---

## Step 2: Run the Streamlit App

```bash
streamlit run app.py
```

The sidebar shows the current **Data Source** (SQLite or Supabase). By default the app reads from local SQLite and falls back to Supabase if the local DB is missing.

### Import Uneekor Data

1. Launch the **Uneekor View** software and locate your report.
2. Get the **Shareable URL** for the report.
3. In the Streamlit app, go to the **Data Import** page, paste the URL, and click **Run Import**.
4. The scraper will fetch JSON data from the Uneekor API, convert metrics to Imperial units, and save to `golf_stats.db`.

### Automated Import (Playwright)

For hands-free import with browser automation:

```bash
playwright install chromium              # First-time only
python automation_runner.py login        # Interactive login, saves cookies
python automation_runner.py discover --headless
python automation_runner.py backfill --start 2025-01-01
```

See [AUTOMATION_GUIDE.md](AUTOMATION_GUIDE.md) for full details.

---

## Step 3: Supabase Setup (Optional)

Supabase provides cloud sync so your data is accessible from any device and backed up to PostgreSQL.

### 3.1 Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click "New Project"
3. Choose organization and fill in project details:
   - Name: `golf-data` (or your preference)
   - Database Password: (strong password)
   - Region: Choose closest to you
4. Wait for project creation (~2 minutes)

### 3.2 Get Supabase Credentials

1. In your project dashboard, go to **Settings** -> **API**
2. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: Long string starting with `eyJ...`

### 3.3 Create the Database Schema

1. In the Supabase dashboard, click **SQL Editor**
2. Copy the entire contents of `supabase_schema.sql`
3. Paste into SQL Editor and click **Run**
4. Verify tables were created: **Database** -> **Tables**
   - `shots` -- 30+ fields including `session_date`, `session_type`, `shot_tag`, optix metrics
   - `tag_catalog` -- shared tags across sessions
   - `shots_archive` -- soft-deleted shots for recovery
   - `change_log` -- audit trail for data modifications
   - `sessions_discovered`, `automation_runs`, `backfill_runs` -- automation state
   - `session_summary` view -- aggregated stats by session + club

### 3.4 Set Environment Variables

Add to your `.env` file:

```env
SUPABASE_URL="https://xxxxx.supabase.co"
SUPABASE_KEY="your-anon-key-here"
```

For shell-wide access, also add to `~/.bashrc` or `~/.zshrc`:

```bash
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_KEY="your-anon-key-here"
```

---

## Step 4: SQLite to Supabase Migration

If you already have shot data in your local `golf_stats.db`, migrate it to Supabase:

### 4.1 Run the Migration Script

```bash
python scripts/migrate_to_supabase.py
```

This will:
- Connect to your local `golf_stats.db`
- Upload all shots to Supabase in batches
- Verify the migration was successful

### 4.2 Verify Migration

```bash
python scripts/migrate_to_supabase.py verify
```

Or check in the Supabase dashboard: **Database** -> **Table Editor** -> **shots**

---

## Step 5: Claude Desktop MCP Setup (Optional)

Connect your Supabase database to Claude Desktop for conversational data analysis using the [Postgres MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres).

### 5.1 Get Your Connection String

1. Go to Supabase Dashboard -> **Connect** button (top right)
2. Select **Transaction Pooler** (port 6543) for best compatibility
3. Copy the URI. It looks like: `postgresql://postgres.[ref]:[password]@aws-0-us-west-1.pooler.supabase.com:6543/postgres`

### 5.2 Configure Claude Desktop

Edit the Claude Desktop config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the MCP server entry:

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

> **Note:** Replace the connection string with your actual Supabase connection string. You must have `node` and `npx` installed.

### 5.3 Auto-generate Config

If you store your Supabase connection string in `SUPABASE_DB_URI`, you can generate the config automatically:

```bash
python scripts/mcp_supabase_config.py
```

This writes: `mcp/claude_desktop_config.supabase.generated.json`

### 5.4 Usage

1. Restart Claude Desktop
2. Look for the MCP connection icon. You should see "supabase-golf-data"
3. Ask Claude: *"Show me the tables in my golf database"* or *"What is my average carry distance by club?"*

---

## Step 6: MCP Supabase Direct Connector

For direct MCP access to your Supabase Postgres from other clients (Codex, Claude Code, etc.):

1. Set `SUPABASE_DB_URI` in your environment (transaction pooler recommended)
2. Generate configs:
   ```bash
   python scripts/mcp_supabase_config.py
   ```
3. Copy `mcp/claude_desktop_config.supabase.generated.json` into your MCP client config
4. Start the MCP server for Codex or other clients:
   ```bash
   scripts/start_mcp_supabase.sh
   ```
5. For Codex, merge `mcp/codex_config.supabase.generated.toml` into `~/.codex/config.toml`. The launcher will read `SUPABASE_DB_URI` from your environment or `.env`.

### Features

- **Conversational Analytics**: Chat with your golf data directly without SQL
- **Autonomous Discovery**: AI agents can independently explore schemas using `list-tables` and `get-table-schema`
- **Multi-client Support**: Works with Claude Desktop, Codex, and any MCP-compatible client

---

## Schema Maintenance

The architecture is designed to be **self-healing**:

- **SQLite**: The `golf_db.py` module automatically adds missing columns to your local database on startup via `init_db()`
- **Supabase**: If you add new metrics, update `supabase_schema.sql` (the canonical schema reference). For existing deployments, see the migration section at the bottom of that file.

---

## Troubleshooting

### Supabase Connection Issues

- Verify URL and key are correct in `.env`
- Check if your IP is allowed in the Supabase dashboard
- Ensure RLS policies allow your key to access data
- Test connection: check the Streamlit sidebar for "Data Source: Supabase"

### MCP Server Issues

- Ensure Node.js and `npx` are installed: `node --version`
- Verify the connection string uses the Transaction Pooler (port 6543)
- Restart Claude Desktop after editing the config file
- Check logs: `~/Library/Logs/Claude/` (macOS)

### Migration Issues

- Ensure `golf_stats.db` exists and has data before running migration
- If migration fails partway, re-run -- it uses upserts and is safe to retry
- Check Supabase dashboard Table Editor to verify row counts match

---

## Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Postgres MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres)
- [Playwright Documentation](https://playwright.dev/python/)
