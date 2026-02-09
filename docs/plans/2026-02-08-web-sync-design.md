# Web UI Sync for Uneekor Sessions

**Date:** 2026-02-08
**Status:** Approved

## Goal

Add a "Sync New Sessions" capability to the Streamlit web UI so new Uneekor sessions can be pulled without using the CLI.

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `services/sync_service.py` | Wraps discover + backfill + reclassify pipeline into `run_sync()` |
| `.uneekor_credentials.json` | Local credential storage (gitignored) |

### Modified Files

| File | Change |
|------|--------|
| `app.py` | Add Sync button between hero stats and calendar strip |
| `pages/4_⚙️_Settings.py` | Add "Automation" tab with connection status, sync controls, history |
| `.gitignore` | Add `.uneekor_credentials.json` entry |

### Not Modified

- No changes to `automation/` modules — called as-is
- No changes to `golf_db.py`
- No new dependencies

## Credential Storage

Simple JSON file at project root, gitignored:

```json
{
  "username": "your@email.com",
  "password": "yourpassword"
}
```

- First sync: if file missing, UI prompts for credentials and saves
- Subsequent syncs: loaded automatically, no prompts
- Settings page: can update or clear credentials

## Sync Service (`services/sync_service.py`)

### Interface

```python
@dataclass
class SyncResult:
    sessions_discovered: int
    sessions_imported: int
    total_shots: int
    errors: list[str]
    duration_seconds: float
    status: str  # "success" | "no_new" | "auth_failed" | "error"

def run_sync(
    username: str,
    password: str,
    on_status: Callable[[str], None] = None,
    max_sessions: int = 10,
) -> SyncResult
```

### Pipeline Steps

1. Set `UNEEKOR_USERNAME` / `UNEEKOR_PASSWORD` in `os.environ` for the automation modules
2. Call `on_status("Discovering new sessions...")`
3. Run `SessionDiscovery.discover_sessions()` in headless mode
4. If new sessions found, run `BackfillRunner.run()` with progress callback
5. Run date reclassification (from-listing + auto-backfill logic)
6. Return `SyncResult` with counts and errors

## Home Page (`app.py`)

### Layout

```
[Sessions: 42] [Total Shots: 1,247]
[Last Practice: 2 days ago] [Streak: 3 days]

  [ Sync New Sessions ]

|Mo|Tu|We|Th|Fr|Sa|Su|Mo|Tu|...  (calendar strip)
```

### Behavior

- Click button -> `st.status()` expander shows live progress
- Success -> summary message, then `st.rerun()` to refresh data
- No new sessions -> "Already up to date" message
- Auth failure -> inline credential form
- Error -> error message with details

### First-Time Setup

If `.uneekor_credentials.json` doesn't exist, clicking Sync shows an inline form (username + password + Save) instead of starting the sync. After saving, immediately runs the sync.

## Settings Page — Automation Tab

Added as 4th tab: Data | Maintenance | Tags | Automation

### Top: Connection Status

- Credentials configured indicator (green/warning)
- Username display (not password)
- Update/clear credentials button

### Middle: Sync Controls

- Same Sync button as Home page
- Optional "Max sessions" number input (default: 10)
- `st.status()` progress display

### Bottom: Sync History

- Table from `backfill_runs` table
- Columns: Date, Sessions Imported, Shots, Duration, Status
- Last 10 runs

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Integration method | In-process async | Reuses existing Python classes, real-time progress |
| Auth storage | JSON file | Simple, no expiry, no cookie staleness |
| Progress display | `st.status()` | Streamlit-native, shows steps in real time |
| UI separation | `sync_service.py` | Keeps Streamlit pages thin |
| Scope | Discover + import all new | Matches "catch me up" use case |
