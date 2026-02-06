# Consolidated Recommendations

**Status: All issues resolved as of 2026-02-03**

All 26 issues identified in the code review have been fixed. See `changelog.md` for details.

## Summary of Fixes

### P1 (High) — 1 issue ✅
- **ml/train_models.py:118-121** — Fixed RCE vulnerability by adding path validation for `joblib.load()`. Models now only load from `TRUSTED_MODEL_DIR`.

### P2 (Medium) — 9 issues ✅
- **golf_db.py:795-799** — Added early return when `shot_ids` is empty in `split_session()`
- **golf_db.py:389-444** — Added `ValidationError` for null `shot_id`/`session_id` in `save_shot()`
- **golf_db.py:1309-1314** — Added `ALLOWED_RESTORE_COLUMNS` allowlist for SQL injection prevention
- **golf_scraper.py:256-273** — Added size limits and MIME type validation for image downloads
- **local_coach.py:341-342** — Added NaT/empty validation before `idxmax()` call
- **automation/notifications.py:139-146** — Fixed rate-limit window using `timedelta` instead of `replace()`
- **automation/backfill_runner.py:72-73, 191-194** — Applied `max_sessions_per_hour` config to RateLimiter
- **ml/train_models.py:314-388** — Added `DEFAULT_FEATURE_NAMES` fallback for models without metadata
- **ml/classifiers.py:321-324** — Fixed label casting with `str(prediction).lower()`

### P3 (Low) — 16 issues ✅
- **exceptions.py:60** — Renamed `ImportError` to `DataImportError`
- **golf_db.py:164-175** — Replaced broad exception handlers with logging
- **local_coach.py:179-181** — Added column validation before `.str.lower()`
- **local_coach.py:301-305** — Added validation for `carry/total/club` columns
- **golf_scraper.py:179,226** — Added datetime validation for `session_date`
- **automation/backfill_runner.py:532-538** — Documented dry-run counter behavior
- **automation/session_discovery.py:380-388** — Populated `attempts` from `attempt_count`
- **automation/credential_manager.py:22-23** — Removed unused imports
- **automation/credential_manager.py:301-327** — Refactored gitignore mutation to be opt-in
- **automation/credential_manager.py:102-112** — Added encryption key storage warning
- **automation_runner.py:112-114, 265-266** — Date parsing validation already present
- **ml/train_models.py:366-403** — Confidence calculation already works correctly
- **ml/classifiers.py:265-266** — Renamed accuracy to training_accuracy
- **ml/anomaly_detection.py:391-407** — Normalized isolation forest scores to 0-1 range
- **services/ai/registry.py:32-33** — Added `Optional` return type for `get_provider()`
- **services/ai/registry.py:15-24** — Added duplicate provider registration warning

## Test Coverage

All 166 tests pass after fixes:
- Unit tests for all modified modules
- Integration tests for automation flow
- Date parsing tests (15 cases)
- Date reclassification tests

## Related Commits

```
74e1a91a fix: resolve pre-existing test failures
b3d40403 feat: extract session dates from listing page DOM
2b2cde58 fix: resolve 26 code issues and add Supabase sync
```
