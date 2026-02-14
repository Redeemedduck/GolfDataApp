# Project Change Log: GolfDataApp

This log summarizes all changes made to the `GolfDataApp` project.

---

## 2026-02-13: Phase 4 — Dashboard Rebuild & Sidebar Cleanup

### Smash Factor Targets
- **`my_bag.json`**: Added per-club `smash_target` values based on tour averages (Driver 1.50, irons 1.38, wedges 1.25, etc.)
- **`utils/bag_config.py`**: Added `get_smash_target(club)` loader
- 62 new tests for bag config

### Sidebar Stripped to Navigation Only
- Removed data source selector, sync status, compact toggle, appearance toggle, and health metrics from sidebar
- All pages now get a clean nav-only sidebar via `shared_sidebar.py`

### New Display Tab in Settings
- Settings page goes from 3 tabs to 4 (Data, Maintenance, Tags, Display)
- Display tab houses relocated controls: data source, sync status, layout toggles, appearance settings

### Stats
- 11 files changed (+225 / -76 lines)

---

## 2026-02-13: Test Isolation Fix

### Fixed
- **`test_agent_tools.py`**: Replaced `sys.modules.setdefault()` with `setUpModule()`/`tearDownModule()` — mocks now properly save/restore
- **`test_claude_provider.py`**: Same fix — no longer clobbers `services` package in `sys.modules`
- Full suite: **360 tests, 0 failures, 0 errors** (was 35 failures + 18 errors)

### Changed
- Rebuilt venv on **Python 3.12** (was 3.9) — supports Agent SDK and all deps

---

## 2026-02-13: Claude Agent SDK Golf Coach

### New Module: `agent/`

Added a Claude Agent SDK-powered golf coaching agent with 8 MCP tools wrapping `golf_db` for data access. Three interfaces: terminal CLI, Claude Code `/golf` slash command, and Streamlit AI Coach provider.

- **`agent/tools.py`**: 8 MCP tools — 5 read (`query_shots`, `get_session_list`, `get_session_summary`, `get_club_stats`, `get_trends`) + 3 write (`tag_session`, `update_session_type`, `batch_rename_sessions`). All tools use `read_mode="sqlite"` to avoid Supabase latency.
- **`agent/core.py`**: System prompt (Big 3 coaching persona), `create_golf_mcp_server()`, `create_golf_agent_options()` (Sonnet 4.5, max 20 turns), `single_query()` async helper.
- **`agent/cli.py`**: Interactive chat mode + `--single` one-shot query. Runnable as `python3 -m agent`.
- **`services/ai/providers/claude_provider.py`**: Streamlit AI Coach provider using `ThreadPoolExecutor` to avoid `asyncio.run()` crash inside Streamlit's event loop.
- **`.env.template`**: 1Password `op://` references for `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`.
- **`~/.claude/skills/golf/SKILL.md`**: Claude Code `/golf` slash command.

### Safety Boundaries

Agent can only read data and perform safe writes (tag, set session type, batch rename). Cannot delete data, trigger automation, run raw SQL, or modify schema.

### Tests

- 70 new tests: 40 tools + 21 core + 9 provider
- All use mock isolation to avoid heavy dependency imports (Streamlit, Supabase, etc.)
- `test_claude_provider.py` uses `importlib.util.spec_from_file_location()` to bypass the provider package auto-import chain

### CI

- Added `agent/*.py` to `py_compile` lint step in `.github/workflows/ci.yml`

### Usage

```bash
# Interactive chat
op run --env-file=.env.template -- python3 -m agent.cli

# One-shot query
op run --env-file=.env.template -- python3 -m agent.cli --single "How's my driver?"

# Claude Code slash command
/golf How's my driver been this month?
```

### Stats
- 13 files changed (+1,300 lines)
- 311 tests total (70 new)

---

## 2026-02-13: Data Model & UX Overhaul — Phases 1-3

### Phase 1: Club Name Normalization (PR #15)

82% of `club` column values were session names (courses, drills, warmups) instead of actual club names. Built a two-tier normalization pipeline that reduced 73 distinct values to 10 clean clubs.

- **`automation/naming_conventions.py`**: Added 15+ regex patterns to `ClubNameNormalizer` (Uneekor formats, reversed wedges, no-space irons, single-digit, bare degrees, M-prefix)
- **`golf_db.py`**: Auto-normalize in `save_shot()`, new `original_club_value` column preserving raw values
- **`supabase_schema.sql`**: Added `original_club_value` column
- **`pages/4_Settings.py`**: Consolidated inline normalizer to use `ClubNameNormalizer`
- **`utils/migrate_club_data.py`**: One-time migration script (`--dry-run`, `--report` modes)
- 94 naming convention tests + 3 golf_db normalization tests

**Migration results**: 1,795 shots updated, 977 with known clubs, 1,182 correctly NULL (sim rounds/drills)

### Phase 2: Date Cleanup (PR #16)

- Standardized all `session_date` to `YYYY-MM-DD` (stripped `T00:00:00` from 39 shots, 117 sessions_discovered rows)
- Fixed 3 misclassified shots (2026-01-28 -> 2026-01-26)
- Marked 2 unreliable `report_page` sessions as `unverified`
- Removed misleading `datetime.utcnow()` fallback in `backfill_runner.py`
- `SessionNamer.generate_name()` handles None dates with "Unknown Date" placeholder

### Phase 3: Session Type System & Bag Config (PR #17)

- **`my_bag.json`**: User-editable bag config (canonical names, aliases, display order)
- **`utils/bag_config.py`**: Loader with caching, sort keys, alias lookup
- Club Profiles dropdown now ordered by bag config (Driver first) instead of alphabetical
- Session type system (`detect_session_type`, `generate_display_name`) already built in Phase 1

### Stats
- 24 files changed (+3,270 lines)
- 281 tests passing
- Supabase synced (2,159 shots, 4 new columns added to remote schema)

---

## 2026-02-06: UI Simplification & Mobile Optimization

### Dashboard: 5 Tabs to 3
- Removed **Compare** tab (moved session comparison to Club Profiles)
- Removed **Export** tab (replaced with single "Export Session CSV" download button on Overview)
- Removed redundant Big 3 summary from Overview (lives in Big 3 Deep Dive tab)
- Removed carry box plot from Overview (dispersion plot covers it)
- Trimmed Overview metrics from 5 to 3: Total Shots, Avg Carry, Avg Smash

### Settings: 5 Tabs to 3
- Merged **Import + Sessions** → **Data** tab
- Merged **Data Quality + Sync** → **Maintenance** tab
- **Tags** tab unchanged

### Journal Cards Tightened
- Metrics: 3 columns → 2 (dropped Best Carry, kept Avg Carry + Smash Factor)
- Big 3: 3-column HTML blocks → single inline line: `Face: Moderate | Path: Consistent | Strike: Scattered`
- Net -47 lines in journal_card.py

### Home Page Mobile Fixes
- Hero stats: `st.columns(4)` → 2x2 grid (`st.columns(2)` × 2 rows)
- Calendar strip: Fixed-width cells → flexbox with `min(18px, 3%)` for responsive width

### Club Profiles Enhancements
- Club selector moved from sidebar to main content area
- Added **"Compare Sessions for This Club"** expander (side-by-side session metrics)
- Radar chart: Auto-selected 5 clubs → user multiselect with `max_selections=3`

### Compact Layout Toggle
- Added `is_compact_layout()` and `render_compact_toggle()` to `utils/responsive.py`
- Toggle appears in sidebar below data source

### DRY Refactors
- Date parsing: Extracted `utils/date_helpers.py` from 3 files (journal_card, journal_view, calendar_strip)
- Big 3 thresholds: Extracted `utils/big3_constants.py` from 2 files (journal_card, big3_summary)

### Dead Code Removed
- Deleted 4 unused components: `session_list.py`, `simple_view.py`, `coach_export.py`, `session_header.py` (1,291 lines)

### Stats
- 23 files changed (+1,008 / -1,838 lines) — net 830 lines lighter
- 202 tests passing

---

## 2026-02-06: UI/UX Redesign — Practice Journal with Big 3 Impact Laws

### Complete Redesign
Transformed the app from a database admin tool into a **golf practice journal** built around **Adam Young's Big 3 Impact Laws** (Face Angle, Club Path, Strike Location).

### New Page Structure
| Page | Purpose |
|------|---------|
| `app.py` | Journal home — rolling 4-week view with calendar strip, session cards, Big 3 per session |
| `pages/1_📊_Dashboard.py` | 5-tab analytics (later simplified to 3 — see 2026-02-06 simplification) |
| `pages/2_🏌️_Club_Profiles.py` | Per-club deep dives with hero stats, distance trends, Big 3 tendencies |
| `pages/3_🤖_AI_Coach.py` | Chat interface with provider selection (unchanged, renumbered) |
| `pages/4_⚙️_Settings.py` | Merged Data Import + Database Manager (later simplified to 3 tabs) |

### Deleted Pages (merged into new structure)
- `pages/1_📥_Data_Import.py` → merged into Settings
- `pages/2_📊_Dashboard.py` → replaced by new Dashboard
- `pages/3_🗄️_Database_Manager.py` → merged into Settings
- `pages/5_🔄_Session_Compare.py` → merged into Dashboard Compare tab

### New Components (12)
- **`components/journal_card.py`** — Session entry card with Big 3 summary, metrics, trend arrows
- **`components/journal_view.py`** — Rolling view grouped by week ("This Week", "Last Week", etc.)
- **`components/calendar_strip.py`** — Horizontal date strip with dots on practice days (HTML/CSS)
- **`components/big3_summary.py`** — Color-coded Big 3 indicator panel (green/yellow/red thresholds)
- **`components/big3_detail_view.py`** — Full tabbed Big 3 deep dive (Face, Path, D-Plane, Strike)
- **`components/face_path_diagram.py`** — D-plane scatter plot (Face Angle vs Club Path with quadrants)
- **`components/direction_tendency.py`** — Face/path histograms + shot shape donut chart
- **`components/club_hero.py`** — Club profile hero card (total shots, avg carry, personal best, smash)
- **`components/club_trends.py`** — Per-club distance + Big 3 trend line charts

### Data Foundation Fixes
- **`golf_db.py`**: Fixed `clean_value()` converting 99999 sentinel → 0.0 instead of NULL (was corrupting all averages). Now returns `None` for invalid values.
- **`golf_db.py`**: Added `face_to_path` and `strike_distance` derived columns, computed on ingest and backfilled for all 2041 existing shots
- **`golf_db.py`**: Added `session_stats` cache table — pre-computed per-session aggregates eliminating N+1 query pattern
- **`golf_db.py`**: Added composite indexes: `idx_shots_session_club`, `idx_shots_date_club`
- **`services/data_access.py`**: New query functions with `@st.cache_data`: `get_recent_sessions_with_stats()`, `get_club_profile()`, `get_rolling_averages()`

### Date Display Fixes
- **`components/journal_card.py`**: Added `_parse_session_date()` + `_format_session_date()` — formats raw ISO datetime strings to clean "Jan 28" display
- **`components/journal_view.py`**: Added date parsing for week grouping logic
- **`components/calendar_strip.py`**: Added `_normalize_practice_dates()` to handle mixed date formats

### Date Extraction
- Ran `--from-listing --auto-backfill` extraction from Uneekor portal listing page
- Scraped 106 sessions across 25 pages, 96 got dates from DOM headers
- Result: 2041/2041 shots now have accurate `session_date` (was 2020/2041)

### Other Changes
- **`components/shared_sidebar.py`**: Updated navigation links for new 4-page structure
- **`.github/workflows/ci.yml`**: Added `components/*.py` and `pages/*.py` lint steps
- **`components/face_path_diagram.py`**: Fixed NaN bug — always compute `face_angle - club_path` from raw columns instead of potentially-null `face_to_path` column

### Tests
- Added `tests/unit/test_data_foundation.py` — tests for `clean_value()`, derived columns, session stats
- 202 tests passing across unit, integration, and e2e suites

### Stats
- 157 files changed (+37,003 / -3,438 lines)
- 12 new components, 4 new pages, 2 test files

---

## 2026-02-05: Session Naming System & Backfill Pipeline

### New Feature: Distribution-Based Session Naming
- **automation/naming_conventions.py**: Added `detect_session_type(clubs)` to `SessionNamer` — classifies sessions by club distribution (>60% threshold): Driver Focus, Iron Work, Short Game, Woods Focus, Mixed Practice, Warmup
- **automation/naming_conventions.py**: Added `generate_display_name(session_date, clubs)` — produces names like `"2026-01-25 Mixed Practice (47 shots)"`
- Handles None dates ("Unknown Date" placeholder), string dates (YYYY-MM-DD and ISO), and datetime objects

### New Feature: Batch Session Rename
- **golf_db.py**: Added `batch_update_session_names()` — retroactively generates display names for all imported sessions using their shot data

### Backfill Pipeline Execution
- Imported 12 sessions (564 shots) from Jan 2025 onwards
- Used SQLite-only import + batch Supabase sync for efficiency (31s import + 20s sync vs 30+ min per-shot sync)
- 41 total sessions now have meaningful display names

### Research Phase (4 Parallel Agents)
- `docs/research/portal-naming-patterns.md` — Portal names are useless ("Open"/None)
- `docs/research/date-inconsistencies.md` — 2 date formats, 226 wrong-date shots, report_page unreliable
- `docs/research/club-naming-variations.md` — 82% of club values are session names, not club names
- `docs/research/codebase-gap-analysis.md` — SessionContextParser dead code, UI metadata disconnect
- `docs/research/SYNTHESIS.md` — Unified naming schema with 4-phase roadmap

### Tests
- 12 new tests for `detect_session_type` and `generate_display_name`
- All 183 tests pass

### Data Status
- SQLite: 2,020 shots | Supabase: 2,020 shots | No drift
- 41 imported sessions with meaningful names
- 77 pending sessions remaining

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
