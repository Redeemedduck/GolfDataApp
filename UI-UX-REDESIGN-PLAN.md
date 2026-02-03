# UI/UX Redesign Plan

**Project:** GolfDataApp
**Version:** 2.0 "Analytics Edition"
**Created:** 2026-02-03

---

## Executive Summary

Transform GolfDataApp from a functional data viewer into the **analytics platform Uneekor users deserve**. Based on research of leading golf apps (Arccos, Trackman, Shot Scope) and golfer needs analysis.

### Key Changes
1. **Progressive disclosure** - Simplify defaults, power when needed
2. **Visual-first** - Charts over tables everywhere
3. **Session-centric** - Better organization and comparison
4. **Actionable insights** - AI Coach integration throughout
5. **Mobile-aware** - Responsive without compromise

---

## Phase 1: Foundation (5 tasks)

### Task 1.1: Extract Shared Sidebar Component
**Effort:** Small | **Priority:** P1

**Current State:**
- Data source selector repeated in all 4 pages
- Inconsistent navigation links
- No shared state management

**Target State:**
- Single `components/shared_sidebar.py` with `render_shared_sidebar()`
- Consistent nav across all pages
- Data source, stats, and health in one place

**Files:**
- Create: `components/shared_sidebar.py`
- Edit: `app.py`, `pages/1_*.py`, `pages/2_*.py`, `pages/3_*.py`, `pages/4_*.py`

---

### Task 1.2: Create Custom Theme
**Effort:** Small | **Priority:** P1

**Current State:**
- Streamlit default blue
- No brand identity
- Inconsistent spacing

**Target State:**
- Golf-themed green/blue palette
- Consistent typography
- Dark mode support

**Files:**
- Create/Edit: `.streamlit/config.toml`
- Create: `assets/style.css` (optional custom CSS)

**Theme Values:**
```toml
[theme]
primaryColor = "#1B5E20"
backgroundColor = "#FAFAFA"
secondaryBackgroundColor = "#E8F5E9"
textColor = "#212121"
font = "sans serif"
```

---

### Task 1.3: Add Loading States
**Effort:** Small | **Priority:** P2

**Current State:**
- Charts render without feedback
- User thinks app is frozen

**Target State:**
- Spinners during data fetch
- Skeleton loaders for charts
- Progress indicators

**Files:**
- Edit: `pages/2_📊_Dashboard.py`
- Edit: `pages/4_🤖_AI_Coach.py`

---

### Task 1.4: Create Empty State Components
**Effort:** Medium | **Priority:** P1

**Current State:**
- "No data" text messages
- No guidance for new users

**Target State:**
- Friendly empty states with illustrations
- Clear call-to-action buttons
- First-time user onboarding

**Files:**
- Create: `components/empty_states.py`
- Edit: All pages

---

### Task 1.5: Fix Deprecated Content
**Effort:** Small | **Priority:** P3

**Current State:**
- About section mentions BigQuery, Cloud Run
- Documentation links broken

**Target State:**
- Accurate architecture description
- Valid documentation links

**Files:**
- Edit: `app.py` (About expander)

---

## Phase 2: Dashboard Redesign (6 tasks)

### Task 2.1: New KPI Cards Component
**Effort:** Medium | **Priority:** P1

**Current State:**
- Basic `st.metric()` calls
- No styling, no trends

**Target State:**
- Custom KPI cards with icons
- Trend indicators (↑↓)
- Benchmark comparisons
- Color-coded status

**Files:**
- Rewrite: `components/metrics_card.py`
- Edit: `pages/2_📊_Dashboard.py`

**Design:**
```python
def render_kpi_card(label, value, unit, trend=None, benchmark=None):
    """
    Renders a styled KPI card with optional trend and benchmark.
    """
```

---

### Task 2.2: Improved Dispersion Plot
**Effort:** Medium | **Priority:** P1

**Current State:**
- Basic Plotly scatter
- Fixed axis ranges
- Minimal styling

**Target State:**
- "Driving range" aesthetic
- Dynamic axis based on data
- Club color legend
- Dispersion ellipse overlay
- Click to see shot details

**Files:**
- Edit: `pages/2_📊_Dashboard.py` (tab1)

---

### Task 2.3: Session Summary Header
**Effort:** Small | **Priority:** P2

**Current State:**
- Plain text "Session: 43285"
- No context

**Target State:**
- Session card header with:
  - Date, shot count, duration
  - Session type badge
  - Tags shown
  - Quick actions (export, compare)

**Files:**
- Create: `components/session_header.py`
- Edit: `pages/2_📊_Dashboard.py`

---

### Task 2.4: Trend Chart Improvements
**Effort:** Medium | **Priority:** P2

**Current State:**
- Basic line chart
- No context or benchmarks

**Target State:**
- Area fill under line
- Rolling average option
- Benchmark line overlay
- Annotation for best/worst sessions
- Click to navigate to session

**Files:**
- Edit: `components/trend_chart.py`

---

### Task 2.5: Impact Heatmap Upgrade
**Effort:** Medium | **Priority:** P2

**Current State:**
- Functional heatmap
- Basic styling

**Target State:**
- Club face outline
- Sweet spot highlight
- Per-club comparison
- Trend over sessions

**Files:**
- Edit: `components/heatmap_chart.py`

---

### Task 2.6: Consolidate Dashboard Tabs
**Effort:** Small | **Priority:** P3

**Current State:**
- 5 tabs with some overlap

**Target State:**
- 4 tabs: Overview, Analysis, Shots, Export
- Merge Impact into Analysis
- Cleaner organization

**Files:**
- Edit: `pages/2_📊_Dashboard.py`

---

## Phase 3: Database Manager Simplification (4 tasks)

### Task 3.1: Reduce Tabs from 7 to 5
**Effort:** Medium | **Priority:** P1

**Current State:**
- 7 tabs: Edit, Delete, Session, Bulk, Quality, Audit, Tags
- Overwhelming for users

**Target State:**
- 5 tabs: Edit, Sessions, Quality, Tags, History
- Merge Delete into Edit (with confirmation)
- Merge Audit into History
- Session ops more prominent

**Files:**
- Edit: `pages/3_🗄️_Database_Manager.py`

---

### Task 3.2: Extract Tag Wizard Component
**Effort:** Medium | **Priority:** P2

**Current State:**
- 300+ lines in Tab 7
- Complex nested UI

**Target State:**
- `components/tag_wizard.py`
- Cleaner interface
- Step-by-step flow

**Files:**
- Create: `components/tag_wizard.py`
- Edit: `pages/3_🗄️_Database_Manager.py`

---

### Task 3.3: Session List View
**Effort:** Medium | **Priority:** P2

**Current State:**
- Dropdown selector only
- No visual session browser

**Target State:**
- Card-based session list
- Filter by type/tag/date
- Sort options
- Quick actions per session

**Files:**
- Create: `components/session_list.py`
- Edit: `pages/3_🗄️_Database_Manager.py`

---

### Task 3.4: Simplified Delete Confirmations
**Effort:** Small | **Priority:** P3

**Current State:**
- Multiple checkboxes
- Scary warnings

**Target State:**
- Single modal confirmation
- Clear undo option
- Less anxiety-inducing

**Files:**
- Edit: `pages/3_🗄️_Database_Manager.py`

---

## Phase 4: AI Coach Enhancement (4 tasks)

### Task 4.1: Collapsible Settings Panel
**Effort:** Small | **Priority:** P1

**Current State:**
- Settings take up sidebar
- Chat area feels cramped

**Target State:**
- Settings in collapsible expander
- Chat is primary focus
- Quick settings toggle

**Files:**
- Edit: `pages/4_🤖_AI_Coach.py`

---

### Task 4.2: Auto-Generated Insights
**Effort:** Large | **Priority:** P1

**Current State:**
- User must ask questions
- No proactive insights

**Target State:**
- "Today's insights" section
- Auto-analysis on session load
- Trend alerts
- Suggested focus areas

**Files:**
- Create: `components/ai_insights.py`
- Edit: `pages/4_🤖_AI_Coach.py`
- Edit: `local_coach.py`

---

### Task 4.3: Improved Chat UI
**Effort:** Medium | **Priority:** P2

**Current State:**
- Basic Streamlit chat
- Function calls in expander

**Target State:**
- Cleaner message bubbles
- Inline data visualizations
- Quick reply suggestions
- Better mobile layout

**Files:**
- Edit: `pages/4_🤖_AI_Coach.py`

---

### Task 4.4: Goal Tracking (Future)
**Effort:** Large | **Priority:** P3

**Current State:**
- No goal system

**Target State:**
- Set goals (e.g., "Driver carry >250")
- Track progress toward goals
- Celebrate achievements
- AI suggests goals

**Files:**
- Create: `components/goals.py`
- Edit: `golf_db.py` (new table)
- Edit: `pages/4_🤖_AI_Coach.py`

---

## Phase 5: Landing Page & Onboarding (3 tasks)

### Task 5.1: Session Summary Cards
**Effort:** Medium | **Priority:** P1

**Current State:**
- Text-based recent activity
- Expandable sections

**Target State:**
- Visual session cards
- Mini-stats visible
- Session type badges
- One-click navigation

**Files:**
- Create: `components/session_card.py`
- Edit: `app.py`

---

### Task 5.2: First-Time User Onboarding
**Effort:** Medium | **Priority:** P2

**Current State:**
- "No sessions yet" message
- Link to import

**Target State:**
- Welcome wizard
- Feature tour
- Sample data option
- Progress milestones

**Files:**
- Create: `components/onboarding.py`
- Edit: `app.py`

---

### Task 5.3: Quick Stats Hero Section
**Effort:** Small | **Priority:** P2

**Current State:**
- 3 basic metrics
- No visual appeal

**Target State:**
- Stylized KPI row
- Trend sparklines
- "Your golf at a glance"

**Files:**
- Edit: `app.py`

---

## Phase 6: Responsive & Polish (3 tasks)

### Task 6.1: Mobile Responsive Layouts
**Effort:** Large | **Priority:** P2

**Current State:**
- Wide layout required
- No mobile consideration

**Target State:**
- Conditional layouts by viewport
- Stacked cards on mobile
- Simplified charts
- Touch-friendly controls

**Files:**
- Edit: All pages and components

---

### Task 6.2: Dark Mode Support
**Effort:** Medium | **Priority:** P3

**Current State:**
- Light mode only

**Target State:**
- Dark theme option
- Persisted preference
- Chart colors adapt

**Files:**
- Edit: `.streamlit/config.toml`
- Edit: Components with hardcoded colors

---

### Task 6.3: Data Source Badge
**Effort:** Small | **Priority:** P3

**Current State:**
- Data source buried in sidebar

**Target State:**
- Visible badge in header
- "SQLite" or "Supabase" indicator
- Sync status icon

**Files:**
- Edit: All pages

---

## Implementation Schedule

### Wave 1: Foundation (Tasks 1.1-1.5)
**Effort:** ~8-10 Codex tasks
**Dependencies:** None
**Deliverable:** Clean codebase ready for features

### Wave 2: Dashboard Core (Tasks 2.1-2.3)
**Effort:** ~6-8 Codex tasks
**Dependencies:** Wave 1
**Deliverable:** Professional dashboard appearance

### Wave 3: Manager + Coach (Tasks 3.1-3.2, 4.1-4.2)
**Effort:** ~6-8 Codex tasks
**Dependencies:** Wave 1
**Deliverable:** Simplified management, smarter coach

### Wave 4: Polish (Remaining tasks)
**Effort:** ~8-10 Codex tasks
**Dependencies:** Waves 2-3
**Deliverable:** Production-ready app

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Page load time | ~3s | <2s |
| Lines of code (DB Manager) | 941 | <600 |
| Tabs (DB Manager) | 7 | 5 |
| Empty state coverage | 0% | 100% |
| Mobile usability | Poor | Good |
| User onboarding | None | Complete |

---

## Research Documents

For detailed research that informed this plan:
- `RESEARCH-GOLF-APPS.md` - UI/UX patterns from leading apps
- `RESEARCH-GOLFER-DATA.md` - What metrics matter to golfers
- `RESEARCH-UNEEKOR-ECOSYSTEM.md` - Competitive landscape
- `DESIGN-PRINCIPLES.md` - Design system and guidelines
- `FRONTEND-ANALYSIS.md` - Current state audit
