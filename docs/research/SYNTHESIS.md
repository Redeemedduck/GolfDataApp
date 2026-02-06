# Research Synthesis: Session Naming Schema

**Date:** 2026-02-05
**Sources:** portal-naming-patterns.md, date-inconsistencies.md, club-naming-variations.md, codebase-gap-analysis.md

---

## 1. Executive Summary

Four parallel research agents investigated the naming, dating, and club data landscape. Key findings:

| Finding | Impact | Source |
|---------|--------|--------|
| Portal provides no meaningful session names ("Open" or None) | All names must be generated post-import | Portal Naming |
| 82% of `club` column values are session names, not club names | Distribution-based session typing is unreliable on raw data | Club Naming |
| Two date formats in `shots.session_date` (YYYY-MM-DD vs ISO with T) | Query/grouping errors, string comparison failures | Date Inconsistencies |
| 226 shots have wrong date (Jan 28 instead of Jan 26) | Wrong date attribution in analytics | Date Inconsistencies |
| `report_page` date source is fundamentally unreliable | 2 sessions dated 2026-02-02 are actually from mid-2024 | Date Inconsistencies |
| `SessionContextParser` is dead code (no production callers) | Could extract clubs from 246 compound names but isn't used | Codebase Gaps |
| `sessions_discovered` metadata never surfaces in UI | Session names, types, and tags are generated but invisible | Codebase Gaps |
| `SessionNamer.shot_count` parameter is accepted but ignored | Names lack shot count despite it being passed | Codebase Gaps |
| Drill/fitting overlap bug in `infer_session_type()` | Fitting type is unreachable for 1-club sessions | Codebase Gaps |

**Core problem:** The existing `SessionNamer` generates names using the import date (not the session date), the names are stored only in `sessions_discovered` (not surfaced to the UI), and the format doesn't include shot count or distribution-based session type.

---

## 2. Proposed Naming Schema

### Display Name Format

```
{YYYY-MM-DD} {SessionType} ({shot_count} shots)
```

**Examples:**
- `2026-01-25 Mixed Practice (47 shots)`
- `2026-01-15 Driver Focus (25 shots)`
- `2026-01-07 Warmup (8 shots)`
- `2026-01-12 Iron Work (62 shots)`

### Implementation: Extend `SessionNamer`

Add a `generate_display_name()` method alongside the existing `generate_name()`:

```python
def generate_display_name(
    self,
    session_date: datetime,
    session_type: str,
    shot_count: int,
) -> str:
    """Generate display name: '2026-01-25 Practice (47 shots)'"""
    date_str = session_date.strftime('%Y-%m-%d')
    type_display = self.SESSION_TYPES.get(session_type, session_type.title())
    return f"{date_str} {type_display} ({shot_count} shots)"
```

This preserves backward compatibility with `generate_name()` while adding the new format.

---

## 3. Session Type Detection

### Current Approach (count-based, in `SessionNamer.infer_session_type`)

| Condition | Type | Issue |
|-----------|------|-------|
| shot_count < 10 | warmup | OK |
| num_clubs <= 2 and shot_count >= 30 | drill | Blocks fitting |
| num_clubs == 1 and shot_count >= 50 | fitting | Unreachable (drill matches first) |
| num_clubs >= 3 | practice | Too broad |
| default | practice | Catch-all |

### Proposed Approach (distribution-based, new method)

Add `detect_session_type(clubs: List[str]) -> str` that classifies by club distribution:

| Condition | Type | Tag Equivalent |
|-----------|------|----------------|
| >60% driver shots | Driver Focus | Matches AutoTagger "Driver Focus" |
| >60% iron shots | Iron Work | Matches AutoTagger "Iron Work" |
| >60% wedge shots | Short Game | Matches AutoTagger "Short Game" |
| shot_count < 10 | Warmup | Matches AutoTagger "Warmup" |
| no dominant club | Mixed Practice | New (replaces generic "Practice") |

### Critical Caveat: Club Data Quality

**82% of club values are session names, not actual club names.** Distribution-based detection will only work correctly when:
1. The club column contains actual club names (18% of current data)
2. The `SessionContextParser` has been used to extract embedded club hints (adds ~246 shots)

**For sessions with un-parseable club names:** Fall back to the existing count-based `infer_session_type()`.

### Club Categories for Detection

```python
DRIVER_CLUBS = {'Driver'}
IRON_CLUBS = {'1 Iron', '2 Iron', '3 Iron', '4 Iron', '5 Iron',
              '6 Iron', '7 Iron', '8 Iron', '9 Iron'}
WEDGE_CLUBS = {'PW', 'GW', 'SW', 'LW'}
WOOD_CLUBS = {'3 Wood', '5 Wood', '7 Wood'}
HYBRID_CLUBS = {'3 Hybrid', '4 Hybrid', '5 Hybrid', '6 Hybrid'}
```

These use the normalized canonical names from `ClubNameNormalizer` output.

---

## 4. Edge Cases

### 4a. Sessions With No Recognizable Club Names (657 shots)

Pure session names like "Warmup", "Sgt Rd1", "Bag Mapping", "Par 3" contain no extractable club information.

**Strategy:** Use count-based `infer_session_type()` as fallback. The type will be "Practice" or "Warmup" based on shot count, which is acceptable.

### 4b. Multiple Sessions on the Same Date (18 dates have 2-5 sessions)

The naming format `{date} {type} ({shots})` may produce duplicates like:
- `2026-01-26 Practice (48 shots)`
- `2026-01-26 Practice (88 shots)`

These are distinguishable by shot count, but if counts match too, append a sequence number: `2026-01-26 Practice (48 shots) #2`.

### 4c. Sessions With NULL Dates (22 sessions)

For sessions where `session_date IS NULL` (older sessions not matched to listing page dates):

**Strategy:** Use "Unknown Date" placeholder: `Unknown Date - Practice (47 shots)`. Don't fall back to `datetime.utcnow()` — this caused the current misleading names.

### 4d. Uneekor Default Format (`IRON7 | MEDIUM`) (20 shots)

Not currently handled by `ClubNameNormalizer`. These should be parseable with a simple regex:
```python
# Pattern: IRON7 | MEDIUM -> 7 Iron
(r'^(iron|wood|hybrid|driver)(\d*)\s*\|.*$', handler)
```

This affects 20 shots across 4 distinct values. Low effort, high confidence fix.

### 4e. Date Format Inconsistency in shots.session_date

246 shots use `YYYY-MM-DDTHH:MM:SS` while 1,115 use `YYYY-MM-DD`. The `generate_display_name()` method must handle both:
```python
# Normalize to date-only before formatting
date_str = session_date.strftime('%Y-%m-%d') if isinstance(session_date, datetime)
           else str(session_date)[:10]
```

---

## 5. Recommended Implementation Order

### Phase 1: Core Naming (Task 6 scope - this pipeline)

1. **Add `detect_session_type(clubs)` to `SessionNamer`** — distribution-based detection with club category sets
2. **Add `generate_display_name()` to `SessionNamer`** — new format: `{date} {type} ({shots})`
3. **Write tests first** (TDD per plan) — test both methods with various club distributions
4. **Handle NULL date edge case** — "Unknown Date" placeholder instead of utcnow() fallback

### Phase 2: Batch Rename (Task 7 scope - this pipeline)

5. **Add `batch_update_session_names()` to `golf_db.py`** — iterate sessions, compute name from existing data, update `sessions_discovered.session_name`
6. **Run batch update** against current data
7. **Verify** — spot-check that names match expected format

### Phase 3: Data Quality (future work, not this pipeline)

8. **Standardize date format** — `UPDATE shots SET session_date = SUBSTR(session_date, 1, 10) WHERE session_date LIKE '%T00:00:00'`
9. **Fix 226 shots with wrong date** — reclassify sessions 42719, 42924, 43032, 43033
10. **Deprecate `report_page` date source** — mark 2 sessions (20842, 20718) as unverified
11. **Add Uneekor default format pattern** to `ClubNameNormalizer` (20 shots)
12. **Integrate `SessionContextParser` into import pipeline** (246 additional shots get club extraction)

### Phase 4: UI Integration (future work)

13. **Create bridge function** — `get_session_metadata()` joining shots with sessions_discovered
14. **Surface session names in UI** — update session selector and list components
15. **Fix drill/fitting overlap** in `infer_session_type()`
16. **Consolidate duplicate normalizer** in `pages/3_Database_Manager.py`

---

## 6. Schema Summary

| Component | Current | Proposed |
|-----------|---------|----------|
| **Name format** | `"Practice - Jan 25, 2026"` | `"2026-01-25 Mixed Practice (47 shots)"` |
| **Type detection** | Count-based (shot_count + num_clubs) | Distribution-based (club category percentages) with count-based fallback |
| **Types available** | practice, drill, round, fitting, warmup, lesson | Driver Focus, Iron Work, Short Game, Mixed Practice, Warmup (+ count-based fallback types) |
| **Where stored** | `sessions_discovered.session_name` only | Same (UI bridge deferred to Phase 4) |
| **NULL date handling** | Falls back to `datetime.utcnow()` | Uses "Unknown Date" placeholder |
| **Shot count in name** | Parameter accepted but ignored | Included in display name |

---

## 7. Alignment with Existing Classes

| Class | Role in New Schema |
|-------|-------------------|
| **SessionNamer** | Gets `generate_display_name()` + `detect_session_type()` methods |
| **AutoTagger** | Unchanged — tags complement but don't replace the session type in the name |
| **ClubNameNormalizer** | Unchanged — provides canonical club names that `detect_session_type()` categorizes |
| **SessionContextParser** | Deferred — Phase 3 integration will unlock club extraction for 246 additional shots |

This approach extends existing classes (per user decision) rather than adding standalone functions, maintaining architectural consistency.
