# Consolidated Recommendations

Grouped by priority (P0=critical, P1=high, P2=medium, P3=low). Each item includes estimated effort and a brief fix description.

## P0 (Critical)
- None identified.

## P1 (High)
- ml/train_models.py:118-121 — **Effort:** medium — `joblib.load` on untrusted paths can enable RCE. Restrict loads to trusted locations, verify file hashes/signatures, or migrate to a safe serialization format.

## P2 (Medium)
- golf_db.py:795-799 — **Effort:** small — `split_session` builds `IN ()` when `shot_ids` is empty. Short-circuit early or guard with a non-empty check before composing SQL.
- golf_db.py:389-444 — **Effort:** medium — `save_shot` accepts null `shot_id`/`session_id`, causing local insert failure while Supabase upsert proceeds. Validate IDs upfront and fail fast with a clear error.
- golf_db.py:1309-1314 — **Effort:** medium — `restore_deleted_shots` builds SQL column lists from archived JSON keys. Whitelist allowed columns and reject/ignore unknown keys before composing SQL.
- golf_scraper.py:256-273 — **Effort:** medium — `upload_shot_images` downloads unbounded remote payloads. Add content-length limits, MIME/type validation, and max size checks.
- local_coach.py:341-342 — **Effort:** small — `_handle_session_analysis` assumes `date_added` has a non-null max; `idxmax()` can raise. Validate column presence and non-NaT values before use.
- automation/notifications.py:139-146 — **Effort:** small — rate-limit window uses `datetime.replace`, which breaks across day boundaries. Use `now - timedelta(hours=1)` for a rolling window.
- automation/backfill_runner.py:72-73, 191-194 — **Effort:** medium — `BackfillConfig.max_sessions_per_hour` isn’t applied to the limiter. Build the `RateLimiter` from config or map the setting explicitly.
- ml/train_models.py:314-388 — **Effort:** small — `DistancePredictor.load()` may leave `_feature_names` unset. Validate metadata and set a default list or raise a clear error before prediction.
- ml/classifiers.py:321-324 — **Effort:** small — `prediction.lower()` assumes string labels. Normalize labels or safely cast to string before lowercasing.

## P3 (Low)
- exceptions.py:60 — **Effort:** small — Custom `ImportError` shadows built-in. Rename to `DataImportError` or similar.
- golf_db.py:164-175 (and similar) — **Effort:** medium — broad `except Exception: pass` silently swallows errors. Replace with explicit handling or logging + rethrow for critical paths.
- local_coach.py:179-181 — **Effort:** small — `_handle_club_stats` assumes `club` column is present and string. Validate column existence and types before `.str.lower()`.
- local_coach.py:301-305 — **Effort:** small — `get_club_comparison` assumes `carry/total/club` columns exist. Add validation and graceful fallback/error.
- golf_scraper.py:179,226 — **Effort:** small — `session_date` assumed to be `datetime`. Validate input or coerce/parse before `.isoformat()`.
- automation/backfill_runner.py:532-538 — **Effort:** small — dry-run increments `sessions_imported` despite no DB updates. Track a separate dry-run counter or leave counts unchanged.
- automation/session_discovery.py:380-388 — **Effort:** small — `ImportQueueItem.attempts` hard-coded to 0. Populate from `attempt_count` when available.
- automation/credential_manager.py:22-23 — **Effort:** small — remove unused imports (`base64`, `hashlib`).
- automation/credential_manager.py:301-327 — **Effort:** medium — `ensure_gitignore_entries()` runs at import and mutates `.gitignore`. Move to CLI/setup workflow to avoid runtime side effects.
- automation/credential_manager.py:102-112 — **Effort:** medium — encryption key stored beside encrypted cookies. Prefer env-provided key or store outside repo tree in production.
- automation_runner.py:112-114, 265-266 — **Effort:** small — invalid date args crash CLI. Add parsing validation with friendly error messages.
- ml/train_models.py:366-403 — **Effort:** small — `predict()` computes confidence after defaults, always 1.0. Compute confidence from original input completeness.
- ml/classifiers.py:265-266 — **Effort:** small — accuracy reported on training set only. Report validation accuracy or label as training accuracy.
- ml/anomaly_detection.py:391-407 — **Effort:** medium — isolation forest scores unbounded, dominate combined score. Normalize `ml_score` to 0–1 before combining.
- services/ai/registry.py:32-33 — **Effort:** small — `get_provider()` returns `None` despite non-optional type. Use `Optional` or raise on missing.
- services/ai/registry.py:15-24 — **Effort:** small — `register_provider()` overwrites existing IDs silently. Guard or warn on duplicate registration.
- services/ai/providers/local_provider.py:50-60 — **Effort:** medium — markdown interpolation without escaping can enable injection. Escape/sanitize suggestion content before rendering.
