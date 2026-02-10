# Architecture Research: Local AI/ML Golf Analytics

**Researched:** 2026-02-10
**Context:** Extending existing layered architecture with enhanced ML coaching capabilities

---

## Current Architecture (Reference)

```
Streamlit UI (pages/, components/)
       |
  Local Coach / Gemini Coach
       |
  AI Provider Registry (services/ai/)
       |
  ML Module (ml/) ← lazy-loaded
       |
  Data Layer (golf_db.py) → SQLite + Supabase
```

**Extension points identified:**
1. `services/ai/registry.py` — add new AI providers via `@register_provider`
2. `ml/` — add new model types alongside existing predictors
3. `local_coach.py` — enhance coaching logic (currently template-based)

---

## Proposed Architecture Extension

### New Components

```
Streamlit UI
  ├── pages/4_AI_Coach.py (enhanced)
  ├── pages/5_ML_Dashboard.py (NEW — model performance, insights)
  └── components/render_insights.py (NEW — reusable insight cards)
       |
  Enhanced Local Coach (local_coach.py)
  ├── Intent Detection (existing)
  ├── Template Responses (existing)
  ├── ML-Powered Insights (NEW)
  └── Practice Plan Generator (NEW)
       |
  AI Provider Registry (services/ai/)
  └── Enhanced Local Provider (NEW — wraps ML insights)
       |
  ML Module (ml/)
  ├── train_models.py (existing — enhance)
  ├── classifiers.py (existing)
  ├── anomaly_detection.py (existing)
  ├── analytics/ (NEW)
  │   ├── dispersion.py — shot scatter analysis
  │   ├── club_distances.py — true distance calculations
  │   ├── strokes_gained.py — practice strokes gained
  │   ├── miss_tendencies.py — directional bias detection
  │   └── progress.py — session-over-session trends
  ├── coaching/ (NEW)
  │   ├── practice_plans.py — generate practice routines
  │   ├── recommendations.py — context-aware suggestions
  │   └── fault_detection.py — swing fault clustering
  ├── monitoring/ (NEW)
  │   ├── drift.py — model drift detection
  │   ├── versioning.py — model version management
  │   └── performance.py — prediction accuracy tracking
  └── models/ (NEW — serialized model storage)
       |
  Data Layer (golf_db.py)
  ├── shots table (existing)
  ├── session_metrics table (NEW — aggregate stats per session)
  └── model_performance table (NEW — prediction tracking)
```

---

## Component Boundaries

### Analytics Engine (`ml/analytics/`)
**Responsibility:** Pure computation — takes DataFrames, returns insights
**Interface:** Each module exposes a main function:
```python
# ml/analytics/dispersion.py
def calculate_dispersion(shots_df: pd.DataFrame, club: str) -> DispersionResult

# ml/analytics/club_distances.py
def calculate_true_distances(shots_df: pd.DataFrame) -> Dict[str, ClubDistance]

# ml/analytics/strokes_gained.py
def calculate_strokes_gained(shots_df: pd.DataFrame, benchmark: str) -> StrokesGainedResult
```
**Depends on:** pandas, numpy, scipy.stats
**Does NOT depend on:** golf_db, Streamlit, ML models

### Coaching Engine (`ml/coaching/`)
**Responsibility:** Transform analytics results into actionable advice
**Interface:**
```python
# ml/coaching/practice_plans.py
def generate_practice_plan(analytics: AnalyticsBundle, duration_minutes: int) -> PracticePlan

# ml/coaching/recommendations.py
def get_session_recommendations(recent_shots: pd.DataFrame) -> List[Recommendation]
```
**Depends on:** ml/analytics/, drill library (static data)
**Does NOT depend on:** golf_db directly (receives data, doesn't fetch it)

### Model Monitor (`ml/monitoring/`)
**Responsibility:** Track model health, trigger retraining
**Interface:**
```python
# ml/monitoring/drift.py
def check_drift(model_version: str, recent_shots: pd.DataFrame) -> DriftReport

# ml/monitoring/versioning.py
def save_model(model, metadata: ModelMetadata) -> str  # returns version ID
def load_model(version: str) -> Tuple[model, ModelMetadata]
```
**Depends on:** joblib, scipy.stats, optional mlflow
**Does NOT depend on:** analytics or coaching modules

---

## Data Flow

### Analytics Flow (Read Path)
```
User opens Dashboard/AI Coach
  → golf_db.get_session_data()
  → ml/analytics/ computes insights
  → components/ renders visualizations
  → local_coach uses insights for responses
```

### Training Flow (Write Path)
```
User triggers retrain (or auto-trigger from drift detection)
  → golf_db.get_all_shots()
  → ml/train_models.py loads data, engineers features
  → Train XGBoost/sklearn models
  → ml/monitoring/versioning.py saves model with metadata
  → ml/monitoring/performance.py logs baseline metrics
```

### Coaching Flow (Interactive)
```
User asks AI Coach a question
  → local_coach.py detects intent
  → If analytics question → ml/analytics/ computes answer
  → If advice question → ml/coaching/ generates recommendation
  → If prediction question → ml/ model predicts + SHAP explains
  → Response rendered with confidence and explanation
```

---

## Build Order (Dependencies)

```
Phase 1: Foundation
├── Refactor ML imports (fix lazy loading)
├── Add session_metrics table schema
├── Add model versioning infrastructure
└── Fix known bugs (rate limiter, error handling)

Phase 2: Analytics Engine
├── Shot dispersion (no dependencies)
├── True club distances (no dependencies)
├── Miss tendency detection (extends existing classifier)
├── Strokes gained (needs benchmark data)
└── Progress tracking (depends on all above)

Phase 3: Coaching & Predictions
├── Enhanced local coach (depends on analytics)
├── Practice plan generator (depends on analytics)
├── Context-aware recommendations (depends on analytics)
├── Model retraining pipeline (depends on versioning)
└── Prediction confidence intervals (depends on MAPIE)

Phase 4: Monitoring & Polish
├── Drift detection (depends on versioning + performance tracking)
├── ML dashboard page (depends on monitoring)
├── Session quality scoring (depends on analytics)
└── Equipment change detection (depends on progress tracking)
```

---

## Integration with Existing Architecture

### Minimal Changes to Existing Code
- `golf_db.py`: Add 2 new tables (session_metrics, model_performance). No changes to existing tables
- `local_coach.py`: Extend `_generate_response()` to call analytics when ML available
- `services/ai/providers/local_provider.py`: Enhance to use analytics results
- `app.py`: No changes needed (new pages auto-discovered by Streamlit)

### New Code (Isolated)
- `ml/analytics/` — entirely new, no coupling to existing ml/ modules
- `ml/coaching/` — entirely new, depends only on analytics
- `ml/monitoring/` — entirely new, wraps existing model persistence
- `pages/5_ML_Dashboard.py` — new Streamlit page

### Risk Mitigation
- All new code in new files/directories — no risk of breaking existing features
- Analytics module has zero dependencies on existing ML models — can ship independently
- Coaching module uses analytics as input — not coupled to specific model implementations
- Monitoring module wraps existing joblib persistence — backward compatible

---
*Architecture research completed: 2026-02-10*
