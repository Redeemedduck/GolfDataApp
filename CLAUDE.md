# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Run the Streamlit app
streamlit run app.py

# Run all tests (unittest runner; pytest also works)
python -m unittest discover -s tests

# Run a single test file
python -m unittest tests.test_golf_db
python -m unittest tests.unit.test_ml_models
python -m unittest tests.unit.test_local_coach
python -m unittest tests.unit.test_date_parsing
python -m unittest tests.unit.test_exceptions
python -m unittest tests.unit.test_credential_manager
python -m unittest tests.unit.test_naming_conventions
python -m unittest tests.integration.test_automation_flow
python -m unittest tests.integration.test_date_reclassification

# Syntax check all Python files (this is what CI runs as "lint")
python -m py_compile app.py golf_db.py local_coach.py exceptions.py
python -m py_compile automation/*.py ml/*.py utils/*.py
python -m py_compile services/ai/*.py services/ai/providers/*.py

# Train ML models (requires shot data in database)
python -m ml.train_models

# Automation CLI (Playwright scraper for Uneekor portal)
playwright install chromium              # First-time only
python automation_runner.py login        # Interactive login, saves cookies
python automation_runner.py discover --headless
python automation_runner.py backfill --start 2025-01-01
python automation_runner.py backfill --start 2025-01-01 --clubs "Driver,7 Iron"
python automation_runner.py backfill --start 2025-01-01 --dry-run
python automation_runner.py backfill --retry-failed

# Session date reclassification
python automation_runner.py reclassify-dates --status
python automation_runner.py reclassify-dates --from-listing   # Extract from listing page DOM
python automation_runner.py reclassify-dates --backfill
python automation_runner.py reclassify-dates --scrape --max 10
python automation_runner.py reclassify-dates --manual 43285 2026-01-15

# Database sync (SQLite <-> Supabase)
python automation_runner.py sync-database --dry-run
python automation_runner.py sync-database
python automation_runner.py sync-database --direction from-supabase

# Data quality validation
python3 .claude/skills/golf-data-quality/scripts/validate_golf_data.py

# Sync quality flags to Supabase (run migration SQL first)
python sync_quality_flags.py --dry-run
python sync_quality_flags.py
python sync_quality_flags.py --flags-only
python sync_quality_flags.py --warmup-only
```

## Architecture Overview

### Data Flow

```
Uneekor Portal --> automation/ --> golf_db.py --> SQLite + Supabase
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
| `golf_db.py` | Database layer: SQLite local-first + optional Supabase cloud sync |
| `local_coach.py` | Local AI coach: intent detection, template responses, ML predictions |
| `gemini_coach.py` | Gemini AI Coach with function calling |
| `automation/` | Playwright-based scraper: rate limiting, checkpointing, cookie persistence |
| `ml/` | ML models: XGBoost distance prediction, shot shape classification, anomaly detection |
| `services/ai/` | AI provider registry (decorator pattern for pluggable backends) |
| `components/` | Reusable Streamlit UI components (all follow `render_*()` pattern) |
| `exceptions.py` | Exception hierarchy: `GolfDataAppError` base with `DatabaseError`, `ValidationError`, `RateLimitError`, `AuthenticationError`, etc. — all carry context dicts |
| `sync_quality_flags.py` | Pushes `shot_quality_flags` data and `is_warmup` values from SQLite to Supabase |
| `golf_scraper.py` | Legacy scraper (pre-Playwright, still functional) |

### Hybrid Database Pattern

All write operations in `golf_db.py` follow:
1. Write to local SQLite (always)
2. Sync to Supabase (if configured, soft dependency)
3. For deletions: archive to `shots_archive` in both SQLite and Supabase before removing

Read modes (`get_read_mode()`/`set_read_mode()`): `"auto"` (SQLite first, Supabase fallback), `"sqlite"` (local only), `"supabase"` (cloud only, for containers).

SQLite uses **WAL mode** for concurrent reads/writes. Schema migrations in `init_db()` use `PRAGMA table_info` to detect and add missing columns dynamically.

### AI Provider System

Providers self-register via `@register_provider` decorator in `services/ai/registry.py`. Each provider defines `PROVIDER_ID` and `DISPLAY_NAME` class attributes. Providers are auto-imported when `services/ai/providers/` is loaded.

```python
from services.ai import list_providers, get_provider
providers = list_providers()        # All registered ProviderSpec objects
spec = get_provider('local')        # Get by ID, returns ProviderSpec
instance = spec.provider_cls()      # Instantiate the provider
```

### ML Module

ML dependencies are **lazy-loaded** via `__getattr__` in `ml/__init__.py`. Code that uses ML gracefully degrades if XGBoost/sklearn aren't installed — rule-based fallbacks handle all cases. Key classes: `DistancePredictor`, `ShotShapeClassifier` (D-plane theory), `SwingFlawDetector` (Isolation Forest).

### Streamlit Pages

- `app.py` — Landing page and navigation
- `pages/1_Data_Import.py` — Import from Uneekor URLs
- `pages/2_Dashboard.py` — Analytics (5 tabs: Overview, Impact, Trends, Shots, Export)
- `pages/3_Database_Manager.py` — CRUD, tagging, session splitting (6 tabs)
- `pages/4_AI_Coach.py` — Chat interface with provider selection dropdown

Components in `components/` are stateless: `render_*(data: pd.DataFrame, **kwargs) -> None`.

### Automation Module

Layered architecture: `automation_runner.py` CLI → `BackfillRunner` (orchestration + checkpointing) → `SessionDiscovery` (dedup + state tracking) → `PlaywrightClient` (browser lifecycle + cookies) → `UneekorPortal` (navigation).

Key behaviors:
- Token bucket rate limiting (6 req/min default via `rate_limiter.py`)
- Encrypted cookie persistence (`credential_manager.py`)
- Resumable backfill with `sessions_discovered` and `backfill_runs` tables
- Club name normalization via `naming_conventions.py` (e.g., "7i" → "7 Iron", "Iron7 | Medium" → "7 Iron", "M 56" → "SW", "9 Iron Magnolia" → "9 Iron")
- Session context parsing via `SessionContextParser` (e.g., "Warmup 50" → warmup + GW, "Dst Compressor 8" → drill + 8 Iron)
- Exponential backoff on retries (10s → 30s → 90s)

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | For AI Coach | Gemini API access |
| `SUPABASE_URL` | No | Cloud sync URL |
| `SUPABASE_KEY` | No | Cloud sync key |
| `SLACK_WEBHOOK_URL` | No | Automation alerts |
| `USE_SUPABASE_READS` | No | Set `1` to force cloud reads (containers) |
| `GOLFDATA_LOGGING` | No | Set `1` for structured logging |

## Database Schema

| Table | Purpose | Supabase Sync |
|-------|---------|---------------|
| `shots` | Main data (35+ fields per shot, including `is_warmup`) | Yes — full upsert |
| `shots_archive` | Soft-deleted shots (recovery) | Yes — archived on session delete |
| `change_log` | Audit trail for modifications | No — local only |
| `tag_catalog` | Shot tag definitions | Yes — upsert/delete |
| `shot_quality_flags` | Data quality flags (severity + category per shot) | Yes — via `sync_quality_flags.py` |
| `sessions_discovered` | Automation: discovered sessions + import status + `date_source` | Yes — service role |
| `automation_runs` | Automation: high-level run tracking | Yes — service role |
| `backfill_runs` | Automation: backfill progress checkpoints | Yes — service role |

| View | Purpose |
|------|---------|
| `shots_clean` | All shots excluding CRITICAL/HIGH quality flags (89.7% of data) |
| `shots_strict` | All shots excluding CRITICAL/HIGH/MEDIUM flags (33.9% of data) |
| `session_summary` | Aggregated per-session, per-club metrics |

Canonical Supabase schema: `supabase_schema.sql` (all tables, indexes, RLS policies, views).
Supabase quality migration: `supabase_quality_migration.sql` (adds `shot_quality_flags`, views, `is_warmup`).

Key date distinction: `session_date` = when the practice occurred, `date_added` = when data was imported.

### Data Quality Infrastructure

The `shot_quality_flags` table stores validation results from the data quality validator (`.claude/skills/golf-data-quality/scripts/validate_golf_data.py`). Each flag has:

- `shot_id` — links to the `shots` table
- `category` — one of 12 check categories (e.g., `physics_violations`, `warmup_detection`, `smash_factor`)
- `severity` — `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`
- `reason` — human-readable explanation

The `is_warmup` column on `shots` (INTEGER, 0 or 1) tags shots from warmup sessions. Combined with `shots_clean`, the canonical analytics query is:

```sql
SELECT * FROM shots_clean WHERE is_warmup = 0
```

This returns the "analytics-ready" dataset: clean data with no warmup contamination.

## Key Conventions

- All database operations use **parameterized SQL**; `update_shot_metadata()` enforces a field allowlist (`ALLOWED_UPDATE_FIELDS`)
- Deletions are **soft deletes** — records go to `shots_archive` for recovery
- The value `99999` is a Uneekor sentinel meaning "no data" — cleaned via `clean_value()` in `golf_db.py`
- Club names are normalized through `automation/naming_conventions.py`
- Sessions are auto-tagged based on characteristics (Driver Focus, Short Game, etc.)

### Coding Style

- Python code uses **4-space indentation**, `snake_case` for functions/variables, `PascalCase` for classes
- Keep modules small and focused; UI-only logic goes in `pages/` or `components/`
- No formatter/linter is configured; keep diffs clean and avoid mixed line endings
- Follow **conventional commit** style: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, etc.
- PRs should include a short summary, manual test steps, and screenshots for UI changes

## Testing

Tests use `unittest` (and are also compatible with `pytest`). Shared fixtures in `tests/conftest.py` provide:

| Fixture | Purpose |
|---------|---------|
| `temp_db_path` | Temporary SQLite path (auto-cleaned) |
| `golf_db_instance` | Initialized `golf_db` module pointed at temp DB with Supabase disabled |
| `populated_golf_db` | `golf_db_instance` pre-loaded with 10 sample shots |
| `sample_shot_data` | Single shot dict with realistic Driver metrics |
| `sample_shots_batch` | 10 shots with varying carry distances |
| `ml_test_dataframe` | 100-row DataFrame with synthetic launch data (seeded) |
| `mock_rate_limiter` | Permissive rate limiter (1000 req/min) for automation tests |
| `local_coach` | Stateless `LocalCoach` instance |
| `discovery_db` | Initialized `SessionDiscovery` with temp DB |

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):
- **test** job: Python 3.10, 3.11, 3.12 — `py_compile` lint + `unittest discover`
- **validate-ml** job: Verifies all ML classes import and `LocalCoach` instantiates

## Known Limitations

### Session Date Accuracy (Uneekor Portal Limitation)

**Problem:** The Uneekor portal does not reliably expose session dates. Report pages show today's "view date", not the original session date.

**Solution (as of 2026-02-03):** The listing page (`/portal/reports`) shows sessions grouped by date headers (e.g., "January 15, 2026"). The `--from-listing` command extracts dates from the DOM by walking the page structure and associating each session link with its preceding date header.

**Recommended approach:**
```bash
# Extract dates from listing page (most reliable)
python automation_runner.py reclassify-dates --from-listing

# Then propagate to shots table
python automation_runner.py reclassify-dates --backfill
```

**Alternative methods:**
- `--manual <report_id> <YYYY-MM-DD>`: Set dates for sessions you remember
- `--scrape`: Visit report pages (less reliable, shows current date)

**Date source tracking:** The `date_source` column in `sessions_discovered` tracks where dates came from:
- `listing_page`: Extracted from listing page DOM (most reliable)
- `link_text`: Parsed from session link text
- `report_page`: Scraped from report page header
- `manual`: Manually entered

## Active Handoff

> **Read `.claude/context-handoff.md` before starting work.** It contains the current task queue from the most recent Cowork session (2026-02-11). Tasks: git commit data quality framework, run Supabase migration, sync quality flags. Remove this section once the handoff is complete.
