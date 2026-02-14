# Session Handoff: Scraper Fix + Clean Re-import

**Date:** 2026-02-13 (completed 2026-02-14)
**Status:** COMPLETE — All 6 tasks done

---

## How to Resume

Say: **"Read `docs/plans/2026-02-13-scraper-fix-handoff.md` and continue execution"**

The full implementation plan is at: `docs/plans/2026-02-13-scraper-fix-reimport-plan.md`
The design doc is at: `docs/plans/2026-02-13-scraper-fix-reimport-design.md`

---

## What We're Doing

Fixing the GolfDataApp scraper to use correct fields from the Uneekor API, then re-importing all data with accurate club names and dates.

### The Problem (Solved)

- 55% of 2,159 shots had `club=NULL` because the scraper read `session.get('name')` (sidebar label like "warmup") instead of `session.get('club_name')` (Uneekor internal name like "WEDGE_PITCHING")
- Session dates came from listing page instead of API's `client_created_date` field

### The Discovery

The Uneekor API at `https://api-v2.golfsvc.com/v2/oldmyuneekor/report/{id}/{key}` returns per-club-group:
```json
{
    "name": "warmup",                    // sidebar label (what scraper used — WRONG)
    "club_name": "WEDGE_PITCHING",       // internal name (what we need — CORRECT)
    "club": 28,                          // numeric club ID
    "client_created_date": "2026-01-25", // actual session date (CORRECT)
    "shots": [...]
}
```

### Special Mappings (User-confirmed)

- **IRON1 → "Sim Round"** — User selects "1 Iron" as default during sim golf rounds. These shots are mixed clubs (Driver, irons, wedges). Cannot be assigned to a specific club.
- **IRON3 → "3 Iron"** — This is the actual 3 Iron driving iron (user's most-used club)
- **WOOD2 → "3 Wood (Cobra)"**, **WOOD3 → "3 Wood (TM)"** — Two different 3 Woods, kept separate
- **HYBRID1, HYBRID3, WEDGE_54 → "Other"** — Testing/fitting, not in bag

---

## Execution Progress

Using **Subagent-Driven Development** pattern: fresh subagent per task with spec + code quality review.

| Task | Status | Commit | Notes |
|------|--------|--------|-------|
| 1. Add Uneekor-to-canonical club mapping | **DONE** | `9c7247db` | `UNEEKOR_TO_CANONICAL` dict + `map_uneekor_club()` in `naming_conventions.py`. 23 tests. |
| 2. Update my_bag.json and bag_config | **DONE** | `9eb6e84e` | 16 clubs + 2 special categories. `get_uneekor_mapping()`, `get_special_categories()`. 11 tests. |
| 3. Add database schema columns | **DONE** | `168ae8d4` | `sidebar_label TEXT`, `uneekor_club_id INTEGER` in migration + save_shot + ALLOWED_UPDATE_FIELDS. 3 tests. |
| 4. Fix golf_scraper.py | **DONE** | `7349b51c` | Uses `club_name` → `map_uneekor_club()`. Uses `client_created_date`. Stores sidebar_label. 3 tests. |
| 5. Add reimport-all CLI command | **DONE** | `a20e6df1` | `python automation_runner.py reimport-all [--dry-run]`. 5% failure threshold. 2 tests. |
| 6. Run clean re-import | **DONE** | — | 126 sessions, 5,578 shots, 0 NULL clubs, 0 errors. |

---

## Key Files

| File | Role | Changes Needed |
|------|------|----------------|
| `automation/naming_conventions.py` | Club name normalization | **DONE** — `UNEEKOR_TO_CANONICAL` + `map_uneekor_club()` |
| `my_bag.json` | Bag configuration | **DONE** — 16 clubs + 2 special categories |
| `utils/bag_config.py` | Bag config loader | **DONE** — `get_uneekor_mapping()`, `get_special_categories()` |
| `golf_db.py` | Database layer | **DONE** — `sidebar_label`, `uneekor_club_id` columns |
| `golf_scraper.py` | Scraper (the core fix) | **DONE** — Uses `club_name`, `client_created_date` |
| `automation_runner.py` | CLI | **DONE** — `reimport-all` command |

---

## Codex Review Findings (Incorporated into Plan)

6 gaps identified, all addressed:
1. BackfillRunner skips imported sessions → standalone reimporter bypasses queue
2. save_shot() silently swallows errors → add error counting with 5% failure threshold
3. Shot ID collision risk → keep numeric group `id` as middle token (no change)
4. sidebar_label needs multi-surface schema updates → explicit steps in plan
5. New canonical names break normalizer → reimporter bypasses normalizer
6. Stale session_stats after wipe → clear session_stats/archive/changelog during reimport

---

## Database Stats

### Pre-fix
- **Total shots:** 2,159
- **With club:** 977 (45%)
- **Without club:** 1,182 (55%)

### Post-reimport
- **Total shots:** 5,578
- **NULL club:** 0 (0%)
- **Sessions:** 126
- **All shots have:** session_date, sidebar_label, original_club_value

## Complete Uneekor Club Name Map (from API scan)

| Uneekor `club_name` | ID | Shots | Canonical |
|---|---|---|---|
| DRIVER | 0 | 379 | Driver |
| WOOD2 | 1 | 31 | 3 Wood (Cobra) |
| WOOD3 | 2 | 14 | 3 Wood (TM) |
| WOOD7 | 6 | 5 | 7 Wood |
| HYBRID1 | 9 | 4 | Other |
| HYBRID3 | 11 | 20 | Other |
| IRON1 | 18 | 1,268 | Sim Round |
| IRON3 | 20 | 125 | 3 Iron |
| IRON4 | 21 | 42 | 4 Iron |
| IRON5 | 22 | 36 | 5 Iron |
| IRON6 | 23 | 176 | 6 Iron |
| IRON7 | 24 | 582 | 7 Iron |
| IRON8 | 25 | 613 | 8 Iron |
| IRON9 | 26 | 407 | 9 Iron |
| WEDGE_PITCHING | 28 | 643 | PW |
| WEDGE_50 | 33 | 595 | GW |
| WEDGE_54 | 35 | 49 | Other |
| WEDGE_56 | 36 | 418 | SW |
| WEDGE_60 | 36 | 117 | LW |
| PUTTER | 37 | 54 | Putter |

---

## Flagged for Later

- Smash factor targets for new clubs (7 Wood, 4 Iron, 5 Iron) — need research
- IRON1/Sim Round shot inference — use carry distance + ball speed to guess actual club
- Supabase schema update (`supabase_schema.sql`) — do after local reimport works
- UI changes for new clubs/categories — separate phase (5-7)
