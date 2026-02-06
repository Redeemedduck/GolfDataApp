# Golf Data Lab (GolfDataApp)

A local-first application for capturing, analyzing, and coaching golf performance using data from Uneekor launch monitors.

## Overview

1. **Practice Journal**: Rolling 4-week view with session cards, Big 3 Impact Laws summary, and calendar strip.
2. **Dashboard**: 5-tab analytics — Overview, Big 3 Deep Dive (D-plane scatter, tendencies), Shots, Compare, Export.
3. **Club Profiles**: Per-club deep dives with hero stats, distance trends, and Big 3 tendencies.
4. **AI Coach**: Conversational coaching with local ML models or Gemini.
5. **Automation**: Browser-based scraper with Playwright for hands-free data import and historical backfill.
6. **Storage**: Local SQLite database with optional sync to Supabase (PostgreSQL).

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

# Extract session dates from listing page
python automation_runner.py reclassify-dates --from-listing

# Sync to Supabase cloud
python automation_runner.py sync-database
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

Use **Settings -> Tags** to:
- Tag warmup/practice/round shots per session.
- Split mixed sessions into clean sub-sessions.
- Label sessions with a `session_type` for filtering.

## License

Personal Use.
