# Frontend Analysis Report

**Generated:** 2026-02-03
**Analyzed by:** Claude (Codex Orchestrator session)

---

## 1. Current UI Architecture Overview

### Stack
- **Framework:** Streamlit (multi-page app)
- **Charts:** Plotly Express + Plotly Graph Objects
- **Layout:** Wide mode, sidebar navigation

### Page Structure
```
app.py                    → Landing page (metrics overview, quick start cards)
pages/
├── 1_📥_Data_Import.py   → Single URL import, import history
├── 2_📊_Dashboard.py     → 5-tab analytics (Overview, Impact, Trends, Shots, Export)
├── 3_🗄️_Database_Manager.py → 7-tab CRUD (Edit, Delete, Session, Bulk, Quality, Audit, Tags)
└── 4_🤖_AI_Coach.py      → Chat interface with provider selection
```

### Component Library (`components/`)
| Component | Purpose |
|-----------|---------|
| `session_selector.py` | Session + club multiselect sidebar widget |
| `metrics_card.py` | KPI row with carry, ball speed, smash |
| `heatmap_chart.py` | Impact location heatmap (Optix data) |
| `trend_chart.py` | Session-over-session line chart |
| `radar_chart.py` | Multi-metric radar comparison |
| `shot_table.py` | Interactive shot data table |
| `export_tools.py` | CSV/PDF export helpers |

---

## 2. Component Inventory with Descriptions

### Landing Page (`app.py`)
- **Metrics row:** 3 columns showing Total Sessions, Total Shots, Unique Clubs
- **Quick Start cards:** 4 navigation cards (Import, Dashboard, Manager, AI Coach)
- **Recent Activity:** Expandable session summaries with mini-stats
- **Sidebar:** Data source selector, system status, health metrics

### Data Import Page
- **URL input:** Single text field for Uneekor report URL
- **Progress feedback:** Progress bar + status text
- **Import history:** Recent sessions list + observability logs

### Dashboard Page (5 tabs)
1. **Performance Overview:** KPI metrics, carry box plot, dispersion scatter, radar chart
2. **Impact Analysis:** Optix heatmap, impact consistency by club
3. **Trends Over Time:** Session-over-session metric trends, club-specific trends
4. **Shot Viewer:** Interactive table with shot detail panel + images
5. **Export Data:** CSV downloads (coach review, equipment fitting, all data)

### Database Manager (7 tabs)
1. **Edit Data:** Rename club, rename session, set session type
2. **Delete Operations:** Delete session, club shots, individual shots
3. **Session Operations:** Merge sessions, split session
4. **Bulk Operations:** Global rename, club normalization presets, recalculate metrics
5. **Data Quality:** Outlier detection, validation, club naming anomalies, deduplication
6. **Audit Trail:** Change log viewer, restore deleted shots
7. **Tags & Split:** Tag catalog, tag+split wizard, quick tagging

### AI Coach Page
- **Provider selection:** Dropdown with model + thinking level controls
- **Focus filters:** Session, club, tag, session type
- **Chat interface:** Message history with function call transparency
- **Suggested questions:** 10 pre-built prompts

---

## 3. UX Issues and Pain Points

### High Priority

| Issue | Location | Impact |
|-------|----------|--------|
| **Sidebar duplication** | All pages | Data source selector + read mode logic repeated 4x |
| **No global navigation** | All pages | Each page manages its own nav links inconsistently |
| **Tab overload** | Database Manager | 7 tabs is overwhelming; some have 3+ sub-sections |
| **Long scrolling** | Database Manager | Tab 7 (Tags) is 300+ lines with nested wizards |
| **No loading states** | Dashboard | Charts render without skeleton/spinner on slow data |
| **Mobile unfriendly** | All pages | Wide layout required; no responsive breakpoints |

### Medium Priority

| Issue | Location | Impact |
|-------|----------|--------|
| **Inconsistent styling** | Landing page vs Dashboard | Cards use different spacing/borders |
| **No dark mode** | Global | All pages use Streamlit default light theme |
| **Emoji overuse** | Page titles, headers | Mixed professionalism (⛳🤖📊🗄️) |
| **Placeholder text** | Data Import | Generic "https://myuneekor.com..." example |
| **No onboarding** | New users | Landing page assumes data exists |
| **Session selector buried** | Sidebar | User must scroll to find filters |

### Low Priority

| Issue | Location | Impact |
|-------|----------|--------|
| **Deprecated references** | About section | Mentions BigQuery/Cloud Run (removed) |
| **Redundant help expanders** | AI Coach | Large help section duplicates suggested questions |
| **No keyboard shortcuts** | Shot viewer | Click-only selection |

---

## 4. Visual Design Assessment

### Current Design Language
- **Colors:** Streamlit default blue accent, white background
- **Typography:** System fonts (no custom typography)
- **Spacing:** Inconsistent (some sections use `st.divider()`, others don't)
- **Icons:** Emoji-based (no icon library like Lucide or Font Awesome)
- **Charts:** Plotly defaults with minimal customization

### Design Strengths
- Clean Plotly visualizations (dispersion plot, box plots)
- Good use of columns for side-by-side layouts
- Metrics cards are readable and well-organized
- Tab organization keeps related features grouped

### Design Weaknesses
- No cohesive color palette beyond Streamlit defaults
- Missing visual hierarchy (headers all same weight)
- No branding elements (logo, custom colors)
- Expanders used inconsistently for progressive disclosure
- Dense UI in Database Manager (too many controls visible at once)

---

## 5. Prioritized Improvement Recommendations

### P1: High Impact, Small Effort

| # | Recommendation | Effort | Files |
|---|----------------|--------|-------|
| 1 | **Extract sidebar to shared component** | Small | Create `components/sidebar.py`, update all pages |
| 2 | **Add global CSS theme** | Small | Create `.streamlit/theme.toml` or custom CSS |
| 3 | **Add loading spinners to charts** | Small | Wrap chart renders in `st.spinner()` |
| 4 | **Fix deprecated references** | Small | Update About section in `app.py` |
| 5 | **Simplify Database Manager tabs** | Small | Combine Edit+Bulk, combine Audit+Tags |

### P2: High Impact, Medium Effort

| # | Recommendation | Effort | Files |
|---|----------------|--------|-------|
| 6 | **Create design system** | Medium | Define color palette, typography, spacing vars |
| 7 | **Add empty state flows** | Medium | Show guided onboarding when no data |
| 8 | **Refactor Tags tab** | Medium | Extract wizard to separate component |
| 9 | **Add session summary cards** | Medium | Replace text-heavy recent activity |
| 10 | **Improve AI Coach layout** | Medium | Move settings to collapsible panel |

### P3: Medium Impact, Large Effort

| # | Recommendation | Effort | Files |
|---|----------------|--------|-------|
| 11 | **Mobile-responsive layouts** | Large | Conditional layouts based on viewport |
| 12 | **Dark mode support** | Large | Dual theme with toggle |
| 13 | **Replace emojis with icon library** | Large | Integrate streamlit-lucide or similar |
| 14 | **Add keyboard navigation** | Large | Custom components with event handlers |
| 15 | **Create unified navigation component** | Large | Replace per-page sidebar links |

### P4: Nice to Have

| # | Recommendation | Effort | Files |
|---|----------------|--------|-------|
| 16 | **Add data source indicator badge** | Small | Show SQLite/Supabase in header |
| 17 | **Session date picker** | Medium | Replace dropdown with calendar |
| 18 | **Animated transitions** | Medium | Chart animation on data change |
| 19 | **Custom Plotly theme** | Medium | Golf-themed color scales |
| 20 | **Export to PDF report** | Large | Generate formatted PDF summary |

---

## 6. Suggested Task Breakdown for Codex Orchestrator

### Wave 1: Foundation (4 tasks, ~2 hours)
1. Extract sidebar component and update all 4 pages
2. Create `.streamlit/config.toml` with custom theme
3. Add loading spinners to Dashboard charts
4. Fix deprecated text in `app.py` About section

### Wave 2: Structure (3 tasks, ~1.5 hours)
5. Consolidate Database Manager from 7 tabs to 5
6. Extract Tags wizard to `components/tag_wizard.py`
7. Add empty state components for new users

### Wave 3: Polish (3 tasks, ~1.5 hours)
8. Create session summary cards for landing page
9. Improve AI Coach settings layout
10. Add data source badge to all page headers

---

## Appendix: File Line Counts

| File | Lines | Complexity |
|------|-------|------------|
| `app.py` | 265 | Low |
| `pages/1_📥_Data_Import.py` | 210 | Low |
| `pages/2_📊_Dashboard.py` | 525 | Medium |
| `pages/3_🗄️_Database_Manager.py` | 941 | High |
| `pages/4_🤖_AI_Coach.py` | 450 | Medium |
| `components/*.py` (total) | ~800 | Low-Medium |

**Total frontend code:** ~3,200 lines
