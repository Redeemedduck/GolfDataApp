# Uneekor Portal Naming Patterns

**Date:** 2026-02-05
**Database analyzed:** `golf_stats.db` (118 sessions in `sessions_discovered`)

---

## 1. Portal Name Patterns (`portal_name` Column)

The `portal_name` field stores the visible link text from the Uneekor listing page. In practice, it is almost entirely useless:

| Value | Count | Notes |
|-------|-------|-------|
| `None` | 113 | No text extracted; the vast majority of sessions |
| `"Open"` | 5 | Only the 5 most-recently-discovered sessions (IDs 43033--43285) |

**Key finding:** The Uneekor portal renders session links with the text "Open" as a clickable action label, not a descriptive session name. The portal does not assign user-facing session names at all. Earlier discovery runs (before the DOM walker was added) produced `None` because the link text was not captured.

**Where `portal_name` is set in code:**
`automation/uneekor_portal.py` line 460 -- it stores the `innerText` of the `<a>` element:
```python
portal_name=text.strip() if text else None,
```
The portal links render as something like `<a href="/power-u-report?id=43285&key=...">Open</a>`, so the extracted text is literally the word "Open".

---

## 2. URL Structure Patterns (`source_url` Column)

### Base URL Pattern

All 118 sessions use the `power-u-report` endpoint (zero use the older `report` endpoint):

```
/power-u-report?id={report_id}&key={api_key}[&distance=yard&speed=mph]
```

### Two URL Formats Exist

| Format | Count | Discovery Method |
|--------|-------|------------------|
| **Relative** (starts with `/power-u-report`) | 93 | Newer DOM walker extraction (JavaScript `node.href` was not used for CSS selector results) |
| **Absolute** (starts with `https://my.uneekor.com/power-u-report`) | 25 | Older discovery runs where JavaScript DOM walker returned absolute URLs |

The difference is an artifact of **which code path extracted the URL**:
- CSS `query_selector_all` returns the raw `href` attribute (relative).
- JavaScript `node.href` returns the fully-resolved absolute URL.

The `_find_session_links()` method in `uneekor_portal.py` merges both sources by matching on `report_id`, but stores whichever URL came first.

### Query Parameter Variations

| Parameter Set | Count | Notes |
|---------------|-------|-------|
| `id` + `key` + `distance` + `speed` | 93 | Newer discovery runs capture the full portal link which includes unit preferences |
| `id` + `key` only | 25 | Older discovery runs; units not in URL |

The `distance=yard&speed=mph` parameters are unit preferences appended by the portal UI, not required for API access. The `SessionInfo.import_url` property strips these and constructs a clean URL:
```
https://my.uneekor.com/report?id={report_id}&key={api_key}
```

Note: The import URL uses `/report` (not `/power-u-report`), which is the API endpoint consumed by `golf_scraper.py`.

### Report ID Structure

- **Range:** 16,076 to 43,806
- **Sequential, globally shared:** IDs are assigned server-side across all Uneekor users. The average gap between consecutive sessions for this user is ~237 IDs, meaning roughly 236 other sessions from other users are interspersed.
- **Monotonically increasing:** Higher IDs = more recent sessions (with a few exceptions where multiple sessions share the same date).

### API Key Structure

- **Length:** 12--16 characters (fairly evenly distributed)
- **Character set:** Alphanumeric (mixed case), no special characters
- **Per-session:** Each session has a unique, opaque API key

---

## 3. Session Date Discovery (`date_source` Column)

| Source | Count | Reliability |
|--------|-------|-------------|
| `listing_page` | 93 | High -- dates extracted from DOM date headers (e.g., "January 15, 2026") |
| `None` (no date) | 22 | Sessions discovered before listing-page extraction was implemented |
| `report_page` | 2 | Low -- report pages show today's view date, not the original session date |
| `manual` | 1 | User-entered via `--manual` CLI flag |

**Critical issue with `report_page` dates:** IDs 20842 and 20718 (from mid-2024 based on surrounding IDs) have `session_date = 2026-02-02` with `date_source = report_page`. These are clearly wrong -- the report page displays the current date when viewed, not the historical session date. This is the exact bug documented in `CLAUDE.md` under "Known Limitations."

**22 sessions have no date at all.** These are a mix of:
- Old sessions discovered before the `--from-listing` feature existed
- Sessions that may not have appeared under date headers on the listing page

---

## 4. How Sessions Are Named Post-Import (`session_name` / `session_type`)

The portal provides no session names. Instead, the **`BackfillRunner`** generates names after import using `SessionNamer` and `SessionNamer.infer_session_type()`:

### Session Type Inference Logic

Based on shot count and number of distinct clubs:

| Condition | Inferred Type |
|-----------|---------------|
| `shot_count < 10` | `warmup` |
| `num_clubs <= 2` and `shot_count >= 30` | `drill` |
| `num_clubs == 1` and `shot_count >= 50` | `fitting` |
| `num_clubs >= 3` | `practice` |
| Default | `practice` |

### Generated Name Format

```
{TypeName} - {Mon DD, YYYY}
```

Examples from the database:
- `Practice - Jan 26, 2026`
- `Drill - Jan 26, 2026`
- `Warmup - Jan 26, 2026`

**Issue: Many imported sessions share the same generated name** because the date used is `date_added` (the import date), not `session_date`. Multiple sessions imported on the same day all get names like "Practice - Jan 26, 2026" or "Drill - Jan 26, 2026", making them indistinguishable.

---

## 5. What the Portal Actually Calls "Club Names"

The Uneekor portal uses a free-text "club" field per shot that users configure on the launch monitor. These are **not standard club names** -- they are user-defined session context labels. Examples from the `shots` table:

| Raw Club Value | Apparent Meaning |
|----------------|------------------|
| `Warmup` | Warmup shots (no club specified) |
| `Warmup 50` | Warmup with 50-degree wedge |
| `Warmup 50 Degree` | Same, more explicit |
| `Warmup Pw` | Warmup with pitching wedge |
| `Par 3` | Par-3 practice mode |
| `Sgt Rd1` | Sim Golf Tour, Round 1 |
| `Sgt Shadowridge Rd2` | Sim Golf Tour, Shadow Ridge course, Round 2 |
| `Sgt Plantation Course` | Sim Golf Tour, Plantation course |
| `Sgt Sony Open 1` | Sim Golf Tour, Sony Open |
| `Sgt Wailaie Rd1 Cont` | Sim Golf Tour, Wailaie, Round 1 continuation |
| `Dst Trainer` | Distance Trainer mode |
| `Dst Compressor 8` | Distance Compressor drill, 8 Iron |
| `Dst Compressor 8 Full` | Full swing variant |
| `Dst Compressor Half Swing` | Half swing variant |
| `8 Dst Warmup` | 8 Iron distance warmup |
| `3/4 Speed Towel Drill` | Specific drill (3/4 speed, towel drill) |
| `Bag Mapping` | Full bag mapping session |
| `Forward Impact Pw` | Forward impact drill with PW |
| `1 Iron` | Standard club name |
| `Driver` | Standard club name |
| `6 Iron` | Standard club name |
| `Wedge Pitching` | Pitching wedge (non-standard naming) |
| `Wedge 50` | 50-degree wedge |
| `50 Warmup` | 50-degree wedge warmup |
| `IRON6 \| MEDIUM` | Legacy format (older sessions, pipe-delimited with speed) |
| `Iron6 \| Medium` | Same, different casing |

The `SessionContextParser` class in `naming_conventions.py` handles many of these patterns, extracting both the session type (warmup, drill, sim_round, etc.) and embedded club names.

---

## 6. Gaps and Inconsistencies

### 6.1 Portal Names Are Not Meaningful
The `portal_name` column stores "Open" or `None`. It cannot be used for session identification or deduplication. The field exists in the schema but serves no practical purpose beyond confirming that a link was found.

### 6.2 URL Format Inconsistency
The `source_url` column contains a mix of relative and absolute URLs depending on when discovery ran. Code that uses `source_url` must handle both. The `SessionInfo.import_url` property correctly normalizes to an absolute URL for the API, but the stored `source_url` remains inconsistent.

### 6.3 Session Name Generation Uses Wrong Date
The `session_name` for imported sessions (e.g., "Practice - Jan 26, 2026") uses the import date rather than the actual session date in many cases. Sessions imported in batch on the same day become indistinguishable by name. Example: session 42719 (session_date=2026-01-15) has session_name="Practice - Jan 26, 2026" because it was imported on Jan 26.

### 6.4 Two Report Page Dates Are Clearly Wrong
Sessions 20842 and 20718 have `date_source=report_page` with `session_date=2026-02-02T00:00:00`. Based on their report IDs (around 20,000), these are from mid-2024. The report page scraper captured the "view date" instead of the session date.

### 6.5 No Clubs Tracked at Discovery Time
The `clubs_json` column is `None` for all 118 sessions. Club information is only available after importing the shot data (from the `shots` table). The portal listing page does not expose per-session club info.

### 6.6 `session_name` and `session_type` Only Populated for Imported Sessions
The 91 pending sessions have no `session_name` or `session_type`. These are only generated during the backfill import process, not at discovery time.

### 6.7 Multiple Sessions Per Day Without Disambiguation
18 dates have 2--5 sessions each. Since the portal provides no session names and the generated names use only the date, there is no way to distinguish "Practice - Jan 26, 2026" (session A) from "Practice - Jan 26, 2026" (session B) without looking at the report ID or shot data.

---

## 7. Summary of Data Flow

```
Uneekor Portal Listing Page
  |
  |  _find_session_links() extracts:
  |    - href (relative or absolute URL with id + key)
  |    - text ("Open" or empty)
  |    - dateContext (date header text, e.g., "January 15, 2026")
  |
  v
_parse_session_from_link() creates SessionInfo:
  - report_id:    extracted from URL ?id= param
  - api_key:      extracted from URL ?key= param
  - portal_name:  link text ("Open" or None)
  - session_date: parsed from dateContext or link text
  - source_url:   raw href from page
  - clubs_used:   always empty (not available on listing page)
  |
  v
save_discovered_session() writes to sessions_discovered table
  |
  v
BackfillRunner.import_session() imports shot data:
  1. Constructs import_url: https://my.uneekor.com/report?id=X&key=Y
  2. Calls golf_scraper.run_scraper() to fetch shots via API
  3. Post-import: reads clubs from shots table
  4. Infers session_type from shot_count + clubs
  5. Generates session_name from type + date
  6. Auto-tags based on club composition
```
