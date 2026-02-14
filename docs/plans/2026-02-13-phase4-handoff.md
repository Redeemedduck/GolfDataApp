# Phase 4: Dashboard Rebuild — Session Handoff

**Date:** 2026-02-13
**Branch:** `feat/phase4-dashboard-rebuild`
**Worktree:** `.worktrees/phase4-dashboard-rebuild`
**Status:** All 4 tasks complete, ready for PR or merge

---

## What Was Done

Phase 4 of the Data Model & UX Overhaul (design doc: `docs/plans/2026-02-13-data-model-and-ux-overhaul-design.md`).

**Note:** Phase 4a (Training Log) and 4b (Session Selector) were already implemented from earlier work. This session completed 4c and 4d.

### Commits (4)

| Commit | Task | Description |
|--------|------|-------------|
| `b8dc7d4` | 4c | Per-club smash factor targets in `my_bag.json` + `bag_config.py` |
| `6c40d0a` | 4d | Stripped sidebar to navigation-only across all 6 pages |
| `d26c5db` | 4d | Added Display tab to Settings with relocated controls |
| `9b97a60` | docs | Updated CLAUDE.md with Phase 4 changes |

### Files Changed

| File | Change |
|------|--------|
| `my_bag.json` | Added `smash_targets` dict (11 clubs) |
| `utils/bag_config.py` | Added `get_smash_target()`, `get_all_smash_targets()` |
| `tests/unit/test_bag_config.py` | New: 9 tests for bag config + smash targets |
| `components/shared_sidebar.py` | Simplified to nav-only; kept individual render functions for Settings import |
| `app.py` | Removed Health section, observability import, doc links; simplified sidebar call |
| `pages/1_📊_Dashboard.py` | Simplified sidebar call |
| `pages/2_🏌️_Club_Profiles.py` | Simplified sidebar call |
| `pages/3_🤖_AI_Coach.py` | Simplified sidebar call |
| `pages/4_⚙️_Settings.py` | Added Display tab (5th tab) with data source, sync status, layout, appearance |
| `CLAUDE.md` | Updated Settings tab count, bag_config functions, sidebar convention |

---

## Test Results

- **261 tests total** (252 baseline + 9 new bag config tests)
- **254 passing**
- **7 pre-existing failures** (unrelated — agent SDK imports, local coach provider, sync service)
- **CI lint:** All `py_compile` checks pass

---

## Next Steps for New Session

### Immediate: Finish this branch

```bash
# Option A: Create PR
cd /Users/max1/Documents/GitHub/GolfDataApp
git push -u origin feat/phase4-dashboard-rebuild
gh pr create --title "feat: Phase 4 - Dashboard rebuild (smash targets + sidebar cleanup)" --body "..."

# Option B: Merge directly
git checkout main
git merge feat/phase4-dashboard-rebuild
```

After merging, clean up:
```bash
git worktree remove .worktrees/phase4-dashboard-rebuild
git branch -d feat/phase4-dashboard-rebuild
```

### Then: Phase 5 — Club Profiles Rebuild

From the design doc, Phase 5 covers:
- **5a.** Filter club dropdown to real clubs from `my_bag.json` only (not session names)
- **5b.** Smart comparison suggestions based on bag position (viewing 7i → suggest 6i, 8i)
- **5c.** Fix Distance Over Time x-axis labels (timestamp formatting bug)

### Later Phases

- **Phase 6:** Big 3 & UX Polish (contrast, quadrant labels, date range filter, session notes)
- **Phase 7:** Advanced Features (trajectory viz, shot-by-shot nav, goal tracking)

---

## Key Decisions Made

1. **Smash targets in `my_bag.json`** (not separate file or database) — simple, co-located
2. **Sidebar = navigation only** — ALL controls moved to Settings > Display tab
3. **Kept render functions in `shared_sidebar.py`** — Settings imports them directly rather than duplicating
