# ⛳ Golf Data Lab (GolfDataApp)

A powerful data pipeline for capturing, syncing, and analyzing golf shot data from Uneekor launch monitors.

## 🚀 Overview

This application automates the flow of golf performance data:
1.  **Capture**: Scrape report data and images from Uneekor's API via a local Streamlit dashboard.
2.  **Automation**: Browser-based scraper with Playwright for hands-free data import and historical backfill.
3.  **Storage**: Save data to a local SQLite database for offline access and sync to **Supabase** (PostgreSQL + Cloud Storage).
4.  **Pipeline**: Automate data export from Supabase to **Google BigQuery** for long-term warehousing.
5.  **Analysis**: Use **Vertex AI (Gemini)** to generate deep insights and performance recommendations.
6.  **AI Coach**: Conversational coaching with Gemini 3.0 function calling.
7.  **Workflow Cleanup**: Tag shots, split sessions, and label session context (practice vs round) inside the Database Manager.

## 🛠️ Quick Start

### 1. Local Setup & Data Capture
To get the Streamlit server running and start importing your Uneekor data:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
*Full details in [SETUP_GUIDE.md](SETUP_GUIDE.md).*

### 1b. Docker (OrbStack)
Run the container from this repo:
```bash
docker compose up -d --build
```
Then open `http://localhost:8501`.

### 2. Cloud Data Sync
Once you have data in Supabase, sync it to your personal data warehouse:
```bash
python scripts/supabase_to_bigquery.py incremental
```
*Full details in [QUICKSTART.md](QUICKSTART.md).*

### 3. AI Performance Insights
Get AI-powered analysis of your swing metrics:
```bash
python scripts/vertex_ai_analysis.py analyze "7 Iron"
```

### 4. Automated Data Import (NEW)
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

### 5. AI Coach
Chat with the AI Coach for personalized insights:
```bash
streamlit run app.py
# Navigate to AI Coach page
```

### 6. Conversational Data Analysis
Connect your databases to an AI agent via MCP for natural language queries:
```bash
# Start the MCP Control Plane
toolbox --tools-file ~/.mcp/database-toolbox/tools.yaml --stdio
```

## 📂 Documentation

- [QUICKSTART.md](QUICKSTART.md): Streamlined guide for Supabase, BigQuery, and Vertex AI.
- [SETUP_GUIDE.md](SETUP_GUIDE.md): Deep dive into every step of the pipeline.
- [AUTOMATION_GUIDE.md](AUTOMATION_GUIDE.md): Instructions for setting up automated syncs (cron).
- [mcp/README.md](mcp/README.md): Supabase MCP connector setup.

## ✅ Tests

Run the unit tests:
```bash
python -m unittest discover -s tests
```

## ⚙️ Data Source Selection

By default the app reads from local SQLite and falls back to Supabase if the local DB is missing.
To prefer cloud reads (useful in containers), set:
```bash
USE_SUPABASE_READS=1
```
The active source appears in the Streamlit sidebar as **Data Source**.

## 🏷️ Tagging & Session Context

Use **Database Manager → Tags & Session Split** to:
- Tag warmup/practice/round shots per session.
- Split mixed sessions into clean sub-sessions.
- Label sessions with a `session_type` for filtering.

## ⚖️ License
Personal Use.
