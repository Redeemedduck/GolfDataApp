# Golf Data App - Improvement Roadmap

**Branch**: `claude/database-ui-ai-coaching-DE7uU`
**Created**: 2025-12-28
**Focus Areas**: Data Presentation, Database Management, GUI Separation, AI/ML Integration

---

## 📊 1. DATA PRESENTATION IMPROVEMENTS

### Current State
- Basic Plotly charts (box plot, dispersion scatter)
- Simple KPI metrics (total shots, avg carry, avg smash, avg ball speed)
- Table view with row selection
- Impact/swing image viewer

### Planned Enhancements

#### A. Advanced Visualizations
| Visualization | Purpose | Priority | Status |
|--------------|---------|----------|--------|
| **Impact Heatmap** | Show strike pattern using optix_x, optix_y | High | ⬜ Not Started |
| **Trend Charts** | Performance over time across sessions | High | ⬜ Not Started |
| **Radar Charts** | Multi-metric club comparison (speed, smash, spin, accuracy) | Medium | ⬜ Not Started |
| **Spin Analysis** | 2D plot of back_spin vs side_spin by shot shape | Medium | ⬜ Not Started |
| **Attack Angle Distribution** | Histogram showing attack angle patterns per club | Medium | ⬜ Not Started |
| **Flight Path 3D** | Combine apex, carry, descent_angle for trajectory view | Low | ⬜ Not Started |
| **Correlation Matrix** | Identify which metrics predict distance/accuracy | Medium | ⬜ Not Started |

#### B. Statistical Dashboards
| Feature | Description | Priority | Status |
|---------|-------------|----------|--------|
| **Percentile Rankings** | Show how each shot ranks vs personal history | High | ⬜ Not Started |
| **Session Comparisons** | Side-by-side analysis of multiple sessions | High | ⬜ Not Started |
| **Club Gapping Analysis** | Identify distance gaps between clubs | High | ⬜ Not Started |
| **Consistency Score** | Standard deviation-based rating per club | Medium | ⬜ Not Started |
| **Heat Streaks** | Identify "dialed in" moments during sessions | Low | ⬜ Not Started |

#### C. Data Export Capabilities
| Export Type | Format | Priority | Status |
|-------------|--------|----------|--------|
| **Filtered Data Export** | CSV | High | ⬜ Not Started |
| **Session Summary PDF** | PDF with charts | Medium | ⬜ Not Started |
| **Excel Multi-Sheet** | One sheet per club | Medium | ⬜ Not Started |
| **Share Links** | Public session view URL | Low | ⬜ Not Started |

---

## ✏️ 2. DATABASE MANAGEMENT ENHANCEMENTS

### Current State ✅
- Delete individual shots (`golf_db.delete_shot()`)
- Delete all shots for a club in session (`golf_db.delete_club_session()`)
- Rename clubs (`golf_db.rename_club()`)
- Hybrid local/cloud sync (SQLite + Supabase)

### Missing Capabilities

#### A. Session-Level Operations
```python
# Functions to add in golf_db.py

def delete_session(session_id):
    """Delete entire session from SQLite + Supabase + BigQuery"""

def merge_sessions(session_ids, new_session_id):
    """Combine multiple sessions into one unified session"""

def split_session(session_id, shot_ids, new_session_id):
    """Move specific shots to a new session"""

def rename_session(session_id, new_session_id):
    """Change session identifier across all systems"""
```

**Priority**: High
**Status**: ⬜ Not Started

#### B. Bulk Editing
```python
def update_shot_metadata(shot_ids, field, value):
    """Bulk update any field (club, session_id, etc.) for multiple shots"""

def recalculate_metrics(session_id=None):
    """Recompute smash factor, clean invalid data (99999 → 0)"""

def bulk_rename_clubs(old_name, new_name):
    """Rename club across ALL sessions (not just one)"""
```

**Priority**: Medium
**Status**: ⬜ Not Started

#### C. Data Quality Tools
```python
def find_outliers(session_id=None, club=None):
    """Detect impossible shots (e.g., carry > 400 for PW, smash > 1.6)"""

def validate_shot_data():
    """Find shots missing critical fields (ball_speed, club_speed, carry)"""

def deduplicate_shots():
    """Remove exact duplicates by shot_id"""

def fix_invalid_values():
    """Batch clean all shots with 99999 sentinel values"""
```

**Priority**: Medium
**Status**: ⬜ Not Started

#### D. Audit Trail & Undo
```python
def archive_deleted_shots(shot_ids):
    """Move to shots_archive table instead of hard delete"""

def restore_deleted_shots(shot_ids):
    """Undo deletion from archive"""

def get_change_log(session_id=None):
    """Show history of edits (timestamp, operation, user)"""
```

**Priority**: Low
**Status**: ⬜ Not Started

---

## 🎨 3. GUI SEPARATION (Multi-Page Architecture)

### Current State
Single monolithic `app.py` (221 lines) with 3 tabs:
- Tab 1: Dashboard (KPIs + charts)
- Tab 2: Shot Viewer (table + images)
- Tab 3: Manage Data (rename/delete)

### Proposed Multi-Page Structure

```
GolfDataApp/
├── app.py                          # Landing page / navigation
├── pages/
│   ├── 1_📥_Data_Import.py         # Scraping GUI (isolated)
│   ├── 2_📊_Dashboard.py           # Analytics & visualizations
│   ├── 3_🗄️_Database_Manager.py   # CRUD operations
│   ├── 4_🤖_AI_Coach.py            # AI analysis & coaching
│   └── 5_⚙️_Settings.py            # Configuration
├── components/                      # Shared UI components
│   ├── __init__.py
│   ├── metrics_card.py             # Reusable KPI cards
│   ├── dispersion_chart.py         # Shot dispersion plot
│   ├── heatmap_chart.py            # Impact location heatmap
│   ├── session_selector.py         # Session dropdown with filters
│   └── shot_table.py               # Interactive shot table
└── utils/
    ├── golf_db.py                  # Database operations
    ├── golf_scraper.py             # API data fetching
    └── ai_coach.py                 # NEW: ML/AI engine
```

### Page Breakdown

#### Page 1: Data Import 📥
**Sole Purpose**: Fetch data from Uneekor API

**Features**:
- URL input field (current implementation)
- Batch import (paste multiple URLs)
- Manual shot entry form (for non-Uneekor data)
- Import history log (show last 10 imports)
- Preview before saving (review shots before DB commit)
- Duplicate detection warnings
- Image upload override (re-fetch images)

**Priority**: High
**Status**: ⬜ Not Started

#### Page 2: Dashboard 📊
**Sole Purpose**: View performance analytics

**Features**:
- Session selector (multi-select for comparison mode)
- Club filter (multi-select, current implementation)
- Date range picker (filter by date_added)
- Advanced charts (heatmaps, trends, radar, spin plots)
- Leaderboards (best shots by carry, smash, accuracy)
- Export buttons (CSV, PDF, Excel)
- "Personal Best" highlights

**Priority**: High
**Status**: ⬜ Not Started

#### Page 3: Database Manager 🗄️
**Sole Purpose**: CRUD operations on data

**Features**:
- Shot editor (inline table editing with st.data_editor)
- Bulk operations (select multiple → delete/update/move)
- Session management (rename, delete, merge, split)
- Data quality checker (find outliers, missing data)
- Audit log viewer (change history)
- Sync status dashboard (SQLite ↔ Supabase ↔ BigQuery)
- Archive viewer (restore deleted shots)

**Priority**: High
**Status**: ⬜ Not Started

#### Page 4: AI Coach 🤖
**Sole Purpose**: Personalized insights & recommendations

**Features**:
- **Ask Coach**: Conversational Q&A (Gemini + RAG over your data)
- **Shot Predictor**: ML-powered distance/dispersion prediction
- **Swing Diagnosis**: Pattern detection (over-the-top, in-to-out, etc.)
- **Drill Recommendations**: Based on detected weaknesses
- **Progress Tracker**: ML-powered trend analysis over weeks/months
- **PGA Tour Benchmarking**: Compare to pro averages (altitude-adjusted)
- **Training Plan Generator**: Personalized practice routines

**Priority**: Medium
**Status**: ⬜ Not Started

#### Page 5: Settings ⚙️
**Sole Purpose**: Configuration management

**Features**:
- Database connections (test Supabase, BigQuery)
- API keys (Gemini, Uneekor, Anthropic)
- AI model selection (Gemini 3 vs Vertex AI vs local models)
- Auto-sync configuration (enable/disable, schedule)
- Data retention policies (archive old sessions)
- Export/import settings

**Priority**: Low
**Status**: ⬜ Not Started

---

## 🤖 4. MACHINE LEARNING & AI COACHING

### Current State
- Uses Gemini API for one-time analysis (stateless)
- Manual triggering via `scripts/gemini_analysis.py`
- No learning from past sessions
- No predictive capabilities

### Proposed ML Architecture

#### A. Persistent Learning System

**New File**: `utils/ai_coach.py`

```python
class GolfCoach:
    """ML-powered coaching system that learns from your data"""

    def __init__(self):
        self.user_profile = self.load_or_create_profile()
        self.ml_models = self.load_models()

    def learn_from_session(self, session_id):
        """Update user profile and retrain models after each session"""
        # 1. Extract patterns (club path consistency, spin tendencies)
        # 2. Update baseline metrics (personal averages, best shots)
        # 3. Retrain prediction models with new data
        # 4. Generate personalized drills based on weaknesses

    def predict_shot_outcome(self, club, club_speed, attack_angle, face_angle):
        """Predict carry distance & dispersion before hitting"""
        # ML model trained on YOUR historical data

    def recommend_optimal_settings(self, club, target_distance):
        """Suggest launch angle, spin rate for desired carry"""

    def detect_swing_changes(self):
        """Identify when mechanics have shifted (time-series analysis)"""
```

**Priority**: Medium
**Status**: ⬜ Not Started

#### B. ML Model Types

##### 1. Regression Models (Predictive)

| Model | Input Features | Output | Algorithm | Priority | Status |
|-------|---------------|--------|-----------|----------|--------|
| **Distance Predictor** | club_speed, launch_angle, back_spin, attack_angle | Predicted carry distance | XGBoost | High | ⬜ Not Started |
| **Dispersion Predictor** | club_path, face_angle, club_speed, side_spin | Expected side_distance | Random Forest | Medium | ⬜ Not Started |
| **Smash Optimizer** | impact_x, impact_y, dynamic_loft, club_speed | Optimal contact point | Gradient Boosting | Medium | ⬜ Not Started |

##### 2. Classification Models (Diagnostic)

| Model | Input Features | Output Classes | Algorithm | Priority | Status |
|-------|---------------|----------------|-----------|----------|--------|
| **Shot Shape Classifier** | club_path, face_angle, side_spin | {Straight, Draw, Fade, Hook, Slice} | Logistic Regression | High | ⬜ Not Started |
| **Swing Flaw Detector** | attack_angle, club_path variance, consistency | {Over-the-top, In-to-out, Steep, Shallow, Inconsistent} | Anomaly Detection | Medium | ⬜ Not Started |
| **Session Quality Scorer** | All shots in session | Quality grade (A-F) | K-Means Clustering | Low | ⬜ Not Started |

##### 3. Time-Series Models (Trend Analysis)

| Model | Purpose | Algorithm | Priority | Status |
|-------|---------|-----------|----------|--------|
| **Progress Tracker** | Track improvement in key metrics over weeks/months | ARIMA / Prophet | Medium | ⬜ Not Started |
| **Fatigue Detector** | Identify when performance degrades during session | LSTM | Low | ⬜ Not Started |

#### C. Advanced AI Features

##### Vector Embeddings for Semantic Search
```python
# Use OpenAI embeddings or SentenceTransformers
"Show me sessions where I struggled with slices"
"Find shots similar to my best 7-iron"
"What drills helped me improve club path last month?"
```

**Priority**: Low
**Status**: ⬜ Not Started

##### Reinforcement Learning (Future)
```python
# RL agent suggests drills based on outcomes
Agent observes: session data
Agent suggests: Focus on attack angle drills
Agent learns: Did carry distance improve in next session?
```

**Priority**: Low (Future Phase)
**Status**: ⬜ Not Started

---

## 🚀 IMPLEMENTATION PHASES

### Phase 1: GUI Separation (Week 1)
**Goal**: Split monolithic app.py into multi-page architecture

**Tasks**:
- [ ] Create `pages/` directory structure
- [ ] Migrate existing tabs to separate page files
  - [ ] `1_📥_Data_Import.py`
  - [ ] `2_📊_Dashboard.py`
  - [ ] `3_🗄️_Database_Manager.py`
- [ ] Create `components/` directory
- [ ] Extract reusable UI components:
  - [ ] `session_selector.py`
  - [ ] `shot_table.py`
  - [ ] `metrics_card.py`
- [ ] Update navigation in `app.py`
- [ ] Test multi-page flow

**Estimated Time**: 2-3 days
**Dependencies**: None
**Deliverable**: Cleaner, modular Streamlit app

---

### Phase 2: Enhanced Database Management (Week 1-2)
**Goal**: Add missing CRUD operations and data quality tools

**Tasks**:
- [ ] Add session-level operations to `golf_db.py`:
  - [ ] `delete_session(session_id)`
  - [ ] `merge_sessions(session_ids, new_session_id)`
  - [ ] `split_session(session_id, shot_ids, new_session_id)`
  - [ ] `rename_session(old_id, new_id)`
- [ ] Add bulk editing functions:
  - [ ] `update_shot_metadata(shot_ids, field, value)`
  - [ ] `recalculate_metrics(session_id=None)`
  - [ ] `bulk_rename_clubs(old_name, new_name)`
- [ ] Add data quality tools:
  - [ ] `find_outliers(session_id, club)`
  - [ ] `validate_shot_data()`
  - [ ] `deduplicate_shots()`
- [ ] Implement audit trail:
  - [ ] Create `shots_archive` table
  - [ ] Add `change_log` table
  - [ ] Modify delete functions to archive instead of hard delete
- [ ] Update UI in `3_🗄️_Database_Manager.py`

**Estimated Time**: 3-4 days
**Dependencies**: None
**Deliverable**: Comprehensive database management interface

---

### Phase 3: Advanced Visualizations (Week 2-3)
**Goal**: Add sophisticated charts for deeper insights

**Tasks**:
- [ ] Create chart components in `components/`:
  - [ ] `heatmap_chart.py` (impact location using optix_x, optix_y)
  - [ ] `trend_chart.py` (performance over time)
  - [ ] `radar_chart.py` (multi-metric club comparison)
  - [ ] `spin_chart.py` (back_spin vs side_spin 2D plot)
  - [ ] `correlation_matrix.py` (metric relationships)
- [ ] Add statistical dashboards:
  - [ ] Percentile rankings
  - [ ] Session comparison tool
  - [ ] Club gapping analysis
  - [ ] Consistency score calculator
- [ ] Implement export functionality:
  - [ ] CSV export (filtered data)
  - [ ] PDF report generator (with charts)
  - [ ] Excel multi-sheet export

**Estimated Time**: 4-5 days
**Dependencies**: Phase 1 (multi-page structure)
**Deliverable**: Professional-grade analytics dashboard

---

### Phase 4: ML Foundation (Week 3-4)
**Goal**: Build machine learning infrastructure

**Tasks**:
- [ ] Create `utils/ai_coach.py` module
- [ ] Create training pipeline:
  - [ ] `scripts/train_models.py`
  - [ ] Build training dataset from BigQuery
  - [ ] Split into train/validation/test sets
- [ ] Train initial models:
  - [ ] Distance predictor (XGBoost)
  - [ ] Shot shape classifier (Logistic Regression)
  - [ ] Swing flaw detector (Anomaly Detection)
- [ ] Model evaluation:
  - [ ] `scripts/evaluate_models.py`
  - [ ] Track accuracy, RMSE, F1 scores
- [ ] Model persistence:
  - [ ] Save to `models/` directory
  - [ ] Create `model_metadata.json`
- [ ] Create user profile system:
  - [ ] Store personal baselines (avg carry, smash, etc.)
  - [ ] Track improvement over time

**Estimated Time**: 7-10 days
**Dependencies**: Sufficient historical data (50+ shots per club)
**Deliverable**: Trained ML models ready for integration

---

### Phase 5: AI Coach GUI (Week 4-5)
**Goal**: Build interactive AI coaching interface

**Tasks**:
- [ ] Create `pages/4_🤖_AI_Coach.py`
- [ ] Implement features:
  - [ ] **Ask Coach**: RAG-powered Q&A
    - [ ] Integrate Gemini API with vector search
    - [ ] Context retrieval from SQLite
  - [ ] **Shot Predictor**: ML predictions
    - [ ] Load trained models
    - [ ] Interactive input sliders
    - [ ] Real-time prediction display
  - [ ] **Swing Diagnosis**: Pattern detection
    - [ ] Analyze recent sessions
    - [ ] Identify trends (improving/declining metrics)
    - [ ] Flag anomalies
  - [ ] **Drill Recommendations**: Personalized drills
    - [ ] Based on detected weaknesses
    - [ ] Prioritized by impact
  - [ ] **Progress Tracker**: Time-series visualization
    - [ ] Show improvement over weeks/months
    - [ ] Milestone achievements
  - [ ] **PGA Tour Benchmarking**:
    - [ ] Compare to tour averages (altitude-adjusted)
    - [ ] Highlight strengths/weaknesses

**Estimated Time**: 5-7 days
**Dependencies**: Phase 4 (ML models)
**Deliverable**: Fully functional AI coach interface

---

### Phase 6: Continuous Learning (Ongoing)
**Goal**: Automate model retraining and improvement tracking

**Tasks**:
- [ ] Auto-retrain after each session:
  - [ ] Trigger `train_models.py` via hook
  - [ ] Incremental learning (update weights, not full retrain)
- [ ] Model performance monitoring:
  - [ ] Track prediction accuracy over time
  - [ ] Alert when accuracy drops
- [ ] A/B testing framework:
  - [ ] Test different ML architectures
  - [ ] Compare Gemini 3 vs Vertex AI vs local models
- [ ] Deploy to Vertex AI (optional):
  - [ ] Upload models to Model Registry
  - [ ] Use Vertex AI Predictions for scalability

**Estimated Time**: Ongoing maintenance
**Dependencies**: Phase 5 (AI Coach GUI)
**Deliverable**: Self-improving AI system

---

## 📁 FINAL FILE STRUCTURE

```
GolfDataApp/
├── app.py                              # Landing page / router
├── pages/
│   ├── 1_📥_Data_Import.py             # Scraping GUI
│   ├── 2_📊_Dashboard.py               # Analytics dashboard
│   ├── 3_🗄️_Database_Manager.py       # CRUD operations
│   ├── 4_🤖_AI_Coach.py                # AI coaching interface
│   └── 5_⚙️_Settings.py                # Configuration
├── components/                          # Reusable UI components
│   ├── __init__.py
│   ├── metrics_card.py
│   ├── dispersion_chart.py
│   ├── heatmap_chart.py
│   ├── radar_chart.py
│   ├── trend_chart.py
│   ├── spin_chart.py
│   ├── session_selector.py
│   └── shot_table.py
├── utils/                               # Business logic
│   ├── golf_db.py                      # Database operations (enhanced)
│   ├── golf_scraper.py                 # API data fetching
│   └── ai_coach.py                     # NEW: ML/AI engine
├── models/                              # Trained ML models
│   ├── distance_predictor.pkl
│   ├── shot_classifier.pkl
│   ├── swing_flaw_detector.pkl
│   └── model_metadata.json
├── scripts/                             # Automation & training
│   ├── train_models.py                 # NEW: ML training pipeline
│   ├── evaluate_models.py              # NEW: Model evaluation
│   ├── gemini_analysis.py              # Existing Gemini integration
│   ├── supabase_to_bigquery.py         # Existing sync script
│   └── auto_sync.py                    # Existing automation
├── tests/                               # Unit tests
│   ├── test_ai_coach.py
│   ├── test_golf_db.py
│   └── test_models.py
├── docs/                                # Documentation
│   ├── README.md
│   ├── CLAUDE.md
│   ├── IMPROVEMENT_ROADMAP.md          # This file
│   ├── PIPELINE_COMPLETE.md
│   └── API_REFERENCE.md                # NEW: Code documentation
└── .streamlit/
    └── config.toml                      # Streamlit settings
```

---

## 🎯 SUCCESS METRICS

### User Experience
- [ ] Reduced clicks to common tasks (import → view → analyze)
- [ ] Faster page load times (<2s)
- [ ] Mobile-responsive design
- [ ] Zero data loss (robust error handling)

### Data Quality
- [ ] <1% outliers/invalid data
- [ ] 100% sync success rate (SQLite ↔ Supabase ↔ BigQuery)
- [ ] Audit trail for all destructive operations

### AI/ML Performance
- [ ] Distance prediction RMSE <5 yards
- [ ] Shot shape classification accuracy >85%
- [ ] Swing flaw detection precision >75%
- [ ] User satisfaction with AI recommendations (qualitative)

### Code Quality
- [ ] Test coverage >80%
- [ ] Type hints on all functions
- [ ] Documentation for all public APIs
- [ ] CI/CD pipeline (GitHub Actions)

---

## 🔗 RELATED DOCUMENTS

- **Main Documentation**: `/CLAUDE.md` (project overview)
- **Branch Instructions**: `/CLAUDE_BRANCH.md` (this branch's focus)
- **API Reference**: `/docs/API_REFERENCE.md` (to be created)
- **Changelog**: `/changelog.md` (track completed work)

---

## 📝 NOTES

### Design Decisions
- **Why Multi-Page**: Single app.py was growing unwieldy; separation improves maintainability
- **Why Local-First ML**: User data privacy + offline capability + faster predictions
- **Why Hybrid Cloud**: Supabase for backup, BigQuery for advanced analytics
- **Why Gemini + Custom ML**: Gemini for conversational AI, custom models for predictions

### Future Considerations
- **Mobile App**: React Native app consuming same Supabase backend
- **Real-Time Sync**: WebSocket integration for live session updates
- **Social Features**: Share sessions with coach, compare with friends
- **Video Analysis**: Integrate swing video with shot data (computer vision)

---

**Last Updated**: 2025-12-28
**Next Review**: After Phase 1 completion
