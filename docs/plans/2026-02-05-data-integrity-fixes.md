# Data Integrity Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix database sync drift, automation rate limiter bug, and automate session date backfill workflow.

**Architecture:** Three independent fix tracks that can be worked in parallel. Each track addresses a specific data integrity issue: (1) Supabase sync with audit trail and conflict detection, (2) rate limiter configuration bug causing 10x faster scraping than intended, (3) automatic date propagation from sessions_discovered to shots table.

**Tech Stack:** Python 3.9+, SQLite, Supabase, Playwright, unittest

---

## Track A: Database Sync Reliability

### Task A1: Add Sync Audit Table

**Files:**
- Modify: `golf_db.py:50-100` (add table creation in init_db)
- Modify: `supabase_schema.sql` (add sync_audit table)
- Test: `tests/test_golf_db.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_golf_db.py
def test_sync_audit_table_exists(self):
    """Verify sync_audit table is created on init."""
    cursor = self.db.conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='sync_audit'
    """)
    result = cursor.fetchone()
    self.assertIsNotNone(result, "sync_audit table should exist")
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_golf_db.TestGolfDB.test_sync_audit_table_exists -v`
Expected: FAIL with "sync_audit table should exist"

**Step 3: Add sync_audit table to init_db**

Add to `golf_db.py` in `init_db()` after other CREATE TABLE statements (~line 85):

```python
# Sync audit trail
cursor.execute('''
    CREATE TABLE IF NOT EXISTS sync_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_type TEXT NOT NULL,  -- 'to_supabase', 'from_supabase', 'full'
        started_at TEXT NOT NULL,
        completed_at TEXT,
        records_synced INTEGER DEFAULT 0,
        records_failed INTEGER DEFAULT 0,
        error_message TEXT,
        details TEXT  -- JSON blob with specifics
    )
''')
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_golf_db.TestGolfDB.test_sync_audit_table_exists -v`
Expected: PASS

**Step 5: Add to Supabase schema**

Add to `supabase_schema.sql`:

```sql
-- Sync audit trail (local tracking, not synced to Supabase)
-- This table is SQLite-only for tracking sync operations
```

**Step 6: Commit**

```bash
git add golf_db.py supabase_schema.sql tests/test_golf_db.py
git commit -m "feat(db): add sync_audit table for tracking sync operations"
```

---

### Task A2: Log Sync Operations

**Files:**
- Modify: `golf_db.py:1606-1700` (sync_to_supabase function)
- Test: `tests/test_golf_db.py`

**Step 1: Write the failing test**

```python
def test_sync_to_supabase_creates_audit_record(self):
    """Verify sync operations are logged to sync_audit."""
    # Add a shot first
    self.db.save_shot(self.sample_shot_data)

    # Run sync (will fail without Supabase, but should still log)
    try:
        self.db.sync_to_supabase(dry_run=True)
    except:
        pass

    cursor = self.db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sync_audit WHERE sync_type = 'to_supabase'")
    count = cursor.fetchone()[0]
    self.assertGreaterEqual(count, 1, "Should have at least one sync audit record")
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_golf_db.TestGolfDB.test_sync_to_supabase_creates_audit_record -v`
Expected: FAIL

**Step 3: Add audit logging to sync_to_supabase**

Modify `sync_to_supabase()` in `golf_db.py` (~line 1650):

```python
def sync_to_supabase(dry_run: bool = False) -> dict:
    """Sync all local shots to Supabase with audit trail."""
    import json
    from datetime import datetime

    started_at = datetime.now().isoformat()
    records_synced = 0
    records_failed = 0
    errors = []

    try:
        # ... existing sync logic ...
        # After each successful batch:
        records_synced += len(batch)
        # After each failed record:
        records_failed += 1
        errors.append(str(e))

    finally:
        # Always log the sync attempt
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sync_audit
            (sync_type, started_at, completed_at, records_synced, records_failed, error_message, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            'to_supabase',
            started_at,
            datetime.now().isoformat(),
            records_synced,
            records_failed,
            '; '.join(errors[:5]) if errors else None,  # First 5 errors
            json.dumps({'dry_run': dry_run})
        ))
        conn.commit()

    return {'synced': records_synced, 'failed': records_failed}
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_golf_db.TestGolfDB.test_sync_to_supabase_creates_audit_record -v`
Expected: PASS

**Step 5: Commit**

```bash
git add golf_db.py tests/test_golf_db.py
git commit -m "feat(db): log sync operations to sync_audit table"
```

---

### Task A3: Add Sync Drift Detection

**Files:**
- Modify: `golf_db.py:1700-1800` (get_detailed_sync_status)
- Test: `tests/test_golf_db.py`

**Step 1: Write the failing test**

```python
def test_get_sync_drift_returns_meaningful_data(self):
    """Verify drift detection identifies local-only records."""
    # Add shots locally
    for i in range(5):
        shot = self.sample_shot_data.copy()
        shot['shot_id'] = f'drift_test_{i}'
        self.db.save_shot(shot)

    status = self.db.get_detailed_sync_status()

    self.assertIn('local_only_count', status)
    self.assertIn('last_sync', status)
    self.assertGreaterEqual(status['local_only_count'], 5)
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_golf_db.TestGolfDB.test_get_sync_drift_returns_meaningful_data -v`
Expected: FAIL (missing keys)

**Step 3: Enhance get_detailed_sync_status**

Modify in `golf_db.py` (~line 1720):

```python
def get_detailed_sync_status() -> dict:
    """Get comprehensive sync status including drift detection."""
    cursor = conn.cursor()

    # Get local count
    cursor.execute("SELECT COUNT(*) FROM shots")
    local_count = cursor.fetchone()[0]

    # Get last sync info
    cursor.execute("""
        SELECT started_at, records_synced, records_failed
        FROM sync_audit
        WHERE sync_type = 'to_supabase' AND completed_at IS NOT NULL
        ORDER BY started_at DESC LIMIT 1
    """)
    last_sync_row = cursor.fetchone()

    last_sync = None
    if last_sync_row:
        last_sync = {
            'timestamp': last_sync_row[0],
            'records_synced': last_sync_row[1],
            'records_failed': last_sync_row[2]
        }

    # Get Supabase count if available
    supabase_count = 0
    if supabase:
        try:
            result = supabase.table('shots').select('shot_id', count='exact').execute()
            supabase_count = result.count or 0
        except Exception as e:
            print(f"Could not get Supabase count: {e}")

    return {
        'local_count': local_count,
        'supabase_count': supabase_count,
        'local_only_count': max(0, local_count - supabase_count),
        'last_sync': last_sync,
        'drift_detected': local_count != supabase_count
    }
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_golf_db.TestGolfDB.test_get_sync_drift_returns_meaningful_data -v`
Expected: PASS

**Step 5: Commit**

```bash
git add golf_db.py tests/test_golf_db.py
git commit -m "feat(db): enhance sync status with drift detection and last sync info"
```

---

## Track B: Fix Rate Limiter Bug

### Task B1: Write Test Exposing the Bug

**Files:**
- Create: `tests/unit/test_rate_limiter_config.py`

**Step 1: Create test file exposing the bug**

```python
# tests/unit/test_rate_limiter_config.py
"""Test rate limiter configuration is correct."""
import unittest
from automation.backfill_runner import BackfillRunner, BackfillConfig

class TestRateLimiterConfig(unittest.TestCase):
    """Verify rate limiter is configured correctly."""

    def test_rate_limiter_uses_per_hour_not_per_minute(self):
        """
        BUG: BackfillRunner passes max_sessions_per_hour to requests_per_minute.

        With max_sessions_per_hour=6:
        - WRONG: 6 requests per minute = 360/hour (60x too fast)
        - RIGHT: 6 requests per hour = 0.1 requests per minute
        """
        config = BackfillConfig(max_sessions_per_hour=6)
        runner = BackfillRunner(config)

        # The rate limiter should allow ~6 requests per hour
        # That's 0.1 requests per minute, or 1 request per 10 minutes
        expected_requests_per_minute = 6 / 60  # 0.1

        # Get actual config from rate limiter
        actual_rpm = runner.rate_limiter.config.requests_per_minute

        self.assertAlmostEqual(
            actual_rpm,
            expected_requests_per_minute,
            places=2,
            msg=f"Rate limiter should be {expected_requests_per_minute} req/min, got {actual_rpm}"
        )

if __name__ == '__main__':
    unittest.main()
```

**Step 2: Run test to verify it fails (exposes bug)**

Run: `python -m unittest tests.unit.test_rate_limiter_config -v`
Expected: FAIL with "Rate limiter should be 0.1 req/min, got 6"

**Step 3: Commit the failing test**

```bash
git add tests/unit/test_rate_limiter_config.py
git commit -m "test: add failing test exposing rate limiter config bug"
```

---

### Task B2: Fix the Rate Limiter Configuration

**Files:**
- Modify: `automation/backfill_runner.py:199-210`

**Step 1: Locate and fix the bug**

In `automation/backfill_runner.py`, find the rate limiter initialization (~line 199):

```python
# BEFORE (buggy):
self.rate_limiter = RateLimiter(RateLimiterConfig(
    requests_per_minute=self.config.max_sessions_per_hour,  # BUG!
))

# AFTER (fixed):
self.rate_limiter = RateLimiter(RateLimiterConfig(
    requests_per_minute=self.config.max_sessions_per_hour / 60,  # Convert hours to minutes
))
```

**Step 2: Run test to verify it passes**

Run: `python -m unittest tests.unit.test_rate_limiter_config -v`
Expected: PASS

**Step 3: Run full test suite**

Run: `python -m unittest discover -s tests -v 2>&1 | tail -5`
Expected: All tests pass

**Step 4: Commit the fix**

```bash
git add automation/backfill_runner.py
git commit -m "fix(automation): correct rate limiter config from per-minute to per-hour

BUG: max_sessions_per_hour was passed directly to requests_per_minute,
causing scraping 60x faster than intended (6/min vs 6/hour).

FIX: Divide by 60 to convert hours to minutes."
```

---

## Track C: Automate Session Date Backfill

### Task C1: Add Auto-Backfill Flag to from-listing

**Files:**
- Modify: `automation_runner.py:389-450` (cmd_reclassify_dates)
- Test: `tests/integration/test_date_reclassification.py`

**Step 1: Write the failing test**

```python
# Add to tests/integration/test_date_reclassification.py
def test_from_listing_with_auto_backfill(self):
    """Verify --from-listing --auto-backfill propagates dates to shots."""
    # Setup: create session_discovered with date
    cursor = self.db.conn.cursor()
    cursor.execute("""
        INSERT INTO sessions_discovered (report_id, session_date, date_source, status)
        VALUES ('test_123', '2026-01-15', 'listing_page', 'imported')
    """)

    # Setup: create shot referencing that session
    cursor.execute("""
        INSERT INTO shots (shot_id, report_id, session_date)
        VALUES ('shot_abc', 'test_123', NULL)
    """)
    self.db.conn.commit()

    # Run backfill
    self.db.backfill_session_dates()

    # Verify shot now has date
    cursor.execute("SELECT session_date FROM shots WHERE shot_id = 'shot_abc'")
    result = cursor.fetchone()
    self.assertEqual(result[0], '2026-01-15')
```

**Step 2: Run test to verify current state**

Run: `python -m unittest tests.integration.test_date_reclassification -v`
Expected: Check if this test exists or needs creation

**Step 3: Add --auto-backfill flag to CLI**

In `automation_runner.py`, modify the argument parser (~line 120):

```python
reclassify_parser.add_argument(
    '--auto-backfill',
    action='store_true',
    help='Automatically run backfill after extracting dates from listing'
)
```

**Step 4: Wire up auto-backfill in cmd_reclassify_dates**

In `cmd_reclassify_dates()` (~line 450):

```python
if args.from_listing:
    # ... existing listing extraction code ...

    if args.auto_backfill:
        print("\n--- Auto-backfilling dates to shots table ---")
        result = golf_db.backfill_session_dates()
        print(f"Updated {result['updated']} shots with session dates")
```

**Step 5: Run tests**

Run: `python -m unittest tests.integration.test_date_reclassification -v`
Expected: PASS

**Step 6: Commit**

```bash
git add automation_runner.py tests/integration/test_date_reclassification.py
git commit -m "feat(automation): add --auto-backfill flag to reclassify-dates --from-listing"
```

---

### Task C2: Add Date Validation

**Files:**
- Modify: `golf_db.py:1555-1599` (update_session_date_for_shots)
- Test: `tests/test_golf_db.py`

**Step 1: Write the failing test**

```python
def test_update_session_date_rejects_future_dates(self):
    """Verify future dates are rejected."""
    from datetime import datetime, timedelta

    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

    with self.assertRaises(ValueError) as ctx:
        self.db.update_session_date_for_shots('test_report', future_date)

    self.assertIn('future', str(ctx.exception).lower())
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_golf_db.TestGolfDB.test_update_session_date_rejects_future_dates -v`
Expected: FAIL (no validation exists)

**Step 3: Add date validation**

In `golf_db.py`, modify `update_session_date_for_shots()` (~line 1560):

```python
def update_session_date_for_shots(report_id: str, session_date: str) -> int:
    """Update session_date for all shots with given report_id."""
    from datetime import datetime

    # Validate date format
    try:
        parsed_date = datetime.strptime(session_date, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {session_date}. Use YYYY-MM-DD.")

    # Reject future dates
    if parsed_date > datetime.now():
        raise ValueError(f"Cannot set future date: {session_date}")

    # Reject dates before 2020 (Uneekor launch)
    if parsed_date.year < 2020:
        raise ValueError(f"Date too old (before Uneekor launch): {session_date}")

    # ... rest of existing update logic ...
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_golf_db.TestGolfDB.test_update_session_date_rejects_future_dates -v`
Expected: PASS

**Step 5: Commit**

```bash
git add golf_db.py tests/test_golf_db.py
git commit -m "feat(db): add date validation to prevent future/invalid session dates"
```

---

## Summary of Changes

| Track | Task | Description | Risk |
|-------|------|-------------|------|
| A | A1 | Add sync_audit table | Low |
| A | A2 | Log sync operations | Low |
| A | A3 | Drift detection | Low |
| B | B1 | Test exposing rate limiter bug | None |
| B | B2 | Fix rate limiter (60x too fast) | **High** |
| C | C1 | Auto-backfill flag | Low |
| C | C2 | Date validation | Low |

## Verification Checklist

After all tasks:

```bash
# Run full test suite
python -m unittest discover -s tests -v

# Verify rate limiter fix
python -c "from automation.backfill_runner import BackfillRunner, BackfillConfig; r = BackfillRunner(BackfillConfig(max_sessions_per_hour=6)); print(f'Rate: {r.rate_limiter.config.requests_per_minute} req/min (should be ~0.1)')"

# Check sync status
python -c "import golf_db; golf_db.init_db(); print(golf_db.get_detailed_sync_status())"

# Test date validation
python -c "import golf_db; golf_db.init_db(); golf_db.update_session_date_for_shots('test', '2099-01-01')"  # Should raise ValueError
```

---

## Documentation Updates

After implementation, update `CLAUDE.md`:

1. Add rate limiter fix to known fixes section
2. Document `--auto-backfill` flag in commands
3. Add sync_audit table to database schema section
4. Note date validation rules
