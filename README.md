# Golf Data Lab (GolfDataApp)

A local-first application for capturing, analyzing, and coaching golf performance using data from Uneekor launch monitors.

## Overview

1. **Capture**: Scrape shot data and images from Uneekor's API via a local Streamlit dashboard.
2. **Automation**: Browser-based scraper with Playwright for hands-free data import and historical backfill.
3. **Storage**: Local SQLite database with optional sync to Supabase (PostgreSQL).
4. **Analysis**: Interactive dashboard with club comparisons, trends, and shot dispersion.
5. **AI Coach**: Conversational coaching with local ML models or Gemini.
6. **Workflow**: Tag shots, split sessions, and label session context inside the Database Manager.

## Quick Start

### 1. Local Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

*Full details in [SETUP_GUIDE.md](SETUP_GUIDE.md).*

### 2. Automated Data Import

Set up hands-free data import with browser automation:

```bash
# Install Playwright browser
playwright install chromium

# First-time login (saves cookies)
python automation_runner.py login

# Discover and import new sessions
python automation_runner.py discover --headless

# Historical backfill
python automation_runner.py backfill --start 2025-01-01
```

*Full details in [AUTOMATION_GUIDE.md](AUTOMATION_GUIDE.md).*

### 3. AI Coach

Chat with the AI Coach for personalized insights:

```bash
streamlit run app.py
# Navigate to AI Coach page
```

### 4. Optional: Supabase Cloud Sync

Sync your local data to Supabase for backup and multi-device access:

```bash
python scripts/migrate_to_supabase.py
```

*Full details in [SETUP_GUIDE.md](SETUP_GUIDE.md).*

## Documentation

- [SETUP_GUIDE.md](SETUP_GUIDE.md): Full setup walkthrough (local environment, Supabase, MCP).
- [AUTOMATION_GUIDE.md](AUTOMATION_GUIDE.md): Playwright scraper setup and usage.
- [mcp/README.md](mcp/README.md): Supabase MCP connector for AI clients.

## Tests

Run the unit tests:

```bash
python -m unittest discover -s tests
```

## Data Source Selection

By default the app reads from local SQLite and falls back to Supabase if the local DB is missing.
To prefer cloud reads (useful when SQLite is empty), set:

```bash
USE_SUPABASE_READS=1
```

The active source appears in the Streamlit sidebar as **Data Source**.

## Tagging & Session Context

Use **Database Manager -> Tags & Session Split** to:
- Tag warmup/practice/round shots per session.
- Split mixed sessions into clean sub-sessions.
- Label sessions with a `session_type` for filtering.

## License

Personal Use.
