# Data Sync and Backfill Implementation Plan

> **For Claude:** This plan has mixed execution modes. Track A uses Codex. Tracks B and C require direct Claude execution (browser automation and rate-limited CLI).

**Goal:** Achieve data consistency between SQLite and Supabase, extract missing dates, and import 93 pending sessions.

**Architecture:** Three sequential tracks that must run in order: (1) Fix database drift by removing test data from Supabase, (2) Extract dates from Uneekor listing page via browser automation, (3) Run backfill to import pending sessions with correct rate limiting.

**Tech Stack:** Python 3.9+, SQLite, Supabase, Playwright browser automation

---

## Current State Summary

| Metric | Value |
|--------|-------|
| SQLite shots | 1,341 |
| Supabase shots | 1,343 |
| Drift | 2 test shots in Supabase only |
| Sessions discovered | 118 |
| Sessions imported | 25 |
| Sessions pending | 93 |
| Sessions with dates | 19 |
| Sessions missing dates | 99 |

---

## Track A: Fix Database Drift (Codex-compatible)

### Task A1: Delete Test Data from Supabase

**Files:**
- Modify: `golf_db.py` (add delete function if needed)
- Or: Direct Supabase API call

**Step 1: Verify test shots exist only in Supabase**

```python
# The shots 'test_shot_1' and 'test_shot_2' exist in Supabase but not SQLite
# They appear to be test data that should be removed
```

**Step 2: Delete test shots from Supabase**

```python
import os
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# Delete test shots
result = supabase.table('shots').delete().in_('shot_id', ['test_shot_1', 'test_shot_2']).execute()
print(f"Deleted {len(result.data)} test shots")
```

**Step 3: Verify drift is resolved**

```bash
./venv/bin/python -c "import golf_db; golf_db.init_db(); s=golf_db.get_detailed_sync_status(); print(f'Drift: {s[\"drift_detected\"]}, Local: {s[\"local_count\"]}, Supabase: {s[\"supabase_count\"]}')"
```

Expected: `Drift: False, Local: 1341, Supabase: 1341`

---

## Track B: Extract Session Dates (Browser Required - Claude Only)

### Task B1: Login and Extract Dates from Listing Page

**Prerequisites:** Valid Uneekor portal cookies (run `python automation_runner.py login` if expired)

**Step 1: Check cookie validity**

```bash
python automation_runner.py status
```

**Step 2: Extract dates from listing page**

```bash
python automation_runner.py reclassify-dates --from-listing --auto-backfill
```

This will:
1. Navigate to Uneekor portal listing page
2. Extract dates from DOM headers (grouped by date)
3. Update `sessions_discovered.session_date` for each session
4. Auto-backfill dates to `shots.session_date`

**Step 3: Verify date extraction**

```bash
./venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('golf_stats.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM sessions_discovered WHERE session_date IS NOT NULL')
print(f'Sessions with dates: {cursor.fetchone()[0]}/118')
"
```

Expected: Most sessions should now have dates (listing_page source)

---

## Track C: Backfill Pending Sessions (Rate-Limited - Claude Only)

### Task C1: Run Backfill with Correct Rate Limiting

**Prerequisites:**
- Track A complete (no drift)
- Track B complete (dates extracted)
- Valid cookies

**Step 1: Dry run to preview**

```bash
python automation_runner.py backfill --start 2025-01-01 --dry-run
```

**Step 2: Start backfill (6 sessions/hour)**

```bash
python automation_runner.py backfill --start 2025-01-01
```

**Note:** With 93 pending sessions at 6/hour, full backfill takes ~15.5 hours. Consider:
- Running overnight
- Using `--max-sessions 20` for a partial run
- Monitoring via `--status` periodically

**Step 3: Monitor progress**

```bash
# Check status
python automation_runner.py status

# View recent imports
./venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('golf_stats.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT import_status, COUNT(*) FROM sessions_discovered GROUP BY import_status
''')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')
"
```

---

## Execution Strategy

### What Codex Can Do (Track A)
- Write Python scripts
- Modify database code
- Run tests
- Commit changes

### What Claude Must Do (Tracks B & C)
- Browser automation (requires cookies, interactive login)
- Rate-limited operations (long-running, need monitoring)
- Operations that require user credentials

### Recommended Execution

1. **Run Track A via Codex** - Quick, code-only task
2. **Pause for user action** - User runs `login` if cookies expired
3. **Claude executes Track B** - Browser automation for date extraction
4. **Claude executes Track C** - Start backfill, optionally in background

---

## Verification Checklist

After all tracks complete:

```bash
# Verify no drift
./venv/bin/python -c "import golf_db; golf_db.init_db(); s=golf_db.get_detailed_sync_status(); print(f'Drift: {s[\"drift_detected\"]}')"

# Verify dates populated
./venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('golf_stats.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM sessions_discovered WHERE session_date IS NULL')
print(f'Sessions missing dates: {cursor.fetchone()[0]}')
"

# Verify sessions imported
./venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('golf_stats.db')
cursor = conn.cursor()
cursor.execute('SELECT import_status, COUNT(*) FROM sessions_discovered GROUP BY import_status')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')
"
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Supabase delete fails | Check API key permissions, use service role |
| Cookies expired | Run `login` command before Track B |
| Rate limiting triggered | Already fixed (6/hour), but monitor for 429s |
| Backfill interrupted | Resumable via checkpoint tables |
| Date extraction misses some | Can re-run `--from-listing`, idempotent |
