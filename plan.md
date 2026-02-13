# Implementation Plan: ML Analytics & Data Quality Enhancement

## Overview

This plan adds 5 major feature areas to the GolfDataApp: enhanced ML pipeline, analytics engine, ML-enhanced coaching, model health monitoring, and a data quality framework. The work is organized into 4 phases with clear dependencies.

**Current state:** 3 ML models (XGBoost distance, shot shape, anomaly detection) with lazy loading, 22 Streamlit components, 4 pages, ~255 tests. No `analytics/` module, no `ml/coaching/` or `ml/monitoring/` subdirectories, no data quality filtering, no prediction intervals.

---

## Phase 1: Foundation & Infrastructure (no UI changes)

### 1.1 Analytics utilities module
- **Create** `analytics/__init__.py` — exports core functions
- **Create** `analytics/utils.py` — `filter_outliers_iqr()`, `check_min_samples()`, `normalize_score()`, `normalize_inverse()`, `calculate_distance_stats()` (median + IQR-based club distances)
- **Create** `tests/unit/test_analytics_utils.py` — edge cases for all 5 functions

### 1.2 ML module restructuring
- **Update** `ml/__init__.py` — replace `__getattr__` lazy loading with explicit `try/except ImportError` blocks; add `ML_AVAILABLE` boolean, `ML_MISSING_DEPS` list, export `HAS_MAPIE` and `get_small_dataset_params`
- **Create** `ml/tuning.py` — `get_small_dataset_params(n_samples)` returns XGBoost hyperparameters tuned for dataset size (<1000, <3000, >=3000)
- **Update** `ml/train_models.py`:
  - Import and use `get_small_dataset_params()` in `train()`
  - Add `train_with_intervals()` method using MAPIE's `CrossConformalRegressor`
  - Add `predict_with_intervals()` method returning lower/upper bounds + confidence level
  - Handle MAPIE model saving/loading alongside base model
  - Add `get_model_info()` method for metadata retrieval
- **Update** `requirements.txt` — add `mapie>=1.3.0`, upgrade `scikit-learn>=1.4.0`
- **Update** `tests/unit/test_ml_models.py` — tests for import failure scenarios, `ML_AVAILABLE`/`ML_MISSING_DEPS` flags, model versioning, `get_model_info()`

### 1.3 Database schema extensions
- **Update** `golf_db.py` `init_db()`:
  - Add `model_predictions` table (predicted_carry, actual_carry, absolute_error, session_id, timestamp)
  - Add `model_performance` table (session_id, mae, baseline_mae, is_drift, timestamp)
  - Add `sync_status` table if needed for UI component
- **Update** `golf_db.py`:
  - Add `get_filtered_shots(quality_level, exclude_warmup)` — filter by `shots_clean`/`shots_strict` views and warmup status
  - Add `get_total_shot_count()` — total unfiltered shots
  - Add `update_session_metrics()` — compute and store session aggregates (called after `save_shot()` and `delete_shot()`)
  - Integrate `get_logger()` for structured logging (replace `print()` statements)

### 1.4 Monitoring infrastructure
- **Create** `ml/monitoring/__init__.py` — exports `DriftDetector`, `PerformanceTracker`, `check_and_trigger_retraining` with graceful degradation
- **Create** `ml/monitoring/drift_detector.py`:
  - `DriftDetector` class: compute session MAE, compare against adaptive baseline (median of last 20 sessions), track consecutive drift sessions
  - `check_and_trigger_retraining()` module function: check drift, optionally trigger retrain if 3+ consecutive drift sessions
- **Create** `ml/monitoring/performance_tracker.py`:
  - `PerformanceTracker` class: `log_prediction()` to record predicted vs actual carry to `model_predictions` table
  - Methods to retrieve session-specific or historical prediction data
- **Create** `tests/unit/test_monitoring.py` — tests for prediction logging, error computation, sentinel handling, drift detection, baseline building, consecutive drift, retraining recommendations
- **Hook into `golf_db.py`**: Lazy-import and call `PerformanceTracker.log_prediction()` in `save_shot()` and `DriftDetector.check_session_drift()` in `update_session_metrics()` (non-blocking)

### 1.5 Coaching ML modules
- **Create** `ml/coaching/__init__.py` — exports `PracticePlanner`, `PracticePlan`, `Drill`, `WeaknessMapper` with graceful degradation
- **Create** `ml/coaching/practice_planner.py`:
  - `Drill` and `PracticePlan` dataclasses
  - `PracticePlanner` with curated `DRILL_LIBRARY` (14 drills across 8 weakness categories)
  - `generate_plan()` method based on detected weaknesses or pre-computed list
  - Default plan for no-data scenarios
- **Create** `ml/coaching/weakness_mapper.py`:
  - `WeaknessMapper` class detecting 8 weakness types (high dispersion, slice/hook pattern, low smash, inconsistent distance, high/low launch, poor strike)
  - Uses `analytics.utils` for IQR-based metrics
  - Cleans sentinel values (99999) before computation
- **Create** `tests/unit/test_practice_planner.py` — tests for all 8 weakness types, drill selection, plan duration constraints, default plans, graceful degradation

---

## Phase 2: Analytics Components (new components, no page wiring yet)

### 2.1 Dispersion chart component
- **Create** `components/dispersion_chart.py`:
  - `render_dispersion_chart(df, club=None)` — Plotly scatter of side_distance vs carry
  - Apply IQR outlier filtering via `analytics.utils`
  - Color-code points by smash factor
  - Display median crosshair lines + key statistics (median carry, IQR, consistency %)

### 2.2 Distance table component
- **Create** `components/distance_table.py`:
  - `render_distance_table(df)` — table of true club distances using median + IQR
  - Sort by median carry descending
  - Include confidence level column based on sample size
  - Interpretation guide explaining IQR methodology

### 2.3 Miss tendency component
- **Create** `components/miss_tendency.py`:
  - `render_miss_tendency(df, club=None)` — D-plane shot shape analysis
  - Classify shots as straight/draw/fade/hook/slice using face_to_path
  - Horizontal bar chart of shape percentages
  - Coaching tips for dominant miss pattern
  - D-plane theory educational section

### 2.4 Progress tracker component
- **Create** `components/progress_tracker.py`:
  - `render_progress_tracker(df)` — session-over-session trend analysis
  - Statistical significance via `scipy.stats.linregress`
  - Color-coded trend lines (green=improving, red=declining, gray=stable)
  - Contextual messages based on trend direction + significance

### 2.5 Session quality component
- **Create** `components/session_quality.py`:
  - `render_session_quality(df)` — composite quality score (0-100)
  - Weighted components: consistency (40%), performance (35%), improvement (25%)
  - Detailed breakdown with progress bars
  - Actionable coaching tips based on weakest component

### 2.6 ML-specific components
- **Create** `components/prediction_interval.py`:
  - `render_prediction_interval(prediction, lower, upper, confidence)` — Plotly horizontal line + marker
  - Shows point estimate, lower/upper bounds, confidence level
  - Fallback message when intervals unavailable
- **Create** `components/retraining_ui.py`:
  - `render_retraining_ui()` — model management panel
  - Current model info (version, trained date, MAE)
  - Retrain button with progress feedback
  - Prediction tester with interactive sliders + interval visualization
- **Create** `components/model_health.py`:
  - `render_model_health_dashboard()` — model monitoring panel
  - Current model status badges
  - Drift alerts with retraining option
  - MAE trend chart (line plot over sessions)
  - Feature importance bar chart
  - Performance history table
  - Graceful degradation for missing ML deps or data
- **Create** `components/sync_status.py`:
  - `render_sync_status()` — cloud sync health indicator
  - Color-coded badges (synced/pending/error/offline)
  - Last sync timestamp + error details

### 2.7 Update components/__init__.py
- Add imports/exports for all 8 new components: `render_dispersion_chart`, `render_distance_table`, `render_miss_tendency`, `render_progress_tracker`, `render_session_quality`, `render_prediction_interval`, `render_retraining_ui`, `render_model_health_dashboard`, `render_sync_status`

---

## Phase 3: Page Integration & Coaching Enhancement

### 3.1 Update local_coach.py
- Replace template-based club stats with analytics-driven responses citing median carry, dispersion IQR, shot shape percentages (using `analytics.utils` and `components.miss_tendency`)
- Add `practice_plan` intent pattern to `INTENT_PATTERNS`
- Add `get_practice_plan()` method using `PracticePlanner` + `WeaknessMapper`
- Add handler to format structured plans into `CoachResponse`
- Enhance `predict_distance()` to include prediction intervals (lower/upper/confidence) when MAPIE model available
- Graceful degradation for all new imports
- **Update** `tests/unit/test_local_coach.py` — tests for analytics-driven responses, practice plan integration, prediction interval integration

### 3.2 Update local_provider
- **Update** `services/ai/providers/local_provider.py` — pass through practice plan data in `CoachResponse.data` dict for visual rendering

### 3.3 Dashboard page updates
- **Update** `pages/1_📊_Dashboard.py` (note: actual filename may differ):
  - Add new "Shot Analytics" tab (tab4) with `render_dispersion_chart`, `render_distance_table`, `render_miss_tendency`, `render_session_quality`
  - Add club selector dropdown in Shot Analytics tab
  - Add `render_progress_tracker` to existing Trends tab
  - Add sidebar controls: warmup checkbox toggle, quality filter dropdown (All/Clean/Strict)
  - Add `render_sync_status()` to sidebar

### 3.4 AI Coach page updates
- **Update** `pages/3_🤖_AI_Coach.py` (note: actual filename may differ):
  - Add "ML Model" sidebar section with model status + manage button
  - Add `render_retraining_ui` and `render_prediction_interval` integration
  - Enhance chat response handler to visually render practice plans via `st.expander`
  - Add warmup checkbox + quality filter dropdown to sidebar
  - Update suggested questions to include practice plan and prediction interval prompts

### 3.5 Model Health page
- **Create** `pages/5_🔬_Model_Health.py` — new standalone page rendering `render_model_health_dashboard()`

### 3.6 Other page updates
- **Update** Data Import page — add `render_sync_status()` to sidebar
- **Update** Database Manager page — add `render_sync_status()` to sidebar (keep showing all 2,141 shots unfiltered)

### 3.7 Update app.py
- Add `get_filtered_shots_cached()` function (Streamlit cached)
- Update landing page metrics to display "Analytics-Ready Shots" based on filtered data

---

## Phase 4: Data Quality Framework & Polish

### 4.1 Data quality SQL migration
- **Create** `supabase_quality_migration.sql`:
  - Add `is_warmup` column to `shots` table
  - Create `shot_quality_flags` table with RLS
  - Define `shots_clean` and `shots_strict` views

### 4.2 Quality sync script
- **Create** `sync_quality_flags.py` — CLI to push `shot_quality_flags` and `is_warmup` from SQLite to Supabase (with dry-run support)

### 4.3 Naming conventions expansion
- **Update** `automation/naming_conventions.py` — expand `CLUB_PATTERNS` and `CLUB_EXTRACTION_PATTERNS` for additional Uneekor-specific formats (M-prefixed, iron+context compound, reversed, bare numbers, degree-based wedges)

### 4.4 Logging integration
- **Update** `utils/logging_config.py` if needed — ensure `get_logger()` writes to both console and `logs/golfdata.log`

### 4.5 Configuration updates
- **Update** `.gitignore` — add `.worktrees/`, `data_quality_report.csv`, `data_quality_summary.json`
- **Update** `CLAUDE.md` — document new data quality framework, commands, schema additions
- **Update** CI if needed — add `py_compile` checks for new files

---

## File Creation/Modification Summary

### New files (24):
| File | Phase |
|------|-------|
| `analytics/__init__.py` | 1.1 |
| `analytics/utils.py` | 1.1 |
| `ml/tuning.py` | 1.2 |
| `ml/monitoring/__init__.py` | 1.4 |
| `ml/monitoring/drift_detector.py` | 1.4 |
| `ml/monitoring/performance_tracker.py` | 1.4 |
| `ml/coaching/__init__.py` | 1.5 |
| `ml/coaching/practice_planner.py` | 1.5 |
| `ml/coaching/weakness_mapper.py` | 1.5 |
| `components/dispersion_chart.py` | 2.1 |
| `components/distance_table.py` | 2.2 |
| `components/miss_tendency.py` | 2.3 |
| `components/progress_tracker.py` | 2.4 |
| `components/session_quality.py` | 2.5 |
| `components/prediction_interval.py` | 2.6 |
| `components/retraining_ui.py` | 2.6 |
| `components/model_health.py` | 2.6 |
| `components/sync_status.py` | 2.6 |
| `pages/5_🔬_Model_Health.py` | 3.5 |
| `supabase_quality_migration.sql` | 4.1 |
| `sync_quality_flags.py` | 4.2 |
| `tests/unit/test_analytics_utils.py` | 1.1 |
| `tests/unit/test_monitoring.py` | 1.4 |
| `tests/unit/test_practice_planner.py` | 1.5 |

### Modified files (16):
| File | Phase | Changes |
|------|-------|---------|
| `ml/__init__.py` | 1.2 | Replace lazy loading with explicit try/except |
| `ml/train_models.py` | 1.2 | Add MAPIE intervals, tuning, model info |
| `requirements.txt` | 1.2 | Add mapie, upgrade scikit-learn |
| `golf_db.py` | 1.3 | New tables, filtered queries, logging |
| `local_coach.py` | 3.1 | Analytics-driven responses, practice plans, intervals |
| `services/ai/providers/local_provider.py` | 3.2 | Pass through practice plan data |
| `components/__init__.py` | 2.7 | Export new components |
| `pages/1_📊_Dashboard.py` or `pages/2_📊_Dashboard.py` | 3.3 | Shot Analytics tab, quality filters |
| `pages/3_🤖_AI_Coach.py` or `pages/4_🤖_AI_Coach.py` | 3.4 | ML model section, retraining UI |
| `pages/1_📥_Data_Import.py` | 3.6 | Sync status sidebar |
| `pages/3_🗄️_Database_Manager.py` or `pages/4_⚙️_Settings.py` | 3.6 | Sync status sidebar |
| `app.py` | 3.7 | Filtered shots cache, analytics-ready metric |
| `automation/naming_conventions.py` | 4.3 | Expanded patterns |
| `.gitignore` | 4.5 | New exclusions |
| `CLAUDE.md` | 4.5 | Documentation updates |
| `tests/unit/test_ml_models.py` | 1.2 | Import failure, versioning tests |
| `tests/unit/test_local_coach.py` | 3.1 | Analytics, plans, intervals tests |

---

## Dependency Graph

```
Phase 1.1 (analytics/utils) ─────────────────────────────┐
Phase 1.2 (ML restructuring + MAPIE) ────┐               │
Phase 1.3 (DB schema) ──────────────────┐│               │
Phase 1.4 (monitoring) ←── 1.2, 1.3    ││               │
Phase 1.5 (coaching) ←── 1.1           ││               │
                                        ││               │
Phase 2.* (components) ←── 1.1, 1.2    ││               │
                                        ↓↓               ↓
Phase 3.* (pages) ←── Phase 2.*, 1.3, 1.4, 1.5
Phase 4.* (quality framework) ←── 1.3
```

## Risk Areas & Mitigations

1. **MAPIE compatibility** — MAPIE requires scikit-learn>=1.4.0. If incompatible with current xgboost version, wrap in try/except and set `HAS_MAPIE=False`. All interval features degrade gracefully.

2. **Database migrations** — New tables added via `init_db()` using `CREATE TABLE IF NOT EXISTS`. Existing databases get new tables on next app start. No destructive changes.

3. **Import cycles** — `ml/coaching/weakness_mapper.py` imports from `analytics.utils` and `components.miss_tendency`. Ensure these are functions, not Streamlit-dependent components. If miss_tendency uses `st.*`, extract pure logic into a separate function.

4. **Test count target** — Plan targets 78 new tests across 7 files to reach 208+ total (9 expected ML-dep skips in envs without xgboost/mapie).

5. **Page numbering** — Current pages use emoji prefixes with numbers. The new Model Health page at `pages/5_🔬_Model_Health.py` follows this pattern. Need to verify existing page numbers don't conflict (current: 1=Dashboard, 2=Club Profiles, 3=AI Coach, 4=Settings).
