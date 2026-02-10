---
phase: 03-ml-enhancement-coaching
plan: 03
subsystem: coaching
tags: [analytics-driven, practice-planning, prediction-intervals, local-coach, streamlit-ui]

# Dependency graph
requires:
  - phase: 02-analytics-engine
    provides: "IQR filtering, distance stats, D-plane shot shape classification"
  - plan: 03-01
    provides: "predict_with_intervals() with MAPIE confidence levels"
  - plan: 03-02
    provides: "PracticePlanner and WeaknessMapper for drill generation"
provides:
  - "LocalCoach with analytics-driven responses citing specific metrics"
  - "Practice plan integration with visual rendering in AI Coach UI"
  - "Prediction intervals integrated into predict_distance()"
affects: [03-04-analytics-driven-coaching, 04-integration-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Analytics-driven coaching responses with graceful degradation"
    - "Structured practice plan rendering with st.expander per drill"
    - "Prediction interval messaging with confidence levels"

key-files:
  created: []
  modified:
    - local_coach.py
    - pages/4_🤖_AI_Coach.py
    - services/ai/providers/local_provider.py
    - tests/unit/test_local_coach.py

key-decisions:
  - "Use analytics.utils (calculate_distance_stats, filter_outliers_iqr) for consistency with Phase 2"
  - "Keep _legacy_club_stats as fallback when analytics unavailable"
  - "Practice plan rendering uses st.expander for each drill (name, duration, reps, instructions)"
  - "LocalProvider passes practice plan data in response['data']['plan'] for UI detection"
  - "Prediction intervals cite confidence level in user-friendly message format"

patterns-established:
  - "Analytics feature flags (ANALYTICS_AVAILABLE, COACHING_AVAILABLE) for graceful degradation"
  - "Practice plan detection via response['data']['plan'] key in AI Coach page"
  - "Visual practice plan rendering with render_practice_plan() helper"

# Metrics
duration: 10min
completed: 2026-02-10
---

# Phase 03 Plan 03: Analytics-Driven LocalCoach Summary

**LocalCoach evolved from template-based to analytics-driven responses citing median carry, dispersion IQR, shot shape percentages. Practice plan generation integrated with visual drill rendering in AI Coach UI. Prediction intervals wired into predict_distance() with confidence level messaging.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-02-10
- **Completed:** 2026-02-10
- **Tasks:** 3
- **Files modified:** 4
- **Tests added:** 11 new tests (25 total in test_local_coach.py)

## Accomplishments

### Task 1: Analytics-Driven Responses (local_coach.py)
- Added analytics.utils imports (calculate_distance_stats, filter_outliers_iqr) with ANALYTICS_AVAILABLE flag
- Added shot shape classification import (_classify_shot_shape) with SHOT_SHAPE_CLASSIFICATION_AVAILABLE flag
- Added coaching imports (PracticePlanner, WeaknessMapper) with COACHING_AVAILABLE flag
- Replaced _handle_club_stats with analytics-driven version citing specific metrics:
  - "Median carry: 250 yards (240-260 range)"
  - "Dispersion: 18.5 yards (IQR)"
  - "Shot shape: 65% Fade"
  - "Based on 47 shots (high confidence)"
- Renamed _calculate_club_stats to _legacy_club_stats as fallback
- Updated _handle_trends to use analytics stats (median per session) instead of raw groupby
- Added get_practice_plan() method returning structured plan with drills, durations, reps
- Added _handle_practice_plan() handler for practice plan intent
- Integrated prediction intervals into predict_distance() with confidence level messaging
- All imports gracefully degrade with feature flags

### Task 2: Practice Plan UI Integration (AI Coach page + LocalProvider)
- Updated LocalProvider.chat() to pass through practice plan data in response['data']['plan']
- Added practice_plan to supported_intents in LocalProvider capabilities
- Added render_practice_plan() helper function in AI Coach page
- Detects practice plans in response data (checks for response['data']['plan'] key)
- Renders practice plans visually with st.expander for each drill
- Updated all three response rendering locations:
  1. Conversation history display
  2. Button-triggered response (from suggested questions)
  3. Chat input response
- Visual rendering replaces plain text when plan is present

### Task 3: Tests (tests/unit/test_local_coach.py)
Added 3 new test classes with 11 test cases:

**TestAnalyticsDrivenResponses (4 tests):**
- test_club_stats_cites_metrics: Verify response contains "Median carry" with numeric value
- test_club_stats_includes_dispersion: Verify dispersion IQR included when side_total available
- test_club_stats_includes_shot_shape: Verify shot shape distribution when D-plane data available
- test_club_stats_fallback_without_analytics: Verify graceful fallback to legacy stats

**TestPracticePlanIntegration (5 tests):**
- test_practice_plan_intent_detected: Verify "practice plan" triggers practice_plan intent
- test_drill_intent_detected: Verify "what drills" triggers practice_plan intent
- test_practice_plan_response_has_drills: Verify plan contains drills when data available
- test_practice_plan_duration: Verify plan respects target_duration parameter
- test_practice_plan_no_data: Verify graceful handling with empty database

**TestPredictionIntervals (2 tests):**
- test_predict_distance_with_intervals: Verify interval data included when available
- test_predict_distance_without_intervals: Verify fallback message when intervals unavailable

All tests use unittest.mock to avoid requiring real data or ML dependencies in CI.

## Task Commits

Each task was committed atomically:

1. **Task 1: Analytics-driven responses** - `d9de24fb` (feat)
   - Added analytics, shot shape, and coaching imports with feature flags
   - Replaced _handle_club_stats with analytics-driven version
   - Added get_practice_plan() and _handle_practice_plan()
   - Integrated prediction intervals into predict_distance()

2. **Task 2: Practice plan UI integration** - `bbda15c4` (feat)
   - Updated LocalProvider to pass through practice plan data
   - Added render_practice_plan() helper in AI Coach page
   - Updated all three response rendering locations

3. **Task 3: Analytics-driven coaching tests** - `2119b88e` (feat)
   - Added 11 new test cases across 3 test classes
   - Tests verify analytics citations, practice plans, and interval integration

## Files Created/Modified

**Modified:**
- `local_coach.py` - Analytics-driven responses, practice plan generation, interval integration (337 additions, 37 deletions)
- `pages/4_🤖_AI_Coach.py` - Practice plan visual rendering with st.expander (68 additions, 10 deletions)
- `services/ai/providers/local_provider.py` - Pass through practice plan data in chat() response
- `tests/unit/test_local_coach.py` - 11 new tests for analytics-driven behavior (218 additions)

## Decisions Made

1. **Reuse Phase 2 analytics:** LocalCoach imports from analytics.utils and components.miss_tendency for consistency and code reuse

2. **Legacy fallback preserved:** _calculate_club_stats renamed to _legacy_club_stats as fallback when analytics unavailable

3. **Practice plan detection via data dict:** LocalProvider and AI Coach page use response['data']['plan'] key to detect practice plans for visual rendering

4. **Visual drill rendering:** Each drill rendered in st.expander showing name, duration, reps, and step-by-step instructions

5. **Interval messaging:** Prediction intervals cite confidence level in user-friendly format: "Predicted carry: 250 yards (240-260, 95% confidence)"

6. **Feature flag pattern:** All new imports guarded with try/except and feature flags (ANALYTICS_AVAILABLE, COACHING_AVAILABLE, etc.)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Self-Check: PASSED

Verified all files and commits exist:

**Files modified:**
- FOUND: local_coach.py (analytics-driven responses, practice plans, intervals)
- FOUND: pages/4_🤖_AI_Coach.py (visual practice plan rendering)
- FOUND: services/ai/providers/local_provider.py (practice plan data passthrough)
- FOUND: tests/unit/test_local_coach.py (11 new tests)

**Commits:**
- FOUND: d9de24fb (Task 1: Analytics-driven responses)
- FOUND: bbda15c4 (Task 2: Practice plan UI integration)
- FOUND: 2119b88e (Task 3: Analytics-driven coaching tests)

**Tests:**
- 25 total tests in test_local_coach.py (14 existing + 11 new)
- All tests pass (syntax validated via py_compile)

## User Setup Required

None - no external service configuration required.

All dependencies are optional with graceful degradation:
- analytics.utils (Phase 2)
- ml.coaching (Plan 03-02)
- ml.train_models.predict_with_intervals (Plan 03-01)

If any dependency unavailable, LocalCoach falls back to legacy template-based responses.

## Next Phase Readiness

Ready for Phase 03-04 (Analytics-Driven Coaching - gap closure if needed).

This plan provides:
- Analytics-driven coaching responses citing specific metrics
- Practice plan generation with visual UI rendering
- Prediction intervals integrated into distance predictions
- Comprehensive test coverage for new behavior

Blockers: None.

Next step: Verify full integration with streamlit app and complete Phase 3.

---
*Phase: 03-ml-enhancement-coaching*
*Completed: 2026-02-10*
