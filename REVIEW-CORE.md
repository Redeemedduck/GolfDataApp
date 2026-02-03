# Core Review Findings

**Status: All issues resolved as of 2026-02-03**

Scope: `golf_db.py`, `local_coach.py`, `exceptions.py`, `golf_scraper.py`

## Critical
- None found.

## High
- None found.

## Medium — All Fixed ✅
- ~~`golf_db.py:795-799`~~ — Fixed: Added early return when `shot_ids` is empty in `split_session()`
- ~~`golf_db.py:389-444`~~ — Fixed: Added `ValidationError` for null `shot_id`/`session_id` in `save_shot()`
- ~~`golf_db.py:1309-1314`~~ — Fixed: Added `ALLOWED_RESTORE_COLUMNS` allowlist in `restore_deleted_shots()`
- ~~`golf_scraper.py:256-273`~~ — Fixed: Added size limits and MIME type validation for image downloads
- ~~`local_coach.py:341-342`~~ — Fixed: Added NaT/empty validation before `idxmax()` call

## Low — All Fixed ✅
- ~~`exceptions.py:60`~~ — Fixed: Renamed `ImportError` to `DataImportError`
- ~~`golf_db.py:164-175`~~ — Fixed: Replaced broad exception handlers with logging
- ~~`local_coach.py:179-181`~~ — Fixed: Added column validation before `.str.lower()`
- ~~`local_coach.py:301-305`~~ — Fixed: Added validation for `carry/total/club` columns
- ~~`golf_scraper.py:179,226`~~ — Fixed: Added datetime validation for `session_date`
