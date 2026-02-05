# Project Change Log: GolfDataApp

This log summarizes all changes made to the `GolfDataApp` project.

---

## 2026-02-05: Data Integrity Fixes

### Critical Bug Fixes
- **automation/backfill_runner.py**: Fixed rate limiter config passing `max_sessions_per_hour` directly to `requests_per_minute` — scraper was running **60x faster** than intended (360/hr vs 6/hr)
- **automation/uneekor_portal.py**: Fixed URL mismatch in session link merging — CSS selectors return relative URLs while JavaScript `node.href` returns absolute; now matches on report_id instead
- **automation_runner.py**: Fixed method name `_save_discovered_session` → `save_discovered_session`
- **automation_runner.py**: Fixed date format — `isoformat()` includes time but function expects `YYYY-MM-DD`; changed to `strftime("%Y-%m-%d")`

### New Feature: Sync Audit Trail
- **golf_db.py**: Added `sync_audit` table for tracking all sync operations
- **golf_db.py**: `sync_to_supabase()` now logs timestamps, record counts, and errors to audit table
- **supabase_schema.sql**: Added note that `sync_audit` is SQLite-only

### New Feature: Drift Detection
- **golf_db.py**: Enhanced `get_detailed_sync_status()` to return:
  - `local_count`: SQLite shot count
  - `supabase_count`: Supabase shot count
  - `local_only_count`: Records missing from Supabase
  - `last_sync`: Most recent sync metadata
  - `drift_detected`: Boolean flag when counts differ

### New Feature: Auto-Backfill for Date Reclassification
- **automation_runner.py**: Added `--auto-backfill` flag to `reclassify-dates --from-listing`
- Automatically propagates extracted dates to shots table after listing extraction

### Data Validation
- **golf_db.py**: `update_session_date_for_shots()` now validates dates:
  - Rejects future dates
  - Rejects dates before 2020 (Uneekor launch)

### Tests
- Added `tests/unit/test_rate_limiter_config.py` to prevent rate limiter regression
- Added tests for sync audit, drift detection, and date validation
- All 171 tests pass

### Usage
```bash
# Extract dates with auto-backfill (run in headless mode)
python automation_runner.py reclassify-dates --from-listing --auto-backfill --headless

# Check sync drift
python -c "import golf_db; golf_db.init_db(); print(golf_db.get_detailed_sync_status())"

# View sync audit history
sqlite3 golf_stats.db "SELECT * FROM sync_audit ORDER BY started_at DESC LIMIT 5"
```

### Data Status After Fixes
- SQLite: 1,341 shots | Supabase: 1,341 shots | No drift
- 93/93 visible sessions have dates extracted from listing page
- 1,341/1,341 shots have `session_date` populated (100%)

---

## 2026-02-03: Code Quality Fixes, Date Extraction, and Supabase Sync

### Security Fix (P1)
- **ml/train_models.py**: Fixed RCE vulnerability in `joblib.load()` by adding path validation to ensure models only load from trusted directory

### Data Integrity Fixes (P2)
- **golf_db.py**: Fixed empty `IN()` clause in `split_session()` when shot_ids is empty
- **golf_db.py**: Added `ValidationError` for null `shot_id`/`session_id` in `save_shot()`
- **golf_db.py**: Added `ALLOWED_RESTORE_COLUMNS` allowlist to prevent SQL injection in `restore_deleted_shots()`
- **golf_scraper.py**: Added size/MIME validation for image downloads
- **local_coach.py**: Fixed `idxmax()` on empty/NaT column in session analysis
- **automation/notifications.py**: Fixed rate-limit window bug using `timedelta` instead of `replace()`
- **automation/backfill_runner.py**: Applied `max_sessions_per_hour` config to RateLimiter
- **ml/train_models.py**: Added `DEFAULT_FEATURE_NAMES` fallback for models without metadata
- **ml/classifiers.py**: Fixed label casting with `str(prediction).lower()`

### Code Quality Fixes (P3)
- **exceptions.py**: Renamed `ImportError` to `DataImportError` (avoid shadowing builtin)
- **local_coach.py**: Added column validation before `.str` accessor usage
- **automation/session_discovery.py**: Populated `attempts` from `attempt_count` column
- **automation/credential_manager.py**: Removed unused imports, added encryption key docs
- **ml/anomaly_detection.py**: Normalized isolation forest scores to 0-1 range
- **services/ai/registry.py**: Added `Optional` return type, duplicate provider warning

### New Feature: Date Extraction from Listing Page
- **automation/naming_conventions.py**: Added `parse_listing_date()` method
- **automation/uneekor_portal.py**: Enhanced `_find_session_links()` with DOM walker to extract date context from listing page headers
- **automation/session_discovery.py**: Store `date_source` to track date provenance
- **automation_runner.py**: Added `--from-listing` option to `reclassify-dates` command

### New Feature: Supabase Sync
- **golf_db.py**: Added `get_detailed_sync_status()`, `sync_to_supabase()`, `sync_from_supabase()`
- **automation_runner.py**: Added `sync-database` CLI command

### Test Fixes
- **tests/test_scraper.py**: Fixed assertion to check `result['status'] == 'success'`
- **ml/train_models.py**: Catch `XGBoostError` (missing libomp) in addition to `ImportError`
- All 166 tests now pass

### Usage
```bash
# Extract dates from listing page DOM
python automation_runner.py reclassify-dates --from-listing

# Sync databases
python automation_runner.py sync-database --dry-run
python automation_runner.py sync-database
```

---

## 2026-01-27: Supabase Schema Alignment

### Problem Solved
The Supabase cloud database schema was out of sync with the local SQLite schema. The `supabase_schema.sql` file only documented `shots` and `tag_catalog`, while the live database had evolved to include 7 tables. The `session_summary` view was missing, and the schema file didn't reflect the actual RLS policy pattern (service role, not authenticated).

### Changes Made

**Live Supabase Migration**
- Added `idx_shots_date_added` and `idx_shots_club` indexes to `shots` table
- Created `session_summary` view with `session_date` column included

**supabase_schema.sql — Complete Rewrite**
- Documented all 7 tables: `shots`, `tag_catalog`, `shots_archive`, `change_log`, `sessions_discovered`, `automation_runs`, `backfill_runs`
- All RLS policies: service role full access + anon read on `shots`/`tag_catalog`
- All 11 indexes across all tables
- `session_summary` view with `session_date`
- Migration guide section for existing deployments

**golf_db.py — Archive Sync**
- `delete_session()` now archives shots to Supabase `shots_archive` before cloud deletion
- Follows existing SQLite-first, Supabase-optional pattern

**Documentation Updates**
- Updated `CLAUDE.md` database schema table with all 7 tables and sync status
- Updated `DEPLOYMENT_SUMMARY.md` Supabase section with current state
- Updated `PHASE2_SUMMARY.md` to reflect archive now syncs to Supabase
- Updated `SETUP_GUIDE.md` schema creation section with full table list
- Updated `AUTOMATION_GUIDE.md` with Supabase sync details

### Files Modified
- `supabase_schema.sql` — Rewritten as canonical reference
- `golf_db.py` — Added Supabase archive sync in `delete_session()`
- `CLAUDE.md`, `changelog.md`, `DEPLOYMENT_SUMMARY.md`, `PHASE2_SUMMARY.md`, `SETUP_GUIDE.md`, `AUTOMATION_GUIDE.md`

---

## 2026-01-26: Session Date Reclassification

### Problem Solved
Sessions were missing accurate dates - only import timestamps (`date_added`) were stored, making trend analysis inaccurate.

### Features Added

**Database Schema**
- Added `session_date TIMESTAMP` column to `shots` table
- Added `date_source TEXT` column to `sessions_discovered` table
- Created index `idx_shots_session_date` for efficient date queries
- Added migration support for existing databases

**Date Parsing (automation/uneekor_portal.py)**
- Enhanced `_parse_date_from_text()` with 7 date format patterns:
  - `YYYY.MM.DD` (Uneekor report page format)
  - `YYYY-MM-DD` (ISO format)
  - `DD.MM.YYYY` (European format)
  - `MM/DD/YYYY` (US format)
  - Abbreviated/full month names

**Report Page Extraction**
- New method `extract_date_from_report_page()` navigates to report pages and extracts dates from headers
- Most reliable date source (YYYY.MM.DD format in headers)

**CLI Commands (automation_runner.py)**
- New `reclassify-dates` command with options:
  - `--status`: Show date status summary
  - `--backfill`: Copy dates from sessions_discovered to shots
  - `--scrape`: Extract dates from report pages (rate-limited)
  - `--manual REPORT_ID DATE`: Set date manually
  - `--dry-run`: Preview without changes

**Database Functions (golf_db.py)**
- `backfill_session_dates()`: Copy dates from sessions_discovered to shots
- `get_sessions_missing_dates()`: Find sessions without dates
- `update_session_date_for_shots()`: Update all shots for a session

**UI Updates**
- Data Import page shows actual session dates
- AI Coach session picker uses session dates
- Trend chart uses session_date for accurate temporal analysis

**Tests**
- `tests/unit/test_date_parsing.py`: 15 test cases for date formats
- `tests/integration/test_date_reclassification.py`: Database operation tests

### Usage
```bash
python automation_runner.py reclassify-dates --status
python automation_runner.py reclassify-dates --backfill
python automation_runner.py reclassify-dates --scrape --max 10
python automation_runner.py reclassify-dates --manual 43285 2026-01-15
```

---

## 2026-01-25: Scraper Automation Features

### Features Added
- `--clubs "Driver,7 Iron"`: Filter sessions by clubs used
- `--dry-run`: Preview imports without database changes
- `--retry-failed`: Retry failed imports with exponential backoff
- Pagination support for portal session discovery
- Improved session naming and auto-tagging

---

## Previous Changes

## 1. Documentation Improvements
Developed comprehensive documentation for missing setup steps and local workflows.
- **[NEW] [README.md](file:///Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My%20Drive/2025%20Golf%20Season/GolfDataApp/README.md)**: Created a central entry point with project overview and quick setup links.
- **[UPDATED] [QUICKSTART.md](file:///Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My%20Drive/2025%20Golf%20Season/GolfDataApp/QUICKSTART.md)**: Added "Step 0: Initial Data Capture (Streamlit)" for local data ingestion.
- **[UPDATED] [SETUP_GUIDE.md](file:///Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My%20Drive/2025%20Golf%20Season/GolfDataApp/SETUP_GUIDE.md)**: Added detailed instructions for virtual environment setup, `.env` configuration, and Uneekor scraping workflow.
- **[UPDATED] [AUTOMATION_GUIDE.md](file:///Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My%20Drive/2025%20Golf%20Season/GolfDataApp/AUTOMATION_GUIDE.md)**: Updated all command paths to reflect the new directory structure.

## 2. Codebase Reorganization
Restructured the project for better maintainability and a clean GitHub repository.
- **`scripts/`**: Created for core pipeline and analysis scripts.
    - Moved: `auto_sync.py`, `migrate_to_supabase.py`, `supabase_to_bigquery.py`, `vertex_ai_analysis.py`, `post_session.py`, `gemini_analysis.py`.
- **`legacy/`**: Created for debug scripts, helper tools, and older scraper versions.
    - Moved: `inspect_api_response.py`, `test_connection.py`, `check_clubs.py`, `debug_scraper*.py`, `golf_scraper_fixed.py`, `golf_scraper_selenium_backup.py`.
- **Cleanup**: Deleted non-essential temporary files: `debug_page_source.html`, `Untitled.rtf`.

## 3. Security & Git Readiness
Enhanced security and prepared the repository for public/private sharing.
- **[NEW] [.gitignore](file:///Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My%20Drive/2025%20Golf%20Season/GolfDataApp/.gitignore)**: Prevents tracking of sensitive files (`.env`), databases (`*.db`), logs, and MacOS system files.
- **[UPDATED] [.env.example](file:///Users/duck/Library/CloudStorage/GoogleDrive-matt@coloradolawclassic.org/My%20Drive/2025%20Golf%20Season/GolfDataApp/.env.example)**: Added placeholders for all required keys, including `GEMINI_API_KEY` and `ANTHROPIC_API_KEY`.
- **Secret Scan**: Verified that no hardcoded credentials exist in tracked files.

## 4. GitHub Integration
- **Initialized Git**: Performed `git init` and initial commit of the organized structure.
- **Remote Repository**: Created private GitHub repository `Redeemedduck/GolfDataApp` and pushed the code.
- **Repository URL**: [https://github.com/Redeemedduck/GolfDataApp](https://github.com/Redeemedduck/GolfDataApp)

## 5. Summary of Core Commands (Post-Cleanup)
- **Run Streamlit**: `streamlit run app.py`
- **Sync to BigQuery**: `python scripts/supabase_to_bigquery.py incremental`
- **AI Analysis**: `python scripts/vertex_ai_analysis.py analyze "Driver"`
- **Post-Session Tool**: `python scripts/post_session.py`
