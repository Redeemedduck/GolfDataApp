# Codebase Gap Analysis: Naming & Session System

**Date:** 2026-02-05
**Branch:** feat/ui-ux-redesign
**Scope:** `automation/naming_conventions.py`, `automation/session_discovery.py`, `golf_db.py`, UI components

---

## 1. Current Capabilities by Class

### ClubNameNormalizer (`naming_conventions.py:39-261`)

**Status: Fully implemented, actively used.**

- Normalizes raw club names to canonical forms (e.g., `"7i"` -> `"7 Iron"`, `"sand"` -> `"SW"`)
- 70+ regex patterns covering woods, hybrids, irons, wedges, putter
- Degree-based wedge mapping (44-62 degrees)
- Custom user-defined mappings via `add_custom_mapping()`
- Batch normalization and confidence-scored results
- Normalization report generation for auditing

**Where it's used:**
- `backfill_runner.py:601` -- normalizes club names post-import
- `uneekor_portal.py:21` -- imported for use during portal navigation
- `automation_runner.py:60` -- imported via `get_normalizer()`
- Singleton accessor: `get_normalizer()` / `normalize_club()` / `normalize_clubs()`

**No gaps identified.** This is the most complete and well-integrated class in the module.

---

### SessionNamer (`naming_conventions.py:264-387`)

**Status: Implemented but limited in output format. Used only in backfill post-processing.**

**What it does:**
- `generate_name()` -- produces names like `"Practice - Jan 25, 2026"`, `"Drill - Driver Consistency - Jan 25, 2026"`
- `infer_session_type()` -- heuristic-based session type detection from shot count + club count
- Supports 6 session types: practice, drill, round, fitting, warmup, lesson

**Where it's used:**
- `backfill_runner.py:607-614` -- called after import to infer type and generate name
- The generated `session_name` is stored in `sessions_discovered.session_name` via `mark_imported()`

**Gaps identified:**

1. **Name format doesn't match the planned schema.** The current format is `"{Type} - {Date}"` (e.g., `"Practice - Jan 25, 2026"`). The planned schema is `"{YYYY-MM-DD} {session_type} ({shot_count} shots)"` (e.g., `"2026-01-25 Practice (47 shots)"`). The `generate_name()` method would need a new format option or a new method entirely.

2. **No shot count in the generated name.** The `shot_count` parameter exists in the method signature but is never used in the output string. It's accepted but silently ignored.

3. **Session name is stored only in `sessions_discovered`, not in `shots`.** The `shots` table has no `session_name` column. The UI (`session_selector.py:31`) displays sessions as `"{session_id} ({date_added})"` -- raw report IDs, not human-readable names. The generated name is essentially invisible to the user.

4. **`infer_session_type()` has overlapping logic.** A session with 1 club and 50 shots hits the "drill" rule (<=2 clubs, >=30 shots) before the "fitting" rule (1 club, >=50 shots). The fitting rule is unreachable for 1-club sessions because drill matches first.

5. **No `generate_name()` format for the planned schema.** There's no method that produces `"{YYYY-MM-DD} {session_type} ({shot_count} shots)"`.

6. **No post-import renaming integration.** When sessions are imported, the name is generated once. If session_date is corrected later (via reclassify-dates), the session name is not regenerated.

---

### AutoTagger (`naming_conventions.py:390-492`)

**Status: Implemented, used in backfill post-processing. Stores tags only in `sessions_discovered`.**

**What it does:**
- 7 built-in rules: Driver Focus, Short Game, Full Bag, High Volume, Warmup, Iron Work, Woods Focus
- Extensible via `add_custom_rule()`
- Returns list of applicable tag strings

**Where it's used:**
- `backfill_runner.py:617-621` -- auto-tags after import, stores in `sessions_discovered.tags_json`

**Gaps identified:**

1. **Tags are stored in `sessions_discovered.tags_json` but never propagated to `shots.shot_tag`.** The `shots` table has a `shot_tag` column (single value per shot), but the auto-tagger output (a list of tags per session) is only saved in the discovery tracking table. The UI components read `session_type` from shots but never read tags from `sessions_discovered`.

2. **Session-level tags vs. shot-level tags mismatch.** The auto-tagger produces session-level tags (e.g., "Driver Focus" for the whole session), but the `shots` table only has `shot_tag` (per-shot). There's no `session_tags` column in `shots` and no separate sessions table to store them.

3. **Tags are not surfaced in the UI.** The session list component (`session_list.py:211-221`) shows `session_type` badges but has no code to display auto-generated tags. The `tag_catalog` table and related functions in `golf_db.py` are for manual shot tagging, not auto-tagging.

4. **No re-tagging mechanism.** If shot data changes (e.g., clubs renamed, shots added/removed), tags are not recalculated.

---

### SessionContextParser (`naming_conventions.py:495-656`)

**Status: Implemented but appears to have zero usage outside of tests.**

**What it does:**
- Parses Uneekor portal session context strings (e.g., `"Warmup PW"`, `"Sgt Rd1"`, `"8 Iron Dst Trainer"`)
- Extracts session_type (warmup, drill, sim_round, bag_mapping, etc.)
- Extracts embedded club names
- Parses listing page date strings via `parse_listing_date()`

**Where it's used:**
- `parse_listing_date()` is used as a convenience function (imported in tests)
- The main `parse()` and `extract_club()` methods appear to have **no callers** outside of `tests/unit/test_naming_conventions.py`

**Gaps identified:**

1. **Dead code for session context parsing.** The `parse()`, `extract_club()`, and `extract_session_type()` methods have no callers in production code. The `SessionContextParser` was built to parse portal session names but is never invoked during discovery or import.

2. **Should be used in `uneekor_portal.py`.** When `_parse_session_from_link()` extracts `portal_name` from the link text, it could pass that through `SessionContextParser.parse()` to extract richer metadata (session_type, primary club). Currently this metadata is lost.

3. **`parse_listing_date()` is well-placed** and used correctly through the convenience function. No gap here.

---

## 2. What's Implemented but Not Used

| Feature | Location | Status |
|---------|----------|--------|
| `SessionContextParser.parse()` | `naming_conventions.py:571` | Dead code -- no production callers |
| `SessionContextParser.extract_club()` | `naming_conventions.py:634` | Dead code -- no production callers |
| `SessionContextParser.extract_session_type()` | `naming_conventions.py:646` | Dead code -- no production callers |
| `SessionNamer.generate_name(shot_count=)` | `naming_conventions.py:313` | Parameter accepted but ignored |
| `sessions_discovered.session_name` column | `session_discovery.py:128` | Written by `mark_imported()` but never read by UI |
| `sessions_discovered.session_type` column | `session_discovery.py:129` | Written by `mark_imported()` but never read by UI |
| `sessions_discovered.tags_json` column | `session_discovery.py:130` | Written by `mark_imported()` but never read by UI |
| `get_session_namer()` singleton | `naming_conventions.py:711` | Used only by backfill_runner |
| `get_auto_tagger()` singleton | `naming_conventions.py:719` | Used only by backfill_runner |
| `get_context_parser()` singleton | `naming_conventions.py:737` | Never used in production |
| `parse_session_context()` convenience | `naming_conventions.py:745` | Never used in production |
| `extract_club_from_context()` convenience | `naming_conventions.py:750` | Never used in production |

---

## 3. What's Missing for the Planned Naming Schema

The planned naming schema is: `"{YYYY-MM-DD} {session_type} ({shot_count} shots)"`

Example: `"2026-01-25 Practice (47 shots)"`

### Missing pieces:

**A. No method to generate names in the target format.**
- `SessionNamer.generate_name()` produces `"Practice - Jan 25, 2026"` format
- Need either a new method or a format parameter that produces `"2026-01-25 Practice (47 shots)"`
- The `shot_count` parameter is already in the signature but unused

**B. No `session_name` column in the `shots` table.**
- `golf_db.py` schema (`init_db()`) has no `session_name` column
- The `sessions_discovered` table has one, but that's in the automation tracking layer
- The UI reads directly from `shots` table via `get_unique_sessions()` and `get_session_data()`
- Need either: a `session_name` column in `shots`, or a join/lookup mechanism to retrieve the name from `sessions_discovered`

**C. No bridge between `sessions_discovered` metadata and the UI.**
- `get_unique_sessions()` in `golf_db.py:540` queries `shots` table only
- Returns `session_id`, `date_added`, `session_type` -- no session_name
- The session selector (`session_selector.py:31`) formats labels from this limited data
- Need a function that enriches session data with names/tags from `sessions_discovered`

**D. No session name regeneration after date corrections.**
- When `reclassify-dates` updates a session's date, the name should be regenerated
- Currently no trigger or function exists for this
- `update_session_date()` in `session_discovery.py:633` only updates the date, not the name

**E. No bulk rename-sessions-by-schema function.**
- For existing sessions already imported, there's no way to retroactively apply the new naming schema
- Need a function that iterates sessions, computes the name from existing data (date, type, shot count), and stores it

---

## 4. Integration Points Between Modules

```
                  naming_conventions.py
                  /        |          \
         ClubName    SessionNamer   AutoTagger    SessionContextParser
         Normalizer                                   (UNUSED)
            |              |              |
            v              v              v
      backfill_runner.py (post-import processing)
            |              |              |
            v              v              v
    golf_db.rename_club  sessions_discovered    sessions_discovered
    (shots.club)         .session_name          .tags_json
                         .session_type
                              |
                              X  <-- GAP: no bridge to UI
                              |
                         UI components read from shots table only
                         session_selector.py: shows session_id + date_added
                         session_list.py: shows session_type badge
                         session_header.py: shows session_type badge
```

### Key integration gaps:

1. **`sessions_discovered` -> `shots` table**: Session name and tags generated during import are stored in `sessions_discovered` but never copied to the `shots` table or surfaced in the UI query path.

2. **`SessionContextParser` -> `uneekor_portal.py`**: The parser can extract session types and clubs from portal names, but the portal navigator doesn't use it. Integrating this would provide richer metadata during discovery.

3. **`AutoTagger` -> `shots.shot_tag`**: The per-shot `shot_tag` column exists in `shots`, but the auto-tagger operates at the session level and its output goes to `sessions_discovered.tags_json`. No code propagates session-level tags to individual shots.

4. **Date reclassification -> name regeneration**: The reclassify-dates commands in `automation_runner.py` update `sessions_discovered.session_date` but don't regenerate `session_name`.

---

## 5. Specific Recommendations

### Extending SessionNamer

1. **Add a format option or new method for the planned schema:**
```python
def generate_display_name(
    self,
    session_date: datetime,
    session_type: str,
    shot_count: int,
) -> str:
    """Generate display name in standard format: '2026-01-25 Practice (47 shots)'"""
    date_str = session_date.strftime('%Y-%m-%d')
    type_name = self.SESSION_TYPES.get(session_type.lower(), session_type.capitalize())
    return f"{date_str} {type_name} ({shot_count} shots)"
```

2. **Fix the `shot_count` parameter in `generate_name()`** so it's actually used. At minimum, append it to the existing format when provided: `"Practice - Jan 25, 2026 (47 shots)"`.

3. **Fix the drill/fitting priority overlap in `infer_session_type()`**: Move the fitting check before the drill check, or add a shot_count threshold to distinguish them (e.g., 1 club + >=50 shots = fitting, 1-2 clubs + 30-49 shots = drill).

4. **Add a `regenerate_name()` method** that takes a report_id, looks up current metadata (date, type, shot count), and returns an updated name. This supports the date reclassification use case.

### Extending AutoTagger

1. **Add a method to propagate tags to shots**: `apply_tags_to_session(session_id, tags)` that writes to `shots.shot_tag` or a new column.

2. **Add a `retag_session()` method** that re-evaluates rules based on current shot data and updates both `sessions_discovered.tags_json` and any shot-level storage.

3. **Consider adding more rules** based on data patterns rather than just club/count heuristics:
   - "Consistency Work" (low standard deviation in carry for a club)
   - "Distance Session" (all clubs hit for max distance)
   - "Mixed Practice" (variety of clubs, moderate counts each)

### Bridging sessions_discovered and the UI

1. **Create a `get_session_metadata()` function in `golf_db.py`** that joins `shots` with `sessions_discovered` to return enriched session data including `session_name`, `tags_json`, and `date_source`.

2. **Alternatively, add `session_name` as a column in `shots`** (migration in `init_db()`), and propagate it during import and during any session rename/date update. This is simpler but denormalizes the data.

3. **Update `get_unique_sessions()`** to include session names in its return data, so UI components can display human-readable labels instead of raw report IDs.

### Activating SessionContextParser

1. **Integrate into `uneekor_portal.py`** during `_parse_session_from_link()`. After extracting the link text as `portal_name`, pass it through `SessionContextParser.parse()` to populate `session_type` and primary club in the `SessionInfo` object.

2. **Use during discovery** to pre-populate `sessions_discovered.session_type` before import, instead of only setting it post-import in the backfill runner.

### Retroactive naming for existing data

1. **Create a CLI command** (e.g., `python automation_runner.py rename-sessions --schema standard`) that:
   - Queries all sessions in `sessions_discovered`
   - For each, computes the new name using date + inferred type + shot count
   - Updates `sessions_discovered.session_name`
   - Optionally propagates to `shots` table if/when that column exists

2. **Wire into `reclassify-dates --backfill`** so that after dates are propagated to shots, session names are also regenerated.

---

## 6. Summary of Priority Actions

| Priority | Action | Effort |
|----------|--------|--------|
| **P0** | Add `generate_display_name()` to `SessionNamer` for new format | Small |
| **P0** | Create bridge function to surface `sessions_discovered` metadata in UI | Medium |
| **P1** | Integrate `SessionContextParser` into `uneekor_portal.py` discovery | Medium |
| **P1** | Add session name regeneration to date reclassification flow | Small |
| **P2** | Fix drill/fitting overlap in `infer_session_type()` | Small |
| **P2** | Make `shot_count` actually appear in `generate_name()` output | Small |
| **P2** | Add retroactive bulk rename CLI command | Medium |
| **P3** | Propagate auto-tagger output to shot-level storage | Medium |
| **P3** | Add re-tagging capability when session data changes | Medium |
