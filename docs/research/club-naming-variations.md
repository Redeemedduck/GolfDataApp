# Club Naming Variations Research

**Date:** 2026-02-05
**Database:** `golf_stats.db`
**Normalizer:** `automation/naming_conventions.py` (`ClubNameNormalizer`, `SessionContextParser`)

---

## 1. All Club Values Found in the Database

The `shots` table contains **43 distinct values** in the `club` column, totaling 1,337 shots. Most values are **session names**, not club names. The Uneekor portal uses a "name" field per session/club group, and the legacy scraper (`golf_scraper.py`) stores it as-is in `data['club']` at line 184 without normalization.

### Full Inventory (sorted by shot count)

| `club` value | Shots | Category | Already Normalized? |
|---|---|---|---|
| Warmup | 128 | Session name | No |
| Sgt Rd1 | 85 | Session name (Sim Golf Tour Round 1) | No |
| 6 Iron | 68 | Standard club | Yes |
| Bag Mapping | 67 | Session name | No |
| Warmup 50 | 52 | Session name (warmup with 50-degree wedge) | No |
| 1 Iron | 50 | Standard club | Yes |
| Sgt Wailaie Rd1 Cont | 49 | Session name (SGT course round) | No |
| Shadow Ridge Sgt | 45 | Session name (SGT course) | No |
| Warmup Pw | 44 | Session name (warmup with PW) | No |
| Silvertip Rd2 | 44 | Session name (SGT course round) | No |
| Silvertip Sgt Tour Rd 1 | 43 | Session name (SGT course round) | No |
| Sgt Rd 2 Kapalua | 42 | Session name (SGT course round) | No |
| Sgt Plantation Course | 42 | Session name (SGT course round) | No |
| Sgt Shadowridge Rd2 | 41 | Session name (SGT course round) | No |
| Par 3 | 40 | Session name (par 3 practice) | No |
| Wmup | 37 | Session name (abbreviation of "Warmup") | No |
| Driver | 33 | Standard club | Yes |
| Warmup 50 Degree | 31 | Session name (warmup with 50-degree wedge) | No |
| 8 Iron | 31 | Standard club | Yes |
| Sgt Sony Open 1 | 30 | Session name (SGT tournament) | No |
| Wedge 50 | 28 | Embedded club reference (50-degree = GW) | No |
| 7 Iron | 28 | Standard club | Yes |
| Sgt Par 3 Rd 2 | 26 | Session name (SGT par 3 round) | No |
| Sgt Newport Par 3 | 26 | Session name (SGT par 3 course) | No |
| Wedge Pitching | 23 | Embedded club reference (= PW) | No |
| Sgt Rd2 Wailaie | 21 | Session name (SGT course round) | No |
| Dst Warmup | 20 | Session name (distance trainer warmup) | No |
| Dst Compressor 8 | 18 | Session name (distance trainer, 8 iron) | No |
| 50 Warmup | 18 | Session name (warmup with 50-degree) | No |
| PW | 17 | Standard club | Yes |
| 8 Iron Dst Trainer Warmup | 17 | Session name (8 iron distance trainer warmup) | No |
| Dst Compressor 8 Full | 15 | Session name (distance trainer, 8 iron full swing) | No |
| Dst Compressor Half Swing | 14 | Session name (distance trainer, half swing) | No |
| 9 Iron | 14 | Standard club | Yes |
| 8 Iron Dst Trainer | 14 | Session name (8 iron distance trainer) | No |
| 8 Dst Warmup | 13 | Session name (8 iron distance warmup) | No |
| Forward Impact Pw | 10 | Session name (forward impact drill with PW) | No |
| 3/4 Speed Towel Drill | 9 | Session name (drill name) | No |
| Dst Trainer | 8 | Session name (distance trainer) | No |
| Iron7 \| Medium | 6 | Uneekor default format | No |
| Iron6 \| Medium | 6 | Uneekor default format | No |
| IRON6 \| MEDIUM | 6 | Uneekor default format (uppercase variant) | No |
| IRON7 \| MEDIUM | 2 | Uneekor default format (uppercase variant) | No |

### Summary

| Category | Count | Shots | Percentage |
|---|---|---|---|
| Already normalized (standard club name) | 7 | 241 | 18.0% |
| Session names (not club names at all) | 32 | 1,072 | 80.2% |
| Uneekor default format (`IRON7 \| MEDIUM`) | 4 | 20 | 1.5% |
| **Total non-standard** | **36** | **1,096** | **82.0%** |

---

## 2. How Club Values Enter the Database

### Legacy Scraper Path (no normalization)

```
Uneekor API JSON
  -> golf_scraper.py line 142: club_name = session.get('name', 'Unknown')
  -> golf_scraper.py line 184: 'club': club_name  (stored raw)
  -> golf_db.py line 435: 'club': data.get('club')  (inserted raw)
```

The legacy scraper (`golf_scraper.py`) calls the Uneekor API directly. Each session in the API response has a `name` field which is the user-defined session name on the portal. This name is stored directly into the `club` column without any normalization. This is the source of the 80%+ non-standard values.

### Backfill Runner Path (normalization applied)

```
Uneekor Portal
  -> automation/uneekor_portal.py: normalize_club() called on extracted club names
  -> automation/backfill_runner.py line 593-603: post-import normalization
     - Reads imported shots, normalizes club names via ClubNameNormalizer
     - Calls golf_db.rename_club() to update non-matching names
```

The newer backfill pipeline does apply normalization -- but only when `normalize_clubs=True` (default). It normalizes after import by reading back the data and renaming clubs that changed.

### Key Problem

The legacy scraper path stores **session names** (like "Warmup", "Sgt Rd1", "Bag Mapping") in the `club` column. These are not club names at all. The Uneekor API uses the session/report name as the "club" grouping, and the scraper blindly passes it through.

---

## 3. ClubNameNormalizer Analysis

### What It Handles Well

The normalizer correctly maps these common variations (tested via regex patterns):

| Input Pattern | Output | Confidence |
|---|---|---|
| `dr`, `1w`, `d` | Driver | 0.95 |
| `7i`, `iron 7`, `7-iron` | 7 Iron | 0.95 |
| `3w`, `3wd`, `fairway 3` | 3 Wood | 0.95 |
| `4h`, `hybrid 4`, `rescue 4` | 4 Hybrid | 0.95 |
| `pw`, `pitching wedge`, `p.w.` | PW | 0.95 |
| `56 deg`, `56 degree` | SW | 0.90 |
| `sand`, `sand wedge` | SW | 0.95 |
| `putter`, `putt`, `putting` | Putter | 0.95 |
| Already-standard names | Same | 1.00 |

### What the Normalizer Cannot Handle (present in DB)

These are values the normalizer would receive but would fail to produce a correct club name for, because they are session names, not club names:

| DB Value | Normalizer Would Produce | Correct Club | Issue |
|---|---|---|---|
| `Warmup` | `Warmup` (0.3 conf, fallback) | Unknown/Mixed | Not a club name |
| `Sgt Rd1` | `Sgt Rd1` (0.3) | Multiple clubs | Sim round session name |
| `Bag Mapping` | `Bag Mapping` (0.3) | Multiple clubs | Bag mapping session |
| `Warmup 50` | `Warmup 50` (0.3) | GW (50-degree) | Session name with embedded club hint |
| `Warmup Pw` | `Warmup Pw` (0.3) | PW | Session name with embedded club hint |
| `Wmup` | `Wmup` (0.3) | Unknown/Mixed | Abbreviation not in patterns |
| `Warmup 50 Degree` | `Warmup 50 Degree` (0.3) | GW (50-degree) | Session name with embedded degree |
| `Wedge 50` | `Wedge 50` (0.3) | GW | "Wedge" prefix not matched as standalone |
| `Wedge Pitching` | `Wedge Pitching` (0.3) | PW | Reversed order not in patterns |
| `Dst Warmup` | `Dst Warmup` (0.3) | Unknown | Distance trainer warmup |
| `Dst Compressor 8` | `Dst Compressor 8` (0.3) | 8 Iron | Distance trainer with club hint |
| `8 Iron Dst Trainer` | `8 Iron Dst Trainer` (0.3) | 8 Iron | Club name embedded in longer string |
| `8 Iron Dst Trainer Warmup` | `8 Iron Dst Trainer Warmup` (0.3) | 8 Iron | Club name embedded in longer string |
| `Forward Impact Pw` | `Forward Impact Pw` (0.3) | PW | Drill name with embedded club |
| `Iron7 \| Medium` | `Iron7 \| Medium` (0.3) | 7 Iron | Uneekor default format not handled |
| `Iron6 \| Medium` | `Iron6 \| Medium` (0.3) | 6 Iron | Uneekor default format not handled |
| `IRON6 \| MEDIUM` | `Iron6 \| Medium` (0.3) | 6 Iron | Uppercase Uneekor default format |
| `IRON7 \| MEDIUM` | `Iron7 \| Medium` (0.3) | 7 Iron | Uppercase Uneekor default format |
| `50 Warmup` | `50 Warmup` (0.3) | GW | Reversed order with degree |
| `8 Dst Warmup` | `8 Dst Warmup` (0.3) | 8 Iron | Abbreviated club reference |
| `3/4 Speed Towel Drill` | `3/4 Speed Towel Drill` (0.3) | Unknown | Pure drill name, no club info |
| `Dst Trainer` | `Dst Trainer` (0.3) | Unknown | Distance trainer, no club specified |
| `Dst Compressor 8 Full` | `Dst Compressor 8 Full` (0.3) | 8 Iron | Distance trainer with club hint |
| `Dst Compressor Half Swing` | `Dst Compressor Half Swing` (0.3) | Unknown | No club specified |
| `Par 3` | `Par 3` (0.3) | Multiple clubs | Practice mode name |

### SessionContextParser Analysis

The `SessionContextParser` class (lines 495-657 in `naming_conventions.py`) is designed specifically to handle these compound session names. It extracts both session type and embedded club references. However, it is **not used in the import pipeline**. It exists in the codebase but the backfill runner only uses `ClubNameNormalizer`, not `SessionContextParser`.

The context parser correctly handles patterns like:
- `Warmup PW` -> session_type=warmup, club=PW
- `Wedge 50` -> club=GW (via degree mapping)
- `Dst Compressor 8` -> session_type=drill, club=8 Iron
- `Sgt Rd1` -> session_type=sim_round, club=None
- `Iron7 | Medium` -> Not handled (no pattern for `IronN | TIER` format)

---

## 4. Uneekor Default Format: `IRON7 | MEDIUM`

The Uneekor portal has a default session naming format documented in `docs/UNEEKOR_PORTAL_MAP.md` line 160:

```
Default format: DRIVER | MEDIUM, IRON7 | PREMIUM
```

The format is: `CLUB_TYPE_NUMBER | TIER` where TIER appears to be a subscription/feature tier indicator (MEDIUM, PREMIUM). Neither the `ClubNameNormalizer` nor the `SessionContextParser` has patterns to handle this format.

Four entries in the database use this format:
- `Iron7 | Medium` (6 shots)
- `Iron6 | Medium` (6 shots)
- `IRON6 | MEDIUM` (6 shots)
- `IRON7 | MEDIUM` (2 shots)

These represent 20 shots that should resolve to `7 Iron` and `6 Iron`.

---

## 5. Database Manager Duplicate Detection

The `pages/3_Database_Manager.py` file (line 459-478) has its own separate normalization function for detecting club naming anomalies in the UI:

```python
def normalize_club_name(name):
    base = (name or "").lower().strip()
    base = re.sub(r"[_-]+", " ", base)
    base = re.sub(r"\s+", " ", base)
    base = base.replace("iron", "i")
    return base
```

This is a **third, independent normalization approach** that is disconnected from `ClubNameNormalizer`. It collapses "7 Iron" to "7 i" and "Iron7" to "i7", which would detect them as similar but uses different logic than the canonical normalizer. This creates a maintenance risk where the two approaches could diverge.

---

## 6. Edge Cases the Normalizer Does Not Handle

### Category A: Uneekor Default Format (20 shots affected)
- `Iron7 | Medium`, `IRON7 | MEDIUM` -> should be `7 Iron`
- `Iron6 | Medium`, `IRON6 | MEDIUM` -> should be `6 Iron`
- Any `DRIVER | MEDIUM` or `WOOD3 | PREMIUM` variants not yet seen

**Fix:** Add a regex pattern like `^(iron|wood|hybrid|driver|wedge)(\d*)\s*\|\s*(medium|premium|basic)$` to `CLUB_PATTERNS`.

### Category B: Session Names with Embedded Club Hints (246 shots affected)
- `Warmup 50`, `Warmup 50 Degree`, `50 Warmup` -> club=GW
- `Warmup Pw`, `Forward Impact Pw` -> club=PW
- `Dst Compressor 8`, `Dst Compressor 8 Full` -> club=8 Iron
- `8 Iron Dst Trainer`, `8 Iron Dst Trainer Warmup` -> club=8 Iron
- `8 Dst Warmup` -> club=8 Iron
- `Wedge 50`, `Wedge Pitching` -> club=GW, club=PW

The `SessionContextParser` handles most of these, but it is not used during import.

### Category C: Pure Session Names with No Club Info (657 shots affected)
- `Warmup` (128 shots) -- could be any club
- `Sgt Rd1`, `Sgt Wailaie Rd1 Cont`, etc. -- sim rounds with full bag
- `Bag Mapping` (67 shots) -- mapping session with all clubs
- `Par 3` (40 shots) -- par 3 practice
- `Wmup` (37 shots) -- warmup abbreviation
- `3/4 Speed Towel Drill` (9 shots) -- drill name
- `Dst Trainer` (8 shots), `Dst Compressor Half Swing` (14 shots) -- no club specified
- `Dst Warmup` (20 shots) -- distance trainer warmup

These cannot be resolved to a single club from the name alone. The actual club data may exist in the Uneekor API response but was not extracted separately by the legacy scraper.

### Category D: Pattern Gaps in ClubNameNormalizer
- `Wmup` is not recognized as a warmup abbreviation (no pattern)
- `Iron7` (without pipe) is not matched (the pattern requires full match: `^(7i|7 iron|iron 7|...)$` but `iron7` with no space does not match `iron 7`)
- `Wedge 50` is not matched (the degree pattern expects `50 deg/degree`, not `Wedge 50`; the `SessionContextParser` has a pattern for this but the normalizer does not)
- `Wedge Pitching` is not matched (the normalizer expects `pitching wedge`, not the reversed form)

---

## 7. Recommendations

### Priority 1: Add Uneekor Default Format Pattern
Add to `CLUB_PATTERNS` in `ClubNameNormalizer`:

```python
# Uneekor default format: "IRON7 | MEDIUM", "DRIVER | PREMIUM"
(r'^driver\s*\|.*$', 'Driver'),
(r'^iron(\d)\s*\|.*$', '_IRON_TIER'),
(r'^wood(\d)\s*\|.*$', '_WOOD_TIER'),
(r'^hybrid(\d)\s*\|.*$', '_HYBRID_TIER'),
(r'^wedge(\d{2})\s*\|.*$', '_WEDGE_TIER'),
```

With corresponding handler logic. This fixes 20 shots immediately and future-proofs against similar imports.

### Priority 2: Integrate SessionContextParser into Import Pipeline
The `SessionContextParser` already handles many of the compound session names. For the 246 shots with embedded club hints, the backfill runner should:
1. First try `ClubNameNormalizer` (for actual club names)
2. If confidence is low (<0.5), fall back to `SessionContextParser.extract_club()`
3. If a club is extracted, update the `club` column and store the original value in a `session_context` or `original_club_name` column

### Priority 3: Add Missing Patterns
- Add `Iron\d` (no space) patterns: `(r'^iron(\d)$', '_IRON_NUM')`
- Add `Wedge + type` reversed patterns: `(r'^wedge\s*(pitching|sand|lob|gap|approach)$', '_WEDGE_TYPE')`
- Add `Wedge + degree` pattern: `(r'^wedge\s*(\d{2})$', '_DEGREE_WEDGE')`

### Priority 4: Data Migration for Existing Records
Run a one-time migration to fix the 1,096 non-standard club values:
1. For values where `SessionContextParser` can extract a club: update `club` column
2. For pure session names with no club info: either leave as-is or set to `Unknown` and preserve the session name in a separate column
3. For Uneekor default format values: parse and normalize

### Priority 5: Consolidate Normalization Logic
Remove the inline `normalize_club_name()` function in `pages/3_Database_Manager.py` and replace it with `ClubNameNormalizer` to prevent logic drift between the two implementations.

### Priority 6: Prevent Future Raw Storage
Modify `golf_scraper.py` to apply normalization at import time (line 184), matching the behavior of the backfill runner. Or better yet, add normalization inside `golf_db.add_shot()` so all paths are covered.

---

## 8. Impact Assessment

| Fix | Shots Fixed | Effort | Risk |
|---|---|---|---|
| Uneekor format pattern | 20 | Low (add regex) | Low |
| Integrate SessionContextParser | 246 | Medium (pipeline change) | Low |
| Add missing patterns | ~30 | Low (add regex) | Low |
| Data migration | 1,096 | Medium (one-time script) | Medium (verify before commit) |
| Consolidate normalizers | 0 (maintenance) | Low (replace function) | Low |
| Normalize at import time | Future-proof | Medium (refactor) | Low |

**Total addressable:** ~296 shots can be automatically fixed to correct club names. The remaining ~800 shots stored under session names (sim rounds, bag mapping, etc.) require either manual review or querying the original Uneekor API data to determine the actual club for each shot.
