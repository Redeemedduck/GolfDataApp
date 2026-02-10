# Codebase Concerns

**Analysis Date:** 2026-02-09

## Tech Debt

### Rate Limiter Configuration Bug (CRITICAL)

**Files:** `automation/backfill_runner.py` (line 200)

**Issue:** The `BackfillRunner` incorrectly passes `max_sessions_per_hour` directly to `requests_per_minute` parameter of `RateLimiter`:

```python
# WRONG (line 200):
self.rate_limiter = RateLimiter(RateLimiterConfig(
    requests_per_minute=self.config.max_sessions_per_hour,  # BUG: mixing units!
))
```

**Impact:** With default `max_sessions_per_hour=6`:
- Intended: 6 requests per hour (1 every 10 minutes)
- Actual: 6 requests per minute (360/hour) — **60x faster than intended**
- Result: Portal rate limits triggered, backfill fails or gets IP blocked

**Fix approach:** Divide by 60 to convert hours to minutes:
```python
requests_per_minute=self.config.max_sessions_per_hour / 60
```

### Pagination Not Fully Implemented (Status: UNCLEAR)

**Files:** `automation/uneekor_portal.py` (lines 154-230)

**Issue:** Documentation in `docs/UNEEKOR_REPORT_PAGE_MAP.md` (2026-01-26) reports critical pagination bug where only page 1 of 8 was being scraped. The code appears to have pagination logic now (lines 243-260 show `_find_pagination_button`), but it's unclear if:
1. The fix was already applied
2. The pagination is fully tested
3. All 80 sessions are being discovered

**Impact:** If not working: 50 sessions remain undiscovered in the portal (only 30 of 80 in DB)

**Fix approach:** Run discovery with verbose logging and verify all 8 pages are visited. Add integration test that validates session count across pagination.

---

## Known Bugs

### Image Loading Failures

**Files:** `golf_scraper.py`, `pages/1_📥_Data_Import.py`

**Symptoms:** Some shots show "No images available" even when URLs exist in database

**Root cause:** Unclear, possibly:
- Image URL expiration (Uneekor URLs time out)
- Download failures not logged
- Cache invalidation issues

**Current mitigation:** None visible

**Recommendation:** Add retry logic with exponential backoff for image downloads; log failed URLs for debugging

### Session Selector Cache Invalidation

**Files:** `pages/3_🗄️_Database_Manager.py`

**Symptoms:** Session dropdown doesn't refresh after delete operation until manual page refresh

**Root cause:** Streamlit cache not cleared after database modification

**Fix:** Add `st.rerun()` after successful session deletion to force cache clear

### Smash Factor Showing 0.0

**Files:** `golf_db.py` (lines 22-26)

**Symptoms:** Smash factor (ball_speed / club_speed) shows 0.0 for valid shots

**Root cause:** Investigate `clean_value()` logic for zero/null handling in smash calculations

---

## Performance Bottlenecks

### Loading All Sessions at Once

**Files:** `golf_db.py`, `pages/2_📊_Dashboard.py`

**Problem:** `get_unique_sessions()` loads entire session list in memory. With 100+ sessions, this is slow and impacts page load time.

**Current scale:** ~80-100 sessions on production

**Scaling limit:** Dashboard becomes noticeably sluggish at 200+ sessions

**Improvement path:**
1. Implement pagination in session selector (load 20 at a time)
2. Add session search/filter to reduce initial load
3. Cache session metadata separately from shot data

### Plotly Charts Freeze with Large Datasets

**Files:** `pages/2_📊_Dashboard.py`, `components/render_*.py`

**Problem:** Plotly charts with >500 data points cause UI freezes

**Cause:** No downsampling or aggregation for large datasets

**Improvement path:**
1. Add adaptive downsampling (every Nth point for large datasets)
2. Implement server-side aggregation for summary stats
3. Consider switching to lighter charting library for high-volume data

### SQLite WAL Mode Concurrent Access

**Files:** `golf_db.py` (line 57)

**Status:** WAL mode is enabled for concurrent access (good), but no explicit connection pooling or timeout handling

**Concern:** With many concurrent writes (during backfill), could hit lock contention. Consider adding `timeout` parameter to `sqlite3.connect()`.

---

## Security Considerations

### Encryption Key File Stored in Plain Text

**Files:** `automation/credential_manager.py` (lines 95-100)

**Risk:** Fernet encryption key stored in `.uneekor_key` file (local filesystem only, 0o600 permissions)

**Current mitigation:** Key file excluded from git, local-only storage, 0o600 permissions

**Recommendation for production:**
- Use environment variable: `UNEEKOR_ENCRYPTION_KEY=op://Private/...` (1Password integration)
- Or use OS-level keystore (Keychain on macOS, Credential Manager on Windows)
- For Cloud Run: use Secret Manager, not environment variable

### Cookie Expiration Validation

**Files:** `automation/credential_manager.py` (line 67)

**Issue:** Cookies expire after 7 days, but no warning given to user before they become stale. Silent auth failures could occur.

**Improvement:** Add pre-expiration alert (5-6 days) to notify user to re-authenticate

### Supabase Soft Dependency Error Handling

**Files:** `golf_db.py` (lines 262-273, 299-300, 321-322)

**Issue:** Many cloud sync operations silently fail with bare `except Exception: pass`. Errors are swallowed without logging.

```python
# Line 299-300: Silent failure
except Exception:
    pass  # Cloud sync failed, but we don't log or warn
```

**Impact:** Users unaware that Supabase sync is broken until they check manually

**Fix approach:** Log all Supabase failures to file/observability, at least at WARNING level

---

## Data Integrity Concerns

### Soft Delete Recovery Window

**Files:** `golf_db.py` (lines 130-137, 700-745)

**Issue:** Deleted shots archived to `shots_archive` table, but no retention policy. Archive grows indefinitely.

**Current behavior:**
- Session deleted → shots moved to `shots_archive`
- Archive never purged
- No audit trail of who deleted what, when

**Improvement:**
1. Add `deleted_by` and `deletion_context` columns to track deletion source
2. Implement archive cleanup (e.g., auto-purge after 90 days)
3. Add restore permissions/validation

### Deduplication Not Guaranteed

**Files:** `golf_db.py` (lines 1480-1515)

**Issue:** `deduplicate_shots()` function removes duplicates, but duplicates shouldn't occur (PRIMARY KEY on shot_id). Function suggests duplicates have been observed in past.

**Question:** Under what conditions do duplicates occur? If the API returns duplicate shots, they'll be silently merged, losing the original.

**Recommendation:** Add logging to understand why duplicates appear; consider moving duplicate detection upstream in scraper

### Data Validation Gaps

**Files:** `pages/1_📥_Data_Import.py` (lines 74-79)

**Issue:** `validate_shot_data()` called AFTER import, not before. Invalid data is already in database.

**Better approach:** Validate before saving, reject batch on validation failure, provide user feedback on specific invalid fields

---

## Fragile Areas

### Automation State Machine (`BackfillRunner`)

**Files:** `automation/backfill_runner.py` (150-230)

**Fragility:** Complex state tracking across multiple tables (`backfill_runs`, `sessions_discovered`, `shots`). Risk of inconsistent state if:
- Process interrupted mid-save
- Checkpoint written but shots not
- Database transaction partially rolled back

**Safe modification:**
1. Review checkpoint logic to ensure atomicity (either full checkpoint or no checkpoint)
2. Add integrity check on resume: verify `last_processed_id` exists in database
3. Test power-failure scenarios (kill -9 during backfill)

### Supabase Sync Without Transaction Control

**Files:** `golf_db.py` (lines 388-505)

**Fragility:** `save_shot()` writes to SQLite, then separately to Supabase. If second call fails:
- Shot exists locally but not in cloud
- No rollback mechanism
- User unaware of sync failure

**Safe modification:**
1. Add transaction-like behavior: batch updates and validate both succeed before committing
2. Or: accept the hybrid model but add monitoring to detect drift
3. Implement compensating transactions for cleanup on failure

### ML Module Lazy Imports

**Files:** `ml/__init__.py` (lines 28-52)

**Fragility:** Using `__getattr__` for lazy imports. If an import fails:
- Error happens at first use, not at startup
- Can cascade through user operations
- Hard to debug

**Safe modification:**
1. Test ML imports at startup (`golf_db.init_db()` or app.py entry)
2. Provide clear error message if scikit-learn/xgboost missing
3. Consider adding explicit `ml.check_dependencies()` function

---

## Missing Critical Features

### Observability & Monitoring

**Files:** `utils/logging_config.py`, `observability.py`

**Gap:** No structured logging for automation runs. Only console output and notification webhooks.

**Missing:**
- Backfill progress metrics (sessions/hour, ETA)
- Error aggregation (which errors are recurring?)
- Performance monitoring (scrape time per session)
- Database health checks (corruption detection, size limits)

**Impact:** Hard to diagnose failures in production; no alerting for slow backfills

**Recommendation:**
1. Add metrics export to Prometheus or similar
2. Log structured JSON to file for post-analysis
3. Add health check endpoint for Cloud Run

### Session Date Extraction Robustness

**Files:** `automation/session_discovery.py`, `automation/uneekor_portal.py`

**Gap:** Multiple date sources (listing page, report page, link text) with no unified strategy. Date accuracy unclear.

**Risk:** Data integrity if dates are incorrectly assigned

**Improvement:**
1. Document each date source's reliability (e.g., listing page = high confidence)
2. Add validation: flag suspicious date ranges (e.g., future dates, >1 year old)
3. Implement date conflict resolution strategy (which source wins?)

---

## Test Coverage Gaps

### Automation Module Under-tested

**Files:** `tests/integration/test_automation_flow.py`, `tests/integration/test_date_reclassification.py`

**Gap:** Automation is complex (scraping, rate limiting, state checkpointing, notifications) but integration tests are minimal. Missing tests for:
- Pagination (all pages visited)
- Rate limiter accuracy (6/hour enforced)
- Checkpoint recovery (resume after interruption)
- Duplicate detection/deduplication
- Cookie expiration handling

**Risk:** Regressions in scraper logic not caught until production

**Priority:** HIGH — automation is production-critical

### Supabase Sync Not Tested

**Files:** No dedicated tests for Supabase sync

**Gap:** Hybrid SQLite/Supabase mode is complex but untested:
- What happens if Supabase is down?
- Does drift get detected?
- Are deletions synced correctly?

**Risk:** Silent data loss or inconsistency

**Improvement:** Add integration tests that mock Supabase and verify sync behavior

### Data Validation Not Tested

**Files:** No test file for `golf_db.validate_shot_data()`

**Gap:** Validation function exists but no coverage for edge cases:
- Missing critical fields
- Invalid data types
- Out-of-range values (e.g., carry > 400 yards)

**Risk:** Invalid data silently accepted or rejected without user feedback

---

## Dependency Risk

### Deprecated Selenium Scraper

**Files:** `golf_scraper.py`, `requirements.txt` (line 2-3)

**Risk:** `selenium` and `webdriver-manager` still in requirements but codebase has moved to `playwright`. Old scraper may be unmaintained.

**Recommendation:**
1. Confirm playwright has fully replaced selenium
2. Remove selenium from requirements.txt
3. Deprecate `golf_scraper.py` or mark as legacy

### ML Dependencies Optional but Not Documented

**Files:** `ml/__init__.py`, `local_coach.py`

**Issue:** scikit-learn, xgboost, joblib are optional, but error messages don't guide user to install them

**Improvement:** Add installation instructions in error message:
```
ML features require: pip install scikit-learn xgboost joblib
```

---

## Scaling Limits

### SQLite Database Size

**Current capacity:** Not measured, but SQLite is single-machine

**Limit:** File-based database will degrade with:
- >1M shots (multiple GB file)
- Concurrent writes during backfill + user queries

**Scaling path:**
1. Monitor database size (run periodic `PRAGMA page_count`)
2. Consider TimescaleDB or PostgreSQL for >1M rows
3. Archive old sessions to cold storage

### Automation Backfill Window

**Current rate:** 6 sessions/hour (default, configurable)

**Timeline:** 80 sessions = ~13 hours

**Issue:** Backfill must complete before new shots arrive, or discovery queue grows indefinitely

**Scaling concern:** If portal has 1000+ sessions, backfill takes weeks

**Solution paths:**
1. Increase rate if portal allows (observe for rate limits)
2. Parallel workers (multiple browser sessions)
3. Server-side filtering (only fetch last N days, not historical)

---

## Configuration & Deployment Risks

### Environment Variables Not Validated

**Files:** `golf_db.py` (lines 13-19), `automation/credential_manager.py`

**Issue:** Missing env vars print warning but don't fail hard. Downstream errors are confusing.

**Example:** If `SUPABASE_URL` missing, Supabase client is None, and later code silently handles it

**Improvement:**
1. Validate critical env vars at startup
2. Fail fast with clear error message
3. Provide setup checklist (`.env.example` → `.env`)

### Cloud Run Deployment Assumptions

**Files:** `golf_db.py` (line 18), `automation/credential_manager.py` (line 88)

**Issue:** Code checks `K_SERVICE` env var to detect Cloud Run. This works but:
- Fragile (depends on Google's env var names)
- Not documented
- No graceful degradation if check fails

**Improvement:** Use feature flags or explicit `ENVIRONMENT=cloud` var

---

## Recommended Action Priority

| Priority | Concern | Impact | Effort |
|----------|---------|--------|--------|
| CRITICAL | Rate limiter unit bug | Backfill gets blocked | 30min |
| CRITICAL | Pagination unverified | Missing 50+ sessions | 2hrs |
| HIGH | Supabase error silencing | Silent data loss | 3hrs |
| HIGH | Automation test gaps | Production bugs | 8hrs |
| MEDIUM | Soft delete retention | Archive bloat | 2hrs |
| MEDIUM | Image download failures | Poor UX | 1hr |
| MEDIUM | Performance (session loading) | Slow UI | 4hrs |
| LOW | Logging/observability | Hard to debug | 6hrs |

---

*Concerns audit: 2026-02-09*
