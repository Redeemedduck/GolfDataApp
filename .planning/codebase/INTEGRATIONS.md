# External Integrations

**Analysis Date:** 2026-02-09

## APIs & External Services

**Google Gemini API:**
- Service: Gemini 3.0 (Flash and Pro models)
- What it's used for: Cloud-based AI golf coaching with function calling
- SDK/Client: `google-generativeai` Python package
- Auth: `GEMINI_API_KEY` environment variable
- Implementation: `gemini_coach.py` (GeminiCoach class)
- Model options:
  - `gemini-3.0-flash-preview` (fast, cost-effective, $0.50/$3 per 1M tokens)
  - `gemini-3.0-pro-preview` (complex reasoning, $2.50/$10 per 1M tokens)
- Features: Function calling for dynamic data access, multi-turn conversations, flexible thinking levels
- Status: Optional - AI Coach page will not load without API key, but rest of app functions

**Uneekor Portal (Launch Monitor Data Source):**
- Service: Uneekor web portal at `https://my.uneekor.com`
- What it's used for: Web scraping golf shot session data
- SDK/Client: Playwright-based browser automation (no official SDK)
- Auth: Uneekor username/password + optional persistent cookies
  - Username/password: `UNEEKOR_USERNAME`, `UNEEKOR_PASSWORD` env vars
  - Cookies: Encrypted storage via `automation/credential_manager.py`
- Implementation: `automation/uneekor_portal.py` (UneekorPortalNavigator class)
- Entry point: `automation/session_discovery.py` (SessionDiscovery orchestration)
- Rate limiting: 6 requests/minute (token bucket in `automation/rate_limiter.py`)
- Features:
  - Session discovery and listing
  - Report URL extraction
  - Session metadata parsing (report_id, api_key)
  - Headless automation with cookie persistence
- Status: Core feature (required for data import)

**Slack Webhooks:**
- Service: Slack incoming webhooks for notifications
- What it's used for: Alerting on automation events (import complete, backfill progress, errors)
- SDK/Client: Direct HTTP POST via `requests` library
- Auth: `SLACK_WEBHOOK_URL` environment variable
  - Format: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`
- Implementation: `automation/notifications.py` (NotificationManager class)
- Features:
  - Structured message formatting with blocks
  - Rate limiting (20 notifications/hour by default)
  - Quiet hours support (configurable)
  - Multiple notification types: import complete, backfill progress, daily summary, errors
- Status: Optional - notifications gracefully disabled if webhook not configured

## Data Storage

**Databases:**

**SQLite (Local-First):**
- Type: File-based relational database
- Connection: `golf_stats.db` in project root
- Client: `sqlite3` (Python standard library)
- Features:
  - WAL mode enabled for concurrent read/write
  - Schema migrations handled dynamically via `PRAGMA table_info`
  - Soft deletes via `shots_archive` table for recovery
- Primary tables:
  - `shots` - Main shot data (30+ fields: carry, total, smash, impact position, etc.)
  - `shots_archive` - Soft-deleted shots for recovery
  - `change_log` - Audit trail (local only, not synced)
  - `tag_catalog` - User-defined shot tags
  - `sessions_discovered` - Automation discovery state
  - `automation_runs` - Run-level tracking
  - `backfill_runs` - Backfill checkpoint progress
- Schema: See `golf_db.py` `init_db()` function

**Supabase (PostgreSQL Cloud Sync - Soft Dependency):**
- Type: PostgreSQL-based cloud database
- Connection: Via Supabase client SDK
  - URL: `SUPABASE_URL` env var
  - Key: `SUPABASE_KEY` env var (service role for automation)
- Client: `supabase` Python SDK
- Sync behavior:
  - Writes: All shot data written to both SQLite and Supabase (if configured)
  - Reads: Configurable via `set_read_mode()` - "auto" (local first), "sqlite" (local only), "supabase" (cloud only)
  - Cloud Run detection: Forces `"supabase"` read mode if `K_SERVICE` env var present
- Features:
  - Upsert semantics for idempotent imports
  - RLS (Row-Level Security) policies for service role access
  - Views for common queries
  - Async-compatible (uses thread executor in places)
- Optional: If credentials missing, app works entirely on SQLite
- Canonical schema: `supabase_schema.sql` (all tables, indexes, RLS policies)

**File Storage:**
- Storage: Local filesystem only (no cloud file storage)
- Locations:
  - Excel exports: Generated in temp directory, served via Streamlit download widget
  - Impact/swing images: Stored in SQLite as URLs (pointing to Uneekor portal)
  - ML models: Serialized to disk via `joblib`

**Caching:**
- Framework: Streamlit's `@st.cache_data()` decorator for session-scoped caching
- Usage:
  - `get_unique_sessions_cached()` in `app.py`
  - `get_session_data_cached()` in `app.py`
  - Page-level cached queries to reduce database load
- Not distributed: Cache is in-process, resets on app reload

## Authentication & Identity

**Auth Provider:**
- Type: No centralized auth system; application-level credentials
  - Uneekor portal credentials passed to Playwright (username/password)
  - Supabase uses service role (public anon key + secret key)
  - Gemini uses API key directly
- Implementation: `automation/credential_manager.py`
  - Encrypts/decrypts Uneekor credentials for persistent storage
  - Uses `cryptography` library for symmetric encryption
  - Cookies stored in `~/.golfdata/credentials/`

## Monitoring & Observability

**Error Tracking:**
- Solution: Not integrated
- Local logging: Console and file logging via `automation/notifications.py`

**Logs:**
- Approach: Dual logging (console + file)
  - File location: `logs/notifications.jsonl` (JSONL format for structured logging)
  - Console: Stdout/stderr
- Structured logging: `observability.py` module (minimal implementation)
- Feature: Notification log entries track channel, timestamp, level (debug/info/warning/error/critical)

## CI/CD & Deployment

**Hosting:**
- Deployment platform: Google Cloud Run (detects via `K_SERVICE` env var)
- Local development: Streamlit dev server via `streamlit run app.py`

**CI Pipeline:**
- Service: GitHub Actions (`.github/workflows/ci.yml`)
- Triggers: Push to main/develop, PR to main
- Jobs:
  1. **test** - Python 3.10, 3.11, 3.12
     - Install deps from requirements.txt
     - Lint with `py_compile`
     - Run `unittest discover -s tests`
  2. **validate-ml** - Post-test validation
     - Verify ML modules import: DistancePredictor, ShotShapeClassifier, SwingFlawDetector
     - Verify LocalCoach instantiates
     - Verify AI provider registry loads

## Environment Configuration

**Required env vars (with defaults/fallbacks):**

| Variable | Purpose | Required | Default |
|----------|---------|----------|---------|
| `GEMINI_API_KEY` | Google Gemini API access | No* | None (AI Coach unavailable) |
| `SUPABASE_URL` | Cloud database URL | No | None (local SQLite only) |
| `SUPABASE_KEY` | Cloud database key | No | None (local SQLite only) |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | No | None (console/file logging only) |
| `SLACK_CHANNEL` | Override Slack default channel | No | Workspace default |
| `SLACK_USERNAME` | Slack bot name | No | "GolfDataApp Bot" |
| `USE_SUPABASE_READS` | Force cloud reads in containers | No | "0" (auto mode) |
| `UNEEKOR_USERNAME` | Uneekor portal login | No | Prompt interactively |
| `UNEEKOR_PASSWORD` | Uneekor portal password | No | Prompt interactively |
| `GOLFDATA_LOGGING` | Structured logging | No | "0" (disabled) |
| `K_SERVICE` | Cloud Run detection | Auto | None |

*No = app functions, specific feature unavailable
*See `.env.example` or project CLAUDE.md for full list

**Secrets location:**
- Method: `python-dotenv` reads `.env` file (not committed, in .gitignore)
- Uneekor credentials: Encrypted via `automation/credential_manager.py`
  - Stored: `~/.golfdata/credentials/` (user home directory)
  - Cipher: Symmetric encryption with hardcoded derivation
- API keys: Environment variables only (never logged or written to disk)

## Webhooks & Callbacks

**Incoming:**
- None - Application is data consumer, not webhook responder

**Outgoing:**
- Slack webhooks: `automation/notifications.py` sends POST requests to Slack
  - Triggered on: Import complete, backfill progress, daily summary, errors
  - Format: JSON block kit messages
  - Rate limited: 20 per hour (configurable)
  - Async-wrapped: Uses `asyncio.run_in_executor()` to run `requests.post()` in thread pool

## Data Flow: Import Pipeline

```
Uneekor Portal
    ↓
Playwright Browser Automation (automation/browser_client.py)
    ↓
UneekorPortalNavigator (automation/uneekor_portal.py)
    ↓
SessionDiscovery (automation/session_discovery.py)
    ↓
BackfillRunner (automation/backfill_runner.py)
    ↓
golf_db.import_session() - Write to SQLite + Supabase
    ↓
SQLite + Supabase (dual write)
    ↓
Slack Notification (automation/notifications.py)
```

Rate limiting at `UneekorPortalNavigator` level (6 req/min by default).
Exponential backoff on retries: 10s → 30s → 90s.

---

*Integration audit: 2026-02-09*
