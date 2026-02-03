# Core Review Findings

Scope: `golf_db.py`, `local_coach.py`, `exceptions.py`, `golf_scraper.py`

## Critical
- None found.

## High
- None found.

## Medium
- `golf_db.py:795-799` — `split_session` builds an `IN ()` clause when `shot_ids` is empty, which raises a SQL syntax error and is only caught/logged. This results in a silent no-op with error output and can break session splitting flows.
- `golf_db.py:389-444` — `save_shot` does not validate `shot_id` / `session_id`. If either is `None`, SQLite insert fails (caught/printed) while the Supabase upsert still runs with a null key, leading to inconsistent data and silent local failures.
- `golf_db.py:1309-1314` — `restore_deleted_shots` dynamically builds the column list from archived JSON keys. If archived data is tampered or malformed, this can produce invalid SQL or allow column injection. Validate keys against a whitelist before composing SQL.
- `golf_scraper.py:256-273` — `upload_shot_images` downloads remote images into memory with no size/type validation and uploads them directly. A large or unexpected payload could exhaust memory or storage. Consider content-length checks, limits, and MIME validation.
- `local_coach.py:341-342` — `_handle_session_analysis` assumes `date_added` exists and contains at least one non-null value; if missing or all-NaT, `idxmax()` will raise. This can break session analysis for older imports or partial data.

## Low
- `exceptions.py:60` — Custom `ImportError` shadows Python’s built-in `ImportError`, which can confuse exception handling and tooling. Consider renaming to `DataImportError` or similar.
- `golf_db.py:164-175` (and multiple similar blocks) — broad `except Exception: pass` swallows errors silently (e.g., `_ensure_default_tags`, `get_shot_counts`, Supabase operations). This violates “no silent failures” and makes debugging data issues difficult.
- `local_coach.py:179-181` — `_handle_club_stats` uses `df['club'].str.lower()` without checking the column exists or handling non-string values; missing columns or unexpected types can raise at runtime.
- `local_coach.py:301-305` — `get_club_comparison` assumes `carry`, `total`, and `club` columns exist; missing columns will raise `KeyError`. Consider graceful fallbacks or validation.
- `golf_scraper.py:179,226` — `session_date` is assumed to be a `datetime` (uses `.isoformat()`), but no validation is performed. Passing a string or other type will raise an `AttributeError`.
