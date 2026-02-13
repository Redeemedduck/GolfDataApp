# PR #14 Bug Fixes Design

**Date:** 2026-02-13
**Scope:** 4 targeted fixes for session classification engine bugs found during code review

## Bugs

### 1. Fitting category unreachable
**File:** `automation/naming_conventions.py` - `SessionClassifier.classify()`
**Bug:** Drill check (`num_unique <= 2 and total >= 20`) fires before fitting check (`num_unique == 1 and total >= 50`), making fitting unreachable for 1-club sessions.
**Fix:** Move fitting check before drill check. Tighten test assertion.

### 2. NULL session_category leaks through filter
**File:** `golf_db.py` - `get_shots_by_category()`
**Bug:** `~isin(exclude_categories)` doesn't filter NaN rows. Unclassified sessions pass through as "practice".
**Fix:** Add `df['session_category'].notna()` filter when exclude_categories is used.

### 3. DB connection leak
**File:** `golf_db.py` - `classify_all_sessions()`
**Bug:** No try/finally around connection. Exceptions leave connection open.
**Fix:** Wrap in try/finally so `conn.close()` always runs.

### 4. session_breakdown intent unreachable
**File:** `local_coach.py` - `INTENT_PATTERNS`
**Bug:** `session_analysis` (`\bsession\b`) matches before `session_breakdown` (`\bsession\s*type\b`). Queries like "show session types" route to wrong handler.
**Fix:** Move `session_breakdown` before `session_analysis` in the dict.

## Approach
- Fix on current branch (`claude/review-ml-implementation-plan-eaach`)
- Single commit with all 4 fixes
- ~15 lines of code changes total
