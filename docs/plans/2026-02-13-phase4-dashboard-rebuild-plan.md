# Phase 4: Dashboard Rebuild — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add per-club smash factor targets to bag config, strip sidebar down to navigation-only, and move all technical controls to a new Settings "Display" tab.

**Architecture:** Extend `my_bag.json` with smash targets, add accessor functions to `bag_config.py`, slim `shared_sidebar.py` to navigation-only, add Display tab to Settings, update all page call sites.

**Tech Stack:** Python 3.10+, Streamlit, unittest

**Design Doc:** `docs/plans/2026-02-13-data-model-and-ux-overhaul-design.md` (Phase 4)

**Note:** Phase 4a (Training Log) and 4b (Session Selector) are already implemented — `app.py` has the 2x2 hero grid, calendar strip, and journal view with week grouping. This plan covers the remaining 4c and 4d work.

---

### Task 1: Add Smash Factor Targets to Bag Config

**Files:**
- Modify: `my_bag.json` (add smash_targets dict)
- Modify: `utils/bag_config.py` (add accessor functions)
- Test: `tests/unit/test_bag_config.py` (new)

**Step 1: Write the failing tests**

Create `tests/unit/test_bag_config.py`:

```python
"""Tests for bag configuration loader."""

import unittest
from utils.bag_config import (
    get_bag_order, get_club_sort_key, is_in_bag,
    get_smash_target, get_all_smash_targets,
)


class TestBagConfig(unittest.TestCase):
    """Verify bag config loads correctly."""

    def test_bag_order_returns_list(self):
        order = get_bag_order()
        self.assertIsInstance(order, list)
        self.assertIn("Driver", order)

    def test_club_sort_key_driver_first(self):
        self.assertEqual(get_club_sort_key("Driver"), 0)

    def test_is_in_bag_true(self):
        self.assertTrue(is_in_bag("Driver"))
        self.assertTrue(is_in_bag("7 Iron"))

    def test_is_in_bag_false(self):
        self.assertFalse(is_in_bag("Putter"))
        self.assertFalse(is_in_bag("Nonexistent"))


class TestSmashTargets(unittest.TestCase):
    """Verify smash factor target accessors."""

    def test_get_smash_target_driver(self):
        target = get_smash_target("Driver")
        self.assertIsNotNone(target)
        self.assertAlmostEqual(target, 1.49, places=1)

    def test_get_smash_target_iron(self):
        target = get_smash_target("7 Iron")
        self.assertIsNotNone(target)
        self.assertGreater(target, 1.0)
        self.assertLess(target, 1.5)

    def test_get_smash_target_unknown_returns_none(self):
        target = get_smash_target("Putter")
        self.assertIsNone(target)

    def test_get_all_smash_targets_returns_dict(self):
        targets = get_all_smash_targets()
        self.assertIsInstance(targets, dict)
        self.assertIn("Driver", targets)
        self.assertIn("7 Iron", targets)

    def test_all_bag_clubs_have_targets(self):
        order = get_bag_order()
        targets = get_all_smash_targets()
        for club in order:
            self.assertIn(club, targets, f"Missing smash target for {club}")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_bag_config -v 2>&1 | tail -5`
Expected: FAIL — `get_smash_target` does not exist

**Step 3: Add smash_targets to my_bag.json**

Add a `smash_targets` key with per-club targets based on the design doc:

```json
{
  "clubs": [...],
  "bag_order": [...],
  "smash_targets": {
    "Driver": 1.49,
    "3 Wood": 1.45,
    "1 Iron": 1.36,
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

**Step 4: Add accessor functions to bag_config.py**

Add after `get_club_sort_key()`:

```python
def get_smash_target(club_name: str) -> Optional[float]:
    """Return the target smash factor for a club, or None if not in bag."""
    targets = _load().get('smash_targets', {})
    return targets.get(club_name)


def get_all_smash_targets() -> Dict[str, float]:
    """Return all per-club smash factor targets."""
    return dict(_load().get('smash_targets', {}))
```

**Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_bag_config -v`
Expected: All PASS

**Step 6: Run full test suite**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: All tests OK

**Step 7: Commit**

```bash
git add my_bag.json utils/bag_config.py tests/unit/test_bag_config.py
git commit -m "feat: add per-club smash factor targets to bag config

Phase 4c: Targets based on typical tour averages by club category.
Loaded from my_bag.json alongside bag order and aliases."
```

---

### Task 2: Strip Sidebar to Navigation Only

**Files:**
- Modify: `components/shared_sidebar.py` (remove non-nav sections, keep functions for reuse)
- Modify: `app.py` (remove sidebar Health section, simplify render_shared_sidebar call)
- Modify: `pages/1_📊_Dashboard.py` (simplify call)
- Modify: `pages/2_🏌️_Club_Profiles.py` (simplify call)
- Modify: `pages/3_🤖_AI_Coach.py` (simplify call)
- Modify: `pages/4_⚙️_Settings.py` (simplify call)

**Step 1: Update render_shared_sidebar to nav-only defaults**

In `components/shared_sidebar.py`, change the default parameters:

```python
def render_shared_sidebar(
    show_navigation: bool = True,
    show_data_source: bool = False,   # Changed: moved to Settings
    show_sync_status: bool = False,   # Changed: moved to Settings
    show_mode_toggle: bool = False,
    current_page: str = None
) -> None:
```

Remove the `render_compact_toggle()` and `render_appearance_toggle()` calls from the main function body. The sidebar should only render navigation by default.

New body:

```python
    with st.sidebar:
        if show_mode_toggle:
            render_mode_toggle()
            st.divider()

        if show_navigation:
            render_navigation(current_page)

        if show_data_source:
            st.divider()
            render_data_source()

        if show_sync_status:
            render_sync_status()
```

Keep all the individual render functions (render_data_source, render_sync_status, etc.) — they'll be imported by the Settings page.

**Step 2: Update app.py — remove Health section and simplify sidebar call**

Replace lines 170-203:

```python
# ─── Sidebar ──────────────────────────────────────────────────
render_shared_sidebar(
    show_navigation=False,
    current_page="home"
)

with st.sidebar:
    st.divider()
    st.caption("Golf Data Lab v3.0 - Practice Journal")
    st.caption("Built around the Big 3 Impact Laws")
```

Remove the Health section (observability metrics) and documentation links — they'll move to Settings.

**Step 3: Update pages/1_📊_Dashboard.py — simplify call**

Change the `render_shared_sidebar` call to:

```python
render_shared_sidebar(current_page="dashboard")
```

**Step 4: Update pages/2_🏌️_Club_Profiles.py — simplify call**

Change to:

```python
render_shared_sidebar(current_page="club_profiles")
```

**Step 5: Update pages/3_🤖_AI_Coach.py — simplify call**

Change to:

```python
render_shared_sidebar(current_page="ai_coach")
```

**Step 6: Update pages/4_⚙️_Settings.py — simplify call**

Change to:

```python
render_shared_sidebar(current_page="settings")
```

**Step 7: Syntax check all modified files**

Run: `python -m py_compile app.py && python -m py_compile components/shared_sidebar.py && for f in pages/*.py; do python -m py_compile "$f"; done`
Expected: No errors

**Step 8: Run full test suite**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: All tests OK

**Step 9: Commit**

```bash
git add components/shared_sidebar.py app.py pages/
git commit -m "refactor: strip sidebar to navigation only

Phase 4d: Move data source, sync status, compact toggle,
appearance toggle, and health metrics out of sidebar.
All pages now get clean nav-only sidebar."
```

---

### Task 3: Add Display Tab to Settings Page

**Files:**
- Modify: `pages/4_⚙️_Settings.py` (add Display tab with relocated controls)

**Step 1: Add Display tab**

Change the tabs line from:

```python
tab_data, tab_maintenance, tab_tags, tab_automation = st.tabs([
    "Data", "Maintenance", "Tags", "Automation",
])
```

To:

```python
tab_data, tab_maintenance, tab_tags, tab_automation, tab_display = st.tabs([
    "Data", "Maintenance", "Tags", "Automation", "Display",
])
```

**Step 2: Import relocated sidebar functions**

Add imports at top of file:

```python
from components.shared_sidebar import (
    render_data_source,
    render_sync_status,
    render_mode_toggle,
    render_appearance_toggle,
)
from utils.responsive import render_compact_toggle
```

**Step 3: Build the Display tab content**

Add after the Automation tab block:

```python
# ================================================================
# TAB 5: DISPLAY (relocated from sidebar)
# ================================================================
with tab_display:
    st.subheader("Data Source")
    render_data_source()

    st.divider()

    st.subheader("Sync Status")
    render_sync_status()

    st.divider()

    st.subheader("Layout")
    render_compact_toggle()
    render_mode_toggle()

    st.divider()

    st.subheader("Appearance")
    render_appearance_toggle()
```

**Step 4: Syntax check**

Run: `python -m py_compile "pages/4_⚙️_Settings.py"`
Expected: No errors

**Step 5: Run full test suite**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: All tests OK

**Step 6: Commit**

```bash
git add "pages/4_⚙️_Settings.py"
git commit -m "feat: add Display tab to Settings with relocated controls

Phase 4d: Data source, sync status, layout toggles, and
appearance settings now live in Settings > Display tab."
```

---

### Task 4: Update CLAUDE.md and Final Verification

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update CLAUDE.md**

Update the "Streamlit Pages" section to reflect changes:
- Settings now has 5 tabs: Data, Maintenance, Tags, Automation, Display
- Sidebar is navigation-only across all pages
- Add `utils/bag_config.py` functions to shared utilities section

Add to Key Conventions:
```markdown
- Per-club smash factor targets are defined in `my_bag.json` under `smash_targets` key
  and accessed via `utils/bag_config.py:get_smash_target()` / `get_all_smash_targets()`
```

**Step 2: Run full test suite and CI lint**

Run: `python -m unittest discover -s tests 2>&1 | tail -3`
Expected: All tests OK

Run: `python -m py_compile app.py && python -m py_compile components/shared_sidebar.py && python -m py_compile utils/bag_config.py && for f in pages/*.py; do python -m py_compile "$f"; done`
Expected: No errors

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for Phase 4 changes (sidebar, smash targets, Display tab)"
```

---

## Verification Checklist

After all tasks are complete:

- [ ] `my_bag.json` has `smash_targets` dict with all 11 clubs
- [ ] `get_smash_target("Driver")` returns ~1.49
- [ ] `get_all_smash_targets()` returns dict with 11 entries
- [ ] Sidebar shows only navigation on all pages (no data source, sync status, toggles)
- [ ] Settings page has 5 tabs: Data, Maintenance, Tags, Automation, Display
- [ ] Display tab shows data source, sync status, layout, appearance controls
- [ ] All existing tests pass
- [ ] CI lint passes (`py_compile` on all Python files)
