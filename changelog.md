# Project Change Log: GolfDataApp

This log summarizes all changes made to the `GolfDataApp` project.

---

## 2026-02-11: Data Quality Framework, Club Normalization, and Warmup Tagging

### Overview
Built a comprehensive data quality validation system spanning 12 check categories, 4 severity
levels, SQLite infrastructure (table + views), Supabase migration SQL, and warmup shot tagging.
Also significantly expanded club name normalization in `naming_conventions.py` to handle
Uneekor system-generated formats, M-prefixed variants, iron+context compound names, and
bare number shorthands.

### New Feature: Data Quality Validation System
- **`shot_quality_flags` table** (SQLite) — Stores 3,506 quality flags linking shot_id → category + severity + reason
- **`shots_clean` view** — 1,920 shots (89.7%) with CRITICAL/HIGH flags excluded; safe for general analytics
- **`shots_strict` view** — 726 shots (33.9%) with CRITICAL/HIGH/MEDIUM excluded; maximum purity for ML and club gapping
- **`is_warmup` column** on `shots` table — 468 warmup shots tagged (INTEGER, 0 or 1) for dashboard toggle
- **12 validation categories**: sentinel values, physics violations, smash factor bounds, total vs carry consistency, duplicate detection, club normalization, warmup detection, mishit detection, multi-club sessions, fatigue detection, extreme spin rates, launch angle outliers
- **4 severity levels**: CRITICAL (exclude always), HIGH (exclude unless manually verified), MEDIUM (review first), LOW (informational)

### New Files
- **`sync_quality_flags.py`** — CLI script to push quality flags and is_warmup values from SQLite to Supabase. Supports `--dry-run`, `--flags-only`, `--warmup-only`.
- **`supabase_quality_migration.sql`** — DDL migration for Supabase: adds `is_warmup` column, creates `shot_quality_flags` table with indexes and RLS, creates `shots_clean` and `shots_strict` views.
- **`data_quality_report.csv`** — Full export of all 3,506 flags with shot metrics (generated, not tracked in git)
- **`data_quality_summary.json`** — Machine-readable summary of flag counts by severity and category (generated, not tracked in git)

### New Skill: golf-data-quality
- **Location**: `.claude/skills/golf-data-quality/`
- **SKILL.md** — Trigger definitions, usage instructions, severity level guide, threshold customization
- **references/validation_rules.md** — Complete physics-based rule definitions for all 12 categories with per-club-type threshold tables
- **scripts/validate_golf_data.py** (961 lines) — Main validation engine with configurable thresholds, CSV/JSON output, console summary

### Club Normalization Improvements (automation/naming_conventions.py)
- **Uneekor system-generated format**: `IRON7 | MEDIUM`, `DRIVER | PREMIUM`, `Wedge 56 | Premium` → canonical names
- **M-prefixed variants**: `M 7` → 7 Iron, `M 56` → SW, `M 7 Iron` → 7 Iron
- **Iron+context compound names**: `9 Iron Magnolia` → 9 Iron, `7 Iron Shoulders Right` → 7 Iron, `8 Iron Magnolia` → 8 Iron
- **Reversed iron format**: `Iron 7` → 7 Iron (in addition to `7 Iron`)
- **Bare single-digit numbers**: `7` → 7 Iron, `9` → 9 Iron, `6` → 6 Iron
- **Bare degree numbers**: `56` → SW, `50` → GW (via DEGREE_TO_WEDGE mapping)
- **Reversed warmup+number**: `50 Warmup` → GW warmup context (SessionContextParser)
- **Reversed word-order wood/hybrid**: `Wood 3`, `Hybrid 4` → canonical forms
- **Driving iron**: `3 Driving Iron` → 3 Wood (by convention)
- **Extended comments**: All pattern groups now have section headers and rationale explaining why each pattern exists

### Database Changes (golf_stats.db)
- Added `is_warmup INTEGER DEFAULT 0` column to `shots` table
- Created `shot_quality_flags` table (3,506 rows) with indexes on shot_id, severity, category, session_id
- Created `shots_clean` SQL view
- Created `shots_strict` SQL view

### Data Quality Results (as of 2026-02-11)
| Metric | Value |
|--------|-------|
| Total shots | 2,141 |
| Total flags | 3,506 across 1,971 unique shots |
| CRITICAL flags | 2 |
| HIGH flags | 237 |
| MEDIUM flags | 1,464 |
| LOW flags | 1,803 |
| Zero-flag ("clean") shots | 170 (7.9%) |
| shots_clean view | 1,920 (89.7%) |
| shots_strict view | 726 (33.9%) |
| Analytics-ready (clean + no warmup) | 1,468 (68.6%) |

### Key Findings
- **Single player confirmed** — Driver club_speed consistently 107–115 mph across all 46 sessions, confirming all data is Duck's
- **1 CRITICAL shot** — Session "Sgt Rd1" had a carry of 109,359.9 yards (sentinel leak); excluded by `shots_clean`
- **False-positive duplicate detection** — 2 flagged "duplicates" were actually different shots that coincidentally shared carry + ball_speed values (20+ other columns differed); flags removed
- **Club normalization coverage** — 944 shots (44.1%) resolve to a specific club via normalizer or context parser; 1,172 shots (54.7%) have session type identified but club is ambiguous (sim rounds, warmups); only 25 shots (1.2%) fully unresolved

### Supabase Sync Status
- SQLite and Supabase both have 2,141 shots (verified in sync)
- `shot_quality_flags` table does NOT yet exist in Supabase — run `supabase_quality_migration.sql` in SQL Editor first
- `is_warmup` column does NOT yet exist in Supabase — same migration adds it
- After migration: run `python sync_quality_flags.py` to push flags and warmup tags

### Usage
```bash
# Run the data quality validator
python3 .claude/skills/golf-data-quality/scripts/validate_golf_data.py

# Sync quality flags to Supabase (after running migration SQL)
python sync_quality_flags.py --dry-run    # Preview
python sync_quality_flags.py              # Full sync

# Query clean data in SQLite
sqlite3 golf_stats.db "SELECT club, AVG(carry) FROM shots_clean WHERE is_warmup = 0 GROUP BY club"
```

### Files Modified
- `automation/naming_conventions.py` — Major expansion of CLUB_PATTERNS, CLUB_EXTRACTION_PATTERNS, added section headers and comments
- `golf_stats.db` — New column, table, and views (see Database Changes above)
- `CHANGELOG.md` — This entry
- `CLAUDE.md` — Updated schema table, added data quality section, new commands
- `supabase_schema.sql` — Added shot_quality_flags table, shots_clean/shots_strict views, is_warmup column

### Files Created
- `sync_quality_flags.py`
- `supabase_quality_migration.sql`
- `.claude/skills/golf-data-quality/SKILL.md`
- `.claude/skills/golf-data-quality/references/validation_rules.md`
- `.claude/skills/golf-data-quality/scripts/validate_golf_data.py`

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
