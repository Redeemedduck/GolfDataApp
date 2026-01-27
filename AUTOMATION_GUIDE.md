# Golf Data Pipeline - Automation Guide

This guide explains how to use the scraper automation system for hands-free data import from Uneekor.

---

## Quick Start

### Option 1: First-Time Setup (Recommended)

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Interactive login to save cookies
python automation_runner.py login

# 3. Discover sessions from portal
python automation_runner.py discover --headless

# 4. Check status
python automation_runner.py status
```

### Option 2: Historical Backfill

Import all your past sessions:

```bash
# Backfill from January 2025
python automation_runner.py backfill --start 2025-01-01

# Check progress
python automation_runner.py backfill --status

# Resume if paused
python automation_runner.py backfill --resume
```

---

## Understanding the Automation System

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  automation_runner.py                    │
│                    (CLI Interface)                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   automation/                            │
├─────────────────────────────────────────────────────────┤
│  credential_manager.py  │  Cookie persistence           │
│  rate_limiter.py        │  Request throttling           │
│  browser_client.py      │  Playwright browser           │
│  uneekor_portal.py      │  Portal navigation            │
│  session_discovery.py   │  Find & track sessions        │
│  naming_conventions.py  │  Standardize names            │
│  backfill_runner.py     │  Historical import            │
│  notifications.py       │  Slack alerts                 │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              golf_scraper.py + golf_db.py               │
│                (Existing Import System)                  │
└─────────────────────────────────────────────────────────┘
```

### How It Works

1. **Browser Automation**: Playwright controls a headless Chrome browser
2. **Login & Cookies**: First login saves encrypted cookies for future use
3. **Session Discovery**: Navigate Uneekor portal to find available sessions
4. **Deduplication**: Check database to avoid re-importing existing data
5. **Rate Limiting**: Conservative request timing to avoid being blocked
6. **Import**: Use existing `golf_scraper.py` to fetch data via API
7. **Normalization**: Standardize club names and generate session metadata

---

## CLI Commands

### `login` - Interactive Login

Opens a browser window for manual login. Saves cookies for future automated runs.

```bash
python automation_runner.py login
```

**When to use**: First time setup, or when cookies expire (every 7 days).

### `discover` - Find Sessions

Discover sessions from the Uneekor portal and save to tracking database.

```bash
# Interactive mode (shows browser)
python automation_runner.py discover

# Headless mode (uses saved cookies)
python automation_runner.py discover --headless

# Limit number of sessions
python automation_runner.py discover --max 50

# Only sessions since a date
python automation_runner.py discover --since 2025-06-01
```

### `backfill` - Historical Import

Import historical sessions with rate limiting and checkpointing.

```bash
# Start new backfill
python automation_runner.py backfill --start 2025-01-01

# With end date
python automation_runner.py backfill --start 2025-01-01 --end 2025-06-30

# Limit sessions per run
python automation_runner.py backfill --start 2025-01-01 --max 20

# Check status
python automation_runner.py backfill --status

# Resume paused backfill
python automation_runner.py backfill --resume

# Skip club normalization
python automation_runner.py backfill --start 2025-01-01 --no-normalize

# Skip auto-tagging
python automation_runner.py backfill --start 2025-01-01 --no-tags
```

### `status` - Check Automation Status

Show current state of credentials, discovery, and backfill.

```bash
python automation_runner.py status
```

Output example:
```
============================================================
AUTOMATION STATUS
============================================================

Credentials:
  Environment variables: No
  Stored cookies:        Yes
  Cookies valid:         Yes
  Cookies expire:        2026-02-01T12:00:00
  Auth method:           cookies

Sessions discovered:
  pending: 15
  imported: 85
  Total shots imported: 4250

Recent backfill runs:
  bf_a1b2c3d4: completed (85 sessions)

Notifications:
  Slack configured: Yes
  Console logging:  Yes
  File logging:     Yes
```

### `notify` - Test Notifications

Send a test notification to verify Slack setup.

```bash
python automation_runner.py notify "Test message"
python automation_runner.py notify "Error test" --level error
```

### `normalize` - Test Club Names

Preview how club names will be normalized.

```bash
python automation_runner.py normalize --test "7i,DR,pw,56 deg"
```

Output:
```
Normalization preview:
  '7i' -> '7 Iron' (95%)
  'DR' -> 'Driver' (95%)
  'pw' -> 'PW' (95%)
  '56 deg' -> 'SW' (90%)
```

### `reclassify-dates` - Session Date Management

Manage and fix session dates in your database. Session dates are the actual dates when practice sessions occurred (vs. `date_added` which is when data was imported).

```bash
# Check date status
python automation_runner.py reclassify-dates --status

# Backfill dates from sessions_discovered to shots table
python automation_runner.py reclassify-dates --backfill

# Scrape dates from Uneekor report pages (slow, rate-limited)
python automation_runner.py reclassify-dates --scrape --max 10 --delay 300

# Set date manually for a specific session
python automation_runner.py reclassify-dates --manual 43285 2026-01-15

# Preview what would change (dry run)
python automation_runner.py reclassify-dates --scrape --dry-run
```

**Options:**
| Option | Description |
|--------|-------------|
| `--status` | Show summary of sessions with/without dates |
| `--backfill` | Copy dates from sessions_discovered to shots table |
| `--scrape` | Navigate to report pages and extract dates (slow) |
| `--manual REPORT_ID DATE` | Set date for a specific session |
| `--max N` | Maximum sessions to scrape (default: 20) |
| `--delay N` | Seconds between scrapes (default: 300 = 5 min) |
| `--headless` | Run browser in headless mode |
| `--dry-run` | Preview without making changes |

**When to use each option:**
- `--backfill`: After import, to copy dates from portal to shots
- `--scrape`: For sessions missing dates (extracts from report page headers)
- `--manual`: When you know the correct date and want to fix it quickly

---

## Rate Limiting Explained

### Why Conservative Rate Limits?

The automation uses conservative rate limiting to avoid being blocked by Uneekor:

| Setting | Value | Explanation |
|---------|-------|-------------|
| Requests/min | 6 | One request every 10 seconds |
| Burst size | 2 | Can do 2 quick requests, then wait |
| Jitter | 0-4 sec | Random delay for natural patterns |
| Backoff | 2x | Double wait time on errors |

### Time Estimates

| Sessions | Time (6 req/min) | Time (10 req/min) |
|----------|------------------|-------------------|
| 10 | ~2 minutes | ~1 minute |
| 50 | ~10 minutes | ~6 minutes |
| 100 | ~20 minutes | ~12 minutes |
| 500 | ~1.5 hours | ~1 hour |

### Why Not Faster?

- Uneekor's rate limits are not documented
- Being blocked = no data at all
- Historical backfill is a one-time operation
- Slow and steady is more reliable

---

## Cookie Persistence

### How Cookies Work

1. **First Login**: You log in manually via browser
2. **Save**: Browser cookies are encrypted and saved locally
3. **Restore**: Future runs restore the session automatically
4. **Expiry**: Cookies expire after 7 days (configurable)

### Cookie Security

- Cookies are encrypted with Fernet (AES-128)
- Encryption key stored separately (`.uneekor_key`)
- Both files excluded from git via `.gitignore`
- Cloud Run uses environment variables instead

### Files Created

```
.uneekor_cookies.enc    # Encrypted cookies
.uneekor_key            # Encryption key
```

### Troubleshooting Cookies

```bash
# Check cookie status
python automation_runner.py status

# Force fresh login
python automation_runner.py login

# Clear cookies manually
rm .uneekor_cookies.enc .uneekor_key
```

---

## Club Name Normalization

### Standard Names

The system normalizes club names to consistent formats:

| Category | Standard Names |
|----------|---------------|
| Woods | Driver, 3 Wood, 5 Wood, 7 Wood |
| Hybrids | 3 Hybrid, 4 Hybrid, 5 Hybrid |
| Irons | 3 Iron, 4 Iron, 5 Iron, 6 Iron, 7 Iron, 8 Iron, 9 Iron |
| Wedges | PW, GW, AW, SW, LW |
| Putter | Putter |

### Normalization Examples

| Input | Output |
|-------|--------|
| `7i`, `7 iron`, `Iron 7`, `7-iron` | `7 Iron` |
| `DR`, `driver`, `1W`, `1 wood` | `Driver` |
| `pw`, `pitching wedge`, `46 deg` | `PW` |
| `sw`, `sand wedge`, `54 deg`, `56 deg` | `SW` |
| `lw`, `lob wedge`, `58 deg`, `60 deg` | `LW` |

### Disable Normalization

```bash
python automation_runner.py backfill --start 2025-01-01 --no-normalize
```

---

## Session Naming & Auto-Tagging

### Session Name Patterns

| Type | Pattern | Example |
|------|---------|---------|
| Practice | `Practice - {date}` | Practice - Jan 25, 2026 |
| Drill | `Drill - {focus} - {date}` | Drill - Driver - Jan 25, 2026 |
| Round | `{course} Round - {date}` | Pebble Beach Round - Jan 25, 2026 |
| Fitting | `Fitting - {club} - {date}` | Fitting - Driver - Jan 25, 2026 |
| Warmup | `Warmup - {date}` | Warmup - Jan 25, 2026 |

### Session Type Inference

The system infers session type from characteristics:

| Condition | Inferred Type |
|-----------|---------------|
| <10 shots | Warmup |
| 1-2 clubs, >30 shots | Drill |
| 1 club, >50 shots | Fitting |
| 3+ clubs | Practice |

### Auto-Tagging Rules

| Condition | Tag |
|-----------|-----|
| Only Driver used | `Driver Focus` |
| Only wedges used | `Short Game` |
| 10+ clubs used | `Full Bag` |
| 100+ shots | `High Volume` |
| <10 shots | `Warmup` |
| All irons (3+ clubs) | `Iron Work` |
| Multiple woods | `Woods Focus` |

### Disable Auto-Tagging

```bash
python automation_runner.py backfill --start 2025-01-01 --no-tags
```

---

## Slack Notifications

### Setup

1. Go to https://api.slack.com/apps
2. Create new app or use existing
3. Enable "Incoming Webhooks"
4. Add webhook to your workspace
5. Copy webhook URL

### Configuration

Add to `.env`:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX
# Optional overrides
SLACK_CHANNEL=#golf-data
SLACK_USERNAME=GolfDataApp Bot
```

### Test Notification

```bash
python automation_runner.py notify "Test message"
```

### Notification Events

- Import completed (session count, shot count)
- Backfill progress (every N sessions)
- Errors (failed imports, rate limiting)

---

## Environment Variables

### Required for Automated Login

```bash
UNEEKOR_USERNAME=your_email@example.com
UNEEKOR_PASSWORD=your_password
```

### Optional Configuration

```bash
# Cookie encryption (auto-generated if not set)
UNEEKOR_COOKIE_KEY=your-32-byte-key

# Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SLACK_CHANNEL=#golf-data

# Notification settings
NOTIFICATION_CONSOLE=true
NOTIFICATION_LOG=true
```

---

## Database Tables

The automation system creates additional tables. All tables exist in both SQLite (local) and Supabase (cloud) — see `supabase_schema.sql` for the canonical Postgres schema.

### `sessions_discovered`

Tracks all discovered sessions and their import status.

```sql
CREATE TABLE sessions_discovered (
    report_id TEXT PRIMARY KEY,
    api_key TEXT,
    portal_name TEXT,
    session_date TIMESTAMP,      -- Actual session date
    date_source TEXT,            -- Where date came from: 'portal', 'report_page', 'manual'
    import_status TEXT,          -- pending, imported, skipped, failed, needs_review
    import_shots_actual INTEGER,
    session_name TEXT,
    session_type TEXT,
    tags_json TEXT,
    attempt_count INTEGER,       -- Number of import attempts
    last_attempt_at TIMESTAMP
);
```

### `shots` (session_date column)

The shots table now includes session_date for accurate trend analysis:

```sql
-- Key date fields in shots table
session_date TIMESTAMP,   -- When the session actually occurred
date_added TIMESTAMP      -- When the data was imported (auto-set)
```

### `automation_runs`

Logs automation run history.

```sql
CREATE TABLE automation_runs (
    run_id TEXT PRIMARY KEY,
    run_type TEXT,  -- discovery, backfill, scheduled
    status TEXT,
    sessions_imported INTEGER,
    total_shots_imported INTEGER,
    duration_seconds REAL
);
```

### `backfill_runs`

Tracks backfill progress for checkpoint/resume.

```sql
CREATE TABLE backfill_runs (
    run_id TEXT PRIMARY KEY,
    status TEXT,  -- running, paused, completed
    sessions_processed INTEGER,
    last_processed_report_id TEXT
);
```

---

## Example Workflows

### Workflow 1: First-Time Full Import

```bash
# 1. Setup
pip install -r requirements.txt
playwright install chromium

# 2. Login
python automation_runner.py login

# 3. Discover all sessions
python automation_runner.py discover --headless

# 4. Import all historical data
python automation_runner.py backfill --start 2024-01-01

# 5. Check results
python automation_runner.py status
```

### Workflow 2: Regular Updates

```bash
# After each practice session
python automation_runner.py discover --headless --max 10

# Or set up a cron job (every 6 hours)
0 */6 * * * cd /path/to/GolfDataApp && python automation_runner.py discover --headless --max 20
```

### Workflow 3: Resume Failed Backfill

```bash
# Check what happened
python automation_runner.py backfill --status

# Resume from checkpoint
python automation_runner.py backfill --resume
```

### Workflow 4: Fix Missing Session Dates

After importing data, some sessions may be missing accurate dates. This workflow fixes them:

```bash
# 1. Check current date status
python automation_runner.py reclassify-dates --status

# 2. First, copy any dates already in sessions_discovered to shots
python automation_runner.py reclassify-dates --backfill

# 3. For remaining sessions, scrape dates from report pages
python automation_runner.py reclassify-dates --scrape --max 10 --delay 300

# 4. For known dates, set manually (faster than scraping)
python automation_runner.py reclassify-dates --manual 43285 2026-01-15

# 5. Verify results
python automation_runner.py reclassify-dates --status
```

**Why session dates matter:**
- Trend charts need accurate dates to show improvement over time
- Session filtering by date requires actual session dates
- Analytics rely on session_date, not import timestamp (date_added)

---

## Troubleshooting

### "No credentials available"

```bash
# Solution 1: Run interactive login
python automation_runner.py login

# Solution 2: Set environment variables
export UNEEKOR_USERNAME=your_email
export UNEEKOR_PASSWORD=your_password
```

### "Cookies expired"

```bash
# Re-run interactive login
python automation_runner.py login
```

### "Rate limited by Uneekor"

The system handles this automatically with exponential backoff. If persistent:

```bash
# Wait 30 minutes and resume
python automation_runner.py backfill --resume
```

### "Session already imported"

This is normal - the deduplication system is working correctly. The session will be skipped.

### "Playwright browser not found"

```bash
playwright install chromium
```

### Viewing Logs

```bash
# Notification logs
cat logs/notifications.jsonl

# View recent entries
tail -20 logs/notifications.jsonl
```

---

## Cloud Run Deployment

For Cloud Run, browser automation runs headless with environment credentials:

```bash
# Set secrets in Cloud Run
gcloud run deploy golf-data-app \
  --set-secrets="UNEEKOR_USERNAME=uneekor-username:latest" \
  --set-secrets="UNEEKOR_PASSWORD=uneekor-password:latest" \
  --set-secrets="SLACK_WEBHOOK_URL=slack-webhook:latest"
```

The Dockerfile already includes Playwright dependencies.

---

## Legacy Automation (BigQuery Sync)

For BigQuery data pipeline automation, see the scripts in `scripts/`:

```bash
# Post-session analysis
python scripts/post_session.py

# Auto sync
python scripts/auto_sync.py

# Manual sync to BigQuery
python scripts/supabase_to_bigquery.py incremental
```

---

## Command Quick Reference

```bash
# Login (saves cookies)
python automation_runner.py login

# Discover sessions
python automation_runner.py discover --headless

# Historical backfill
python automation_runner.py backfill --start 2025-01-01

# Check status
python automation_runner.py status

# Resume backfill
python automation_runner.py backfill --resume

# Retry failed imports
python automation_runner.py backfill --retry-failed

# Preview backfill without importing
python automation_runner.py backfill --start 2025-01-01 --dry-run

# Filter by clubs
python automation_runner.py backfill --start 2025-01-01 --clubs "Driver,7 Iron"

# Test notification
python automation_runner.py notify "Test"

# Test club normalization
python automation_runner.py normalize --test "7i,DR,pw"

# Date reclassification
python automation_runner.py reclassify-dates --status
python automation_runner.py reclassify-dates --backfill
python automation_runner.py reclassify-dates --scrape --max 10
python automation_runner.py reclassify-dates --manual 43285 2026-01-15
```

---

**Last Updated**: 2026-01-26
