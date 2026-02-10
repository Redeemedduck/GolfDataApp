---
phase: 03-ml-enhancement-coaching
plan: 02
subsystem: coaching
tags: [practice-planning, weakness-detection, analytics-integration, d-plane-theory, iqr-filtering]

# Dependency graph
requires:
  - phase: 02-analytics-engine
    provides: IQR filtering, distance stats, D-plane shot shape classification
provides:
  - WeaknessMapper with 8 weakness detection types
  - PracticePlanner with 10+ curated drills
  - Structured practice plan generation (15-30 min time-bounded)
affects: [03-03-conformal-prediction, 03-04-analytics-driven-coaching]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Analytics-driven weakness detection using Phase 2 utilities
    - Structured drill library with severity-based selection
    - Graceful degradation for missing columns and sentinel values

key-files:
  created:
    - ml/coaching/__init__.py
    - ml/coaching/weakness_mapper.py
    - ml/coaching/practice_planner.py
    - tests/unit/test_practice_planner.py
  modified: []

key-decisions:
  - "WeaknessMapper uses analytics.utils (filter_outliers_iqr, calculate_distance_stats) for consistency"
  - "D-plane shot shape classification reuses _classify_shot_shape from components.miss_tendency"
  - "Drill library stored in-code (not JSON/database) for offline-first simplicity"
  - "Greedy drill selection prioritizes highest severity weaknesses first"
  - "Minimum 5 shots required for weakness detection (statistical reliability)"
  - "Sentinel values (0, 99999) cleaned before all calculations"

patterns-established:
  - "Weakness detection returns Dict[str, float] with severity scores 0.0-1.0"
  - "Practice plans are time-bounded with duration_min tracking"
  - "Drills have name, duration, focus, instructions (step-by-step), reps, and weakness_key"
  - "PracticePlan includes rationale citing detected weaknesses with numbers"

# Metrics
duration: 5min
completed: 2026-02-10
---

# Phase 03 Plan 02: Practice Planner + Weakness Mapper Summary

**Analytics-driven practice planner with 8 weakness types (dispersion, shot shape, smash, distance, launch) and 10+ curated drills**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-10T21:20:06Z
- **Completed:** 2026-02-10T21:25:06Z
- **Tasks:** 2
- **Files created:** 4
- **Tests added:** 24

## Accomplishments
- WeaknessMapper detects 8 weakness types from shot data using Phase 2 analytics (IQR filtering, distance stats, D-plane classification)
- PracticePlanner has 10+ drills across 8 weakness categories with step-by-step instructions
- Structured practice plan generation with time-bounded drills (15-30 min target)
- Graceful degradation for missing columns, sentinel values, and insufficient data
- 24 comprehensive unit tests covering all weakness types and plan generation scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1: Create WeaknessMapper and PracticePlanner with drill library** - `067b5aac` (feat)
2. **Task 2: Add unit tests for weakness detection and practice plan generation** - `63bdc597` (feat)

## Files Created/Modified

**Created:**
- `ml/coaching/__init__.py` - Exports PracticePlanner, PracticePlan, Drill, WeaknessMapper with graceful degradation
- `ml/coaching/weakness_mapper.py` - Detects 8 weakness types using analytics utilities
- `ml/coaching/practice_planner.py` - Generates time-bounded practice plans with curated drill library (10+ drills)
- `tests/unit/test_practice_planner.py` - 24 test cases for weakness detection and plan generation

## Decisions Made

1. **Reuse Phase 2 analytics:** WeaknessMapper imports from `analytics.utils` (filter_outliers_iqr, calculate_distance_stats) and `components.miss_tendency` (_classify_shot_shape) for consistency and code reuse

2. **In-code drill library:** Drill library stored as Python dict (not JSON/database) for offline-first simplicity and easy maintenance

3. **Severity scoring 0.0-1.0:** All weaknesses return normalized severity scores for consistent prioritization

4. **Greedy drill selection:** PracticePlanner selects drills for highest severity weaknesses first until target duration reached

5. **Minimum 5 shots:** All weakness checks require 5+ shots for statistical reliability (prevent false positives)

6. **Sentinel value cleaning:** All calculations clean sentinel values (0, 99999) from Uneekor data before computing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Test data determinism:** Initial test for high_dispersion_detected used `np.random.normal(0, 10, 20)` which didn't guarantee IQR > 15 threshold with seed 42.

**Resolution:** Changed to explicit side_total values that guarantee IQR > 15 for deterministic test behavior.

**Impact:** Test reliability improved; no functional change to implementation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 03-03 (Conformal Prediction):**
- WeaknessMapper provides foundation for analytics-driven coaching responses
- PracticePlanner ready to be integrated into LocalCoach or AI Coach UI
- Drill library extensible for future additions

**Ready for Phase 03-04 (Analytics-Driven Coaching):**
- Weakness detection ready to replace template-based responses
- Practice plan generation provides actionable, data-driven recommendations

**Integration points:**
- LocalCoach can use `PracticePlanner.generate_plan(df)` directly
- AI Coach UI can display PracticePlan with drills, duration, and rationale
- Weakness severity scores can inform coaching response tone

---
*Phase: 03-ml-enhancement-coaching*
*Completed: 2026-02-10*

## Self-Check: PASSED

**Files verified:**
- ✓ ml/coaching/__init__.py
- ✓ ml/coaching/weakness_mapper.py
- ✓ ml/coaching/practice_planner.py
- ✓ tests/unit/test_practice_planner.py

**Commits verified:**
- ✓ 067b5aac (Task 1: WeaknessMapper and PracticePlanner)
- ✓ 63bdc597 (Task 2: Unit tests)

**Tests verified:**
- ✓ 24/24 tests passing
- ✓ No regressions in full test suite (243 tests)
