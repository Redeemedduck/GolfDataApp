# Automation Architecture Guide

This document provides a comprehensive roadmap for understanding and operating the GolfDataApp automation system that imports shot data from the Uneekor portal.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Data Flow Diagram](#data-flow-diagram)
3. [Component Deep Dive](#component-deep-dive)
4. [Database Schema](#database-schema)
5. [Command Reference](#command-reference)
6. [Common Workflows](#common-workflows)
7. [Troubleshooting](#troubleshooting)
8. [Configuration Reference](#configuration-reference)

---

## System Overview

The automation system performs three core functions:

1. **Discovery**: Finds sessions on the Uneekor portal
2. **Import**: Downloads shot data via CSV API
3. **Tracking**: Maintains state for resumable operations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GolfDataApp Automation System                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────┐  │
│   │   Uneekor   │───>│   Session    │───>│  Backfill   │───>│  SQLite   │  │
│   │   Portal    │    │  Discovery   │    │   Runner    │    │  + Supa   │  │
│   └─────────────┘    └──────────────┘    └─────────────┘    └───────────┘  │
│         │                   │                   │                  │        │
│         │ Playwright        │ sessions_         │ CSV API          │ shots  │
│         │ Browser           │ discovered        │ + Scraper        │ table  │
│         │                   │ table             │                  │        │
│         v                   v                   v                  v        │
│   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌───────────┐  │
│   │  Credential │    │     Rate     │    │   Naming    │    │ Streamlit │  │
│   │   Manager   │    │   Limiter    │    │ Conventions │    │    App    │  │
│   └─────────────┘    └──────────────┘    └─────────────┘    └───────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

### Complete Pipeline

```
                            UNEEKOR PORTAL
                    ┌─────────────────────────┐
                    │  https://my.uneekor.com │
                    │                         │
                    │  ┌───────────────────┐  │
                    │  │  /login           │  │
                    │  │  Email + Password │  │
                    │  └─────────┬─────────┘  │
                    │            │            │
                    │            v            │
                    │  ┌───────────────────┐  │
                    │  │  /report          │  │
                    │  │  Session List     │  │
                    │  │  (Paginated)      │  │
                    │  │                   │  │
                    │  │  Page 1 [1][2]... │  │
                    │  │  Page 2 [1][2]... │  │
                    │  │  ...              │  │
                    │  │  Page N           │  │
                    │  └─────────┬─────────┘  │
                    │            │            │
                    └────────────┼────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │    SESSION DISCOVERY    │
                    │                         │
                    │  For each page:         │
                    │   - Find <a> links      │
                    │   - Extract report_id   │
                    │   - Extract api_key     │
                    │   - Parse session date  │
                    │   - Save to database    │
                    │                         │
                    └────────────┬────────────┘
                                 │
                                 v
        ┌────────────────────────────────────────────────────┐
        │              sessions_discovered TABLE              │
        │                                                    │
        │  report_id │ api_key │ status  │ session_date     │
        │  ──────────┼─────────┼─────────┼────────────────── │
        │  43285     │ abc123  │ pending │ 2026-01-26       │
        │  43166     │ def456  │ pending │ 2026-01-25       │
        │  ...       │ ...     │ ...     │ ...              │
        │                                                    │
        └────────────────────────┬───────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │     BACKFILL RUNNER     │
                    │                         │
                    │  For each pending:      │
                    │   1. Rate limit wait    │
                    │   2. Build import URL   │
                    │   3. Call golf_scraper  │
                    │   4. Update status      │
                    │   5. Checkpoint         │
                    │                         │
                    └────────────┬────────────┘
                                 │
                                 v
                    ┌─────────────────────────┐
                    │      UNEEKOR API        │
                    │                         │
                    │  CSV Export Endpoint:   │
                    │  api-v2.golfsvc.com     │
                    │  /v2/oldmyuneekor/      │
                    │  report/export/         │
                    │  allsessions/{id}/{key} │
                    │  /yard/mph              │
                    │                         │
                    │  Returns: 17 columns    │
                    │  - Club, Ball Speed     │
                    │  - Launch Angle, Spin   │
                    │  - Carry, Total, etc.   │
                    │                         │
                    └────────────┬────────────┘
                                 │
                                 v
        ┌────────────────────────────────────────────────────┐
        │                    shots TABLE                      │
        │                                                    │
        │  30+ fields per shot:                              │
        │  - session_id, shot_number, club                   │
        │  - ball_speed, club_speed, smash_factor            │
        │  - launch_angle, launch_direction                  │
        │  - backspin, sidespin, spin_axis                   │
        │  - carry_distance, total_distance                  │
        │  - apex_height, descent_angle                      │
        │  - offline_distance, curve_distance                │
        │                                                    │
        └────────────────────────────────────────────────────┘
```

### Simplified Flow

```
┌──────────┐   discover   ┌───────────────┐   backfill   ┌────────┐
│  Portal  │ ──────────> │ sessions_disc │ ──────────> │ shots  │
│  (Web)   │             │   (SQLite)    │             │(SQLite)│
└──────────┘             └───────────────┘             └────────┘
     │                          │                           │
     │                          │                           │
     v                          v                           v
  Playwright              Import Queue               Streamlit
  (Browser)              + Status Track              Dashboard
```

---

## Component Deep Dive

### 1. Portal Login and Cookie Persistence

**File:** `automation/credential_manager.py`

The credential manager handles authentication with three modes:

```
┌─────────────────────────────────────────────────────────────┐
│                   AUTHENTICATION FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Method 1: STORED COOKIES (Development)                    │
│   ─────────────────────────────────────────                 │
│   .uneekor_cookies.enc ─────> Fernet Decrypt ─────> Browser │
│                                                             │
│   - Cookies encrypted with symmetric key                    │
│   - Valid for 7 days                                        │
│   - Run `login` command to refresh                          │
│                                                             │
│   Method 2: ENVIRONMENT VARIABLES (Production)              │
│   ─────────────────────────────────────────────             │
│   UNEEKOR_USERNAME ┐                                        │
│   UNEEKOR_PASSWORD ┴─────> Full Login Flow ─────> Browser   │
│                                                             │
│   - Used in Cloud Run (ephemeral storage)                   │
│   - Logs in fresh each time                                 │
│                                                             │
│   Method 3: INTERACTIVE (First-time Setup)                  │
│   ─────────────────────────────────────────                 │
│   Browser opens ─────> User logs in ─────> Cookies saved    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Files:**
- `.uneekor_cookies.enc` - Encrypted cookie storage
- `.uneekor_key` - Encryption key (auto-generated)

**Environment Variables:**
```bash
UNEEKOR_USERNAME=your_email@example.com
UNEEKOR_PASSWORD=your_password
UNEEKOR_COOKIE_KEY=optional_custom_key
```

---

### 2. Session Discovery with Pagination

**File:** `automation/session_discovery.py`, `automation/uneekor_portal.py`

Discovery navigates the portal and extracts session metadata:

```
┌─────────────────────────────────────────────────────────────┐
│                    DISCOVERY PROCESS                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Step 1: Navigate to /report                               │
│   ┌───────────────────────────────────────────────────────┐ │
│   │ Reports                                               │ │
│   │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │ │
│   │ │Session 1 │ │Session 2 │ │Session 3 │ │Session 4 │  │ │
│   │ │ 1/26/26  │ │ 1/25/26  │ │ 1/24/26  │ │ 1/23/26  │  │ │
│   │ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │ │
│   │                                                       │ │
│   │ [1] [2] [3] [4] [5] ... [23]  <- Pagination buttons   │ │
│   └───────────────────────────────────────────────────────┘ │
│                                                             │
│   Step 2: For each page                                     │
│   ─────────────────────                                     │
│   - Find all <a href="report?id=XXXXX&key=YYYYY">          │
│   - Extract report_id and api_key from URL                  │
│   - Parse session name and date from link text              │
│   - Deduplicate (same session can appear multiple times)    │
│   - Click next page button                                  │
│                                                             │
│   Step 3: Save to database                                  │
│   ────────────────────────                                  │
│   - INSERT or UPDATE sessions_discovered                    │
│   - Mark as 'pending' for import                            │
│   - Track clubs_used if visible                             │
│                                                             │
│   URL Pattern Extracted:                                    │
│   ───────────────────────                                   │
│   https://my.uneekor.com/report?id=43285&key=abc123xyz     │
│                                     │         │             │
│                              report_id    api_key           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Discovery Statistics Example:**
```
Page 1: 5 sessions
Page 2: 5 sessions
...
Page 23: 2 sessions
─────────────────
Total: 95 sessions discovered
New:   65 sessions (not seen before)
Known: 30 sessions (already in database)
```

---

### 3. CSV Export API Endpoints

**Files:** `golf_scraper.py`, `automation/uneekor_portal.py`

The Uneekor API provides direct CSV download:

```
┌─────────────────────────────────────────────────────────────┐
│                    API ENDPOINTS                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   BASE URL: https://api-v2.golfsvc.com                      │
│                                                             │
│   ENDPOINT 1: All Sessions CSV (Primary)                    │
│   ──────────────────────────────────────                    │
│   /v2/oldmyuneekor/report/export/allsessions/{id}/{key}/    │
│   yard/mph                                                  │
│                                                             │
│   Returns: CSV with 17 columns                              │
│   ┌────────┬─────────┬─────────┬──────────┬─────────────┐  │
│   │ Club   │ Ball Sp │ Club Sp │ Smash    │ Launch Ang  │  │
│   │ Driver │ 165.2   │ 112.3   │ 1.47     │ 12.5        │  │
│   │ 7 Iron │ 142.1   │ 93.5    │ 1.52     │ 18.2        │  │
│   └────────┴─────────┴─────────┴──────────┴─────────────┘  │
│                                                             │
│   ENDPOINT 2: Single Shot Data                              │
│   ────────────────────────────                              │
│   /v2/oldmyuneekor/report/export/shotdata/{id}/{key}/       │
│   {session}/{shot}/yard/mph                                 │
│                                                             │
│   ENDPOINT 3: Swing Video                                   │
│   ───────────────────────                                   │
│   /v2/oldmyuneekor/report/export/swingoptix/{id}/{key}/     │
│   {session}/{shot}                                          │
│                                                             │
│   Unit Options:                                             │
│   ─────────────                                             │
│   - yard/mph   (imperial - default)                         │
│   - meter/kmh  (metric)                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**CSV Columns (17 fields):**
```
1.  Club             - Club used
2.  Ball Speed       - Ball velocity (mph)
3.  Club Speed       - Club head speed (mph)
4.  Smash Factor     - Efficiency ratio
5.  Launch Angle     - Vertical launch (degrees)
6.  Launch Direction - Horizontal aim (degrees)
7.  Backspin         - Backspin rate (rpm)
8.  Sidespin         - Sidespin rate (rpm)
9.  Spin Axis        - Spin tilt (degrees)
10. Carry            - Carry distance (yards)
11. Total            - Total distance (yards)
12. Apex             - Max height (yards)
13. Descent Angle    - Landing angle (degrees)
14. Offline          - Left/right miss (yards)
15. Curve            - Ball curve amount (yards)
16. Attack Angle     - Club path vertical (degrees)
17. Club Path        - Club path horizontal (degrees)
```

---

### 4. Backfill with Rate Limiting

**Files:** `automation/backfill_runner.py`, `automation/rate_limiter.py`

The backfill system imports sessions with controlled pacing:

```
┌─────────────────────────────────────────────────────────────┐
│                    BACKFILL PROCESS                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   RATE LIMITING (Token Bucket Algorithm)                    │
│   ──────────────────────────────────────                    │
│                                                             │
│   Conservative (default):                                   │
│   - 6 requests/minute                                       │
│   - 8 second minimum delay                                  │
│   - 0-4 second random jitter                                │
│   - ~10 minutes per request                                 │
│                                                             │
│   Backfill mode:                                            │
│   - 10 requests/minute                                      │
│   - 5 second minimum delay                                  │
│   - 0-3 second random jitter                                │
│   - ~6 minutes per request                                  │
│                                                             │
│   Timeline for 90 sessions:                                 │
│   ─────────────────────────                                 │
│   Conservative: 90 x 10 min = 15 hours                      │
│   Backfill:     90 x  6 min = 9 hours                       │
│   Custom delay: 90 x  5 min = 7.5 hours (--delay 300)       │
│                                                             │
│                                                             │
│   CHECKPOINT SYSTEM                                         │
│   ─────────────────                                         │
│                                                             │
│   Every 5 sessions:                                         │
│   - Save progress to backfill_runs table                    │
│   - Record last_processed_report_id                         │
│   - Can resume with --resume if interrupted                 │
│                                                             │
│   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐         │
│   │ S1  │──>│ S2  │──>│ S3  │──>│ S4  │──>│ S5  │──>SAVE  │
│   └─────┘   └─────┘   └─────┘   └─────┘   └─────┘         │
│                                                   │         │
│                                                   v         │
│                                            [Checkpoint]     │
│                                                             │
│                                                             │
│   RETRY LOGIC                                               │
│   ───────────                                               │
│                                                             │
│   On failure:                                               │
│   - Attempt 1: Wait 10s, retry                              │
│   - Attempt 2: Wait 30s, retry                              │
│   - Attempt 3: Wait 90s, retry                              │
│   - After 3 failures: Mark as 'needs_review'                │
│                                                             │
│   Exponential backoff: delay = 10s * 3^(attempt-1)          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 5. Database Tables and Relationships

**File:** `golf_db.py`, `automation/session_discovery.py`

```
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE SCHEMA                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              sessions_discovered                     │   │
│   │  (Automation tracking table)                         │   │
│   ├─────────────────────────────────────────────────────┤   │
│   │  report_id TEXT PRIMARY KEY                          │   │
│   │  api_key TEXT NOT NULL                               │   │
│   │  portal_name TEXT                                    │   │
│   │  session_date TIMESTAMP                              │   │
│   │  clubs_json TEXT              -- ["Driver", "7 Iron"]│   │
│   │  import_status TEXT           -- pending/importing/  │   │
│   │                               -- imported/failed/    │   │
│   │                               -- needs_review        │   │
│   │  import_shots_actual INTEGER                         │   │
│   │  import_error TEXT                                   │   │
│   │  attempt_count INTEGER                               │   │
│   │  session_name TEXT            -- Generated name      │   │
│   │  session_type TEXT            -- practice/drill/etc  │   │
│   │  tags_json TEXT                                      │   │
│   │  discovered_at TIMESTAMP                             │   │
│   │  import_completed_at TIMESTAMP                       │   │
│   └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          │ report_id = session_id           │
│                          v                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                       shots                          │   │
│   │  (Main data table - 30+ fields)                      │   │
│   ├─────────────────────────────────────────────────────┤   │
│   │  id INTEGER PRIMARY KEY                              │   │
│   │  session_id TEXT              -- Links to report_id  │   │
│   │  shot_number INTEGER                                 │   │
│   │  club TEXT                                           │   │
│   │  ball_speed REAL                                     │   │
│   │  club_speed REAL                                     │   │
│   │  smash_factor REAL                                   │   │
│   │  launch_angle REAL                                   │   │
│   │  launch_direction REAL                               │   │
│   │  backspin REAL                                       │   │
│   │  sidespin REAL                                       │   │
│   │  spin_axis REAL                                      │   │
│   │  carry_distance REAL                                 │   │
│   │  total_distance REAL                                 │   │
│   │  apex_height REAL                                    │   │
│   │  descent_angle REAL                                  │   │
│   │  offline_distance REAL                               │   │
│   │  curve_distance REAL                                 │   │
│   │  attack_angle REAL                                   │   │
│   │  club_path REAL                                      │   │
│   │  face_angle REAL                                     │   │
│   │  face_to_path REAL                                   │   │
│   │  ... (more fields)                                   │   │
│   │  imported_at TIMESTAMP                               │   │
│   │  tags TEXT                                           │   │
│   │  notes TEXT                                          │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                   backfill_runs                      │   │
│   │  (Backfill operation tracking)                       │   │
│   ├─────────────────────────────────────────────────────┤   │
│   │  run_id TEXT PRIMARY KEY      -- bf_abc123          │   │
│   │  started_at TIMESTAMP                                │   │
│   │  completed_at TIMESTAMP                              │   │
│   │  status TEXT                  -- running/paused/     │   │
│   │                               -- completed/failed    │   │
│   │  sessions_total INTEGER                              │   │
│   │  sessions_processed INTEGER                          │   │
│   │  sessions_imported INTEGER                           │   │
│   │  sessions_failed INTEGER                             │   │
│   │  total_shots INTEGER                                 │   │
│   │  config_json TEXT                                    │   │
│   │  error_log TEXT                                      │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                  shots_archive                       │   │
│   │  (Soft-deleted shots for recovery)                   │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                   change_log                         │   │
│   │  (Audit trail for modifications)                     │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Status Flow:**

```
┌─────────┐   discover   ┌───────────┐   backfill   ┌──────────┐
│ (none)  │ ──────────> │  pending  │ ──────────> │ imported │
└─────────┘             └───────────┘             └──────────┘
                              │                        ^
                              │                        │
                              v                        │
                        ┌───────────┐   retry    ┌────┴─────┐
                        │ importing │ <──────── │  failed  │
                        └───────────┘           └──────────┘
                              │                        │
                              │ max retries            │
                              v                        │
                        ┌──────────────┐              │
                        │ needs_review │ ─────────────┘
                        └──────────────┘   --retry-failed
```

---

## Command Reference

### automation_runner.py Commands

```bash
# ════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ════════════════════════════════════════════════════════════════

# Interactive login - opens browser for manual login
# Saves cookies for future headless runs
python automation_runner.py login

# ════════════════════════════════════════════════════════════════
# DISCOVERY
# ════════════════════════════════════════════════════════════════

# Discover all sessions (opens browser window)
python automation_runner.py discover

# Discover in headless mode (requires saved cookies)
python automation_runner.py discover --headless

# Discover with limits
python automation_runner.py discover --headless --max 50

# Discover only recent sessions
python automation_runner.py discover --headless --since 2026-01-01

# ════════════════════════════════════════════════════════════════
# BACKFILL (IMPORT)
# ════════════════════════════════════════════════════════════════

# Import all pending sessions
python automation_runner.py backfill --start 2025-01-01

# Import with date range
python automation_runner.py backfill --start 2025-01-01 --end 2025-12-31

# Import newest sessions first (default is oldest first)
python automation_runner.py backfill --start 2025-01-01 --recent

# Limit number of sessions
python automation_runner.py backfill --start 2025-01-01 --max 20

# Filter by clubs used
python automation_runner.py backfill --start 2025-01-01 --clubs "Driver,7 Iron"

# Custom delay between imports (seconds)
python automation_runner.py backfill --start 2025-01-01 --delay 300

# Preview without making changes
python automation_runner.py backfill --start 2025-01-01 --dry-run

# Resume interrupted backfill
python automation_runner.py backfill --resume

# Retry previously failed imports
python automation_runner.py backfill --retry-failed

# Skip club name normalization
python automation_runner.py backfill --start 2025-01-01 --no-normalize

# Skip auto-tagging
python automation_runner.py backfill --start 2025-01-01 --no-tags

# Show backfill run history
python automation_runner.py backfill --status

# ════════════════════════════════════════════════════════════════
# STATUS & DIAGNOSTICS
# ════════════════════════════════════════════════════════════════

# Show overall automation status
python automation_runner.py status

# Test notification system
python automation_runner.py notify "Test message"
python automation_runner.py notify "Error test" --level error

# Test club name normalization
python automation_runner.py normalize --test "7i,SW,PW,Dr"
```

### Command Options Summary

| Command | Key Options | Description |
|---------|-------------|-------------|
| `login` | (none) | Interactive browser login |
| `discover` | `--headless`, `--max N`, `--since DATE` | Find sessions on portal |
| `backfill` | `--start`, `--end`, `--max`, `--clubs`, `--delay`, `--dry-run`, `--resume`, `--retry-failed`, `--recent` | Import shot data |
| `status` | (none) | Show system status |
| `notify` | `--level` | Test notifications |
| `normalize` | `--test` | Test club name normalization |

---

## Common Workflows

### Workflow 1: Initial Setup (First Time)

```bash
# Step 1: Install Playwright browser
playwright install chromium

# Step 2: Interactive login to save cookies
python automation_runner.py login
# -> Browser opens, log in manually
# -> Cookies saved for 7 days

# Step 3: Verify status
python automation_runner.py status
# Credentials:
#   Stored cookies: Yes
#   Cookies valid:  Yes
```

### Workflow 2: Full Discovery and Import

```bash
# Step 1: Discover all sessions
python automation_runner.py discover --headless
# Output:
#   Total discovered: 95
#   New sessions:     65
#   Already known:    30

# Step 2: Preview what would be imported
python automation_runner.py backfill --start 2024-01-01 --dry-run
# [DRY RUN] Would import 43285: Practice - Jan 26, 2026
# [DRY RUN] Would import 43166: Drill - Jan 25, 2026
# ...

# Step 3: Import in batches (controlled)
python automation_runner.py backfill --start 2024-01-01 --max 20 --delay 300
# Progress: 1/20 (5%) - 45 shots
# Progress: 2/20 (10%) - 92 shots
# ...

# Step 4: Verify import
python automation_runner.py status
# Sessions discovered:
#   imported: 20
#   pending:  70
```

### Workflow 3: Daily Sync (Ongoing)

```bash
# Discover new sessions (quick check)
python automation_runner.py discover --headless --max 20

# Import any new sessions
python automation_runner.py backfill --start 2026-01-20 --max 10
```

### Workflow 4: Recover from Failures

```bash
# Check for failed sessions
python automation_runner.py status
# Sessions discovered:
#   failed: 3
#   needs_review: 2

# Retry failed imports
python automation_runner.py backfill --retry-failed
# Found 5 failed session(s):
#   - 43100: Practice - Jan 15 (needs_review, Attempts: 3)
# Reset 5 session(s) for retry.
# Starting retry backfill...
```

### Workflow 5: Selective Import (Specific Clubs)

```bash
# Import only Driver sessions for analysis
python automation_runner.py backfill \
  --start 2025-06-01 \
  --clubs "Driver" \
  --max 50

# Import short game practice
python automation_runner.py backfill \
  --start 2025-06-01 \
  --clubs "PW,SW,LW,56 Wedge,60 Wedge"
```

---

## Troubleshooting

### Problem: "Login failed" or "Not logged in"

**Symptoms:**
```
Error: Must be logged in to get sessions
Error: Failed to log in to Uneekor portal
```

**Solutions:**

1. **Refresh cookies:**
   ```bash
   python automation_runner.py login
   # Log in manually, wait for success message
   ```

2. **Check credentials:**
   ```bash
   python automation_runner.py status
   # Look for:
   #   Cookies valid: No
   #   Cookies expire: [past date]
   ```

3. **Clear and re-login:**
   ```bash
   rm .uneekor_cookies.enc
   python automation_runner.py login
   ```

---

### Problem: "Discovery finds 0 sessions"

**Symptoms:**
```
Scanning page 1...
No sessions found on page 1, stopping pagination
Total sessions found: 0
```

**Solutions:**

1. **Check if portal changed:** Visit https://my.uneekor.com/report manually

2. **Check login status:** Ensure cookies are valid

3. **Try non-headless mode:**
   ```bash
   python automation_runner.py discover
   # Watch browser for errors
   ```

---

### Problem: "Rate limited" or "Too many requests"

**Symptoms:**
```
Error: HTTP 429 Too Many Requests
Error: Connection refused
Consecutive failures increasing
```

**Solutions:**

1. **Increase delay:**
   ```bash
   python automation_runner.py backfill --start 2025-01-01 --delay 600
   # 10 minutes between imports
   ```

2. **Reduce batch size:**
   ```bash
   python automation_runner.py backfill --start 2025-01-01 --max 10
   ```

3. **Wait and resume:**
   ```bash
   # Wait an hour, then:
   python automation_runner.py backfill --resume
   ```

---

### Problem: "Session import fails repeatedly"

**Symptoms:**
```
Attempt 1/3 failed for 43100: Connection timeout
Attempt 2/3 failed for 43100: Connection timeout
Attempt 3/3 failed for 43100: Connection timeout
Failed 43100 after 3 attempts
```

**Solutions:**

1. **Check session in portal:** May be corrupted or empty

2. **Manual import:** Use Streamlit Data Import page

3. **Skip problematic session:**
   ```sql
   -- In SQLite:
   UPDATE sessions_discovered
   SET import_status = 'skipped',
       skip_reason = 'Manual skip - corrupted data'
   WHERE report_id = '43100';
   ```

---

### Problem: "Backfill stuck or not progressing"

**Symptoms:**
```
Progress: 5/50 (10%) - 200 shots
[hangs for hours]
```

**Solutions:**

1. **Check current status:**
   ```bash
   python automation_runner.py backfill --status
   ```

2. **Kill and resume:**
   ```bash
   # Ctrl+C to stop
   python automation_runner.py backfill --resume
   ```

3. **Check for paused run:**
   ```sql
   SELECT * FROM backfill_runs WHERE status = 'running';
   -- If stuck, update:
   UPDATE backfill_runs SET status = 'paused' WHERE run_id = 'bf_xxx';
   ```

---

### Problem: "Duplicate shots in database"

**Symptoms:**
```
SELECT session_id, COUNT(*) FROM shots GROUP BY session_id HAVING COUNT(*) > expected;
```

**Solutions:**

1. **Check import status:**
   ```sql
   SELECT report_id, import_status, import_shots_actual
   FROM sessions_discovered
   WHERE report_id = '43285';
   ```

2. **Delete duplicates:**
   ```sql
   -- Keep only first instance of each shot
   DELETE FROM shots WHERE id NOT IN (
     SELECT MIN(id) FROM shots GROUP BY session_id, shot_number
   );
   ```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `UNEEKOR_USERNAME` | For headless | Portal email |
| `UNEEKOR_PASSWORD` | For headless | Portal password |
| `UNEEKOR_COOKIE_KEY` | No | Custom encryption key |
| `SLACK_WEBHOOK_URL` | No | Slack notifications |
| `SUPABASE_URL` | No | Cloud sync |
| `SUPABASE_KEY` | No | Cloud sync |

### Rate Limiter Presets

| Preset | Requests/min | Min Delay | Use Case |
|--------|--------------|-----------|----------|
| Conservative | 6 | 8s | Daily sync |
| Backfill | 10 | 5s | Historical import |
| Aggressive | 20 | 2s | Testing only |

### Backfill Configuration Options

```python
BackfillConfig(
    date_start=date(2025, 1, 1),      # Earliest date
    date_end=date(2025, 12, 31),      # Latest date
    clubs_filter=["Driver", "7 Iron"], # Club filter
    max_sessions_per_run=50,           # Batch size
    max_sessions_per_hour=6,           # Rate limit
    checkpoint_interval=5,             # Save every N
    normalize_clubs=True,              # Fix club names
    auto_tag=True,                     # Generate tags
    dry_run=False,                     # Preview mode
    max_retries=3,                     # Retry attempts
    retry_delay_base=10,               # Initial retry delay
    delay_seconds=None,                # Custom delay (overrides rate limiter)
    recent_first=False,                # Newest first
)
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                   AUTOMATION QUICK REFERENCE                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   FIRST TIME SETUP:                                         │
│   playwright install chromium                               │
│   python automation_runner.py login                         │
│                                                             │
│   DAILY WORKFLOW:                                           │
│   python automation_runner.py discover --headless           │
│   python automation_runner.py backfill --start 2026-01-01   │
│                                                             │
│   CHECK STATUS:                                             │
│   python automation_runner.py status                        │
│                                                             │
│   CONTROLLED IMPORT:                                        │
│   --max 20          # Limit batch size                      │
│   --delay 300       # 5 min between imports                 │
│   --dry-run         # Preview only                          │
│   --recent          # Newest first                          │
│                                                             │
│   RECOVERY:                                                 │
│   --resume          # Continue interrupted run              │
│   --retry-failed    # Retry failed sessions                 │
│                                                             │
│   DATABASE LOCATION:                                        │
│   golf_stats.db (SQLite, project root)                      │
│                                                             │
│   KEY TABLES:                                               │
│   sessions_discovered  # Import tracking                    │
│   shots                # Shot data                          │
│   backfill_runs        # Run history                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

*Last updated: 2026-01-26*
