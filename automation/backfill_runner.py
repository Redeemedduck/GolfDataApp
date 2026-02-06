"""
Backfill Runner for Historical Session Import.

Manages the controlled import of historical sessions:
- Prioritized queue processing
- Rate-limited API calls
- Checkpoint/resume support
- Progress tracking and logging

Understanding Backfill:
    Backfill = importing old data you haven't scraped yet.

    Why do it slowly?
    - Uneekor may have rate limits (not documented)
    - Importing 100 sessions at once could get you blocked
    - Spreading imports over days is more reliable
    - You can pause and resume anytime

    Example timeline:
    - 100 sessions to import
    - 6 sessions/hour (conservative rate)
    - ~17 hours total (can run overnight)
    - Or: 10 sessions/day over 10 days (very conservative)
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import golf_scraper
    import golf_db
    HAS_SCRAPER = True
except ImportError:
    HAS_SCRAPER = False

from .session_discovery import SessionDiscovery, ImportQueueItem, ImportStatus
from .rate_limiter import RateLimiter, get_backfill_limiter
from .naming_conventions import (
    ClubNameNormalizer,
    SessionNamer,
    AutoTagger,
    get_normalizer,
    get_session_namer,
    get_auto_tagger,
)
from .notifications import NotificationManager, get_notifier


class BackfillStatus(Enum):
    """Status of a backfill run."""
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAILED = 'failed'


@dataclass
class BackfillConfig:
    """Configuration for backfill run."""
    date_start: Optional[date] = None           # Earliest date to include
    date_end: Optional[date] = None             # Latest date to include
    clubs_filter: Optional[List[str]] = None    # Only import sessions with these clubs
    max_sessions_per_run: int = 50              # Stop after this many sessions
    max_sessions_per_hour: int = 6              # Rate limit (conservative)
    checkpoint_interval: int = 5                # Save progress every N sessions
    normalize_clubs: bool = True                # Apply club name normalization
    auto_tag: bool = True                       # Apply automatic tagging
    notify_on_complete: bool = True             # Send notification when done
    notify_on_error: bool = True                # Send notification on errors
    dry_run: bool = False                       # Preview mode - no actual imports
    max_retries: int = 3                        # Max retries for failed imports
    retry_delay_base: int = 10                  # Base delay in seconds for retry backoff
    delay_seconds: Optional[int] = None         # Fixed delay between imports (overrides rate limiter)
    recent_first: bool = False                  # Import newest sessions first


@dataclass
class BackfillProgress:
    """Progress tracking for backfill run."""
    run_id: str
    status: BackfillStatus
    started_at: datetime
    sessions_total: int
    sessions_processed: int
    sessions_imported: int
    sessions_skipped: int
    sessions_failed: int
    total_shots: int
    last_processed_id: Optional[str]
    last_checkpoint: Optional[datetime]
    estimated_remaining_minutes: Optional[float]
    errors: List[str] = field(default_factory=list)


@dataclass
class BackfillResult:
    """Result of a backfill run."""
    run_id: str
    status: BackfillStatus
    sessions_imported: int
    sessions_skipped: int
    sessions_failed: int
    total_shots: int
    duration_seconds: float
    errors: List[str]


class BackfillRunner:
    """
    Manages historical data backfill with rate limiting and checkpointing.

    Usage:
        # Create runner with config
        runner = BackfillRunner(BackfillConfig(
            date_start=date(2025, 1, 1),
            max_sessions_per_run=20,
        ))

        # Start or resume backfill
        result = await runner.run()

        # Check progress
        progress = runner.get_progress()
        print(f"{progress.sessions_processed}/{progress.sessions_total} processed")

        # Pause and resume later
        runner.pause()
        # ... later ...
        await runner.run()  # Resumes from checkpoint

    Rate Limiting Explained:
        The default is 6 sessions per hour:
        - Each session = 1 API call to get data + 1-N image downloads
        - 6/hour = one every 10 minutes
        - This is VERY conservative

        You can increase max_sessions_per_hour for faster backfill,
        but watch for rate limit errors from Uneekor.
    """

    # SQL for backfill state tracking
    CREATE_BACKFILL_RUNS_SQL = '''
        CREATE TABLE IF NOT EXISTS backfill_runs (
            run_id TEXT PRIMARY KEY,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            status TEXT DEFAULT 'running',
            config_json TEXT,
            target_date_start DATE,
            target_date_end DATE,
            clubs_filter TEXT,
            sessions_total INTEGER DEFAULT 0,
            sessions_processed INTEGER DEFAULT 0,
            sessions_imported INTEGER DEFAULT 0,
            sessions_skipped INTEGER DEFAULT 0,
            sessions_failed INTEGER DEFAULT 0,
            total_shots INTEGER DEFAULT 0,
            last_processed_report_id TEXT,
            last_checkpoint_at TIMESTAMP,
            error_log TEXT
        )
    '''

    def __init__(
        self,
        config: Optional[BackfillConfig] = None,
        discovery: Optional[SessionDiscovery] = None,
        rate_limiter: Optional[RateLimiter] = None,
        notifier: Optional[NotificationManager] = None,
        resume_run_id: Optional[str] = None,
    ):
        """
        Initialize backfill runner.

        Args:
            config: Backfill configuration
            discovery: SessionDiscovery instance
            rate_limiter: Rate limiter (uses backfill limiter if not provided)
            notifier: Notification manager
            resume_run_id: Run ID to resume (loads config from database)
        """
        self.config = config or BackfillConfig()
        self.discovery = discovery or SessionDiscovery()
        # Apply max_sessions_per_hour config to rate limiter if not explicitly provided
        if rate_limiter:
            self.rate_limiter = rate_limiter
        else:
            from .rate_limiter import RateLimiter, RateLimiterConfig
            # Use configured sessions per hour (default 6) instead of ignoring it
            self.rate_limiter = RateLimiter(RateLimiterConfig(
                requests_per_minute=self.config.max_sessions_per_hour / 60,
            ))
        self.notifier = notifier or get_notifier()

        # Naming tools
        self.club_normalizer = get_normalizer()
        self.session_namer = get_session_namer()
        self.auto_tagger = get_auto_tagger()

        # State
        self.run_id: Optional[str] = resume_run_id
        self.status = BackfillStatus.RUNNING
        self._should_pause = False

        # Progress tracking
        self.sessions_total = 0
        self.sessions_processed = 0
        self.sessions_imported = 0
        self.sessions_skipped = 0
        self.sessions_failed = 0
        self.total_shots = 0
        self.last_processed_id: Optional[str] = None
        self.errors: List[str] = []

        # Initialize database
        self._init_tables()

        # Resume if specified
        if resume_run_id:
            self._load_checkpoint(resume_run_id)

    def _init_tables(self) -> None:
        """Initialize backfill tracking tables."""
        conn = sqlite3.connect(self.discovery.db_path)
        try:
            conn.execute(self.CREATE_BACKFILL_RUNS_SQL)
            conn.commit()
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.discovery.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_run(self) -> str:
        """Create a new backfill run record."""
        import uuid
        run_id = f"bf_{uuid.uuid4().hex[:8]}"

        conn = self._get_connection()
        try:
            conn.execute('''
                INSERT INTO backfill_runs
                (run_id, config_json, target_date_start, target_date_end, clubs_filter)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                run_id,
                json.dumps({
                    'max_sessions_per_run': self.config.max_sessions_per_run,
                    'max_sessions_per_hour': self.config.max_sessions_per_hour,
                    'normalize_clubs': self.config.normalize_clubs,
                    'auto_tag': self.config.auto_tag,
                }),
                self.config.date_start.isoformat() if self.config.date_start else None,
                self.config.date_end.isoformat() if self.config.date_end else None,
                json.dumps(self.config.clubs_filter) if self.config.clubs_filter else None,
            ))
            conn.commit()
            return run_id
        finally:
            conn.close()

    def _load_checkpoint(self, run_id: str) -> None:
        """Load state from a previous run."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                'SELECT * FROM backfill_runs WHERE run_id = ?',
                (run_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Run ID not found: {run_id}")

            self.sessions_total = row['sessions_total'] or 0
            self.sessions_processed = row['sessions_processed'] or 0
            self.sessions_imported = row['sessions_imported'] or 0
            self.sessions_skipped = row['sessions_skipped'] or 0
            self.sessions_failed = row['sessions_failed'] or 0
            self.total_shots = row['total_shots'] or 0
            self.last_processed_id = row['last_processed_report_id']

            if row['error_log']:
                self.errors = json.loads(row['error_log'])

            # Load config if not provided
            if row['config_json']:
                saved_config = json.loads(row['config_json'])
                self.config.max_sessions_per_run = saved_config.get('max_sessions_per_run', 50)
                self.config.max_sessions_per_hour = saved_config.get('max_sessions_per_hour', 6)

            if row['target_date_start']:
                self.config.date_start = date.fromisoformat(row['target_date_start'])
            if row['target_date_end']:
                self.config.date_end = date.fromisoformat(row['target_date_end'])
            if row['clubs_filter']:
                self.config.clubs_filter = json.loads(row['clubs_filter'])

            print(f"Resumed backfill run {run_id}: {self.sessions_processed}/{self.sessions_total} processed")
        finally:
            conn.close()

    def _save_checkpoint(self) -> None:
        """Save current progress as checkpoint."""
        if not self.run_id:
            return

        conn = self._get_connection()
        try:
            conn.execute('''
                UPDATE backfill_runs
                SET status = ?,
                    sessions_total = ?,
                    sessions_processed = ?,
                    sessions_imported = ?,
                    sessions_skipped = ?,
                    sessions_failed = ?,
                    total_shots = ?,
                    last_processed_report_id = ?,
                    last_checkpoint_at = ?,
                    error_log = ?
                WHERE run_id = ?
            ''', (
                self.status.value,
                self.sessions_total,
                self.sessions_processed,
                self.sessions_imported,
                self.sessions_skipped,
                self.sessions_failed,
                self.total_shots,
                self.last_processed_id,
                datetime.utcnow().isoformat(),
                json.dumps(self.errors) if self.errors else None,
                self.run_id,
            ))
            conn.commit()
        finally:
            conn.close()

    def _complete_run(self) -> None:
        """Mark the run as completed."""
        if not self.run_id:
            return

        conn = self._get_connection()
        try:
            conn.execute('''
                UPDATE backfill_runs
                SET status = ?,
                    completed_at = ?,
                    sessions_total = ?,
                    sessions_processed = ?,
                    sessions_imported = ?,
                    sessions_skipped = ?,
                    sessions_failed = ?,
                    total_shots = ?,
                    error_log = ?
                WHERE run_id = ?
            ''', (
                self.status.value,
                datetime.utcnow().isoformat(),
                self.sessions_total,
                self.sessions_processed,
                self.sessions_imported,
                self.sessions_skipped,
                self.sessions_failed,
                self.total_shots,
                json.dumps(self.errors) if self.errors else None,
                self.run_id,
            ))
            conn.commit()
        finally:
            conn.close()

    def pause(self) -> None:
        """Request pause at next checkpoint."""
        self._should_pause = True
        self.status = BackfillStatus.PAUSED

    def get_progress(self) -> BackfillProgress:
        """Get current progress."""
        # Estimate remaining time
        estimated_remaining = None
        if self.sessions_processed > 0 and self.sessions_total > self.sessions_processed:
            remaining = self.sessions_total - self.sessions_processed
            # Assume 10 minutes per session (conservative)
            estimated_remaining = remaining * 10

        return BackfillProgress(
            run_id=self.run_id or 'not_started',
            status=self.status,
            started_at=datetime.utcnow(),  # Would need to track actual start
            sessions_total=self.sessions_total,
            sessions_processed=self.sessions_processed,
            sessions_imported=self.sessions_imported,
            sessions_skipped=self.sessions_skipped,
            sessions_failed=self.sessions_failed,
            total_shots=self.total_shots,
            last_processed_id=self.last_processed_id,
            last_checkpoint=None,
            estimated_remaining_minutes=estimated_remaining,
            errors=self.errors.copy(),
        )

    async def run(
        self,
        progress_callback: Optional[Callable[[BackfillProgress], None]] = None,
    ) -> BackfillResult:
        """
        Execute the backfill.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            BackfillResult with final statistics
        """
        start_time = datetime.utcnow()

        # Create or resume run
        if not self.run_id:
            self.run_id = self._create_run()

        self.status = BackfillStatus.RUNNING

        try:
            # Get pending sessions
            date_start_dt = datetime.combine(self.config.date_start, datetime.min.time()) if self.config.date_start else None
            date_end_dt = datetime.combine(self.config.date_end, datetime.max.time()) if self.config.date_end else None

            pending = self.discovery.get_pending_sessions(
                limit=self.config.max_sessions_per_run,
                date_start=date_start_dt,
                date_end=date_end_dt,
                clubs_filter=self.config.clubs_filter,
                recent_first=self.config.recent_first,
            )

            # Log filtered clubs if specified
            if self.config.clubs_filter:
                print(f"Filtering for clubs: {', '.join(self.config.clubs_filter)}")

            self.sessions_total = len(pending)
            print(f"Backfill run {self.run_id}: {self.sessions_total} sessions to process")

            # Track processed IDs for this run to avoid duplicates
            processed_in_run = set()

            # Process sessions
            for i, item in enumerate(pending):
                if self._should_pause:
                    print("Backfill paused by request")
                    break

                # Skip if we've hit the per-run limit
                if self.sessions_processed >= self.config.max_sessions_per_run:
                    print(f"Reached max sessions per run ({self.config.max_sessions_per_run})")
                    break

                # Skip if already processed in this run
                if item.report_id in processed_in_run:
                    continue

                # Rate limit - use custom delay if specified, otherwise use rate limiter
                if self.config.delay_seconds:
                    # Only delay between sessions (not before the first one)
                    if self.sessions_processed > 0:
                        remaining = self.sessions_total - self.sessions_processed
                        eta_min = (remaining * self.config.delay_seconds) // 60
                        print(f"  Waiting {self.config.delay_seconds}s before next import... (ETA: ~{eta_min} min)")
                        await asyncio.sleep(self.config.delay_seconds)
                else:
                    await self.rate_limiter.wait_async('import_session')

                # Import the session
                success = await self._import_session(item)

                self.sessions_processed += 1
                self.last_processed_id = item.report_id
                processed_in_run.add(item.report_id)

                # Checkpoint periodically
                if self.sessions_processed % self.config.checkpoint_interval == 0:
                    self._save_checkpoint()
                    if progress_callback:
                        progress_callback(self.get_progress())

            # Determine final status
            if self._should_pause:
                self.status = BackfillStatus.PAUSED
            elif self.sessions_failed > 0 and self.sessions_imported == 0:
                self.status = BackfillStatus.FAILED
            else:
                self.status = BackfillStatus.COMPLETED

        except Exception as e:
            self.status = BackfillStatus.FAILED
            self.errors.append(f"Backfill error: {str(e)}")

        # Save final state
        self._complete_run()

        # Calculate duration
        duration = (datetime.utcnow() - start_time).total_seconds()

        # Notify if configured
        if self.config.notify_on_complete and self.status == BackfillStatus.COMPLETED:
            await self._send_completion_notification()
        elif self.config.notify_on_error and self.errors:
            await self._send_error_notification()

        return BackfillResult(
            run_id=self.run_id,
            status=self.status,
            sessions_imported=self.sessions_imported,
            sessions_skipped=self.sessions_skipped,
            sessions_failed=self.sessions_failed,
            total_shots=self.total_shots,
            duration_seconds=duration,
            errors=self.errors,
        )

    async def _import_session(self, item: ImportQueueItem, attempt: int = 1) -> bool:
        """
        Import a single session with retry support.

        Args:
            item: ImportQueueItem to import
            attempt: Current attempt number (for retry logic)

        Returns:
            True if import successful
        """
        # Handle dry-run mode
        if self.config.dry_run:
            clubs_str = ', '.join(item.clubs_used) if item.clubs_used else 'unknown clubs'
            date_str = item.session_date.strftime('%Y-%m-%d') if item.session_date else 'unknown date'
            print(f"  [DRY RUN] Would import {item.report_id}: {item.portal_name or 'Unnamed'} ({date_str}) - {clubs_str}")
            # Increment sessions_imported for progress tracking (even though not actually imported)
            # This is intentional: dry-run simulates what would happen
            self.sessions_imported += 1
            return True

        if not HAS_SCRAPER:
            self.errors.append("golf_scraper not available")
            self.sessions_failed += 1
            return False

        try:
            # Mark as importing and update attempt count
            self.discovery.mark_importing(item.report_id)
            self.discovery.update_attempt_count(item.report_id, attempt)

            # Build the import URL
            import_url = f"https://my.uneekor.com/report?id={item.report_id}&key={item.api_key}"

            # Run the scraper
            # Note: run_scraper is synchronous, so we run it in executor
            def progress_callback(msg):
                """Simple progress callback for automation."""
                print(f"    [scraper] {msg}")

            # Pass session_date to scraper if available
            session_date = item.session_date

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: golf_scraper.run_scraper(import_url, progress_callback, session_date=session_date)
            )

            if result and result.get('status') == 'success':
                shots_imported = result.get('total_shots_imported', 0)
                self.total_shots += shots_imported
                self.sessions_imported += 1

                # Apply naming conventions
                session_name = None
                session_type = None
                tags = None

                if self.config.normalize_clubs and shots_imported > 0:
                    # Get the imported shots to normalize club names
                    df = golf_db.get_session_data(item.report_id)
                    if df is not None and not df.empty:
                        clubs = df['club'].unique().tolist()

                        # Normalize club names
                        for old_name in clubs:
                            new_name = self.club_normalizer.normalize(old_name).normalized
                            if new_name != old_name:
                                golf_db.rename_club(item.report_id, old_name, new_name)

                        # Generate session name and type
                        normalized_clubs = self.club_normalizer.normalize_all(clubs)
                        session_type = self.session_namer.infer_session_type(
                            shots_imported, normalized_clubs
                        )
                        session_name = self.session_namer.generate_name(
                            session_type=session_type,
                            session_date=item.session_date or datetime.utcnow(),
                            clubs_used=normalized_clubs,
                        )

                        # Auto-tag
                        if self.config.auto_tag:
                            tags = self.auto_tagger.auto_tag(
                                clubs_used=normalized_clubs,
                                shot_count=shots_imported,
                            )

                # Mark as imported
                self.discovery.mark_imported(
                    item.report_id,
                    shot_count=shots_imported,
                    session_name=session_name,
                    session_type=session_type,
                    tags=tags,
                )

                print(f"  Imported {item.report_id}: {shots_imported} shots")
                self.rate_limiter.report_success()
                return True
            else:
                error_msg = result.get('message', 'Unknown error') if result else 'No result'
                return await self._handle_import_failure(item, error_msg, attempt)

        except Exception as e:
            return await self._handle_import_failure(item, str(e), attempt)

    async def _handle_import_failure(self, item: ImportQueueItem, error_msg: str, attempt: int) -> bool:
        """
        Handle a failed import with retry logic.

        Args:
            item: ImportQueueItem that failed
            error_msg: Error message from the failure
            attempt: Current attempt number

        Returns:
            True if retry succeeded, False otherwise
        """
        if attempt < self.config.max_retries:
            # Calculate exponential backoff delay
            delay = self.config.retry_delay_base * (3 ** (attempt - 1))  # 10s, 30s, 90s
            print(f"  Attempt {attempt}/{self.config.max_retries} failed for {item.report_id}: {error_msg}")
            print(f"  Retrying in {delay}s...")

            await asyncio.sleep(delay)

            # Retry the import
            return await self._import_session(item, attempt + 1)
        else:
            # Max retries exceeded - mark as needs_review
            self.discovery.mark_needs_review(item.report_id, error_msg, attempt)
            self.sessions_failed += 1
            self.errors.append(f"Failed {item.report_id} after {attempt} attempts: {error_msg}")
            self.rate_limiter.report_error()
            return False

    async def _send_completion_notification(self) -> None:
        """Send notification that backfill completed."""
        if not self.notifier:
            return

        message = (
            f"Backfill completed: {self.sessions_imported} sessions imported, "
            f"{self.total_shots} total shots"
        )
        await self.notifier.send(message, level='info')

    async def _send_error_notification(self) -> None:
        """Send notification about errors."""
        if not self.notifier:
            return

        message = f"Backfill errors: {len(self.errors)} errors occurred. First: {self.errors[0]}"
        await self.notifier.send(message, level='error')


def get_backfill_status(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a backfill run.

    Args:
        run_id: The run ID to check

    Returns:
        Dict with run status, or None if not found
    """
    discovery = SessionDiscovery()
    conn = sqlite3.connect(discovery.db_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute(
            'SELECT * FROM backfill_runs WHERE run_id = ?',
            (run_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def list_backfill_runs(limit: int = 10) -> List[Dict[str, Any]]:
    """
    List recent backfill runs.

    Args:
        limit: Maximum number of runs to return

    Returns:
        List of run records
    """
    discovery = SessionDiscovery()
    conn = sqlite3.connect(discovery.db_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute('''
            SELECT * FROM backfill_runs
            ORDER BY started_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
