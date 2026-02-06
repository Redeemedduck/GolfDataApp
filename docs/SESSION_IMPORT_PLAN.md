# Session Import & Classification Plan

**Created**: 2026-01-26
**Status**: Ready for Execution

---

## Current State

| Metric | Count | Notes |
|--------|-------|-------|
| Total shots imported | 1,341 | Across 25 sessions |
| Sessions imported | 25 | In shots table |
| Sessions pending | 70 | Discovered but not imported |
| Sessions missing dates | 95 | In sessions_discovered |
| Shots missing session_date | 1,341 | All existing shots (column just added) |

---

## Goals

1. **Fix session dates** for all 95 sessions missing dates
2. **Import remaining 70 sessions** with proper dates
3. **Normalize all club names** consistently
4. **Auto-tag sessions** for categorization
5. **Backfill session_date** to existing shots

---

## Phase 1: Date Reclassification (Priority: HIGH)

### Step 1.1: Backfill Existing Dates

First, copy any dates already captured in `sessions_discovered` to the `shots` table:

```bash
python automation_runner.py reclassify-dates --backfill
```

**Expected Result**: Some shots will get session_date from sessions_discovered.

### Step 1.2: Check Status

```bash
python automation_runner.py reclassify-dates --status
```

This shows:
- Sessions with dates vs. without
- Shots needing date updates

### Step 1.3: Scrape Missing Dates from Report Pages

For sessions still missing dates, scrape from Uneekor report page headers:

```bash
# Preview first
python automation_runner.py reclassify-dates --scrape --max 5 --dry-run

# Start with small batch
python automation_runner.py reclassify-dates --scrape --max 10 --delay 300

# Continue in batches (5-min delay between = ~5 hours for 60 sessions)
python automation_runner.py reclassify-dates --scrape --max 20 --delay 300
```

**Rate Limiting**:
- Default 5-minute delay between scrapes
- 95 sessions ÷ 12/hour = ~8 hours total
- Can run overnight or in batches

### Step 1.4: Manual Date Entry for Known Sessions

For sessions where you know the date, set manually:

```bash
python automation_runner.py reclassify-dates --manual <REPORT_ID> <YYYY-MM-DD>

# Examples:
python automation_runner.py reclassify-dates --manual 41245 2025-06-15
python automation_runner.py reclassify-dates --manual 41360 2025-07-02
```

---

## Phase 2: Import Pending Sessions (Priority: HIGH)

### Step 2.1: Preview Pending Imports

```bash
python automation_runner.py backfill --start 2024-01-01 --dry-run
```

This shows what would be imported without making changes.

### Step 2.2: Import in Batches

Import sessions with rate limiting to avoid portal issues:

```bash
# Start with recent sessions first
python automation_runner.py backfill --start 2025-01-01 --max 10 --recent --delay 300

# Continue with more
python automation_runner.py backfill --start 2025-01-01 --max 20 --delay 300

# Or import all at once (slower, ~6 hours for 70 sessions)
python automation_runner.py backfill --start 2024-01-01 --delay 300
```

### Step 2.3: Filter by Club (Optional)

If you want to focus on specific clubs first:

```bash
# Import only Driver and 7 Iron sessions
python automation_runner.py backfill --start 2025-01-01 --clubs "Driver,7 Iron"
```

### Step 2.4: Handle Failed Imports

After initial import, retry any failures:

```bash
python automation_runner.py backfill --retry-failed
```

---

## Phase 3: Club Name Normalization (Priority: MEDIUM)

### Step 3.1: Preview Normalization

```bash
python automation_runner.py normalize --test "7i,DR,pw,56 deg"
```

### Step 3.2: Verify Clubs in Database

```bash
sqlite3 golf_stats.db "SELECT DISTINCT club, COUNT(*) as shots FROM shots GROUP BY club ORDER BY shots DESC;"
```

### Step 3.3: Apply Normalization During Import

Normalization is applied automatically during backfill unless disabled:

```bash
# With normalization (default)
python automation_runner.py backfill --start 2025-01-01

# Without normalization
python automation_runner.py backfill --start 2025-01-01 --no-normalize
```

---

## Phase 4: Session Analysis & Tagging (Priority: MEDIUM)

### Step 4.1: Review Auto-Tags

Auto-tagging is applied during import. Tags include:
- `Driver Focus` - Only driver used
- `Short Game` - Only wedges used
- `Full Bag` - 10+ clubs used
- `High Volume` - 100+ shots
- `Iron Work` - All irons, 3+ clubs
- `Woods Focus` - Multiple woods

### Step 4.2: Verify Tags

```bash
sqlite3 golf_stats.db "SELECT tags_json, COUNT(*) FROM sessions_discovered WHERE tags_json IS NOT NULL GROUP BY tags_json;"
```

### Step 4.3: Session Type Classification

Session types are inferred:
- `Warmup` - <10 shots
- `Drill` - 1-2 clubs, >30 shots
- `Fitting` - 1 club, >50 shots
- `Practice` - 3+ clubs

---

## Phase 5: Verification (Priority: HIGH)

### Step 5.1: Run Full Status Check

```bash
python automation_runner.py status
```

### Step 5.2: Verify Date Coverage

```bash
# Check sessions with dates
sqlite3 golf_stats.db "SELECT COUNT(*) FROM sessions_discovered WHERE session_date IS NOT NULL;"

# Check shots with dates
sqlite3 golf_stats.db "SELECT COUNT(*) FROM shots WHERE session_date IS NOT NULL;"

# Check date distribution
sqlite3 golf_stats.db "SELECT strftime('%Y-%m', session_date) as month, COUNT(*) FROM shots WHERE session_date IS NOT NULL GROUP BY month ORDER BY month;"
```

### Step 5.3: Verify Club Normalization

```bash
sqlite3 golf_stats.db "SELECT DISTINCT club FROM shots ORDER BY club;"
```

Expected output should show normalized names:
- `Driver` (not "DR", "1W", "driver")
- `7 Iron` (not "7i", "7 iron", "Iron 7")
- `PW` (not "pw", "pitching wedge")

### Step 5.4: Test UI

```bash
streamlit run app.py
```

Verify:
1. **Dashboard Trends tab** - Shows data plotted by actual session date
2. **AI Coach session picker** - Shows session dates, not import dates
3. **Data Import history** - Shows actual session dates

---

## Execution Timeline

### Day 1: Date Reclassification
| Time | Task | Command |
|------|------|---------|
| 0:00 | Backfill existing dates | `reclassify-dates --backfill` |
| 0:05 | Check status | `reclassify-dates --status` |
| 0:10 | Start scraping (batch 1) | `reclassify-dates --scrape --max 20` |
| 2:00 | Continue scraping (batch 2) | `reclassify-dates --scrape --max 20` |
| 4:00 | Continue scraping (batch 3) | `reclassify-dates --scrape --max 20` |
| 6:00 | Final batch | `reclassify-dates --scrape --max 35` |
| 8:00 | Manual fixes for any remaining | `reclassify-dates --manual ...` |

### Day 2: Import Pending Sessions
| Time | Task | Command |
|------|------|---------|
| 0:00 | Preview imports | `backfill --start 2024-01-01 --dry-run` |
| 0:05 | Import batch 1 (recent) | `backfill --start 2025-06-01 --max 20 --recent` |
| 2:00 | Import batch 2 | `backfill --start 2025-01-01 --max 20` |
| 4:00 | Import batch 3 | `backfill --start 2024-01-01 --max 30` |
| 6:00 | Retry failures | `backfill --retry-failed` |
| 7:00 | Final verification | `status` + UI testing |

---

## Troubleshooting

### "Cookies expired"
```bash
python automation_runner.py login
```

### "Rate limited"
Wait 30 minutes, then resume. The system uses exponential backoff automatically.

### "Session already imported"
Normal - deduplication is working. The session will be skipped.

### "No date found on report page"
Use manual entry:
```bash
python automation_runner.py reclassify-dates --manual <REPORT_ID> <DATE>
```

### Database integrity check
```bash
sqlite3 golf_stats.db "PRAGMA integrity_check;"
```

---

## Post-Import Checklist

- [ ] All 95 sessions have dates
- [ ] All 1341+ shots have session_date
- [ ] 70 pending sessions imported
- [ ] Club names normalized
- [ ] Sessions auto-tagged
- [ ] Trend chart shows accurate dates
- [ ] AI Coach session picker works
- [ ] No failed imports remaining

---

## Quick Commands Reference

```bash
# Status checks
python automation_runner.py status
python automation_runner.py reclassify-dates --status
python automation_runner.py backfill --status

# Date management
python automation_runner.py reclassify-dates --backfill
python automation_runner.py reclassify-dates --scrape --max 20 --delay 300
python automation_runner.py reclassify-dates --manual <ID> <DATE>

# Import
python automation_runner.py backfill --start 2024-01-01 --dry-run
python automation_runner.py backfill --start 2024-01-01 --delay 300
python automation_runner.py backfill --retry-failed

# Verification
sqlite3 golf_stats.db "SELECT COUNT(*) FROM shots WHERE session_date IS NOT NULL;"
sqlite3 golf_stats.db "SELECT import_status, COUNT(*) FROM sessions_discovered GROUP BY import_status;"
```

---

**Next Step**: Run `python automation_runner.py reclassify-dates --status` to see current state.

---

## Known Issues

### Issue: "No date found on report page" (2026-01-26)

**Status**: OPEN - Needs investigation

**Symptom**:
```
[1/1] Scraping 16206...
  No date found on report page
```

**Root Cause**: The `extract_date_from_report_page()` method in `automation/uneekor_portal.py` is not finding dates. Possible causes:
1. CSS selectors don't match current Uneekor page structure
2. Page needs more load time before extracting
3. Date format/location changed on Uneekor portal
4. Session 16206 may genuinely have no date displayed

**Investigation Needed**:
1. Manually visit `https://my.uneekor.com/report?id=16206&key=...` to see page structure
2. Check if date is visible in browser and what format it uses
3. Update selectors in `extract_date_from_report_page()` if needed
4. Consider adding longer wait time or different selectors

**Workaround**: Use `--manual` to set dates for known sessions:
```bash
python automation_runner.py reclassify-dates --manual 16206 2025-06-15
```

**Files to Investigate**:
- `automation/uneekor_portal.py` lines 521-585 (`extract_date_from_report_page`)
- `docs/UNEEKOR_REPORT_PAGE_MAP.md` - portal structure documentation

---

## Resume Instructions

To pick up where we left off:

1. **Check current status**:
   ```bash
   python automation_runner.py reclassify-dates --status
   ```

2. **Investigate the scraping issue**:
   - Open Uneekor portal manually
   - Navigate to a report page
   - Inspect where date is displayed
   - Update selectors in `uneekor_portal.py`

3. **Alternative: Use manual date entry**:
   ```bash
   python automation_runner.py reclassify-dates --manual <REPORT_ID> <DATE>
   ```

4. **Continue with imports after fixing dates**:
   ```bash
   python automation_runner.py backfill --start 2024-01-01 --dry-run
   ```
