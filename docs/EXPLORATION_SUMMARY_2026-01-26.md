# Uneekor Portal Exploration Summary

**Date:** 2026-01-26
**Session:** Complete portal and report page exploration

---

## Executive Summary

### What We Discovered

| Item | Expected | Actual | Status |
|------|----------|--------|--------|
| Report page tabs | 7 tabs | 7 tabs | ✅ Fully documented |
| CSV API | Working | Working | ✅ Verified |
| Portal sessions | 30 (page 1 only) | **95 (23+ pages)** | ✅ FIXED - pagination implemented |
| Sessions in DB | 30 | 95 | ✅ Complete - all sessions discovered |

### Fixes Applied

**1. Pagination bug fixed in `automation/uneekor_portal.py`**

Discovery results after fix:
- **85 sessions discovered** in single run
- **65 NEW sessions** added to database
- **95 total sessions** now tracked
- Pages scanned: 1-23

**2. Controlled backfill with new CLI options**

New flags added to `automation_runner.py`:
- `--delay N` - Wait N seconds between imports
- `--recent` - Import newest sessions first

**3. First batch import complete (20 sessions)**

```bash
python3 automation_runner.py backfill --max 20 --recent --delay 300
```

Results:
- **20 sessions imported** successfully
- **1,136 new shots** added to database
- **0 failures**
- Duration: ~100 minutes (5 min between each)

---

## Where We Were Misled

### 1. Session Discovery Only Gets Page 1

**Initial Assumption:** Running `python3 automation_runner.py discover` gets all sessions.

**Reality:** The `UneekorPortalNavigator.get_all_sessions()` method in `automation/uneekor_portal.py`:
- Navigates to `https://my.uneekor.com/report`
- Scrapes links on that ONE page
- Returns results
- **NEVER clicks pagination buttons**

The SELECTORS dictionary includes pagination selectors (lines 103-104), but they're never used!

```python
# Defined but NEVER USED:
'next_page': 'button:has-text("Next"), a:has-text("Next"), [class*="next"]',
'page_indicator': '.pagination, [class*="page"]',
```

### 2. Database Shows Partial Data

**Initial Assumption:** Database has all discovered sessions.

**Reality:**
- Database has 30 sessions
- Portal has 80 sessions across 8 pages
- 50 sessions have NEVER been discovered

### 3. Discovery Output Was Misleading

The discovery output showed:
```
Total discovered:  20
New sessions:      0
Already known:     20
```

This made it LOOK like we had everything, but actually:
- It only checked page 1 (10 sessions)
- Some sessions were duplicates (appearing in both "Unnamed" and "Open" sections)
- 70+ sessions on pages 2-8 were never checked

---

## Actual Portal Structure

### Session Listing Page

**URL:** `https://my.uneekor.com/report`

**Layout:**
```
+--------------------------------------------------+
| Reports                                          |
+--------------------------------------------------+
| [Session 1] [Session 2] ... [Session 10]         |  <- 10 per page
+--------------------------------------------------+
| [1] [2] [3] [4] [5] [6] [7] [8]                   |  <- Pagination buttons
+--------------------------------------------------+
```

### Pagination Statistics (Updated After Fix)

| Metric | Before Fix | After Fix |
|--------|------------|-----------|
| Sessions per page | ~5 | ~5 |
| Total pages scanned | 1 | 23 |
| Sessions discovered | 30 | 95 |
| Missing sessions | ~65 | **0** ✅ |

---

## Report Page Structure (Fully Documented)

### 7 Tabs Explored

| Tab | Purpose | Key Data |
|-----|---------|----------|
| Summary | Statistics | Avg/Max aggregates |
| Side | Trajectory | Side-view ball flight |
| Top | Dispersion | Bird's eye pattern |
| Group | Clustering | Shot scatter with ellipse |
| Club | D-Plane | Attack angle, face angle, club path |
| Optix | Impact | High-speed camera frames |
| Swing | Annotation | Drawing canvas for video |

### Interactive Elements Verified

| Element | Location | Behavior |
|---------|----------|----------|
| Shot navigator | Metrics cards | Cycles through shots |
| Row click | Shot table | Selects shot |
| Eye icon | Each row | Toggle visibility |
| Export buttons | Above table | Download data |

### API Export URLs (Critical Discovery)

The export buttons expose direct API endpoints:

```
CSV Export (all shots):
https://api-v2.golfsvc.com/v2/oldmyuneekor/report/export/allsessions/{id}/{key}/yard/mph

Shot Data (single shot):
https://api-v2.golfsvc.com/v2/oldmyuneekor/report/export/shotdata/{id}/{key}/{session}/{shot}/yard/mph

Swing Video:
https://api-v2.golfsvc.com/v2/oldmyuneekor/report/export/swingoptix/{id}/{key}/{session}/{shot}
```

**KEY INSIGHT:** CSV API returns 17 columns with complete shot data - no browser scraping needed!

---

## Database State

### Current Inventory (After First Batch Import)

```sql
SELECT import_status, COUNT(*)
FROM sessions_discovered
GROUP BY import_status;
```

| Status | Count | Notes |
|--------|-------|-------|
| pending | 70 | Ready for next batch |
| imported | 25 | Successfully imported |
| **Total** | **95** | ✅ Complete discovery |

### Import Statistics

| Metric | Value |
|--------|-------|
| Total sessions imported | 25 |
| Total shots in database | 1,341 |
| Sessions remaining | 70 |

### Top Sessions by Shot Count

| Session ID | Shots |
|------------|-------|
| 42646 | 112 |
| 41422 | 100 |
| 42924 | 88 |
| 43032 | 87 |
| 41360 | 85 |

---

## Fixes Applied

### 1. ✅ Pagination Added to Session Discovery

**File:** `automation/uneekor_portal.py`
**Method:** `get_all_sessions()` - Modified to loop through all pagination pages
**New Method:** `_find_pagination_button()` - Finds page number buttons

Key changes:
- Added `while True` loop to iterate pages
- Added `seen_report_ids` set to deduplicate sessions
- Added `_find_pagination_button()` helper with multiple selector strategies
- Added verbose logging for debugging

### 2. ✅ Discovery Re-run Complete

```bash
python3 automation_runner.py discover --headless
```

Results:
- **85 sessions discovered** (vs. 30 before)
- **65 new sessions** added to tracking database
- **23 pages scanned** (vs. 1 before)

### 3. ✅ First Batch Import Complete

```bash
python3 automation_runner.py backfill --max 20 --recent --delay 300
```

Run ID: `bf_fa50dce4`
- 20 sessions imported
- 1,136 shots added
- 0 failures

### 4. Pending: Import Remaining Sessions

```bash
python3 automation_runner.py backfill --max 70 --recent --delay 300
```

70 sessions ready for import.

---

## Verification Checklist

- [x] Report page tabs (7/7 documented)
- [x] Interactive elements (all verified)
- [x] Export API (CSV tested, working)
- [x] Field mapping (22 fields mapped)
- [x] **Portal pagination (FIXED - `_find_pagination_button()` method added)**
- [x] **Full session inventory (95 sessions discovered)**
- [x] **First batch import (20 sessions, 1,136 shots)**
- [ ] Import remaining sessions (70 pending)
- [ ] Session date reclassification from report page

---

## Files Modified

| File | Changes |
|------|---------|
| `docs/UNEEKOR_REPORT_PAGE_MAP.md` | Added tab details, interactive elements, field mapping |
| `docs/EXPLORATION_SUMMARY_2026-01-26.md` | This summary document |
| `automation/uneekor_portal.py` | **FIXED:** Added pagination loop, `_find_pagination_button()` method |
| `automation/backfill_runner.py` | Added `delay_seconds` and `recent_first` config options |
| `automation/session_discovery.py` | Added `recent_first` parameter to `get_pending_sessions()` |
| `automation_runner.py` | Added `--delay` and `--recent` CLI flags |
| `docs/tutorials/REPORT_PAGE_TUTORIAL.md` | **NEW:** Visual guide to report tabs |
| `docs/tutorials/SHOT_DATA_REFERENCE.md` | **NEW:** 764-line metrics reference |
| `docs/tutorials/AUTOMATION_ARCHITECTURE.md` | **NEW:** Automation system roadmap |

---

## Lessons Learned

1. **Always verify pagination** - Don't assume "discover" means "discover all"
2. **Check scroll/pagination at bottom of web pages** - The user correctly identified pagination was visible
3. **Validate database counts against source** - 30 sessions in DB should have been questioned against portal count
4. **Test automation outputs manually** - The discovery reported success but was incomplete

---

## Next Steps

1. ~~**Fix pagination bug** in `automation/uneekor_portal.py`~~ ✅ DONE
2. ~~**Re-run discovery** to get all sessions~~ ✅ DONE (95 sessions found)
3. ~~**Add controlled import options** (`--delay`, `--recent`)~~ ✅ DONE
4. ~~**First batch import** (20 sessions)~~ ✅ DONE (1,136 shots)
5. **Session date reclassification** - Extract dates from report page
6. **Import remaining sessions** (70 pending)
7. **Validate** database has all sessions after import

## Tailscale Access

The Streamlit app is running and accessible via Tailscale:
```
http://100.102.92.28:8501
http://ducks-macbook-pro-2:8501
```
