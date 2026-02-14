# Data Model & UX Overhaul — Design Document

**Date:** 2026-02-13
**Status:** Approved
**Approach:** Bottom-Up Data Fix (Approach A)

## Problem Statement

82% of `club` column values in the `shots` table are **session names** (courses, drills, warmups), not actual club names. The Uneekor API returns data grouped by user-defined session names (e.g., "Sgt Rd1", "Warmup 50", "Bag Mapping"), and the scraper at `golf_scraper.py:142-184` stores these directly as the `club` field.

This breaks every downstream view: Club Profiles shows ~60+ entries mixing clubs, courses, and drills; the Dashboard averages 3-yard wedge shots with 324-yard driver shots; the radar chart compares nonsense.

### Data Breakdown

| Category | Shots | Percentage |
|----------|-------|------------|
| Already normalized (standard club name) | 241 | 18.0% |
| Session names (not club names) | 1,072 | 80.2% |
| Uneekor default format (`IRON7 \| MEDIUM`) | 20 | 1.5% |

### Additional Issues

- Two date formats in `shots.session_date` (YYYY-MM-DD vs ISO with T)
- 226 shots with wrong dates (Jan 28 instead of actual dates)
- `SessionContextParser` is dead code (handles 246 shots but unused)
- Session names generated from import date, not session date
- `datetime.utcnow()` fallback creates misleading session names
- Three independent normalization approaches in the codebase

## Architecture

The fix follows a bottom-up approach: clean data first, then rebuild UI on the clean foundation. Each phase is independently valuable and testable.

```
Phase 1: Data Model Fix
  └── Phase 2: Date Cleanup
       └── Phase 3: Session Type System
            └── Phase 4: Dashboard Rebuild
                 └── Phase 5: Club Profiles Rebuild
                      └── Phase 6: Big 3 & UX Polish
                           └── Phase 7: Advanced Features
```

---

## Phase 1: Data Model Fix (Foundation)

### 1a. Schema Change

Add `original_club_value` column to `shots` table to preserve raw Uneekor values:

```sql
ALTER TABLE shots ADD COLUMN original_club_value TEXT;
```

Add to both SQLite (`golf_db.init_db()`) and Supabase schema (`supabase_schema.sql`).

### 1b. Fix ClubNameNormalizer

Add 3 missing pattern categories to `automation/naming_conventions.py`:

**Uneekor default format** (20 shots):
```python
# IRON7 | MEDIUM -> 7 Iron
(r'^(iron|wood|hybrid|driver|wedge)(\d*)\s*\|.*$', handler)
```

**Reversed forms** (~30 shots):
```python
# Wedge Pitching -> PW, Wedge 50 -> GW
(r'^wedge\s*(pitching|sand|lob|gap|approach)$', handler)
(r'^wedge\s*(\d{2})$', handler)
```

**No-space iron** (~12 shots):
```python
# Iron7 -> 7 Iron
(r'^iron(\d)$', handler)
```

### 1c. Integrate SessionContextParser

Wire `SessionContextParser` into the normalization pipeline. Currently dead code (lines 495-657 in `naming_conventions.py`).

**Pipeline logic:**
1. Try `ClubNameNormalizer` first
2. If confidence < 0.5, fall back to `SessionContextParser.extract_club()`
3. Store extracted session context (warmup, drill, sim_round) for Phase 3

**Handles 246 shots** with embedded club hints:
- `Warmup PW` → club=PW, context=warmup
- `Dst Compressor 8` → club=8 Iron, context=drill
- `Wedge 50` → club=GW
- `8 Iron Dst Trainer` → club=8 Iron, context=drill

### 1d. Data Migration Script

One-time migration (`utils/migrate_club_data.py`):

1. Copy current `club` → `original_club_value` for all rows
2. Run enhanced normalizer on all 1,337 shots
3. For 657 shots with pure session names (no extractable club): set `club = "Unknown"`
4. Log all changes to `change_log` table
5. Print summary report: shots fixed, confidence levels, unresolvable sessions

**Categories after migration:**

| Status | Shots | Action |
|--------|-------|--------|
| Already correct | 241 | No change |
| Uneekor format fixed | 20 | Normalize |
| Embedded club extracted | ~246 | SessionContextParser |
| Missing patterns fixed | ~30 | New normalizer patterns |
| Pure session names | ~657 | Set to "Unknown" |
| Other edge cases | ~143 | Manual review list |

### 1e. Normalize at Import Time

Add normalization inside `golf_db.add_shot()` so all import paths are covered:

```python
def add_shot(self, data):
    # Normalize club name before storage
    raw_club = data.get('club', 'Unknown')
    data['original_club_value'] = raw_club
    normalized = self._normalize_club(raw_club)
    data['club'] = normalized.canonical_name
    # ... existing logic
```

### 1f. Consolidate Normalizers

Remove inline `normalize_club_name()` function in `pages/4_⚙️_Settings.py` (Database Manager tab). Replace with `ClubNameNormalizer` to prevent logic drift.

---

## Phase 2: Date Cleanup

### 2a. Standardize Date Format

All `shots.session_date` to `YYYY-MM-DD` (date-only string):

```sql
UPDATE shots SET session_date = SUBSTR(session_date, 1, 10)
WHERE session_date LIKE '%T00:00:00';
```

Fix code paths:
- `golf_db.backfill_session_dates()`: Strip time component before writing
- `golf_scraper.py:183`: Use `strftime('%Y-%m-%d')` instead of `isoformat()`

### 2b. Fix Known Wrong Dates

226 shots across 4 sessions have `session_date = 2026-01-28` but were imported Jan 26:

```bash
python automation_runner.py reclassify-dates --manual 43033 2026-01-26
python automation_runner.py reclassify-dates --manual 43032 2026-01-26
python automation_runner.py reclassify-dates --manual 42924 2026-01-26
python automation_runner.py reclassify-dates --manual 42719 2026-01-26
```

Mark 2 `report_page` sessions (20842, 20718) as unverified — their dates are ~18 months wrong.

### 2c. Fix datetime.utcnow() Fallback

In `backfill_runner.py:612`:

```python
# Before (misleading):
session_date=item.session_date or datetime.utcnow(),

# After (explicit):
session_date=item.session_date,  # May be None
```

Update `SessionNamer.generate_name()` to handle `None` dates with "Unknown Date" placeholder.

### 2d. Regenerate Session Names

Run `batch_update_session_names()` with corrected dates. New format: `"2026-01-25 Mixed Practice (47 shots)"`.

---

## Phase 3: Session Type System

### 3a. Distribution-Based Session Typing

Add `detect_session_type(clubs: List[str]) -> str` to `SessionNamer`:

| Condition | Session Type |
|-----------|-------------|
| >60% driver shots | Driver Focus |
| >60% iron shots | Iron Work |
| >60% wedge shots | Short Game |
| >60% wood shots | Woods Focus |
| shot_count < 10 | Warmup |
| No dominant club category | Mixed Practice |

Club categories use canonical names from `ClubNameNormalizer`:

```python
DRIVER_CLUBS = {'Driver'}
IRON_CLUBS = {'1 Iron', '2 Iron', '3 Iron', '4 Iron', '5 Iron',
              '6 Iron', '7 Iron', '8 Iron', '9 Iron'}
WEDGE_CLUBS = {'PW', 'GW', 'SW', 'LW'}
WOOD_CLUBS = {'3 Wood', '5 Wood', '7 Wood'}
HYBRID_CLUBS = {'3 Hybrid', '4 Hybrid', '5 Hybrid', '6 Hybrid'}
```

Falls back to count-based `infer_session_type()` when clubs are "Unknown".

### 3b. My Bag Configuration

`my_bag.json` in project root (user-editable):

```json
{
  "clubs": [
    {"canonical": "Driver", "aliases": ["DR", "1W"]},
    {"canonical": "3 Wood", "aliases": ["3W"]},
    {"canonical": "1 Iron", "aliases": ["1I"]},
    {"canonical": "6 Iron", "aliases": ["6I"]},
    {"canonical": "7 Iron", "aliases": ["7I"]},
    {"canonical": "8 Iron", "aliases": ["8I"]},
    {"canonical": "9 Iron", "aliases": ["9I"]},
    {"canonical": "PW", "aliases": ["Pitching Wedge"]},
    {"canonical": "GW", "aliases": ["50", "Gap Wedge", "50 Degree"]},
    {"canonical": "SW", "aliases": ["56", "Sand Wedge"]},
    {"canonical": "LW", "aliases": ["60", "Lob Wedge"]}
  ],
  "bag_order": ["Driver", "3 Wood", "1 Iron", "6 Iron", "7 Iron", "8 Iron", "9 Iron", "PW", "GW", "SW", "LW"]
}
```

Used by Club Profiles and Dashboard to filter and order clubs.

### 3c. Session Display Names

Format: `{YYYY-MM-DD} {SessionType} ({shot_count} shots)`

Examples:
- `2026-01-25 Mixed Practice (47 shots)`
- `2026-01-15 Driver Focus (25 shots)`
- `Unknown Date - Iron Work (62 shots)`

Handle duplicates with sequence numbers: `2026-01-26 Practice (48 shots) #2`

---

## Phase 4: Dashboard Rebuild

### 4a. Training Log Landing Page

Replace single-session view in `app.py` with "Recent Activity" overview:

- **Hero stats row** (existing 2x2 grid): total sessions, total shots, avg carry, avg smash
- **Recent sessions list**: last 5-7 sessions as cards showing:
  - Date + session type tag (color-coded)
  - Shot count + highlight stat (best carry or avg smash)
  - Click to expand into session detail
- **Calendar strip** (existing): keep practice frequency visualization

### 4b. Session Selector

Move session selection from bottom of sidebar to main content area:
- Dropdown with human-readable names: `"Iron Work — Feb 10 (25 shots)"`
- Group by week (matching existing journal view pattern)

### 4c. Dynamic Targets

Per-club smash factor targets instead of hardcoded 1.50:

| Club | Target Smash |
|------|-------------|
| Driver | 1.48-1.50 |
| 3 Wood | 1.44-1.46 |
| Irons (long) | 1.34-1.38 |
| Irons (mid) | 1.30-1.34 |
| Irons (short) | 1.26-1.30 |
| Wedges | 1.20-1.25 |

Store in `my_bag.json` or derive from club type.

### 4d. Clean Up Sidebar

Move technical controls to Settings page:
- Remove Data Source, Read Mode, SQLite/Supabase indicators from sidebar
- Sidebar: navigation + context-relevant filters only
- Consolidate duplicate navigation

---

## Phase 5: Club Profiles Rebuild

### 5a. Filter to Real Clubs

Club dropdown shows only clubs from `my_bag.json`, not session names:
- Organized in bag order: Driver → Woods → Hybrids → Irons → Wedges
- Visual "bag" card layout instead of giant dropdown (optional)
- Shots with `club = "Unknown"` excluded from club-specific views

### 5b. Smart Comparison

Default comparison suggestions based on bag position:
- Viewing 7 Iron → suggest 6 Iron, 8 Iron
- Viewing Driver → suggest 3 Wood
- Never suggest non-club entries

### 5c. Fix Chart Issues

- Fix Distance Over Time x-axis labels (timestamp formatting bug)
- Clean date formatting throughout

---

## Phase 6: Big 3 & UX Polish

### 6a. Visual Fixes

- Increase contrast on Big 3 summary cards (dark text on light cards or light text on dark cards)
- Add quadrant labels to D-Plane scatter plot: Draw, Fade, Pull, Push

### 6b. New Visualizations

- Shot-by-shot trend lines within a session (face angle/club path progression across shot numbers 1-N)
- Fatigue/warmup analysis: "getting better as you warm up or worse as you fatigue?"

### 6c. Date Range Filtering

- Global date range filter: "this week", "last month", "custom range"
- Affects Dashboard, Club Profiles, and Big 3 views

### 6d. Session Notes

- Add `notes` to `ALLOWED_UPDATE_FIELDS` in `golf_db.py`
- Text input in session detail view
- Stored in `shots` table (per-session, applied to all shots in session) or `sessions_discovered`

---

## Phase 7: Advanced Features

### 7a. Trajectory Visualization

2D side-view trajectory overlay:
- X-axis: horizontal distance (yards)
- Y-axis: height (using apex, launch angle, descent angle)
- Multiple shots overlaid for consistency visualization

### 7b. Shot-by-Shot Navigation

Arrow button navigation through individual shots:
- Full shot details + mini trajectory
- Previous/next within session

### 7c. Goal Tracking

- Set goals per club: "get 7-iron carry to 165 yards"
- Track progress over sessions
- Visual progress bar on Club Profiles

---

## Files Modified Per Phase

### Phase 1
| File | Change |
|------|--------|
| `golf_db.py` | Add `original_club_value` column, normalize in `add_shot()` |
| `automation/naming_conventions.py` | Add 3 pattern categories, wire SessionContextParser |
| `supabase_schema.sql` | Add `original_club_value` column |
| `utils/migrate_club_data.py` | New: one-time migration script |
| `pages/4_⚙️_Settings.py` | Remove inline normalizer, use ClubNameNormalizer |

### Phase 2
| File | Change |
|------|--------|
| `golf_db.py` | Fix `backfill_session_dates()` date format |
| `golf_scraper.py` | Fix line 183 date format |
| `automation/backfill_runner.py` | Fix `datetime.utcnow()` fallback |
| `automation/naming_conventions.py` | Handle None dates in `generate_name()` |

### Phase 3
| File | Change |
|------|--------|
| `automation/naming_conventions.py` | Add `detect_session_type()`, `generate_display_name()` |
| `my_bag.json` | New: bag configuration |
| `utils/bag_config.py` | New: bag config loader |

### Phase 4
| File | Change |
|------|--------|
| `app.py` | Rebuild as training log |
| `components/session_card.py` | New or update journal_card |

### Phase 5
| File | Change |
|------|--------|
| `pages/2_🏌️_Club_Profiles.py` | Filter to bag clubs, smart comparison |

### Phase 6
| File | Change |
|------|--------|
| `components/big3_summary.py` | Contrast fix |
| `components/face_path_diagram.py` | Quadrant labels |
| `components/shot_trends.py` | New: within-session trend lines |
| `golf_db.py` | Add `notes` to allowed fields |

### Phase 7
| File | Change |
|------|--------|
| `components/trajectory_view.py` | New: 2D trajectory |
| `components/shot_navigator.py` | New: shot-by-shot detail |
| `utils/goal_tracker.py` | New: goal tracking logic |

---

## Testing Strategy

- Phase 1: Unit tests for new normalizer patterns, SessionContextParser integration, migration script dry-run
- Phase 2: Test date standardization with known edge cases
- Phase 3: Test session type detection with various club distributions
- Phase 4-7: Manual testing with screenshots for UI changes

## Success Criteria

- Club Profiles dropdown shows only real clubs (11-14 entries, not 60+)
- Dashboard shows meaningful session summaries with correct dates
- Big 3 metrics only computed on shots with known clubs
- No session names appear in club-related views
- All existing tests continue to pass
