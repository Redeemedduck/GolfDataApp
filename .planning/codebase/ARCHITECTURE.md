# Architecture

**Analysis Date:** 2026-02-09

## Pattern Overview

**Overall:** Local-first hybrid architecture with multi-layered separation of concerns

**Key Characteristics:**
- SQLite primary storage (local-first) with optional Supabase cloud sync
- Plugin-based AI provider system with graceful degradation
- Lazy-loaded ML modules for optional advanced features
- Async/await orchestration for browser automation and API calls
- WAL (Write-Ahead Logging) mode for concurrent SQLite access
- Soft-delete pattern with archival for data recovery

## Layers

**Data Access Layer:**
- Purpose: Abstract database operations and read mode selection (auto/sqlite/supabase)
- Location: `golf_db.py`
- Contains: SQLite/Supabase clients, CRUD operations, data merging logic, migration handlers
- Depends on: sqlite3, supabase SDK, exceptions
- Used by: All pages, coaches, automation, and scrapers

**Business Logic Layer:**
- Purpose: Core domain operations specific to golf analytics
- Location: `local_coach.py`, `gemini_coach.py`, `golf_scraper.py`
- Contains: Intent detection, template-based coaching, scraping logic, data extraction
- Depends on: golf_db, services.ai, ml (optional), exceptions
- Used by: Streamlit pages, automation workflows

**Automation Layer:**
- Purpose: Orchestrate Uneekor portal interaction, session discovery, and backfill
- Location: `automation/`
- Contains: Browser client, session discovery state machine, backfill orchestrator, rate limiting
- Depends on: golf_db, golf_scraper, Playwright, encryption for cookies
- Used by: automation_runner.py CLI, backfill scheduling

**AI Provider Registry:**
- Purpose: Pluggable AI backends with self-registration
- Location: `services/ai/registry.py` and `services/ai/providers/`
- Contains: Provider specs, decorator-based registration, loader
- Depends on: Provider implementations (local, gemini)
- Used by: Local coach, Gemini coach, AI coach page

**ML Module (Optional):**
- Purpose: Advanced predictive features and anomaly detection
- Location: `ml/`
- Contains: Distance predictor, shot shape classifier, swing flaw detector
- Depends on: sklearn, XGBoost (lazy-loaded via __getattr__)
- Used by: Local coach (graceful fallback if ML unavailable)

**UI Layer:**
- Purpose: Streamlit pages and reusable components
- Location: `app.py` (landing), `pages/` (multi-page), `components/`
- Contains: Session management, visualization, data export, navigation
- Depends on: golf_db, coaches, components
- Used by: End users

## Data Flow

**Session Import Flow:**
1. User pastes Uneekor URL in Data Import page (`pages/1_📥_Data_Import.py`)
2. `golf_scraper.run_scraper()` extracts shots from Uneekor API
3. For each shot: `golf_db.save_shot()` writes to SQLite
4. On save: Supabase sync happens (if configured) via upsert
5. Images uploaded to storage if available
6. `observability.append_event()` logs import to `import_runs.jsonl`
7. Streamlit cache invalidated via `st.cache_data.clear()`

**Backfill Flow:**
1. `automation_runner.py backfill --start YYYY-MM-DD` invokes `BackfillRunner`
2. `SessionDiscovery` finds sessions on Uneekor portal (Playwright-based)
3. `BackfillRunner` enforces rate limits via `RateLimiter` (token bucket)
4. For each session: `golf_scraper.run_scraper()` fetches and saves shots
5. Progress checkpointed to `backfill_runs` table every N sessions
6. Failures logged and retried with exponential backoff (10s → 30s → 90s)
7. Notifications sent on completion or error

**Read Mode Logic (auto/sqlite/supabase):**
1. Check `READ_MODE` global (set by `set_read_mode()`)
2. If "auto": Check if SQLite has data. If yes, read SQLite; else read Supabase
3. If "sqlite": Read only from local SQLite
4. If "supabase": Read only from cloud (for containerized/cloud-run deployments)
5. Merge logic in `_merge_shots()` deduplicates by shot_id

**State Management:**
- Session-level: Streamlit `st.session_state` (e.g., `read_mode` dropdown)
- Database-level: SQLite `change_log`, `sessions_discovered`, `backfill_runs` tables
- Browser-level: Encrypted cookies in `credential_manager.py` for Uneekor login
- Event logs: Structured JSON in `logs/` (import_runs.jsonl, sync_runs.jsonl)

## Key Abstractions

**ReadMode (auto/sqlite/supabase):**
- Purpose: Switch data source without code changes
- Examples: `golf_db.get_session_data(read_mode="auto")`, `golf_db.set_read_mode("supabase")`
- Pattern: Global `READ_MODE` variable with `_normalize_read_mode()` validator; fetch logic branches on mode

**AI Provider (Local/Gemini):**
- Purpose: Swap AI backends without changing coach code
- Examples: `services.ai.get_provider("local")`, `services.ai.get_provider("gemini")`
- Pattern: `@register_provider` decorator auto-populates registry; `ProviderSpec` holds class and metadata

**Clean Values (Sentinel Handling):**
- Purpose: Handle Uneekor's "99999" (no data) sentinel
- Examples: `clean_value(99999, default=0.0)` → returns 0.0
- Pattern: Centralized `clean_value()` function; called on shot data import

**Soft Delete Archive:**
- Purpose: Recover accidentally deleted shots without migration rollback
- Examples: Delete shot → moved to `shots_archive` → `restore_deleted_shots(shot_ids)` re-inserts
- Pattern: `delete_shot()` writes to archive before DELETE; `get_archived_shots()` queries archive table

**ML Graceful Degradation:**
- Purpose: Run without ML if sklearn/XGBoost unavailable
- Examples: `local_coach.py` has fallback rules when `HAS_ML=False`
- Pattern: Try-except on imports; `@property ml_available` checks; rule-based logic if ML fails

## Entry Points

**Streamlit App:**
- Location: `app.py` (landing page), `pages/` (multi-page nav)
- Triggers: User opens browser at `localhost:8501`
- Responsibilities: Route to pages, display dashboards, manage read mode UI

**Automation CLI:**
- Location: `automation_runner.py`
- Triggers: User runs `python automation_runner.py <command>`
- Responsibilities: Parse args, invoke discovery/backfill/login, manage async workflows

**Golf Scraper (Legacy + Active):**
- Location: `golf_scraper.py` (legacy), also used by backfill
- Triggers: Data Import page or backfill runner
- Responsibilities: Fetch shot data from Uneekor API, extract fields, validate

**Session Discovery:**
- Location: `automation/session_discovery.py`
- Triggers: Backfill runner or discovery CLI command
- Responsibilities: Navigate Uneekor portal, extract session links, dedup sessions

## Error Handling

**Strategy:** Typed exception hierarchy with context dicts; try-except at boundaries (data layer, UI, automation)

**Patterns:**
- `DatabaseError(msg, operation, table)` for SQL failures → logged and UI-shown
- `ValidationError(msg, field, value)` for invalid shots → added to invalid_shots table for review
- `RateLimitError(msg, retry_after)` for API throttling → waits and retries with backoff
- `AuthenticationError(msg, provider)` for Uneekor login → UI prompts re-login
- `DataImportError(msg, session_id, source)` for import failures → logged to change_log

## Cross-Cutting Concerns

**Logging:** Structured JSON events in `logs/` directory
- `import_runs.jsonl`: {status, shots_imported, duration_sec, timestamp}
- `sync_runs.jsonl`: {status, mode, shots, duration_sec, timestamp}
- `change_log` SQLite table: {timestamp, operation, entity_type, entity_id, details}

**Validation:** Two-stage approach
- Pre-save: `golf_scraper` validates field presence and types
- Post-save: `golf_db.validate_shot_data()` checks for missing critical fields; adds to database for review

**Authentication:**
- Uneekor: Encrypted cookies via `credential_manager.py` (AES-256 via cryptography)
- Supabase: API key in `.env` (environment variable, never hardcoded)
- Gemini: API key in `.env` (environment variable)

---

*Architecture analysis: 2026-02-09*
