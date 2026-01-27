# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Branch Context

This branch includes both **cloud AI (Gemini)** and **local ML models** for hybrid coaching. Local ML provides offline-first predictions while Gemini offers advanced conversational coaching.

## Common Commands

```bash
# Run the Streamlit app
streamlit run app.py

# Run tests
python -m unittest discover -s tests

# Run a single test file
python -m unittest tests/test_golf_db.py
python -m unittest tests.unit.test_ml_models
python -m unittest tests.unit.test_local_coach
python -m unittest tests.unit.test_date_parsing
python -m unittest tests.integration.test_date_reclassification

# Syntax check all Python files
python -m py_compile app.py golf_db.py local_coach.py exceptions.py
python -m py_compile automation/*.py ml/*.py utils/*.py

# Train ML models (requires shot data in database)
python -m ml.train_models

# Docker local testing
docker build -t golf-data-app .
docker run -p 8080:8080 -e GEMINI_API_KEY="key" golf-data-app

# Automation CLI (scraper)
playwright install chromium              # First-time only
python automation_runner.py login        # Interactive login, saves cookies
python automation_runner.py discover --headless
python automation_runner.py backfill --start 2025-01-01
python automation_runner.py backfill --start 2025-01-01 --clubs "Driver,7 Iron"  # Filter by clubs
python automation_runner.py backfill --start 2025-01-01 --dry-run  # Preview without importing
python automation_runner.py backfill --retry-failed  # Retry failed imports

# Session date reclassification
python automation_runner.py reclassify-dates --status                   # Show date status
python automation_runner.py reclassify-dates --backfill                 # Copy dates to shots
python automation_runner.py reclassify-dates --scrape --max 10          # Extract from portal (slow)
python automation_runner.py reclassify-dates --manual 43285 2026-01-15  # Set date manually

# Cloud sync
python scripts/supabase_to_bigquery.py incremental
```

## Architecture Overview

### Data Flow

```
Uneekor API/Portal --> automation/ --> golf_db.py --> SQLite + Supabase
                                              |
                                              v
                                      Streamlit Pages
                                              |
                                    ┌─────────┴─────────┐
                                    v                   v
                            local_coach.py      gemini_coach.py
                            (Offline ML)        (Cloud AI)
```

### Core Modules

| Module | Purpose |
|--------|---------|
| `golf_db.py` | Database layer with hybrid sync (SQLite local-first + Supabase cloud backup) |
| `local_coach.py` | **NEW**: Local AI coach with template-based insights and ML predictions |
| `gemini_coach.py` | Gemini 3.0 AI Coach with function calling |
| `automation/` | Playwright-based scraper automation with rate limiting |
| `ml/` | **NEW**: Machine learning models for predictions and analysis |
| `utils/` | **NEW**: Logging configuration and utilities |
| `exceptions.py` | **NEW**: Custom exception hierarchy |

### ML Module (`ml/`)

The ML package provides local machine learning capabilities:

| File | Purpose |
|------|---------|
| `train_models.py` | XGBoost distance prediction model |
| `classifiers.py` | Shot shape classification (draw, fade, hook, slice, etc.) |
| `anomaly_detection.py` | Swing flaw detection using Isolation Forest |

**Key Classes:**
- `DistancePredictor`: Predicts carry distance from launch conditions
- `ShotShapeClassifier`: Classifies shot shape using D-plane theory
- `SwingFlawDetector`: Detects swing issues (over-the-top, early release, etc.)

ML models work without dependencies via rule-based fallbacks.

### Local Coach (`local_coach.py`)

The LocalCoach provides AI coaching without cloud APIs:
- Intent detection routes queries to appropriate handlers
- Template-based responses with data injection
- ML predictions when models are trained
- Registered as AI provider via `services/ai/providers/local_provider.py`

### AI Provider System

Providers are registered via decorator pattern in `services/ai/`:
```python
from services.ai import list_providers, get_provider

providers = list_providers()  # Returns [GeminiProvider, LocalProvider]
spec = get_provider('local')  # Get specific provider
```

### Hybrid Database Pattern

All write operations in `golf_db.py` follow this pattern:
1. Write to local SQLite (always)
2. Sync to Supabase (if configured)

SQLite uses **WAL mode** for better concurrent access.

### Streamlit Multi-Page Structure

- `app.py` - Landing page and navigation
- `pages/1_Data_Import.py` - Import from Uneekor URLs
- `pages/2_Dashboard.py` - Analytics with 5 tabs (Overview, Impact, Trends, Shots, Export)
- `pages/3_Database_Manager.py` - CRUD operations with 6 tabs
- `pages/4_AI_Coach.py` - Chat interface with **provider selection** (Local or Gemini)

### Component Pattern

All UI components in `components/` follow this pattern:
```python
def render_component_name(data: pd.DataFrame, **kwargs) -> None:
    st.subheader("Title")
    # implementation
```

### Automation Module

The `automation/` package provides Playwright-based scraping:

| File | Purpose |
|------|---------|
| `credential_manager.py` | Encrypted cookie persistence |
| `rate_limiter.py` | Token bucket throttling (6 req/min default) |
| `session_discovery.py` | Find and deduplicate sessions, **club filtering**, **retry tracking** |
| `naming_conventions.py` | Normalize club names (e.g., "7i" -> "7 Iron") |
| `backfill_runner.py` | Historical import with checkpointing, **dry-run mode**, **retry logic** |
| `notifications.py` | Slack alerts |

**New Features:**
- `--clubs "Driver,7 Iron"`: Filter sessions by clubs used
- `--dry-run`: Preview imports without database changes
- `--retry-failed`: Retry failed imports with exponential backoff (10s → 30s → 90s)

## Environment Variables

```bash
# Required for Gemini AI Coach
GEMINI_API_KEY=your_key

# Optional for cloud sync
SUPABASE_URL=your_url
SUPABASE_KEY=your_key

# Optional for automation
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Force cloud reads in containers
USE_SUPABASE_READS=1

# Enable structured logging
GOLFDATA_LOGGING=1
```

## Database Tables

| Table | Purpose |
|-------|---------|
| `shots` | Main data (30+ fields per shot, including `session_date`) |
| `shots_archive` | Soft-deleted shots for recovery |
| `change_log` | Audit trail for all modifications |
| `sessions_discovered` | Automation: discovered sessions, import status, `date_source` |
| `backfill_runs` | Automation: backfill progress and checkpointing |
| `tag_catalog` | Shot tag definitions |

### Key Date Fields

| Field | Table | Purpose |
|-------|-------|---------|
| `session_date` | shots | When the practice session actually occurred |
| `date_added` | shots | When the data was imported (auto-set) |
| `session_date` | sessions_discovered | Discovered session date from portal |
| `date_source` | sessions_discovered | Where date came from: `portal`, `report_page`, `manual` |

## Security

- **SQL Injection Protection**: `update_shot_metadata()` uses field allowlist (`ALLOWED_UPDATE_FIELDS`)
- **Parameterized Queries**: All database operations use parameterized SQL
- **Soft Deletes**: Deletions are archived for recovery

## Key Conventions

- Database operations always use parameterized SQL
- Deletions are archived for recovery (soft delete)
- Club names are normalized via `automation/naming_conventions.py`
- Sessions auto-tagged based on characteristics (Driver Focus, Short Game, etc.)
- The `99999` value is a Uneekor sentinel meaning "no data" - cleaned via `clean_value()`
- ML imports are lazy to avoid requiring dependencies for all uses

## Testing

```bash
# All tests
python -m unittest discover -s tests

# By category
python -m unittest tests.test_golf_db                           # Database tests
python -m unittest tests.unit.test_ml_models                    # ML model tests
python -m unittest tests.unit.test_local_coach                  # Local coach tests
python -m unittest tests.unit.test_date_parsing                 # Date format parsing
python -m unittest tests.integration.test_automation_flow       # Automation tests
python -m unittest tests.integration.test_date_reclassification # Date management
```

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`) runs:
- Tests on Python 3.10, 3.11, 3.12
- Syntax validation on all Python files
- ML module load validation
