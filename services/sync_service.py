"""
Sync Service — wraps automation pipeline for Streamlit UI use.

Provides a synchronous interface (using asyncio.run internally) so
Streamlit can trigger the async discover + backfill pipeline with
a single function call.
"""
import os
import json
import asyncio
import threading
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Dict, Any

import observability

CREDENTIALS_FILE = Path(__file__).parent.parent / '.uneekor_credentials.json'

SYNC_TIMEOUT_SECONDS = 300  # 5 minutes; generous for Playwright + network I/O


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    status: str  # 'completed', 'no_new_sessions', 'partial', 'failed'
    sessions_discovered: int = 0
    new_sessions: int = 0
    sessions_imported: int = 0
    sessions_failed: int = 0
    total_shots: int = 0
    dates_updated: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    error_message: str = ''


# ── Credential helpers ────────────────────────────────────────

def load_credentials() -> Optional[Dict[str, str]]:
    """Load credentials from JSON file."""
    if not CREDENTIALS_FILE.exists():
        return None
    try:
        data = json.loads(CREDENTIALS_FILE.read_text())
        if data.get('username') and data.get('password'):
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def save_credentials(username: str, password: str) -> None:
    """Save credentials to JSON file."""
    CREDENTIALS_FILE.write_text(json.dumps({
        'username': username,
        'password': password,
    }, indent=2))
    CREDENTIALS_FILE.chmod(0o600)


def clear_credentials() -> bool:
    """Delete credential file. Returns True if file existed."""
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()
        return True
    return False


def has_credentials() -> bool:
    """Check if credentials are configured."""
    return load_credentials() is not None


# ── Pre-flight checks ────────────────────────────────────────

def check_playwright_available() -> tuple:
    """Check if Playwright is importable.
    Returns (available: bool, message: str).
    """
    try:
        from playwright.async_api import async_playwright  # noqa: F401
        return True, "Playwright available"
    except ImportError:
        return False, "Playwright not installed. Run: pip install playwright && playwright install chromium"


# ── Main sync function ────────────────────────────────────────

def run_sync(
    username: str,
    password: str,
    on_status: Optional[Callable[[str], None]] = None,
    max_sessions: int = 10,
) -> SyncResult:
    """
    Run the full sync pipeline: discover -> backfill -> reclassify dates.

    Synchronous wrapper around the async automation pipeline.

    Args:
        username: Uneekor portal username/email
        password: Uneekor portal password
        on_status: Callback for status updates (str message)
        max_sessions: Maximum sessions to import per run
    """
    start_time = datetime.now(timezone.utc)

    def status(msg: str):
        if on_status:
            on_status(msg)

    pw_available, pw_msg = check_playwright_available()
    if not pw_available:
        return SyncResult(success=False, status='failed', error_message=pw_msg)

    # Temporarily set env vars for CredentialManager
    old_user = os.environ.get('UNEEKOR_USERNAME')
    old_pass = os.environ.get('UNEEKOR_PASSWORD')
    os.environ['UNEEKOR_USERNAME'] = username
    os.environ['UNEEKOR_PASSWORD'] = password

    try:
        result = _run_async_pipeline_sync(status, max_sessions)
    except Exception as e:
        result = SyncResult(
            success=False, status='failed',
            error_message=str(e), errors=[str(e)],
        )
    finally:
        # Restore original env vars.
        # Safe even on pipeline timeout: credentials are read early in the
        # pipeline (during CredentialManager init), well before any timeout.
        if old_user is not None:
            os.environ['UNEEKOR_USERNAME'] = old_user
        else:
            os.environ.pop('UNEEKOR_USERNAME', None)
        if old_pass is not None:
            os.environ['UNEEKOR_PASSWORD'] = old_pass
        else:
            os.environ.pop('UNEEKOR_PASSWORD', None)

    result.duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()

    observability.append_event("sync_runs.jsonl", {
        "status": result.status,
        "mode": "ui_sync",
        "sessions_discovered": result.sessions_discovered,
        "new_sessions": result.new_sessions,
        "sessions_imported": result.sessions_imported,
        "shots": result.total_shots,
        "errors": len(result.errors),
        "duration_sec": round(result.duration_seconds, 1),
    })

    return result


def _run_async_pipeline_sync(
    status: Callable[[str], None],
    max_sessions: int,
) -> SyncResult:
    """Run async pipeline from sync code, even if a loop is already running."""
    try:
        asyncio.get_running_loop()
        has_running_loop = True
    except RuntimeError:
        has_running_loop = False

    if not has_running_loop:
        return asyncio.run(_async_sync_pipeline(status, max_sessions))

    result_box: Dict[str, SyncResult] = {}
    error_box: Dict[str, Exception] = {}

    def runner() -> None:
        try:
            result_box['result'] = asyncio.run(_async_sync_pipeline(status, max_sessions))
        except Exception as exc:
            error_box['error'] = exc

    thread = threading.Thread(target=runner, name="sync-service-runner", daemon=True)
    thread.start()
    thread.join(timeout=SYNC_TIMEOUT_SECONDS)

    if thread.is_alive():
        return SyncResult(
            success=False, status='failed',
            error_message=f'Sync timed out after {SYNC_TIMEOUT_SECONDS}s',
            errors=[f'Pipeline did not complete within {SYNC_TIMEOUT_SECONDS}s'],
        )

    if 'error' in error_box:
        raise error_box['error']

    return result_box['result']


async def _async_sync_pipeline(
    status: Callable[[str], None],
    max_sessions: int,
) -> SyncResult:
    """Async implementation of the sync pipeline."""
    from automation.session_discovery import get_discovery
    from automation.backfill_runner import BackfillRunner, BackfillConfig
    import golf_db

    errors = []
    result = SyncResult(success=True, status='completed')

    # ── Phase 1: Discover sessions ──
    status("Discovering sessions from Uneekor portal...")
    discovery = get_discovery()

    try:
        disc_result = await discovery.discover_sessions(
            headless=True,
            max_sessions=100,
        )
    except Exception as e:
        return SyncResult(
            success=False, status='failed',
            error_message=f"Discovery failed: {e}", errors=[str(e)],
        )

    result.sessions_discovered = disc_result.total_discovered
    result.new_sessions = disc_result.new_sessions
    errors.extend(disc_result.errors)

    # Check for auth failure
    for err in disc_result.errors:
        if 'log in' in err.lower() or 'login' in err.lower():
            return SyncResult(
                success=False, status='failed',
                error_message='Authentication failed. Check your credentials.',
                errors=disc_result.errors,
                sessions_discovered=disc_result.total_discovered,
            )

    if disc_result.new_sessions == 0:
        status("No new sessions found.")
        result.status = 'no_new_sessions'
        return result

    status(f"Found {disc_result.new_sessions} new session(s). Importing...")

    # ── Phase 2: Backfill (import shot data) ──
    config = BackfillConfig(
        max_sessions_per_run=max_sessions,
        normalize_clubs=True,
        auto_tag=True,
        notify_on_complete=False,
        notify_on_error=False,
    )
    runner = BackfillRunner(config=config)

    def backfill_progress(progress):
        pct = (progress.sessions_processed / progress.sessions_total * 100) \
            if progress.sessions_total > 0 else 0
        status(f"Importing: {progress.sessions_processed}/{progress.sessions_total} sessions ({pct:.0f}%)")

    try:
        bf_result = await runner.run(progress_callback=backfill_progress)
    except Exception as e:
        errors.append(f"Backfill error: {e}")
        result.errors = errors
        result.status = 'partial'
        result.error_message = f"Import error: {e}"
        return result

    result.sessions_imported = bf_result.sessions_imported
    result.sessions_failed = bf_result.sessions_failed
    result.total_shots = bf_result.total_shots
    errors.extend(bf_result.errors)

    # ── Phase 3: Date reclassification ──
    status("Updating session dates...")
    try:
        date_result = golf_db.backfill_session_dates()
        if isinstance(date_result, dict):
            result.dates_updated = date_result.get('updated', 0)
        else:
            result.dates_updated = date_result or 0
    except Exception as e:
        errors.append(f"Date backfill warning: {e}")

    # ── Phase 4: Recompute session stats ──
    status("Recomputing session statistics...")
    try:
        golf_db.compute_session_stats()
        golf_db.batch_update_session_names()
    except Exception as e:
        errors.append(f"Stats recompute warning: {e}")

    # Final status
    result.errors = errors
    if result.sessions_failed > 0 and result.sessions_imported > 0:
        result.status = 'partial'
    elif result.sessions_failed > 0 and result.sessions_imported == 0:
        result.status = 'failed'
        result.success = False
        result.error_message = f"All {result.sessions_failed} imports failed"

    return result


# ── History & status helpers ──────────────────────────────────

def get_sync_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent backfill run history from database."""
    try:
        from automation.backfill_runner import list_backfill_runs
        return list_backfill_runs(limit=limit)
    except Exception:
        return []


def get_automation_status() -> Dict[str, Any]:
    """Get combined automation status for UI display."""
    try:
        from automation.credential_manager import CredentialManager
        cred_manager = CredentialManager()
        cred_info = cred_manager.get_credential_info()
    except Exception:
        cred_info = {}

    has_creds = has_credentials()
    creds = load_credentials()

    return {
        'credentials_configured': has_creds,
        'username': creds.get('username', '') if creds else '',
        'cookies_valid': cred_info.get('cookies_valid', False),
        'cookies_expires': cred_info.get('cookies_expires_at'),
    }
