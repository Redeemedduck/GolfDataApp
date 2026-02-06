# Backfill Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute validated backfill of 12 sessions, research naming patterns with parallel agents, synthesize findings, and implement improved session naming.

**Architecture:** Five-stage sequential pipeline with validation gate and parallel research phase. Uses Codex orchestrator for code analysis tasks, Claude CLI for browser automation.

**Tech Stack:** Python, Playwright, Codex CLI, SQLite, Supabase

---

## Task 1: Stage 1 - Dry Run

**Files:**
- Read: `automation_runner.py`
- Output: Console output (captured for Stage 2)

**Step 1: Run dry run command**

Run:
```bash
./venv/bin/python automation_runner.py backfill --start 2025-01-01 --max-sessions 3 --dry-run --headless 2>&1 | tee /tmp/backfill-dry-run.log
```

Expected output contains:
- "DRY RUN" indicator
- List of 3 session IDs
- No error messages

**Step 2: Verify output captured**

Run:
```bash
cat /tmp/backfill-dry-run.log | head -50
```

Expected: Log file exists with dry run output

---

## Task 2: Stage 2 - Validation Gate

**Files:**
- Read: `/tmp/backfill-dry-run.log`
- Read: `golf_stats.db` (sessions_discovered table)

**Step 1: Check for errors in dry run output**

Run:
```bash
grep -iE "error|exception|failed|traceback|429" /tmp/backfill-dry-run.log || echo "PASS: No errors found"
```

Expected: "PASS: No errors found"

**Step 2: Validate dates in database**

Run:
```bash
./venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('golf_stats.db')
cursor = conn.cursor()

# Check for null dates
cursor.execute('SELECT COUNT(*) FROM sessions_discovered WHERE session_date IS NULL AND import_status = \"pending\"')
null_dates = cursor.fetchone()[0]

# Check for future dates
cursor.execute('SELECT COUNT(*) FROM sessions_discovered WHERE session_date > date(\"now\")')
future_dates = cursor.fetchone()[0]

# Check for pre-2020 dates
cursor.execute('SELECT COUNT(*) FROM sessions_discovered WHERE session_date < \"2020-01-01\"')
old_dates = cursor.fetchone()[0]

print(f'Null dates: {null_dates}')
print(f'Future dates: {future_dates}')
print(f'Pre-2020 dates: {old_dates}')

if null_dates == 0 and future_dates == 0 and old_dates == 0:
    print('VALIDATION PASSED - Proceeding to Stage 3')
else:
    print('VALIDATION FAILED - Review required')
"
```

Expected: "VALIDATION PASSED - Proceeding to Stage 3"

**Step 3: Gate decision**

If PASSED → Continue to Task 3
If FAILED → Stop and report issues to user

---

## Task 3: Stage 3 - Backfill Execution

**Files:**
- Modify: `golf_stats.db` (shots, sessions_discovered tables)
- Sync: Supabase shots table

**Step 1: Run backfill for 12 sessions**

Run:
```bash
./venv/bin/python automation_runner.py backfill --start 2025-01-01 --max-sessions 12 --headless 2>&1 | tee /tmp/backfill-run.log
```

Expected duration: ~2 hours (6 sessions/hour rate limit)

**Step 2: Verify backfill completed**

Run:
```bash
./venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('golf_stats.db')
cursor = conn.cursor()

cursor.execute('SELECT import_status, COUNT(*) FROM sessions_discovered GROUP BY import_status')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')

cursor.execute('SELECT COUNT(*) FROM shots')
print(f'Total shots: {cursor.fetchone()[0]}')
"
```

Expected: Shows increased imported count and shot total

**Step 3: Verify sync status**

Run:
```bash
./venv/bin/python -c "
import golf_db
golf_db.init_db()
s = golf_db.get_detailed_sync_status()
print(f'Local: {s[\"local_count\"]} | Supabase: {s[\"supabase_count\"]} | Drift: {s[\"drift_detected\"]}')
"
```

Expected: No drift between local and Supabase

---

## Task 4: Stage 4 - Research Phase (Parallel Agents)

**Files:**
- Create: `docs/research/portal-naming-patterns.md`
- Create: `docs/research/date-inconsistencies.md`
- Create: `docs/research/club-naming-variations.md`
- Create: `docs/research/codebase-gap-analysis.md`

**Step 1: Create research directory**

Run:
```bash
mkdir -p docs/research
```

**Step 2: Launch Agent A - Portal Naming Patterns**

Use Task tool with Codex orchestrator:
```
Investigate how Uneekor portal names reports. Analyze:
1. sessions_discovered table - portal_name column patterns
2. source_url column - URL structure patterns
3. automation/uneekor_portal.py - existing parsing logic

Write findings to docs/research/portal-naming-patterns.md
```

**Step 3: Launch Agent B - Date Inconsistencies (parallel)**

Use Task tool with Codex orchestrator:
```
Investigate date/time inconsistencies. Analyze:
1. sessions_discovered table - session_date, date_added, date_source columns
2. automation/naming_conventions.py - parse_listing_date function
3. Date formats seen: YYYY.MM.DD, "Jan 15, 2026", etc.

Write findings to docs/research/date-inconsistencies.md
```

**Step 4: Launch Agent C - Club Naming Variations (parallel)**

Use Task tool with Codex orchestrator:
```
Investigate club naming variations. Analyze:
1. shots table - SELECT DISTINCT club FROM shots
2. automation/naming_conventions.py - normalize_club_name function
3. Edge cases: "7i" vs "7 Iron", "PW" vs "Pitching Wedge"

Write findings to docs/research/club-naming-variations.md
```

**Step 5: Launch Agent D - Codebase Gap Analysis (parallel)**

Use Task tool with Codex orchestrator:
```
Investigate codebase gaps in naming. Analyze:
1. automation/naming_conventions.py - full review
2. golf_db.py - session tagging logic
3. automation/session_discovery.py - how sessions are stored

Write findings to docs/research/codebase-gap-analysis.md
```

**Step 6: Wait for all agents to complete**

Verify all 4 research files exist:
```bash
ls -la docs/research/*.md
```

Expected: 4 markdown files created

---

## Task 5: Stage 4.5 - Research Synthesis

**Files:**
- Read: `docs/research/portal-naming-patterns.md`
- Read: `docs/research/date-inconsistencies.md`
- Read: `docs/research/club-naming-variations.md`
- Read: `docs/research/codebase-gap-analysis.md`
- Create: `docs/research/SYNTHESIS.md`

**Step 1: Launch Synthesis Agent**

Use Task tool with Codex orchestrator:
```
Synthesize findings from 4 research documents into unified naming schema.

Read:
- docs/research/portal-naming-patterns.md
- docs/research/date-inconsistencies.md
- docs/research/club-naming-variations.md
- docs/research/codebase-gap-analysis.md

Output docs/research/SYNTHESIS.md containing:
1. Executive summary of findings
2. Proposed naming schema: "{date} {session_type} ({shot_count} shots)"
3. Session types: Driver Focus, Iron Work, Short Game, Mixed Practice
4. Edge cases to handle
5. Recommended implementation order
```

**Step 2: Verify synthesis complete**

Run:
```bash
cat docs/research/SYNTHESIS.md | head -100
```

Expected: Comprehensive synthesis document with naming schema

---

## Task 6: Stage 5 - Naming Implementation

**Files:**
- Modify: `automation/naming_conventions.py`
- Modify: `golf_db.py`
- Modify: `automation/session_discovery.py`
- Create: `tests/unit/test_session_naming.py`

**Step 1: Write failing test for generate_session_name**

Create `tests/unit/test_session_naming.py`:
```python
import unittest
from datetime import datetime

class TestSessionNaming(unittest.TestCase):
    def test_generate_session_name_driver_focus(self):
        """Session with >60% driver shots should be 'Driver Focus'"""
        from automation.naming_conventions import generate_session_name

        session_date = datetime(2026, 2, 2)
        clubs = ['Driver'] * 15 + ['7 Iron'] * 5  # 75% driver

        result = generate_session_name(session_date, clubs)

        self.assertEqual(result, "2026-02-02 Driver Focus (20 shots)")

    def test_generate_session_name_mixed_practice(self):
        """Session with no dominant club should be 'Mixed Practice'"""
        from automation.naming_conventions import generate_session_name

        session_date = datetime(2026, 1, 28)
        clubs = ['Driver'] * 5 + ['7 Iron'] * 5 + ['PW'] * 5

        result = generate_session_name(session_date, clubs)

        self.assertEqual(result, "2026-01-28 Mixed Practice (15 shots)")

    def test_detect_session_type_short_game(self):
        """Session with >60% wedges should be 'Short Game'"""
        from automation.naming_conventions import detect_session_type

        clubs = ['PW'] * 10 + ['SW'] * 8 + ['Driver'] * 2

        result = detect_session_type(clubs)

        self.assertEqual(result, "Short Game")

if __name__ == '__main__':
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run:
```bash
./venv/bin/python -m unittest tests.unit.test_session_naming -v
```

Expected: ImportError - generate_session_name not found

**Step 3: Implement naming functions**

Add to `automation/naming_conventions.py`:
```python
from datetime import datetime
from typing import List
from collections import Counter

# Club categories for session type detection
DRIVER_CLUBS = {'Driver', 'driver', '1 Wood'}
IRON_CLUBS = {'3 Iron', '4 Iron', '5 Iron', '6 Iron', '7 Iron', '8 Iron', '9 Iron',
              '3i', '4i', '5i', '6i', '7i', '8i', '9i'}
WEDGE_CLUBS = {'PW', 'Pitching Wedge', 'GW', 'Gap Wedge', 'SW', 'Sand Wedge',
               'LW', 'Lob Wedge', '52', '54', '56', '58', '60'}

def detect_session_type(clubs: List[str]) -> str:
    """
    Detect session type based on club distribution.

    Returns:
        'Driver Focus' if >60% driver shots
        'Iron Work' if >60% iron shots
        'Short Game' if >60% wedge shots
        'Mixed Practice' otherwise
    """
    if not clubs:
        return "Mixed Practice"

    total = len(clubs)
    normalized = [normalize_club_name(c) for c in clubs]

    driver_count = sum(1 for c in normalized if c in DRIVER_CLUBS or c == 'Driver')
    iron_count = sum(1 for c in normalized if c in IRON_CLUBS or 'Iron' in c)
    wedge_count = sum(1 for c in normalized if c in WEDGE_CLUBS or 'Wedge' in c)

    if driver_count / total > 0.6:
        return "Driver Focus"
    elif iron_count / total > 0.6:
        return "Iron Work"
    elif wedge_count / total > 0.6:
        return "Short Game"
    else:
        return "Mixed Practice"

def generate_session_name(session_date: datetime, clubs: List[str]) -> str:
    """
    Generate a meaningful session name.

    Format: "{YYYY-MM-DD} {session_type} ({shot_count} shots)"

    Examples:
        "2026-02-02 Driver Focus (25 shots)"
        "2026-01-28 Mixed Practice (45 shots)"
    """
    date_str = session_date.strftime("%Y-%m-%d")
    session_type = detect_session_type(clubs)
    shot_count = len(clubs)

    return f"{date_str} {session_type} ({shot_count} shots)"
```

**Step 4: Run tests to verify they pass**

Run:
```bash
./venv/bin/python -m unittest tests.unit.test_session_naming -v
```

Expected: All 3 tests pass

**Step 5: Commit naming implementation**

Run:
```bash
git add automation/naming_conventions.py tests/unit/test_session_naming.py
git commit -m "feat(naming): add session naming and type detection

- detect_session_type() categorizes by club distribution
- generate_session_name() creates readable session names
- Session types: Driver Focus, Iron Work, Short Game, Mixed Practice

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Backfill Existing Session Names

**Files:**
- Modify: `golf_db.py`
- Modify: `golf_stats.db`

**Step 1: Add batch update function to golf_db.py**

Add to `golf_db.py`:
```python
def batch_update_session_names():
    """
    Update session names for all sessions based on their shots.

    Returns:
        Number of sessions updated
    """
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Get all unique session IDs
    cursor.execute('SELECT DISTINCT session_id FROM shots WHERE session_id IS NOT NULL')
    session_ids = [row[0] for row in cursor.fetchall()]

    updated = 0
    for session_id in session_ids:
        # Get clubs and date for this session
        cursor.execute('''
            SELECT club, session_date FROM shots
            WHERE session_id = ? AND club IS NOT NULL
        ''', (session_id,))
        rows = cursor.fetchall()

        if not rows:
            continue

        clubs = [row[0] for row in rows]
        session_date_str = rows[0][1]

        if session_date_str:
            from datetime import datetime
            from automation.naming_conventions import generate_session_name

            try:
                session_date = datetime.strptime(session_date_str[:10], "%Y-%m-%d")
                new_name = generate_session_name(session_date, clubs)

                # Update sessions_discovered if report_id matches
                cursor.execute('''
                    UPDATE sessions_discovered
                    SET portal_name = ?
                    WHERE report_id = ?
                ''', (new_name, session_id))

                if cursor.rowcount > 0:
                    updated += 1
            except (ValueError, TypeError):
                continue

    conn.commit()
    conn.close()
    return updated
```

**Step 2: Run batch update**

Run:
```bash
./venv/bin/python -c "
import golf_db
golf_db.init_db()
updated = golf_db.batch_update_session_names()
print(f'Sessions renamed: {updated}')
"
```

Expected: Shows number of sessions renamed

**Step 3: Verify sample session names**

Run:
```bash
./venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('golf_stats.db')
cursor = conn.cursor()
cursor.execute('SELECT report_id, portal_name, session_date FROM sessions_discovered LIMIT 10')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} ({row[2]})')
"
```

Expected: Sessions have meaningful names like "2026-02-02 Driver Focus (25 shots)"

**Step 4: Commit batch update function**

Run:
```bash
git add golf_db.py
git commit -m "feat(db): add batch_update_session_names function

Generates meaningful session names based on club distribution:
- Driver Focus (>60% driver)
- Iron Work (>60% irons)
- Short Game (>60% wedges)
- Mixed Practice (no dominant club)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Final Verification

**Step 1: Run all tests**

Run:
```bash
./venv/bin/python -m unittest discover -s tests -v 2>&1 | tail -20
```

Expected: All tests pass

**Step 2: Verify database state**

Run:
```bash
./venv/bin/python -c "
import sqlite3
import golf_db
golf_db.init_db()

conn = sqlite3.connect('golf_stats.db')
cursor = conn.cursor()

print('=== Final Status ===')
cursor.execute('SELECT COUNT(*) FROM shots')
print(f'Total shots: {cursor.fetchone()[0]}')

cursor.execute('SELECT import_status, COUNT(*) FROM sessions_discovered GROUP BY import_status')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')

cursor.execute('SELECT COUNT(*) FROM sessions_discovered WHERE portal_name LIKE \"%Focus%\" OR portal_name LIKE \"%Practice%\" OR portal_name LIKE \"%Work%\" OR portal_name LIKE \"%Game%\"')
print(f'Sessions with meaningful names: {cursor.fetchone()[0]}')

s = golf_db.get_detailed_sync_status()
print(f'Sync status: Local={s[\"local_count\"]}, Supabase={s[\"supabase_count\"]}, Drift={s[\"drift_detected\"]}')
"
```

**Step 3: Commit research and documentation**

Run:
```bash
git add docs/research/
git commit -m "docs: add naming research and synthesis

Research phase analyzed:
- Portal naming patterns
- Date inconsistencies
- Club naming variations
- Codebase gaps

Synthesis produced unified naming schema.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Success Checklist

- [ ] Stage 1: Dry run completed without errors
- [ ] Stage 2: Validation passed (no null/future/old dates)
- [ ] Stage 3: 12 sessions backfilled successfully
- [ ] Stage 4: 4 research documents created
- [ ] Stage 4.5: SYNTHESIS.md with naming schema
- [ ] Stage 5: Naming functions implemented and tested
- [ ] Task 7: Existing sessions renamed
- [ ] Task 8: All tests pass, sync verified
