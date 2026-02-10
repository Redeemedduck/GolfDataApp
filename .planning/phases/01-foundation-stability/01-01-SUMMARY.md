---
phase: 01-foundation-stability
plan: 01
subsystem: ml-module
tags:
  - refactoring
  - imports
  - graceful-degradation
  - feature-flags
dependency_graph:
  requires: []
  provides:
    - ML_AVAILABLE flag for dependency checking
    - ML_MISSING_DEPS list for diagnostics
    - Explicit import error handling
  affects:
    - local_coach.py (now uses ML feature flags)
    - ml/__init__.py (removed __getattr__ lazy loading)
    - tests/unit/test_ml_models.py (added fallback tests)
tech_stack:
  added: []
  patterns:
    - Explicit try/except imports with None fallbacks
    - Feature flags for optional dependencies
    - Defensive instantiation checks
key_files:
  created: []
  modified:
    - ml/__init__.py: Replaced lazy loading with explicit imports
    - local_coach.py: Added ML status checks and get_ml_status() method
    - tests/unit/test_ml_models.py: Added TestMLImportFallback test class
decisions:
  - Use None for unavailable classes rather than raising ImportError
  - Track missing dependencies by parsing ImportError messages
  - LocalCoach checks ML_AVAILABLE in __init__ before loading models
  - get_ml_status() provides user-friendly pip install instructions
metrics:
  duration: 2 minutes 14 seconds
  tasks_completed: 3
  files_modified: 3
  tests_added: 4
  completed_at: 2026-02-10T08:30:07Z
---

# Phase 01 Plan 01: Explicit ML Import Handling Summary

**One-liner:** Replaced fragile `__getattr__` lazy loading with explicit try/except imports and ML_AVAILABLE/ML_MISSING_DEPS feature flags for early error detection.

## Overview

Refactored the ML module's import system from implicit lazy loading (via `__getattr__`) to explicit imports with feature flags. This change surfaces import failures at app startup rather than at feature use time, providing immediate user feedback with actionable error messages.

## What Changed

### 1. ml/__init__.py - Explicit Import Structure
- **Removed:** `__getattr__` lazy loading function (28 lines)
- **Added:** Explicit try/except blocks for each submodule import
- **Added:** `ML_AVAILABLE` boolean flag (True if all imports succeed)
- **Added:** `ML_MISSING_DEPS` list of missing package names
- **Pattern:** Each import block sets exports to None on failure and populates ML_MISSING_DEPS

Import structure:
```python
ML_AVAILABLE = True
ML_MISSING_DEPS = []

try:
    from .train_models import DistancePredictor, train_distance_model, ...
except ImportError as e:
    DistancePredictor = None
    ML_AVAILABLE = False
    ML_MISSING_DEPS.append("xgboost")
```

### 2. local_coach.py - ML Status Integration
- **Changed:** Import from `ml` module (not submodules directly)
- **Changed:** `__init__` checks `ML_AVAILABLE` before calling `_load_ml_models()`
- **Changed:** `ml_available` property returns `ML_AVAILABLE` flag directly
- **Changed:** `_load_ml_models()` adds defensive None checks before instantiation
- **Added:** `get_ml_status()` method returns availability dict with:
  - `available`: bool
  - `missing_deps`: list
  - `message`: user-friendly string with pip install instructions

### 3. tests/unit/test_ml_models.py - Fallback Testing
- **Added:** `TestMLImportFallback` test class (4 tests)
- **Tests:**
  - `test_ml_available_flag_exists` - Flag is accessible and boolean
  - `test_ml_missing_deps_is_list` - Missing deps list is accessible
  - `test_ml_unavailable_when_deps_missing` - Flag is False when deps missing
  - `test_ml_exports_none_when_unavailable` - Classes are None when unavailable

All tests pass in both ML-available and ML-unavailable environments.

## Verification Results

All verification criteria met:

1. **All unit tests pass:** 136 tests pass (51 skipped for missing deps)
2. **ML module imports cleanly:** `import ml` succeeds, prints ML_AVAILABLE status
3. **LocalCoach syntax valid:** `py_compile` succeeds
4. **No `__getattr__` in ml/__init__.py:** grep returns empty (pattern removed)

## Technical Details

### Import Failure Handling
When ML dependencies are missing, the module:
1. Sets all exported classes to None (no AttributeError on access)
2. Sets `ML_AVAILABLE = False`
3. Populates `ML_MISSING_DEPS` with specific package names
4. Parses ImportError messages to identify which packages ("xgboost", "scikit-learn", "joblib")

### Graceful Degradation Path
1. App startup: Import ml module (always succeeds)
2. Check `ML_AVAILABLE` flag
3. If False: Display `get_ml_status()['message']` to user
4. LocalCoach: Skip model loading if `ML_AVAILABLE` is False
5. Feature use: Check if specific classes are None before instantiation

### User Experience Improvement
**Before:** Late runtime errors during feature use
```python
# User clicks "Predict Distance" -> AttributeError: module 'ml' has no attribute 'DistancePredictor'
```

**After:** Early startup detection with guidance
```python
import ml
if not ml.ML_AVAILABLE:
    print(ml.ML_MISSING_DEPS)  # ['xgboost', 'scikit-learn']
    coach = LocalCoach()
    print(coach.get_ml_status()['message'])
    # "ML features unavailable. Install: pip install xgboost, scikit-learn"
```

## Commits

| Task | Commit | Files | Description |
|------|--------|-------|-------------|
| 1 | a02ae787 | ml/__init__.py | Replace lazy loading with explicit imports and feature flags |
| 2 | e520f508 | local_coach.py | Update LocalCoach to use ML_AVAILABLE and add get_ml_status() |
| 3 | ab5d08f4 | tests/unit/test_ml_models.py | Add unit tests for import fallback scenarios |

## Deviations from Plan

None - plan executed exactly as written.

## Impact Assessment

### Before
- Import failures hidden until feature use
- `__getattr__` complexity (dictionary lookups, string matching)
- No visibility into which dependencies are missing
- Poor user experience: cryptic AttributeError messages

### After
- Import failures surface at app startup
- Simple explicit imports (no magic methods)
- Clear visibility: `ML_AVAILABLE` flag, `ML_MISSING_DEPS` list
- Good user experience: actionable pip install instructions

### Risk Reduction
- **Late runtime errors → Early startup errors:** Users know immediately if setup is incomplete
- **Cryptic errors → Actionable guidance:** Error messages include exact pip install commands
- **Silent failures → Explicit status:** get_ml_status() provides diagnostic information

## Next Steps

Plan 01-01 is complete. The ML module now uses explicit imports with feature flags, providing early error detection and user-friendly diagnostics.

Recommended follow-up (from Phase 1 roadmap):
- **Plan 01-02:** Database sync monitoring
- **Plan 01-03:** Model versioning and validation
- **Plan 01-04:** Session metrics table

## Self-Check: PASSED

**Files created:** None (all modifications)

**Files modified:**
- `/Users/max1/Documents/GitHub/GolfDataApp/ml/__init__.py` - EXISTS ✓
- `/Users/max1/Documents/GitHub/GolfDataApp/local_coach.py` - EXISTS ✓
- `/Users/max1/Documents/GitHub/GolfDataApp/tests/unit/test_ml_models.py` - EXISTS ✓

**Commits exist:**
- `a02ae787` - FOUND ✓
- `e520f508` - FOUND ✓
- `ab5d08f4` - FOUND ✓

**Test results:**
- 136 tests pass, 51 skipped (expected for missing ML deps)
- New TestMLImportFallback class: 4 tests pass

All claims verified. Plan execution complete.
