---
phase: 03-ml-enhancement-coaching
plan: 04
subsystem: ui-integration
tags: [retraining-ui, prediction-intervals, streamlit, model-management, visualization]

# Dependency graph
requires:
  - plan: 03-01
    provides: "predict_with_intervals() with MAPIE confidence levels, get_model_info() for metadata"
  - plan: 03-02
    provides: "PracticePlanner and WeaknessMapper (not directly used, but available via LocalCoach)"
  - plan: 03-03
    provides: "Practice plan rendering already in AI Coach page (lines 283-301, 320-322, 396-398)"
provides:
  - "render_prediction_interval() component with Plotly horizontal line visualization"
  - "render_retraining_ui() component with model info, retrain button, prediction tester"
  - "AI Coach page sidebar with ML Model status and Manage Model button"
  - "AI Coach page retraining panel (activated via sidebar button)"
  - "Practice plan and weakness questions in suggested prompts"
affects: [04-integration-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Stateless render_*() component convention for Streamlit UI"
    - "Graceful degradation with try/except for all ML imports"
    - "Session state for retraining panel visibility (show_retrain flag)"
    - "Plotly horizontal line + marker for interval visualization"

key-files:
  created:
    - components/prediction_interval.py
    - components/retraining_ui.py
  modified:
    - components/__init__.py
    - pages/4_🤖_AI_Coach.py

key-decisions:
  - "Use Plotly (not matplotlib) for interval visualization - already in codebase"
  - "Retraining panel appears below chat (not replacing it) - model management is secondary to chat"
  - "Sidebar button activates retraining panel via st.session_state.show_retrain flag"
  - "Model status shows compact info: version, MAE - full details in retraining panel"
  - "Prediction tester included in retraining panel for immediate validation after training"
  - "Practice plan rendering already complete from 03-03 - Task 2 adds retraining/intervals only"

patterns-established:
  - "Pattern 1: Sidebar compact status + main area detailed panel for model management"
  - "Pattern 2: Prediction interval visualization as horizontal line (light blue) + point estimate (blue dot)"
  - "Pattern 3: Graceful degradation messages when intervals/ML not available"

# Metrics
duration: 7min 11sec
completed: 2026-02-10
---

# Phase 03 Plan 04: Retraining UI + Prediction Interval Visualization Summary

**Built Streamlit components for prediction interval visualization (Plotly horizontal line) and model retraining UI (model info + retrain button + prediction tester), then integrated into AI Coach page with sidebar model status and on-demand retraining panel.**

## Performance

- **Duration:** 7 min 11 sec
- **Started:** 2026-02-10T21:45:37Z
- **Completed:** 2026-02-10T21:52:49Z
- **Tasks:** 2
- **Files created:** 2 (components)
- **Files modified:** 2 (components/__init__.py, AI Coach page)

## Accomplishments

### Task 1: Create prediction interval and retraining UI components

**Created `components/prediction_interval.py`:**
- `render_prediction_interval(prediction: dict, club: str = None) -> None`
- Shows point estimate as st.metric with delta (+/- interval_width/2) when intervals available
- Shows confidence interval caption (e.g., "95% confidence interval: 245-260 yards")
- Plotly visualization: horizontal line (light blue, width=8) from lower_bound to upper_bound
- Point estimate marker: blue dot (size=12) at predicted_value
- Graceful fallback: shows point estimate only with explanation when intervals unavailable
- Follows stateless `render_*()` pattern matching existing components

**Created `components/retraining_ui.py`:**
- `render_retraining_ui() -> None`
- Shows current model info: version, trained date, samples, MAE, R² score
- Indicates if intervals enabled (MAPIE model type)
- Retrain button with spinner: trains with `train_with_intervals()` if 1000+ shots and MAPIE available, else `train()`
- Shows success message with MAE, R², samples, training time
- Stores training result in st.session_state for persistence
- Prediction tester expander: sliders for ball_speed, launch_angle, back_spin
- Calls `predict_with_intervals()` if available, else `predict()`
- Renders prediction using `render_prediction_interval()`
- All ML imports guarded with try/except

**Updated `components/__init__.py`:**
- Added imports for `render_prediction_interval` and `render_retraining_ui`
- Added both to `__all__` list

### Task 2: Integrate retraining UI and interval display into AI Coach page

**Updated `pages/4_🤖_AI_Coach.py`:**

1. **Added imports:**
   - `from components import render_retraining_ui`
   - `from ml.train_models import get_model_info, DISTANCE_MODEL_PATH` (with try/except)

2. **Added ML Model section in sidebar (after "Your Data" section):**
   - Shows compact model status: version, MAE if model exists
   - Shows "No model trained" or "ML not available" if not ready
   - "Manage Model" button sets `st.session_state.show_retrain = True`

3. **Added retraining panel in main content area:**
   - Appears below chat interface when `st.session_state.show_retrain` is True
   - Calls `render_retraining_ui()` for full model management
   - Close button clears `show_retrain` flag and reruns

4. **Updated suggested questions:**
   - Added "Generate a personalized practice plan for me"
   - Added "What are my biggest weaknesses?"

5. **Updated help section:**
   - Added "Advanced Features" section with two bullets:
     - Prediction Intervals: Ask "Predict my 7-iron distance" for predictions with confidence intervals
     - Practice Plans: Ask "Give me a practice plan" for personalized drill plans

**Note:** Practice plan rendering was already implemented by plan 03-03 (lines 283-301, 320-322, 396-398). Task 2 added retraining/interval features without duplicating practice plan work.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create prediction interval and retraining UI components** - `81f82920` (feat)
   - Created components/prediction_interval.py with Plotly visualization
   - Created components/retraining_ui.py with model info, retrain button, prediction tester
   - Updated components/__init__.py to export both components
   - All ML imports guarded with try/except for graceful degradation

2. **Task 2: Integrate retraining UI and interval display into AI Coach page** - `d7da4be9` (feat)
   - Added ML Model section in sidebar with model status
   - Added retraining panel in main area (activated via sidebar button)
   - Added practice plan and weakness questions to suggested prompts
   - Updated help section with Prediction Intervals and Practice Plans info
   - Existing chat flow and practice plan rendering unchanged

## Files Created/Modified

**Created:**
- `components/prediction_interval.py` - Plotly horizontal line visualization for intervals (107 lines)
- `components/retraining_ui.py` - Model management UI with retrain button and prediction tester (267 lines)

**Modified:**
- `components/__init__.py` - Export new components (+2 imports, +2 exports)
- `pages/4_🤖_AI_Coach.py` - ML Model sidebar section + retraining panel + updated prompts/help (+52 lines)

## Decisions Made

1. **Plotly over matplotlib:** Use plotly.graph_objects for interval visualization - already in codebase, no new dependency.

2. **Retraining panel placement:** Appears below chat interface (not replacing it). Model management is secondary to chat functionality. Activated via sidebar button for clean default UI.

3. **Sidebar compact status:** Show minimal model info in sidebar (version, MAE). Full details in retraining panel. Keeps sidebar uncluttered.

4. **Session state for visibility:** Use `st.session_state.show_retrain` flag to control retraining panel visibility. Allows user to open/close without losing chat context.

5. **Prediction tester included:** Add prediction tester in retraining panel for immediate validation after training. Uses sliders for ball_speed, launch_angle, back_spin.

6. **Practice plan rendering preservation:** Plan 03-03 already implemented practice plan visual rendering with st.expander per drill. Task 2 adds retraining/interval features without touching practice plan code.

## Deviations from Plan

None - plan executed exactly as written.

Plan correctly noted that practice plan rendering was already complete from 03-03. Task 2 focused solely on retraining UI and interval display as specified.

## Issues Encountered

None.

## Self-Check: PASSED

Verified all files and commits exist:

**Files created:**
- FOUND: components/prediction_interval.py (render_prediction_interval with Plotly visualization)
- FOUND: components/retraining_ui.py (render_retraining_ui with model info, retrain button, prediction tester)

**Files modified:**
- FOUND: components/__init__.py (exports both new components)
- FOUND: pages/4_🤖_AI_Coach.py (sidebar ML Model section, retraining panel, updated prompts/help)

**Commits:**
- FOUND: 81f82920 (Task 1: prediction interval and retraining UI components)
- FOUND: d7da4be9 (Task 2: integrate into AI Coach page)

**Compilation:**
- All files compile successfully: components/prediction_interval.py, components/retraining_ui.py, components/__init__.py, pages/4_🤖_AI_Coach.py

**Tests:**
- 207 tests run (same as before - no regressions)
- 8 errors are expected (missing numpy/pandas in CI environment)
- 91 skipped (expected for optional dependencies)
- No new test failures introduced

## User Setup Required

None - no external service configuration required.

All dependencies are optional with graceful degradation:
- MAPIE for confidence intervals (optional, fallback to point estimates)
- ML dependencies for model training (XGBoost, scikit-learn, joblib)
- If missing, UI shows install instructions

## Next Phase Readiness

Phase 3 (ML Enhancement & Coaching) is now **COMPLETE**.

This plan (03-04) was the final plan in Phase 3. All 4 plans executed successfully:
- Plan 03-01: MAPIE prediction intervals + XGBoost tuning ✅
- Plan 03-02: Practice planner + weakness mapper ✅
- Plan 03-03: Analytics-driven LocalCoach ✅
- Plan 03-04: Retraining UI + interval visualization ✅

Ready for Phase 04 (Integration & Verification).

Blockers: None.

---
*Phase: 03-ml-enhancement-coaching*
*Completed: 2026-02-10*
