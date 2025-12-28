# CLAUDE.md - Branch: claude/database-ui-ai-coaching-DE7uU

This file provides guidance to Claude Code when working with code in this branch.

**Branch Focus**: Database Management UI + AI Coaching Integration (Phases 1-3 Complete)

---

## 🎯 Branch Status

**Completed Phases**:
- ✅ **Phase 1**: Multi-page architecture transformation
- ✅ **Phase 2**: Enhanced database management with audit trail
- ✅ **Phase 3**: Advanced visualizations and export tools

**Upcoming Phases**:
- 🔜 **Phase 4**: ML Foundation (distance prediction, shot classification)
- 🔜 **Phase 5**: AI Coach GUI (conversational interface, predictions)
- 🔜 **Phase 6**: Continuous Learning (auto-retrain, performance monitoring)

**Progress**: 3 of 6 phases complete (50%)
**Total Code Added**: ~2,912 lines across all phases

---

## 📁 Project Structure (Updated)

```
GolfDataApp/
├── app.py                              # Landing page (Phase 1 refactor)
├── golf_db.py                          # Database layer (866 lines, Phase 2 enhanced)
├── golf_scraper.py                     # Uneekor API client
│
├── pages/                              # Multi-page app (Phase 1)
│   ├── 1_📥_Data_Import.py             # Uneekor data import interface
│   ├── 2_📊_Dashboard.py               # Analytics & visualizations (Phase 3 enhanced)
│   └── 3_🗄️_Database_Manager.py       # CRUD operations (Phase 2 enhanced)
│
├── components/                          # Reusable UI components (Phase 1 & 3)
│   ├── __init__.py
│   ├── session_selector.py             # Session/club filter widget
│   ├── metrics_card.py                 # KPI metrics display
│   ├── shot_table.py                   # Interactive shot table
│   ├── heatmap_chart.py                # Impact location heatmap (Phase 3)
│   ├── trend_chart.py                  # Performance trends (Phase 3)
│   ├── radar_chart.py                  # Multi-metric comparison (Phase 3)
│   └── export_tools.py                 # CSV/Excel/text export (Phase 3)
│
├── scripts/                            # Cloud pipeline & automation
│   ├── supabase_to_bigquery.py
│   ├── gemini_analysis.py
│   ├── vertex_ai_analysis.py
│   ├── auto_sync.py
│   └── post_session.py
│
├── docs/                               # Phase summaries
│   ├── PHASE1_SUMMARY.md
│   ├── PHASE2_SUMMARY.md
│   ├── PHASE3_SUMMARY.md
│   ├── IMPROVEMENT_ROADMAP.md
│   └── CLAUDE_BRANCH.md
│
└── legacy/                             # Debug tools & backups
    └── ...
```

---

## 🚀 Running the Application

### Start the App
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501/` with:
- **Landing page**: Quick stats and navigation
- **5 pages**: Data Import, Dashboard, Database Manager (and more)
- **Auto-navigation**: Streamlit sidebar with emoji icons

### Navigation
- 📥 **Data Import**: Import from Uneekor URLs
- 📊 **Dashboard**: Advanced analytics (5 tabs)
- 🗄️ **Database Manager**: CRUD operations (6 tabs)

---

## 🏗️ Architecture Overview

### Phase 1: Multi-Page Architecture

**Before**: Single `app.py` with 3 tabs (221 lines)
**After**:
- Landing page (`app.py` - 190 lines)
- 3 dedicated page files (`pages/` - 1,041 lines)
- 8 reusable components (`components/` - 599 lines Phase 1, +599 Phase 3)

**Benefits**:
- Separation of concerns (UI, components, data)
- Improved maintainability
- Better UX (clear navigation)
- Reusable components

### Phase 2: Enhanced Database Management

**golf_db.py** expanded from 233 → 866 lines (+633, +271%)

**New Database Tables**:
```sql
shots_archive    -- Deleted shots for recovery (undo functionality)
change_log       -- Audit trail for all modifications
```

**New Functions** (13 total):

**Session Operations** (4):
- `delete_session(session_id, archive=True)` - Delete with archiving
- `merge_sessions(session_ids, new_session_id)` - Combine sessions
- `split_session(session_id, shot_ids, new_session_id)` - Move shots
- `rename_session(old_session_id, new_session_id)` - Change session ID

**Bulk Editing** (3):
- `update_shot_metadata(shot_ids, field, value)` - Bulk update
- `recalculate_metrics(session_id=None)` - Recompute smash, clean data
- `bulk_rename_clubs(old_name, new_name)` - Global club rename

**Data Quality** (3):
- `find_outliers(session_id, club)` - Detect unrealistic values
- `validate_shot_data()` - Find missing critical fields
- `deduplicate_shots()` - Remove duplicates

**Audit Trail** (3):
- `restore_deleted_shots(shot_ids)` - Undo deletions
- `get_change_log(session_id, limit)` - View modification history
- `get_archived_shots(session_id)` - View deleted shots

### Phase 3: Advanced Visualizations

**New Visualization Components** (4 modules, 599 lines):

**Heatmap Chart** (`heatmap_chart.py` - 167 lines):
- Impact location visualization
- Sweet spot overlay (green circle)
- Center crosshairs (red lines)
- Average impact marker (yellow X)
- Consistency metrics (std dev)
- Supports Optix or standard impact data

**Trend Chart** (`trend_chart.py` - 94 lines):
- Performance tracking across sessions
- Linear regression trend line
- Improvement annotation (absolute + %)
- Summary statistics (best/worst/avg/latest)
- 6 metrics: carry, total, ball speed, smash, spin, launch

**Radar Chart** (`radar_chart.py` - 143 lines):
- Multi-metric club comparison (up to 5 clubs)
- 5 metrics: carry, ball speed, smash, back spin, launch
- Normalized 0-100 scale
- Color-coded polar plots
- Detailed comparison table

**Export Tools** (`export_tools.py` - 195 lines):
- CSV export with auto-filenames
- Text summary generator
- Excel multi-sheet export (one per club)
- Batch export (all sessions, per club)
- Preview mode

---

## 📊 Dashboard (Enhanced - 5 Tabs)

### Tab 1: 📈 Performance Overview
- KPI metrics row (shots, carry, total, smash, ball speed)
- Carry distance box plot
- Shot dispersion scatter (colored by smash)
- **NEW**: Multi-metric radar chart

### Tab 2: 🎯 Impact Analysis (NEW)
- Impact location heatmap
- Sweet spot overlay visualization
- Average impact marker
- Consistency statistics table by club

### Tab 3: 📊 Trends Over Time (NEW)
- Global trends (all sessions)
- Linear regression with improvement annotation
- Club-specific filtering
- Metric selector (6 options)
- Requires minimum 2 sessions

### Tab 4: 🔍 Shot Viewer
- Interactive shot table
- Shot detail panel with metrics
- Impact/swing image viewer
- (Unchanged from Phase 1)

### Tab 5: 💾 Export Data (NEW)
- Session export (CSV + text summary + Excel)
- All sessions export
- Per-club export
- Data preview (first 20 rows)

---

## 🗄️ Database Manager (Enhanced - 6 Tabs)

### Tab 1: ✏️ Edit Data
- Rename club (this session)
- Rename session (change session ID)
- Shot count by club table

### Tab 2: 🗑️ Delete Operations
- Delete entire session (with archiving)
- Delete all shots for club
- Delete individual shot
- Confirmation checkboxes for safety

### Tab 3: 🔄 Session Operations (NEW)
- Merge multiple sessions
- Split session (move shots to new session)
- Multi-select interfaces

### Tab 4: ⚡ Bulk Operations (NEW)
- Bulk rename club (across all sessions)
- Recalculate metrics (smash + clean invalid data)
- Scope selector (current session or all)

### Tab 5: 📊 Data Quality
- Outlier detection (carry > 400, smash > 1.6, etc.)
- Data validation (missing critical fields)
- Deduplication

### Tab 6: 📜 Audit Trail (NEW)
- Change log viewer (last 20 modifications)
- Restore deleted shots from archive
- Multi-select restore interface

---

## 🔧 Development Guidelines

### Working with Components

All components in `components/` follow this pattern:

```python
def render_component_name(data: pd.DataFrame, **kwargs) -> None:
    """
    Component description.

    Args:
        data: Input data
        **kwargs: Additional options
    """
    # Render Streamlit widgets
    st.subheader("Title")
    # ... implementation ...
```

**Import Pattern**:
```python
from components import (
    render_session_selector,
    render_metrics_row,
    render_impact_heatmap,
    render_trend_chart,
    render_radar_chart,
    render_summary_export
)
```

### Working with golf_db.py

**Hybrid Sync Pattern** (all write operations):
```python
def operation():
    # 1. Local SQLite
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        # ... execute ...
        conn.commit()

        # Log to change_log
        cursor.execute("INSERT INTO change_log ...")
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")

    # 2. Cloud Supabase (if available)
    if supabase:
        try:
            # ... execute same operation ...
        except Exception as e:
            print(f"Supabase Error: {e}")
```

**Database Tables**:
- `shots` - Main data (30 fields)
- `shots_archive` - Deleted shots (4 fields)
- `change_log` - Modification history (6 fields)

### Adding New Visualizations

1. Create component in `components/new_chart.py`
2. Follow the `render_*` naming convention
3. Add to `components/__init__.py` exports
4. Import in dashboard: `from components import render_new_chart`
5. Use in tab: `render_new_chart(df)`

### Database Schema Changes

**IMPORTANT**: Never modify existing columns without migration

**Add New Column**:
1. Add to `required_columns` dict in `golf_db.py:init_db()`
2. Auto-migration will add to existing databases
3. Update BigQuery schema if using cloud sync

**Example**:
```python
required_columns = {
    'optix_x': 'REAL',
    'optix_y': 'REAL',
    'new_field': 'TEXT'  # Add here
}
```

---

## 🧪 Testing

### Syntax Validation
```bash
python -m py_compile app.py golf_db.py components/*.py pages/*.py
```

### Run Specific Page
```bash
streamlit run pages/2_📊_Dashboard.py
```

### Test Database Operations
```python
import golf_db

# Initialize
golf_db.init_db()

# Test new functions
golf_db.merge_sessions(['84428', '84500'], 'Combined_Session')
outliers = golf_db.find_outliers('84428')
print(outliers)
```

---

## 📖 Key Files & Line Counts

| File | Lines | Purpose | Phase |
|------|-------|---------|-------|
| **app.py** | 190 | Landing page | 1 |
| **golf_db.py** | 866 | Database layer | 2 |
| **golf_scraper.py** | ~300 | API client | Original |
| **pages/1_📥_Data_Import.py** | 131 | Import UI | 1 |
| **pages/2_📊_Dashboard.py** | 435 | Analytics | 1,3 |
| **pages/3_🗄️_Database_Manager.py** | 475 | CRUD | 1,2 |
| **components/heatmap_chart.py** | 167 | Impact viz | 3 |
| **components/trend_chart.py** | 105 | Trends | 3 |
| **components/radar_chart.py** | 143 | Comparison | 3 |
| **components/export_tools.py** | 195 | Export | 3 |
| **Total** | 2,863+ | Core app | - |

---

## 🎓 Common Workflows

### After Practice Session
```bash
# 1. Import data
Open app → Data Import page → Paste Uneekor URL → Run Import

# 2. View analytics
Dashboard page → Impact Analysis tab → Check strike pattern

# 3. Export for coach
Dashboard page → Export Data tab → Download CSV + summary
```

### Merge Multiple Sessions
```bash
Database Manager → Session Operations tab → Select sessions → Enter new ID → Merge
```

### Track Improvement
```bash
Dashboard → Trends Over Time tab → Select metric → View trend line
```

### Clean Bad Data
```bash
Database Manager → Data Quality tab → View outliers → Delete tab → Remove bad shots
```

### Restore Deleted Shot
```bash
Database Manager → Audit Trail tab → View archive → Select shots → Restore
```

---

## 🔗 Documentation Links

- **Branch Instructions**: `/CLAUDE_BRANCH.md`
- **Full Roadmap**: `/IMPROVEMENT_ROADMAP.md`
- **Phase 1 Summary**: `/PHASE1_SUMMARY.md`
- **Phase 2 Summary**: `/PHASE2_SUMMARY.md`
- **Phase 3 Summary**: `/PHASE3_SUMMARY.md`
- **Main Project README**: `/README.md`

---

## 🚨 Important Notes

### Database Integrity
- All write operations sync to SQLite + Supabase
- Deletions are archived for recovery
- Change log tracks all modifications
- Never hard-code SQL without parameterization

### Visualization Guidelines
- Always filter invalid data (zeros, NaN, 99999)
- Use Plotly for interactive charts
- Provide hover tooltips with details
- Include contextual help text

### Export Functionality
- CSV: UTF-8 encoding
- Excel: Requires openpyxl (graceful failure if missing)
- Filenames: Include session ID + timestamp
- Preview: Show first 20 rows before download

### Performance
- Heatmaps: Filter to <1000 points for responsiveness
- Trend charts: Cache regression results for repeated views
- Radar charts: Limit to 5 clubs max
- Export: In-memory only (no disk I/O on server)

---

## 🐛 Known Issues

### Resolved
- ✅ Session selector refresh (Phase 1)
- ✅ Smash factor calculation (Phase 2)
- ✅ Missing data handling (Phase 3)

### Outstanding
- ⚠️ Image loading: Some shots show "No images available" even when URLs exist
  - **Workaround**: Re-run import to fetch images again
- ⚠️ Excel export: Requires openpyxl installation
  - **Workaround**: Install via `pip install openpyxl`

---

## 💡 Future Enhancements (Phases 4-6)

### Phase 4: ML Foundation
- Distance prediction model (XGBoost)
- Shot shape classifier
- Swing flaw detector
- Clustering for shot grouping

### Phase 5: AI Coach GUI
- Conversational Q&A interface
- ML-powered predictions
- Personalized training plan generator
- PGA Tour benchmarking

### Phase 6: Continuous Learning
- Auto-retrain models after each session
- Performance monitoring dashboard
- A/B testing framework
- Vertex AI deployment (optional)

---

## 📝 Changelog (This Branch)

### 2025-12-28: Phase 3 Complete
- Added impact location heatmap
- Added performance trend charts
- Added multi-metric radar charts
- Added comprehensive export tools (CSV/Excel/text)
- Enhanced Dashboard to 5 tabs

### 2025-12-28: Phase 2 Complete
- Added 13 new database functions
- Created shots_archive table for recovery
- Created change_log table for audit trail
- Enhanced Database Manager to 6 tabs
- Implemented undo functionality

### 2025-12-28: Phase 1 Complete
- Refactored monolithic app.py to multi-page architecture
- Created 3 dedicated page files
- Extracted 8 reusable components
- Improved navigation and UX

---

**Last Updated**: 2025-12-28
**Branch**: `claude/database-ui-ai-coaching-DE7uU`
**Status**: Active Development (3 of 6 phases complete)
