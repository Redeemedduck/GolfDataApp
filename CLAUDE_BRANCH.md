# CLAUDE.md - Branch-Specific Instructions

**Branch**: `claude/database-ui-ai-coaching-DE7uU`
**Created**: 2025-12-28
**Focus**: Database Management Enhancements, GUI Separation, AI/ML Coaching Integration

---

## 🎯 BRANCH OBJECTIVES

This branch is dedicated to three major architectural improvements:

1. **Enhanced Database Management**: Add missing CRUD operations (session deletion, bulk editing, data quality tools)
2. **GUI Separation**: Split monolithic `app.py` into multi-page Streamlit app
3. **AI/ML Integration**: Build intelligent coaching system that learns from user data

See `/IMPROVEMENT_ROADMAP.md` for detailed implementation plan.

---

## 📋 CURRENT STATUS

### Completed ✅
- ✅ Documentation created (IMPROVEMENT_ROADMAP.md, CLAUDE_BRANCH.md)
- ✅ Branch initialized and synced

### In Progress 🚧
- 🚧 Phase 1: GUI Separation (Not Started)
- 🚧 Phase 2: Database Management (Not Started)
- 🚧 Phase 3: Advanced Visualizations (Not Started)
- 🚧 Phase 4: ML Foundation (Not Started)
- 🚧 Phase 5: AI Coach GUI (Not Started)

### Next Steps 🎯
1. Begin Phase 1: Create multi-page structure
2. Migrate existing tabs to separate page files
3. Extract reusable components

---

## 🏗️ ARCHITECTURE CHANGES

### Before (Current)
```
GolfDataApp/
├── app.py                    # Monolithic (221 lines, 3 tabs)
├── golf_db.py                # Basic CRUD (missing session ops, bulk edits)
├── golf_scraper.py           # API fetching
└── scripts/
    └── gemini_analysis.py    # Stateless AI analysis
```

### After (Target)
```
GolfDataApp/
├── app.py                         # Landing page / router
├── pages/
│   ├── 1_📥_Data_Import.py        # Isolated scraping GUI
│   ├── 2_📊_Dashboard.py          # Advanced analytics
│   ├── 3_🗄️_Database_Manager.py  # Comprehensive CRUD
│   ├── 4_🤖_AI_Coach.py           # ML-powered coaching
│   └── 5_⚙️_Settings.py           # Configuration
├── components/                     # Reusable UI widgets
│   ├── session_selector.py
│   ├── shot_table.py
│   ├── heatmap_chart.py
│   └── metrics_card.py
├── utils/
│   ├── golf_db.py                 # Enhanced with 15+ new functions
│   ├── golf_scraper.py            # Unchanged
│   └── ai_coach.py                # NEW: ML engine
├── models/                         # NEW: Trained ML models
│   └── distance_predictor.pkl
└── scripts/
    ├── train_models.py            # NEW: ML training pipeline
    └── gemini_analysis.py         # Existing (unchanged)
```

---

## 🔧 KEY DEVELOPMENT GUIDELINES

### Database Operations
When adding new database functions to `golf_db.py`:

1. **Maintain Hybrid Architecture**: All write operations must sync to both SQLite AND Supabase
2. **Handle Errors Gracefully**: Wrap in try/except, never crash on cloud failures
3. **Test Locally First**: Verify SQLite operations before testing cloud sync
4. **Update BigQuery**: If schema changes, update `bigquery_schema.json` and sync script

**Example Pattern**:
```python
def new_db_operation(param):
    """Description of operation"""
    # 1. Local SQLite operation
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        # ... execute operation ...
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite Error: {e}")

    # 2. Cloud Supabase operation (if available)
    if supabase:
        try:
            # ... execute same operation on Supabase ...
        except Exception as e:
            print(f"Supabase Error: {e}")
```

### Multi-Page App Guidelines

1. **File Naming**: Use `N_emoji_PageName.py` format (e.g., `1_📥_Data_Import.py`)
2. **Shared State**: Use `st.session_state` for data sharing between pages
3. **Navigation**: Streamlit auto-generates sidebar navigation from filenames
4. **Imports**: Import from `../components/` and `../utils/` using relative paths

**Example Page Structure**:
```python
# pages/2_📊_Dashboard.py
import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from components.session_selector import render_session_selector
from utils import golf_db

st.set_page_config(layout="wide", page_title="Dashboard")

# Page content...
```

### Component Design

All components in `components/` should:
1. Be pure functions that return Streamlit widgets
2. Accept data as parameters (no direct DB calls)
3. Use type hints for clarity
4. Include docstrings

**Example**:
```python
# components/metrics_card.py
import streamlit as st

def render_metrics_card(title: str, value: str, delta: str = None) -> None:
    """
    Render a styled metric card.

    Args:
        title: Metric label
        value: Primary value to display
        delta: Optional change indicator
    """
    st.metric(label=title, value=value, delta=delta)
```

### ML Model Development

When building models in `utils/ai_coach.py`:

1. **Train on BigQuery Data**: Use full historical dataset for training
2. **Save Models Locally**: Persist to `models/` directory using joblib/pickle
3. **Version Models**: Include date in filename (`distance_predictor_2025-12-28.pkl`)
4. **Log Metrics**: Track RMSE, accuracy, F1 scores in `model_metadata.json`
5. **Validate Before Deploy**: Test on holdout data before exposing to UI

**Training Pipeline**:
```
1. scripts/train_models.py: Fetch data from BigQuery → Train → Save models
2. utils/ai_coach.py: Load models → Predict on new data
3. pages/4_🤖_AI_Coach.py: UI for predictions and insights
```

---

## 🚨 IMPORTANT NOTES

### Database Schema Considerations
- **DO NOT** modify existing columns without migration plan
- **ADD** new columns via ALTER TABLE (golf_db.py already has auto-migration)
- **TEST** schema changes on SQLite before Supabase/BigQuery

### Data Integrity Rules
- All shot deletions must be logged in `change_log` table (Phase 2)
- Never hard delete without user confirmation
- Always offer undo for destructive operations
- Validate shot_id format before operations

### Performance Optimization
- Use indexes on frequently queried columns (session_id, club, date_added)
- Lazy load images (don't fetch all at once)
- Cache ML predictions in session_state
- Paginate large result sets (>100 rows)

### Code Quality Standards
- Type hints required for all new functions
- Docstrings required (Google style)
- Error messages must be user-friendly
- Log all exceptions to file (`logs/app.log`)

---

## 🧪 TESTING REQUIREMENTS

Before merging to main:

### Unit Tests
- [ ] All new `golf_db.py` functions have tests
- [ ] ML models achieve minimum accuracy thresholds:
  - Distance predictor: RMSE <5 yards
  - Shot classifier: Accuracy >85%
- [ ] Component rendering tests (visual regression)

### Integration Tests
- [ ] Multi-page navigation works correctly
- [ ] SQLite → Supabase sync succeeds
- [ ] Image upload/download works
- [ ] ML predictions return valid values

### User Acceptance Tests
- [ ] Can import session via URL
- [ ] Can delete session and restore from archive
- [ ] Can bulk rename clubs across all sessions
- [ ] AI Coach provides actionable recommendations
- [ ] Export to CSV/PDF works

---

## 📦 DEPENDENCIES TO ADD

### Python Packages
```bash
# For ML models
pip install scikit-learn xgboost joblib

# For advanced charts
pip install plotly kaleido  # kaleido for PDF export

# For embeddings (Phase 5)
pip install sentence-transformers openai

# For time-series analysis (Phase 6)
pip install prophet statsmodels
```

### Update Requirements
Add to `requirements.txt`:
```
scikit-learn>=1.3.0
xgboost>=2.0.0
joblib>=1.3.0
kaleido>=0.2.1
sentence-transformers>=2.2.0  # Optional for Phase 5
```

---

## 🐛 KNOWN ISSUES TO ADDRESS

### Current Bugs
1. **Image loading**: Some shots show "No images available" even when URLs exist in DB
   - **Fix**: Add retry logic in `golf_scraper.py` image download
2. **Session selector**: Doesn't refresh after delete until manual page refresh
   - **Fix**: Add `st.rerun()` after successful delete
3. **Smash factor**: Showing 0.0 for some valid shots
   - **Fix**: Check `clean_value()` logic in `golf_db.py:22-26`

### Performance Issues
1. Loading all sessions at once (slow with 100+ sessions)
   - **Fix**: Implement pagination or lazy loading
2. Plotly charts freeze with >500 data points
   - **Fix**: Add downsampling for large datasets

---

## 📖 REFERENCE DOCUMENTS

- **Main CLAUDE.md**: `/CLAUDE.md` (general project instructions)
- **Roadmap**: `/IMPROVEMENT_ROADMAP.md` (detailed implementation plan)
- **Pipeline Docs**: `/PIPELINE_COMPLETE.md` (cloud architecture)
- **API Docs**: Uneekor API documentation (internal)

---

## 🔄 GIT WORKFLOW

### Commit Message Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring
- `docs`: Documentation changes
- `test`: Test additions
- `chore`: Maintenance tasks

**Examples**:
```bash
git commit -m "feat(db): add session merge function"
git commit -m "refactor(ui): split app.py into multi-page structure"
git commit -m "feat(ml): implement distance prediction model"
```

### Branch Lifecycle
1. **Development**: Work in `claude/database-ui-ai-coaching-DE7uU`
2. **Commits**: Frequent, atomic commits with clear messages
3. **Push**: Push to origin after each phase completion
4. **PR**: Create PR to main branch when all phases complete
5. **Review**: Self-review using `/IMPROVEMENT_ROADMAP.md` checklist

---

## 💡 QUICK REFERENCE

### File Locations (Frequently Used)
```bash
# Database operations
utils/golf_db.py

# UI pages
pages/1_📥_Data_Import.py
pages/2_📊_Dashboard.py
pages/3_🗄️_Database_Manager.py

# ML engine
utils/ai_coach.py
scripts/train_models.py

# Configuration
.env
```

### Common Commands
```bash
# Run app locally
streamlit run app.py

# Train ML models
python scripts/train_models.py

# Test database connection
python legacy/test_connection.py

# Sync to BigQuery
python scripts/supabase_to_bigquery.py full
```

### Useful Queries (SQLite)
```sql
-- Count shots per session
SELECT session_id, COUNT(*) FROM shots GROUP BY session_id;

-- Find outliers (carry > 300 yards)
SELECT * FROM shots WHERE carry > 300 ORDER BY carry DESC;

-- Check for duplicates
SELECT shot_id, COUNT(*) FROM shots GROUP BY shot_id HAVING COUNT(*) > 1;
```

---

## 🎓 LEARNING RESOURCES

### Streamlit Multi-Page Apps
- [Official Docs](https://docs.streamlit.io/library/get-started/multipage-apps)
- [Example Apps](https://streamlit.io/gallery)

### ML for Golf Analysis
- [TrackMan University](https://trackmangolf.com/university) (similar metrics to Uneekor)
- [Golf Analytics Research](https://scholar.google.com/scholar?q=golf+shot+prediction)

### BigQuery ML
- [BigQuery ML Docs](https://cloud.google.com/bigquery-ml/docs)
- [Golf Data on BigQuery](https://cloud.google.com/blog/topics/developers-practitioners/analyzing-golf-stats-bigquery) (case study)

---

**Last Updated**: 2025-12-28
**Next Review**: After Phase 1 completion
**Questions?**: See `/IMPROVEMENT_ROADMAP.md` for detailed context
