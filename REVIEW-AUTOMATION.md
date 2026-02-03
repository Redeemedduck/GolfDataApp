# Automation Review Findings

Scope: `automation/` and `automation_runner.py`.

## Critical
- None found.

## High
- None found.

## Medium
- `automation/notifications.py:139-146` — Rate-limit window calculation uses `datetime.replace(...)` instead of subtracting a real timedelta. At midnight (or across day boundaries) this can make the “last hour” window incorrect, allowing too many notifications or suppressing legitimate ones. Prefer `now - timedelta(hours=1)` for a correct rolling window.
- `automation/backfill_runner.py:72-73, 191-194` — `BackfillConfig.max_sessions_per_hour` is never applied to the `RateLimiter`. The runner always uses `get_backfill_limiter()` defaults (10 req/min) regardless of user configuration, which can unintentionally exceed intended limits. Consider constructing a limiter from config or mapping this setting to the limiter.

## Low
- `automation/backfill_runner.py:532-538` — Dry-run mode increments `sessions_imported` and returns success without updating the DB. This makes results look like real imports and can mislead operators. Consider incrementing a “skipped/dry-run” counter or leaving counters untouched.
- `automation/session_discovery.py:380-388` — `ImportQueueItem.attempts` is hard-coded to 0 even though `attempt_count` exists in the schema. This produces incorrect retry/attempt reporting (e.g., in CLI output). Populate it from `row['attempt_count']` when available.
- `automation/credential_manager.py:22-23` — Unused imports (`base64`, `hashlib`) add noise and can confuse readers.
- `automation/credential_manager.py:301-327` — `ensure_gitignore_entries()` runs on module import and mutates `.gitignore`. That side effect is surprising in production/runtime contexts (and can fail in read-only environments). Consider moving it to a CLI/setup path instead.
- `automation/credential_manager.py:102-112` — Encryption key is persisted in `.uneekor_key` next to the encrypted cookie file. If the project directory is shared or backed up, the key and cookies can be exfiltrated together, reducing the value of encryption. Consider requiring the key via environment variables in production or storing it outside the repo tree.
- `automation_runner.py:112-114, 265-266` — Date parsing for `--since`, `--start`, and `--end` lacks error handling. Invalid inputs crash the CLI with a stack trace instead of a user-friendly error message.

## Notes
- No automated tests were run; this was a static review only.
