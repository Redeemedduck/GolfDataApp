# UI Simplification & Mobile Optimization Design

**Date:** 2026-02-06
**Status:** Approved
**Branch:** feat/ui-ux-redesign

## Problem

The app feels overwhelming. Agent audit found:
- Dashboard: 9 tab levels, 50-70 metrics, 10-15 screens of scroll
- Home: 28 metrics across 8 session cards
- 10 instances of `st.columns(3+)` that collapse poorly on mobile
- 4 dead components never imported
- Date parsing duplicated in 3 files, Big 3 thresholds in 2

## Design Decisions

### Dashboard: 5 Tabs to 3

| Keep | Cut | Destination |
|------|-----|-------------|
| Overview | — | Trim to 3 metrics, remove box plot, remove Big 3 summary (lives in Big 3 tab) |
| Big 3 | — | Remove redundant summary at top, start directly with sub-tabs |
| Shots | — | Keep as-is (lean) |
| ~~Compare~~ | Cut | Move to Club Profiles (compare sessions for a specific club) |
| ~~Export~~ | Cut | Move to sidebar download button |

### Home Page: Tighten Cards

- Hero stats: `st.columns(4)` → 2x2 grid
- Journal cards: Drop "Best Carry" metric (keep Avg Carry + Smash)
- Big 3 in cards: Single-line summary instead of 3-column HTML blocks
- Calendar strip: Dynamic cell width for mobile

### Mobile: Layout Toggle

Add "Compact Layout" toggle in sidebar (`utils/responsive.py`):
- Controls column counts, chart heights, calendar weeks
- No CSS viewport hacks — pure Python layout switching
- Single source of truth: `is_compact_layout()` function

### Club Profiles: Absorb Compare

- Add session comparison for selected club (from Dashboard Compare tab)
- Move club selector from sidebar to main area
- Limit radar chart to 3 clubs max

### Settings: 5 Tabs to 3

- "Import" + "Sessions" → "Data"
- "Data Quality" + "Sync" → "Maintenance"
- "Tags" → stays

### Code Cleanup (DRY)

1. Date parsing (`_parse_session_date()`) in 3 files → `utils/date_helpers.py`
2. Big 3 thresholds in 2 files → `utils/big3_constants.py`
3. Delete dead components: `session_list.py`, `simple_view.py`, `coach_export.py`, `session_header.py`

## Files Affected

| Action | Files |
|--------|-------|
| **New** | `utils/date_helpers.py`, `utils/big3_constants.py` |
| **Delete** | `components/session_list.py`, `components/simple_view.py`, `components/coach_export.py`, `components/session_header.py` |
| **Modify** | `pages/1_Dashboard.py`, `pages/2_Club_Profiles.py`, `pages/4_Settings.py`, `app.py`, `components/journal_card.py`, `components/journal_view.py`, `components/calendar_strip.py`, `components/big3_summary.py`, `components/big3_detail_view.py`, `components/club_hero.py`, `components/metrics_card.py`, `components/face_path_diagram.py`, `components/radar_chart.py`, `components/shared_sidebar.py`, `utils/responsive.py`, `components/__init__.py` |

## Success Criteria

- Dashboard: 3 tabs, < 35 metrics total
- Home: Expanded journal card fits in ~1.5 mobile screens (was ~4)
- Mobile: All pages functional at 390px with Compact Layout on
- Zero duplicated date parsing or Big 3 threshold logic
- All existing tests pass + no dead code
