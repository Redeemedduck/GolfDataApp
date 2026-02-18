# Session Handoff: Uneekor Field Trip & Data Model Brainstorm

**Date:** 2026-02-13
**Status:** In-progress — club group extraction ~30% done
**Context:** Brainstorming before Phase 5-7 execution revealed fundamental data problems

---

## What We Were Doing

Originally planning to execute Phases 5-7 (Club Profiles Rebuild, Big 3 & UX Polish, Advanced Features) via Codex Orchestrator. User correctly stopped us to brainstorm because **the app's data model is divorced from reality**.

## The Core Problem (Confirmed by Data)

### Database Reality
- **2,159 total shots** in SQLite
- **977 shots (45%)** have a resolved club name — maps to 11 clubs in `my_bag.json`
- **1,182 shots (55%)** have `club=NULL` — unresolvable session names like "Warmup", "Sgt Rd1", "Bag Mapping"
- The normalizer (Phases 1-3) resolved what it could from text, but pure session names have zero club info

### User's Real Bag (14-15 clubs)
Driver, 3+ Wood (Cobra Darkforce), 3 Wood (TaylorMade RS11), 7 Wood, 3 Iron (driving iron — currently labeled "1 Iron" in my_bag.json), 4 Iron, 5 Iron, 6 Iron, 7 Iron, 8 Iron, 9 Iron, PW, GW (50°), SW (56°), LW (60°)

**`my_bag.json` is missing:** 7 Wood, 4 Iron, 5 Iron
**`my_bag.json` is wrong:** "1 Iron" should be "3 Iron" (driving iron)
**`my_bag.json` doesn't handle:** Two different 3 Woods

### Uneekor Has the Data
Every Uneekor report has **two naming systems**:
1. **Sidebar labels** (user-friendly): "dpc scottsdale", "Iron 8", "warmup"
2. **Internal Uneekor names** (standardized): IRON1, IRON8, DRIVER, 50WEDGE, PITCHINGWEDGE

The scraper currently captures session names, not the per-shot club group data. **This is the root cause of the 1,182 NULL-club shots.**

### Critical Caveat
Uneekor club groups are **self-reported** (based on what club the user selected in the software), NOT auto-detected. Example: "warmup" session (43285) — all 41 shots tagged PITCHINGWEDGE, but shot 16 has 196-yard carry and 1.50 smash factor, which is clearly a Driver.

## What We've Extracted So Far

### Complete Report Listing: 120 reports
Saved to: `docs/research/uneekor-report-listing-2026-02-13.md`
All 120 session names, dates, shot counts, and report URLs.

### Club Group Extractions (8 reports done)

| Report ID | Session Name | Shots | Club Groups (Internal Names) |
|-----------|-------------|-------|------------------------------|
| 43806 | dpc scottsdale | 80 | IRON1(26), IRON8(3), DRIVER(4), 60WEDGE(3+6), 50WEDGE(3), PITCHINGWEDGE(3+29), IRON9(3) |
| 44413 | sgt pebble | 97 | IRON1(52), 50WEDGE(15), PITCHINGWEDGE(30) |
| 41360 | bag mapping | 85 | IRON1(67), 50WEDGE(18) |
| 43285 | warmup | 41 | PITCHINGWEDGE(41) — but contains mis-classified Driver shots |
| 43101 | sgt rd1 | 68 | IRON1(32), IRON6(9), PITCHINGWEDGE(10+17) |
| 43166 | par 3 | 40 | IRON1(40) |
| 27056 | 60 shot challenge | 98 | IRON8(60), IRON9(26), PITCHINGWEDGE(12) |
| 42646 | sgt wailaie rd1 cont | 112 | IRON1(49), IRON7(28), PITCHINGWEDGE(35) |
| 41985 | shadow ridge sgt | 73 | IRON1(45), IRON8(14), 50WEDGE(14) |

### Key Pattern: IRON1 Dominance
Most multi-club sessions show IRON1 as the main club group, inheriting the session name. This maps to the user's "3 Iron driving iron" — their most-used club.

## Remaining Work

### Still Need to Extract (~90 more reports)
The report listing has 120 total. We've extracted club groups for 8. The remaining ~30 NULL-club sessions are the highest priority, but ideally we extract all 120 for a complete picture.

**Method that works:** osascript + Chrome JavaScript injection. Navigate to report URL, wait 4-5 seconds, extract sidebar buttons and internal pill names.

**Chrome extension (mcp__claude-in-chrome):** NOT working — returns "Browser extension is not connected." The extension IS installed and active (shows "Claude is active in this tab group") but the MCP bridge isn't establishing. We used osascript as a workaround.

### After Extraction: Next Steps
1. **Save complete club group map** → `docs/research/`
2. **Cross-reference with database** — match report IDs to sessions_discovered, identify what's recoverable
3. **Update `my_bag.json`** — add 7 Wood, 4 Iron, 5 Iron; rename 1 Iron → 3 Iron
4. **Design scraper fix** — capture per-shot club groups from report sidebar during import
5. **Re-import strategy** — re-scrape the ~30 NULL-club sessions with the fixed scraper
6. **THEN proceed with Phases 5-7** on clean data

## Technical Notes

### How to Extract Club Groups via osascript
```applescript
tell application "Google Chrome"
    -- Navigate to report
    set URL of t to "https://my.uneekor.com/power-u-report?id=XXXXX&key=YYYYY&distance=yard&speed=mph"
    delay 5
    -- Extract sidebar groups
    execute t javascript "
        var sidebar = [];
        document.querySelectorAll('button').forEach(function(b) {
            var text = b.innerText.trim().replace(/\\n/g, ' ');
            if (text.match(/^\\(\\d+\\)/) && text.length < 80) sidebar.push(text);
        });
        // Internal names appear as text nodes matching CLUBNAME(COUNT)
        var pills = document.body.innerText.match(/(?:IRON|DRIVER|WOOD|HYBRID|PITCHING|50WEDGE|56WEDGE|60WEDGE)\\w*\\s*\\(\\d+\\)/g);
    "
end tell
```

### Uneekor Internal Club Name → Canonical Mapping
| Uneekor Internal | Canonical (should be) |
|---|---|
| IRON1 | 3 Iron (driving iron) |
| IRON5 | 5 Iron |
| IRON6 | 6 Iron |
| IRON7 | 7 Iron |
| IRON8 | 8 Iron |
| IRON9 | 9 Iron |
| DRIVER | Driver |
| WOOD2 | 3 Wood (?) |
| WOOD3 | 3 Wood |
| 50WEDGE | GW (50°) |
| 56WEDGE | SW (56°) |
| 60WEDGE | LW (60°) |
| PITCHINGWEDGE | PW |

Note: IRON1 in Uneekor = user's "1 Iron" selection, but it's actually a 3 Iron driving iron. The Uneekor software doesn't know the difference — it's whatever club slot the user selected.

### Files Created This Session
- `docs/research/uneekor-report-listing-2026-02-13.md` — all 120 reports
- `docs/research/session-handoff-2026-02-13-field-trip.md` — THIS FILE
- `.codex-session.md` — updated with Phase 5-7 task plan (will need revision after data work)

### Design Doc Reference
Full Phase 1-7 design: `docs/plans/2026-02-13-data-model-and-ux-overhaul-design.md`
Phase 4 handoff: `docs/plans/2026-02-13-phase4-handoff.md`

---

## Decision Point When Resuming

The user wants to:
1. **Complete the club group extraction** for all 120 reports (or at least all NULL-club sessions)
2. **Use Codex Orchestrator + parallel agents** for the heavy lifting once data mapping is complete
3. **Fix the scraper** to capture club groups per shot
4. **Re-import** the 1,182 orphaned shots with proper club data
5. **Then** build Phases 5-7 UI on clean, complete data

The brainstorming skill flow is at step 2 (clarifying questions) — we need to finish data mapping before we can propose approaches and present a design.
