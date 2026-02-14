# Design: Scraper Fix + Clean Re-import

**Date:** 2026-02-13
**Status:** Approved
**Reviewed by:** Codex (GPT-5.3-Codex) — 6 gaps identified and addressed

---

## Problem

55% of 2,159 shots have `club=NULL` because `golf_scraper.py` reads `session.get('name')` (the user-friendly sidebar label, e.g., "dpc scottsdale") instead of `session.get('club_name')` (the Uneekor internal name, e.g., "IRON1"). Additionally, session dates are sourced from the listing page rather than the API's `client_created_date` field, causing occasional inaccuracies.

## Root Cause

The Uneekor API at `https://api-v2.golfsvc.com/v2/oldmyuneekor/report/{id}/{key}` returns each club group with:

```json
{
    "id": 89069,
    "name": "warmup",                    // sidebar label (currently used — WRONG)
    "club_name": "WEDGE_PITCHING",       // internal Uneekor name (should use — CORRECT)
    "club": 28,                          // numeric club ID
    "club_type": "4",
    "ball_name": "MEDIUM",
    "client_created_date": "2026-01-25", // actual session date (should use)
    "created": "2026-01-25T23:52:51Z",   // server upload timestamp
    "shots": [...]
}
```

The scraper only reads `name`, `id`, and `shots`. The `club_name` and `client_created_date` fields are ignored.

## Solution: Fix Scraper + Clean Re-import

### Approach

1. Fix `golf_scraper.py` to use the correct API fields
2. Add Uneekor-to-canonical club mapping
3. Update `my_bag.json` with complete bag
4. Build standalone reimport command
5. Wipe shots table and re-import all 126 sessions from API

### Why Clean Re-import

- 55% of existing data has NULL clubs — not worth preserving
- Date accuracy is uncertain across all existing data
- API provides authoritative data for all fields
- Simpler than migration scripts; no ID matching complexity
- Gets all ~5,500 shots with correct clubs and dates

---

## Uneekor Club Name Mapping

### Complete API → Canonical Map

| Uneekor `club_name` | Numeric `club` ID | Canonical Name | Category |
|---|---|---|---|
| DRIVER | 0 | Driver | In bag |
| WOOD2 | 1 | 3 Wood (Cobra) | In bag |
| WOOD3 | 2 | 3 Wood (TM) | In bag |
| WOOD7 | 6 | 7 Wood | In bag |
| IRON1 | 18 | Sim Round | Special — mixed clubs |
| IRON3 | 20 | 3 Iron | In bag (driving iron) |
| IRON4 | 21 | 4 Iron | In bag |
| IRON5 | 22 | 5 Iron | In bag |
| IRON6 | 23 | 6 Iron | In bag |
| IRON7 | 24 | 7 Iron | In bag |
| IRON8 | 25 | 8 Iron | In bag |
| IRON9 | 26 | 9 Iron | In bag |
| WEDGE_PITCHING | 28 | PW | In bag |
| WEDGE_50 | 33 | GW | In bag |
| WEDGE_56 | 36 | SW | In bag |
| WEDGE_60 | 36 | LW | In bag |
| PUTTER | 37 | Putter | In bag |
| HYBRID1 | 9 | Other | Testing/fitting |
| HYBRID3 | 11 | Other | Testing/fitting |
| WEDGE_54 | 35 | Other | Testing/fitting |

### IRON1 = Sim Round Explanation

When playing simulated golf rounds, the user selects "1 Iron" as a default in the Uneekor software and doesn't switch between shots. The IRON1 group in sim rounds therefore contains shots hit with many different physical clubs (Driver, irons, wedges). These shots cannot be accurately classified by club.

**Treatment:** Label as "Sim Round" and exclude from per-club analytics. Future: infer clubs from shot data (carry distance, ball speed ranges).

---

## Changes by File

### 1. `golf_scraper.py`

**In `run_scraper()`:**
- Read `session.get('club_name')` → map to canonical via `UNEEKOR_TO_CANONICAL`
- Read `session.get('client_created_date')` → use as `session_date`
- Store sidebar label (`session.get('name')`) in new `sidebar_label` field
- Store raw `club_name` in `original_club_value` field
- Store numeric `club` ID in new `uneekor_club_id` field
- Keep `session.get('id')` as middle token of shot ID (no change to ID format)

### 2. `automation/naming_conventions.py`

**Add:**
- `UNEEKOR_TO_CANONICAL` mapping dict (config-driven, not regex)
- `map_uneekor_club(club_name: str) -> str` function
- New canonical names to known club sets: "3 Wood (Cobra)", "3 Wood (TM)", "7 Wood", "3 Iron", "4 Iron", "5 Iron", "Putter", "Sim Round", "Other"

### 3. `my_bag.json`

**Updated bag (16 clubs + 2 special categories):**

```json
{
  "clubs": [
    {"canonical": "Driver", "aliases": ["DR", "1W"], "uneekor": "DRIVER"},
    {"canonical": "3 Wood (Cobra)", "aliases": ["3W Cobra"], "uneekor": "WOOD2"},
    {"canonical": "3 Wood (TM)", "aliases": ["3W TM"], "uneekor": "WOOD3"},
    {"canonical": "7 Wood", "aliases": ["7W"], "uneekor": "WOOD7"},
    {"canonical": "3 Iron", "aliases": ["3I", "Driving Iron"], "uneekor": "IRON3"},
    {"canonical": "4 Iron", "aliases": ["4I"], "uneekor": "IRON4"},
    {"canonical": "5 Iron", "aliases": ["5I"], "uneekor": "IRON5"},
    {"canonical": "6 Iron", "aliases": ["6I"], "uneekor": "IRON6"},
    {"canonical": "7 Iron", "aliases": ["7I"], "uneekor": "IRON7"},
    {"canonical": "8 Iron", "aliases": ["8I"], "uneekor": "IRON8"},
    {"canonical": "9 Iron", "aliases": ["9I"], "uneekor": "IRON9"},
    {"canonical": "PW", "aliases": ["Pitching Wedge"], "uneekor": "WEDGE_PITCHING"},
    {"canonical": "GW", "aliases": ["50", "Gap Wedge", "50 Degree"], "uneekor": "WEDGE_50"},
    {"canonical": "SW", "aliases": ["56", "Sand Wedge"], "uneekor": "WEDGE_56"},
    {"canonical": "LW", "aliases": ["60", "Lob Wedge"], "uneekor": "WEDGE_60"},
    {"canonical": "Putter", "aliases": ["PT"], "uneekor": "PUTTER"}
  ],
  "special_categories": [
    {"canonical": "Sim Round", "uneekor": "IRON1", "exclude_from_club_analytics": true},
    {"canonical": "Other", "uneekor": ["HYBRID1", "HYBRID3", "WEDGE_54"], "exclude_from_club_analytics": true}
  ],
  "bag_order": ["Driver", "3 Wood (Cobra)", "3 Wood (TM)", "7 Wood", "3 Iron", "4 Iron", "5 Iron", "6 Iron", "7 Iron", "8 Iron", "9 Iron", "PW", "GW", "SW", "LW", "Putter"],
  "smash_targets": {
    "Driver": 1.49,
    "3 Wood (Cobra)": 1.45,
    "3 Wood (TM)": 1.45,
    "7 Wood": 1.42,
    "3 Iron": 1.36,
    "4 Iron": 1.35,
    "5 Iron": 1.34,
    "6 Iron": 1.34,
    "7 Iron": 1.33,
    "8 Iron": 1.31,
    "9 Iron": 1.29,
    "PW": 1.24,
    "GW": 1.22,
    "SW": 1.20,
    "LW": 1.18
  }
}
```

**Note:** Smash targets for new clubs (7 Wood, 4 Iron, 5 Iron) are estimates — flagged for research.

### 4. `golf_db.py`

**Schema changes in `init_db()`:**
- Add `sidebar_label TEXT` column to `shots` table
- Add `uneekor_club_id INTEGER` column to `shots` table
- Existing `original_club_value` column stores raw `club_name`

**Update `save_shot()`:**
- Accept new fields: `sidebar_label`, `uneekor_club_id`

**Update restore allowlist (`ALLOWED_UPDATE_FIELDS`):**
- Add new columns

### 5. `automation_runner.py`

**Add `reimport-all` command:**

```
python automation_runner.py reimport-all [--dry-run]
```

This command:
1. Backs up `golf_stats.db` → `golf_stats.db.bak-YYYYMMDD`
2. Clears: `shots`, `shots_archive`, `change_log`, `session_stats`
3. For each row in `sessions_discovered`:
   - Calls Uneekor API: `GET /v2/oldmyuneekor/report/{id}/{key}`
   - Reads `client_created_date` → `session_date`
   - For each club group: maps `club_name` → canonical
   - Saves all shots with correct club, date, sidebar_label, uneekor_club_id
   - Tracks success/failure count with hard-fail threshold (>5% failures = abort)
4. Resets all `sessions_discovered.import_status` to reflect new state
5. Rebuilds `session_stats` cache
6. Reports summary: total sessions, total shots, clubs found, failures

**Key difference from BackfillRunner:** Standalone function that iterates `sessions_discovered` directly, ignoring `import_status`. Does NOT use the normalizer — maps directly from `club_name`.

### 6. `supabase_schema.sql`

- Add `sidebar_label TEXT` column
- Add `uneekor_club_id INTEGER` column

---

## Codex Review Findings (Addressed)

| # | Issue | Severity | Resolution |
|---|---|---|---|
| 1 | BackfillRunner skips imported sessions | HIGH | Standalone reimporter bypasses BackfillRunner queue |
| 2 | save_shot() silently swallows errors | HIGH | Add error counting with >5% failure threshold |
| 3 | Shot ID collision if middle token changes | MEDIUM | Keep numeric group `id` as middle token (no change) |
| 4 | sidebar_label needs multi-surface schema updates | MEDIUM | Explicit steps for SQLite, Supabase, allowlist, sync |
| 5 | New canonical names break normalizer | MEDIUM | Reimporter bypasses normalizer; add names to known sets |
| 6 | Stale session_stats after wipe | LOW | Clear session_stats, shots_archive, change_log during reimport |

---

## Out of Scope

- Per-shot club inference for IRON1/Sim Round shots (future feature)
- Smash target research for new clubs (flagged)
- Supabase sync during reimport (reimport is local-only; sync separately after)
- UI changes for new clubs/categories (separate phase)

---

## Success Criteria

After reimport:
- 0 shots with `club=NULL` (all mapped to canonical or "Sim Round"/"Other")
- All shots have `session_date` from `client_created_date`
- All shots have `sidebar_label` and `original_club_value` populated
- `my_bag.json` reflects actual bag (16 clubs + 2 special categories)
- Total shot count matches API totals (~5,500+)
- All 126 sessions represented
