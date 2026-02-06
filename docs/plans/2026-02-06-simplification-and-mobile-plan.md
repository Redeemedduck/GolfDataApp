# UI Simplification & Mobile Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce Dashboard from 5 tabs to 3, tighten journal cards, add mobile layout toggle, DRY up duplicated code, delete dead components.

**Architecture:** Extract shared utilities (date parsing, Big 3 thresholds), add compact layout toggle to responsive.py, simplify Dashboard/Settings tab structure, move Compare to Club Profiles, move Export to sidebar.

**Tech Stack:** Streamlit, Plotly, Python 3.10+, unittest

---

### Task 1: Extract shared date parsing utility

**Files:**
- Create: `utils/date_helpers.py`
- Modify: `components/journal_card.py`
- Modify: `components/journal_view.py`
- Modify: `components/calendar_strip.py`
- Test: `tests/unit/test_date_parsing.py` (already exists, verify still passes)

**Step 1: Create `utils/date_helpers.py`**

```python
"""Shared date parsing utilities."""
from datetime import date, datetime
from typing import Optional


def parse_session_date(value) -> Optional[date]:
    """Parse a session date from ISO datetime/date strings with fallbacks."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return datetime.fromisoformat(raw.split("T", 1)[0]).date()
            except (ValueError, TypeError):
                return None


def format_session_date(value, fmt: str = "short") -> str:
    """Format a session date for display.

    Args:
        value: Date value to format.
        fmt: "short" for "Jan 28", "long" for "Jan 28, 2026".
    """
    parsed = parse_session_date(value)
    if parsed is None:
        return "No date"
    if fmt == "long":
        return f"{parsed.strftime('%b')} {parsed.day}, {parsed.year}"
    return f"{parsed.strftime('%b')} {parsed.day}"
```

**Step 2: Update journal_card.py — replace local `_parse_session_date` and `_format_session_date` with imports**

Remove `_parse_session_date()` (lines 56-80) and `_format_session_date()` (lines 83-88).
Add import: `from utils.date_helpers import parse_session_date, format_session_date`
Update usage on line 105: `date = format_session_date(stats.get('session_date'))`

**Step 3: Update journal_view.py — replace local `_parse_session_date` with import**

Remove `_parse_session_date()` (lines 14-38).
Add import: `from utils.date_helpers import parse_session_date`
Update usage on line 55: `session_date = parse_session_date(session.get('session_date'))`

**Step 4: Update calendar_strip.py — replace local `_parse_practice_date` and `_normalize_practice_dates` with import**

Remove `_parse_practice_date()` (lines 11-35) and `_normalize_practice_dates()` (lines 38-45).
Add import: `from utils.date_helpers import parse_session_date`
Replace normalize logic inline:
```python
def _normalize_practice_dates(practice_dates):
    normalized = set()
    for value in practice_dates or set():
        parsed = parse_session_date(value)
        if parsed is not None:
            normalized.add(parsed.isoformat())
    return normalized
```

**Step 5: Run tests**

Run: `python -m unittest tests.unit.test_date_parsing -v`
Expected: All 15 tests PASS

**Step 6: Syntax check**

Run: `python -m py_compile utils/date_helpers.py && python -m py_compile components/journal_card.py && python -m py_compile components/journal_view.py && python -m py_compile components/calendar_strip.py`
Expected: No errors

**Step 7: Commit**

```bash
git add utils/date_helpers.py components/journal_card.py components/journal_view.py components/calendar_strip.py
git commit -m "refactor: extract shared date parsing to utils/date_helpers.py"
```

---

### Task 2: Extract shared Big 3 thresholds

**Files:**
- Create: `utils/big3_constants.py`
- Modify: `components/journal_card.py`
- Modify: `components/big3_summary.py`

**Step 1: Create `utils/big3_constants.py`**

```python
"""Shared Big 3 Impact Laws thresholds and label functions.

Thresholds based on Adam Young's teaching:
- Face Angle std: <1.5 consistent, <3.0 moderate, >3.0 scattered
- Club Path std: <2.0 consistent, <4.0 moderate, >4.0 scattered
- Strike Distance: <0.25 center, <0.5 decent, >0.5 scattered
"""

# Colors
GREEN = "#2ca02c"
YELLOW = "#ff7f0e"
RED = "#d62728"
GRAY = "gray"


def face_label(std):
    """Classify face angle consistency."""
    if std is None:
        return "—", GRAY
    if std < 1.5:
        return "Consistent", GREEN
    if std < 3.0:
        return "Moderate", YELLOW
    return "Scattered", RED


def path_label(std):
    """Classify club path consistency."""
    if std is None:
        return "—", GRAY
    if std < 2.0:
        return "Consistent", GREEN
    if std < 4.0:
        return "Moderate", YELLOW
    return "Scattered", RED


def strike_label(avg_dist):
    """Classify strike location quality."""
    if avg_dist is None:
        return "—", GRAY
    if avg_dist < 0.25:
        return "Center", GREEN
    if avg_dist < 0.5:
        return "Decent", YELLOW
    return "Scattered", RED
```

**Step 2: Update journal_card.py**

Remove `_face_label()`, `_path_label()`, `_strike_label()` (lines 23-53).
Add import: `from utils.big3_constants import face_label, path_label, strike_label`
Update usages on lines 152-154:
```python
face_lbl, face_clr = face_label(stats.get('std_face_angle'))
path_lbl, path_clr = path_label(stats.get('std_club_path'))
strike_lbl, strike_clr = strike_label(stats.get('avg_strike_distance'))
```

**Step 3: Update big3_summary.py — use shared labels if it has its own threshold logic**

Read big3_summary.py and replace any duplicated threshold logic with imports from `utils/big3_constants.py`.

**Step 4: Run all tests**

Run: `python -m unittest discover -s tests -v 2>&1 | tail -5`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add utils/big3_constants.py components/journal_card.py components/big3_summary.py
git commit -m "refactor: extract Big 3 thresholds to utils/big3_constants.py"
```

---

### Task 3: Delete dead components

**Files:**
- Delete: `components/session_list.py`
- Delete: `components/simple_view.py`
- Delete: `components/coach_export.py`
- Delete: `components/session_header.py`
- Modify: `components/__init__.py` (remove exports)

**Step 1: Verify no imports exist**

Run: `grep -r "session_list\|simple_view\|coach_export\|session_header" --include="*.py" pages/ app.py`
Expected: No results (these components are unused)

**Step 2: Delete the files**

```bash
git rm components/session_list.py components/simple_view.py components/coach_export.py components/session_header.py
```

**Step 3: Remove from `components/__init__.py`**

Remove any imports or `__all__` entries for the deleted components.

**Step 4: Run tests**

Run: `python -m unittest discover -s tests -v 2>&1 | tail -5`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add components/__init__.py
git commit -m "chore: remove 4 unused components (session_list, simple_view, coach_export, session_header)"
```

---

### Task 4: Add compact layout toggle

**Files:**
- Modify: `utils/responsive.py`
- Modify: `components/shared_sidebar.py`

**Step 1: Add compact layout functions to `utils/responsive.py`**

```python
def is_compact_layout() -> bool:
    """Check if compact (mobile) layout is enabled."""
    return st.session_state.get('compact_layout', False)


def render_compact_toggle():
    """Render compact layout toggle in sidebar."""
    st.session_state.compact_layout = st.toggle(
        "Compact Layout",
        value=st.session_state.get('compact_layout', False),
        help="Optimized for small screens",
    )
```

**Step 2: Add toggle to shared_sidebar.py**

Import and call `render_compact_toggle()` in the sidebar render function, below the data source section.

**Step 3: Syntax check**

Run: `python -m py_compile utils/responsive.py && python -m py_compile components/shared_sidebar.py`

**Step 4: Commit**

```bash
git add utils/responsive.py components/shared_sidebar.py
git commit -m "feat: add compact layout toggle for mobile optimization"
```

---

### Task 5: Simplify Dashboard — remove Compare and Export tabs

**Files:**
- Modify: `pages/1_📊_Dashboard.py`

**Step 1: Remove Compare tab**

Delete the Compare tab block and its `render_session_comparison()` import. Remove the tab from the `st.tabs()` call.

**Step 2: Remove Export tab**

Delete the Export tab block. Add a simple download button to the sidebar or bottom of Overview instead:
```python
# At bottom of Overview tab
if not df.empty:
    csv = df.to_csv(index=False)
    st.download_button("Export Session CSV", csv, f"session_{session_id}.csv", "text/csv")
```

**Step 3: Remove Big 3 summary from Overview tab**

Delete the `render_big3_summary()` call in the Overview tab (it's redundant with the Big 3 tab).

**Step 4: Trim Overview metrics from 5 to 3**

Keep: Total Shots, Avg Carry, Avg Smash. Remove: Avg Total, Ball Speed.

**Step 5: Remove carry box plot from Overview**

Delete the box plot chart — dispersion plot already shows carry distribution.

**Step 6: Verify tab structure is now `["Overview", "Big 3 Deep Dive", "Shots"]`**

**Step 7: Syntax check and run tests**

Run: `python -m py_compile pages/1_📊_Dashboard.py && python -m unittest discover -s tests -v 2>&1 | tail -5`

**Step 8: Commit**

```bash
git add pages/1_📊_Dashboard.py
git commit -m "feat: simplify Dashboard from 5 tabs to 3 (remove Compare, Export)"
```

---

### Task 6: Tighten journal cards for mobile

**Files:**
- Modify: `components/journal_card.py`

**Step 1: Remove Best Carry metric**

In `render_journal_card()`, change from 3-column metrics to 2-column:
```python
col1, col2 = st.columns(2)
```
Remove the `col3` block with Best Carry.

**Step 2: Replace Big 3 HTML blocks with inline summary**

Replace the 3-column Big 3 HTML section with a single-line:
```python
face_lbl, face_clr = face_label(stats.get('std_face_angle'))
path_lbl, path_clr = path_label(stats.get('std_club_path'))
strike_lbl, strike_clr = strike_label(stats.get('avg_strike_distance'))

st.markdown(
    f"**Big 3:** "
    f"<span style='color:{face_clr}'>Face: {face_lbl}</span> | "
    f"<span style='color:{path_clr}'>Path: {path_lbl}</span> | "
    f"<span style='color:{strike_clr}'>Strike: {strike_lbl}</span>",
    unsafe_allow_html=True,
)
```

**Step 3: Syntax check**

Run: `python -m py_compile components/journal_card.py`

**Step 4: Commit**

```bash
git add components/journal_card.py
git commit -m "feat: tighten journal cards — 2 metrics, inline Big 3 summary"
```

---

### Task 7: Fix home page hero layout

**Files:**
- Modify: `app.py`

**Step 1: Change hero stats from 4 columns to 2x2 grid**

```python
from utils.responsive import is_compact_layout

# Hero stats — 2x2 grid (works on both desktop and mobile)
r1c1, r1c2 = st.columns(2)
r2c1, r2c2 = st.columns(2)
with r1c1:
    st.metric("Sessions", session_count)
with r1c2:
    st.metric("Total Shots", total_shots)
with r2c1:
    st.metric("Last Practice", last_practice_label)
with r2c2:
    st.metric("Streak", streak_label)
```

**Step 2: Syntax check**

Run: `python -m py_compile app.py`

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: 2x2 hero grid for better mobile layout"
```

---

### Task 8: Fix calendar strip for mobile

**Files:**
- Modify: `components/calendar_strip.py`

**Step 1: Make cell width dynamic**

Replace hardcoded `width:18px` with percentage-based or `calc()` sizing:
```python
cell_size = "min(18px, calc((100vw - 60px) / {total_days}))"
```

Or simpler — use flexbox with wrap:
```python
cells_html = f"""
<div style="display:flex;flex-wrap:wrap;gap:1px;max-width:100%">
    {''.join(cells)}
</div>
"""
```
And change each cell from `display:inline-block` to flex item with `flex:0 0 auto; width:min(18px, 3%)`.

**Step 2: Syntax check**

Run: `python -m py_compile components/calendar_strip.py`

**Step 3: Commit**

```bash
git add components/calendar_strip.py
git commit -m "fix: calendar strip responsive width for mobile"
```

---

### Task 9: Simplify Settings from 5 tabs to 3

**Files:**
- Modify: `pages/4_⚙️_Settings.py`

**Step 1: Merge Import + Sessions into "Data" tab**

Combine the content of both tabs under one tab. Use `st.subheader()` to separate sections.

**Step 2: Merge Data Quality + Sync into "Maintenance" tab**

Combine both tabs. Use `st.subheader()` for sections.

**Step 3: Keep Tags tab as-is**

**Step 4: Update tab creation**

```python
tab_data, tab_maintenance, tab_tags = st.tabs(["Data", "Maintenance", "Tags"])
```

**Step 5: Syntax check and test**

Run: `python -m py_compile pages/4_⚙️_Settings.py && python -m unittest discover -s tests -v 2>&1 | tail -5`

**Step 6: Commit**

```bash
git add pages/4_⚙️_Settings.py
git commit -m "feat: simplify Settings from 5 tabs to 3 (Data, Maintenance, Tags)"
```

---

### Task 10: Move Compare to Club Profiles

**Files:**
- Modify: `pages/2_🏌️_Club_Profiles.py`

**Step 1: Add session comparison section for selected club**

After the existing Big 3 section, add a "Compare Sessions" expander:
```python
with st.expander("Compare Sessions for This Club"):
    # Get sessions that used this club
    # Let user pick 2 sessions
    # Show side-by-side metrics (carry, smash, Big 3)
```

**Step 2: Move club selector from sidebar to main area**

Replace `st.sidebar.selectbox("Club", ...)` with `st.selectbox("Club", ...)` in the main content area.

**Step 3: Limit radar chart to 3 clubs**

Change the multiselect max: `st.multiselect("Compare Clubs", clubs, max_selections=3)`

**Step 4: Syntax check**

Run: `python -m py_compile pages/2_🏌️_Club_Profiles.py`

**Step 5: Commit**

```bash
git add pages/2_🏌️_Club_Profiles.py
git commit -m "feat: add session comparison to Club Profiles, move club selector to main area"
```

---

### Task 11: Final verification

**Step 1: Run all tests**

Run: `python -m unittest discover -s tests -v`
Expected: All 202+ tests PASS

**Step 2: Syntax check all modified files**

Run: `python -m py_compile app.py && python -m py_compile components/*.py && for f in pages/*.py; do python -m py_compile "$f"; done && python -m py_compile utils/*.py`

**Step 3: Visual check**

Run: `streamlit run app.py`
Verify:
- Home page: 2x2 hero, compact journal cards, responsive calendar
- Dashboard: 3 tabs only (Overview, Big 3, Shots)
- Club Profiles: Club selector in main area, compare section, radar max 3
- Settings: 3 tabs (Data, Maintenance, Tags)
- Toggle Compact Layout in sidebar — verify layout changes

**Step 4: Commit any final fixes**

```bash
git add -A
git commit -m "fix: final polish for simplification and mobile optimization"
```
