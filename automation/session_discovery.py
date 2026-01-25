"""
Session Discovery and Deduplication.

Discovers sessions from Uneekor portal and manages import state:
- Tracks discovered sessions in database
- Deduplicates against already-imported data
- Provides import queue management
- Supports checkpointing for resumable operations

Database Tables (created in golf_db.py):
- sessions_discovered: Tracks all discovered sessions
- automation_runs: Logs automation run history
"""

import json
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

# Import from parent package
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import golf_db
    HAS_GOLF_DB = True
except ImportError:
    HAS_GOLF_DB = False

from .uneekor_portal import SessionInfo, UneekorPortalNavigator
from .browser_client import PlaywrightClient, BrowserConfig
from .rate_limiter import get_conservative_limiter


class ImportStatus(Enum):
    """Status of a discovered session."""
    PENDING = 'pending'
    IMPORTING = 'importing'
    IMPORTED = 'imported'
    SKIPPED = 'skipped'
    FAILED = 'failed'


@dataclass
class DiscoveryResult:
    """Result of a session discovery operation."""
    total_discovered: int
    new_sessions: int
    already_known: int
    sessions: List[SessionInfo]
    errors: List[str]
    duration_seconds: float


@dataclass
class ImportQueueItem:
    """Item in the import queue."""
    report_id: str
    api_key: str
    portal_name: Optional[str]
    session_date: Optional[datetime]
    priority: int
    status: ImportStatus
    attempts: int
    last_attempt: Optional[datetime]
    error_message: Optional[str]


class SessionDiscovery:
    """
    Manages session discovery and import tracking.

    This class:
    1. Discovers sessions from Uneekor portal
    2. Tracks discovered sessions in local database
    3. Deduplicates against already-imported shots
    4. Manages import queue with priorities
    5. Provides checkpoint/resume support

    Usage:
        discovery = SessionDiscovery()

        # Initialize database tables
        discovery.init_tables()

        # Discover new sessions
        result = await discovery.discover_sessions()
        print(f"Found {result.new_sessions} new sessions")

        # Get sessions ready for import
        pending = discovery.get_pending_sessions(limit=10)

        # Mark session as imported
        discovery.mark_imported(report_id, shot_count=75)
    """

    # SQL for creating discovery tables
    CREATE_SESSIONS_DISCOVERED_SQL = '''
        CREATE TABLE IF NOT EXISTS sessions_discovered (
            report_id TEXT PRIMARY KEY,
            api_key TEXT NOT NULL,
            portal_name TEXT,
            session_date TIMESTAMP,
            shot_count_expected INTEGER,
            clubs_json TEXT,
            source_url TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            import_status TEXT DEFAULT 'pending',
            import_started_at TIMESTAMP,
            import_completed_at TIMESTAMP,
            import_shots_actual INTEGER,
            import_error TEXT,
            skip_reason TEXT,
            last_checked_at TIMESTAMP,
            checksum TEXT,
            priority INTEGER DEFAULT 0,
            session_name TEXT,
            session_type TEXT,
            tags_json TEXT
        )
    '''

    CREATE_AUTOMATION_RUNS_SQL = '''
        CREATE TABLE IF NOT EXISTS automation_runs (
            run_id TEXT PRIMARY KEY,
            run_type TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            status TEXT DEFAULT 'running',
            sessions_discovered INTEGER DEFAULT 0,
            sessions_imported INTEGER DEFAULT 0,
            sessions_skipped INTEGER DEFAULT 0,
            sessions_failed INTEGER DEFAULT 0,
            total_shots_imported INTEGER DEFAULT 0,
            trigger_source TEXT,
            error_log TEXT,
            duration_seconds REAL,
            config_json TEXT
        )
    '''

    CREATE_INDEXES_SQL = [
        'CREATE INDEX IF NOT EXISTS idx_sessions_discovered_status ON sessions_discovered(import_status)',
        'CREATE INDEX IF NOT EXISTS idx_sessions_discovered_date ON sessions_discovered(session_date)',
        'CREATE INDEX IF NOT EXISTS idx_sessions_discovered_priority ON sessions_discovered(priority DESC)',
        'CREATE INDEX IF NOT EXISTS idx_automation_runs_type ON automation_runs(run_type)',
    ]

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize session discovery.

        Args:
            db_path: Path to SQLite database (uses golf_db default if not specified)
        """
        if db_path:
            self.db_path = db_path
        elif HAS_GOLF_DB:
            self.db_path = golf_db.SQLITE_DB_PATH
        else:
            self.db_path = Path(__file__).parent.parent / 'golf_stats.db'

    def init_tables(self) -> None:
        """Create discovery tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(self.CREATE_SESSIONS_DISCOVERED_SQL)
            cursor.execute(self.CREATE_AUTOMATION_RUNS_SQL)
            for index_sql in self.CREATE_INDEXES_SQL:
                cursor.execute(index_sql)
            conn.commit()
            print("Discovery tables initialized")
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_known_report_ids(self) -> List[str]:
        """
        Get all report IDs that have been discovered or imported.

        Returns:
            List of report IDs
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute('SELECT report_id FROM sessions_discovered')
            return [row['report_id'] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_imported_report_ids(self) -> List[str]:
        """
        Get report IDs that have been successfully imported.

        Checks both sessions_discovered table and actual shots table.

        Returns:
            List of imported report IDs
        """
        conn = self._get_connection()
        try:
            # From discovery tracking
            cursor = conn.execute(
                "SELECT report_id FROM sessions_discovered WHERE import_status = 'imported'"
            )
            discovered_imported = {row['report_id'] for row in cursor.fetchall()}

            # From actual shots (session_id = report_id)
            try:
                cursor = conn.execute('SELECT DISTINCT session_id FROM shots')
                shots_sessions = {row['session_id'] for row in cursor.fetchall()}
            except sqlite3.OperationalError:
                shots_sessions = set()

            return list(discovered_imported | shots_sessions)
        finally:
            conn.close()

    def save_discovered_session(self, session: SessionInfo) -> bool:
        """
        Save a discovered session to the database.

        Uses UPSERT to update if exists or insert if new.

        Args:
            session: SessionInfo to save

        Returns:
            True if new session, False if updated existing
        """
        conn = self._get_connection()
        try:
            # Check if exists
            cursor = conn.execute(
                'SELECT report_id FROM sessions_discovered WHERE report_id = ?',
                (session.report_id,)
            )
            exists = cursor.fetchone() is not None

            clubs_json = json.dumps(session.clubs_used) if session.clubs_used else None

            if exists:
                # Update existing
                conn.execute('''
                    UPDATE sessions_discovered
                    SET last_checked_at = ?,
                        portal_name = COALESCE(?, portal_name),
                        session_date = COALESCE(?, session_date),
                        clubs_json = COALESCE(?, clubs_json)
                    WHERE report_id = ?
                ''', (
                    datetime.utcnow().isoformat(),
                    session.portal_name,
                    session.session_date.isoformat() if session.session_date else None,
                    clubs_json,
                    session.report_id,
                ))
            else:
                # Insert new
                conn.execute('''
                    INSERT INTO sessions_discovered
                    (report_id, api_key, portal_name, session_date, clubs_json, source_url, discovered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session.report_id,
                    session.api_key,
                    session.portal_name,
                    session.session_date.isoformat() if session.session_date else None,
                    clubs_json,
                    session.source_url,
                    datetime.utcnow().isoformat(),
                ))

            conn.commit()
            return not exists
        finally:
            conn.close()

    def get_pending_sessions(
        self,
        limit: int = 10,
        date_start: Optional[datetime] = None,
        date_end: Optional[datetime] = None,
    ) -> List[ImportQueueItem]:
        """
        Get sessions pending import.

        Args:
            limit: Maximum number to return
            date_start: Only include sessions after this date
            date_end: Only include sessions before this date

        Returns:
            List of ImportQueueItem objects
        """
        conn = self._get_connection()
        try:
            query = '''
                SELECT * FROM sessions_discovered
                WHERE import_status = 'pending'
            '''
            params = []

            if date_start:
                query += ' AND session_date >= ?'
                params.append(date_start.isoformat())

            if date_end:
                query += ' AND session_date <= ?'
                params.append(date_end.isoformat())

            query += ' ORDER BY priority DESC, session_date DESC LIMIT ?'
            params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            items = []
            for row in rows:
                items.append(ImportQueueItem(
                    report_id=row['report_id'],
                    api_key=row['api_key'],
                    portal_name=row['portal_name'],
                    session_date=datetime.fromisoformat(row['session_date']) if row['session_date'] else None,
                    priority=row['priority'] or 0,
                    status=ImportStatus(row['import_status']),
                    attempts=0,  # Not tracked in current schema
                    last_attempt=None,
                    error_message=row['import_error'],
                ))

            return items
        finally:
            conn.close()

    def mark_importing(self, report_id: str) -> None:
        """Mark a session as currently being imported."""
        conn = self._get_connection()
        try:
            conn.execute('''
                UPDATE sessions_discovered
                SET import_status = 'importing',
                    import_started_at = ?
                WHERE report_id = ?
            ''', (datetime.utcnow().isoformat(), report_id))
            conn.commit()
        finally:
            conn.close()

    def mark_imported(
        self,
        report_id: str,
        shot_count: int,
        session_name: Optional[str] = None,
        session_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Mark a session as successfully imported.

        Args:
            report_id: The report ID
            shot_count: Number of shots imported
            session_name: Generated session name
            session_type: Inferred session type
            tags: Auto-generated tags
        """
        conn = self._get_connection()
        try:
            conn.execute('''
                UPDATE sessions_discovered
                SET import_status = 'imported',
                    import_completed_at = ?,
                    import_shots_actual = ?,
                    session_name = ?,
                    session_type = ?,
                    tags_json = ?,
                    import_error = NULL
                WHERE report_id = ?
            ''', (
                datetime.utcnow().isoformat(),
                shot_count,
                session_name,
                session_type,
                json.dumps(tags) if tags else None,
                report_id,
            ))
            conn.commit()
        finally:
            conn.close()

    def mark_failed(self, report_id: str, error: str) -> None:
        """Mark a session as failed to import."""
        conn = self._get_connection()
        try:
            conn.execute('''
                UPDATE sessions_discovered
                SET import_status = 'failed',
                    import_error = ?
                WHERE report_id = ?
            ''', (error, report_id))
            conn.commit()
        finally:
            conn.close()

    def mark_skipped(self, report_id: str, reason: str) -> None:
        """Mark a session as skipped."""
        conn = self._get_connection()
        try:
            conn.execute('''
                UPDATE sessions_discovered
                SET import_status = 'skipped',
                    skip_reason = ?
                WHERE report_id = ?
            ''', (reason, report_id))
            conn.commit()
        finally:
            conn.close()

    def set_priority(self, report_id: str, priority: int) -> None:
        """Set the import priority for a session."""
        conn = self._get_connection()
        try:
            conn.execute(
                'UPDATE sessions_discovered SET priority = ? WHERE report_id = ?',
                (priority, report_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_discovery_stats(self) -> Dict[str, Any]:
        """
        Get statistics about discovered sessions.

        Returns:
            Dict with counts by status and other stats
        """
        conn = self._get_connection()
        try:
            stats = {}

            # Count by status
            cursor = conn.execute('''
                SELECT import_status, COUNT(*) as count
                FROM sessions_discovered
                GROUP BY import_status
            ''')
            stats['by_status'] = {row['import_status']: row['count'] for row in cursor.fetchall()}

            # Total shots imported
            cursor = conn.execute('''
                SELECT SUM(import_shots_actual) as total
                FROM sessions_discovered
                WHERE import_status = 'imported'
            ''')
            row = cursor.fetchone()
            stats['total_shots_imported'] = row['total'] or 0

            # Date range
            cursor = conn.execute('''
                SELECT MIN(session_date) as earliest, MAX(session_date) as latest
                FROM sessions_discovered
            ''')
            row = cursor.fetchone()
            stats['date_range'] = {
                'earliest': row['earliest'],
                'latest': row['latest'],
            }

            # Recent activity
            cursor = conn.execute('''
                SELECT COUNT(*) as count
                FROM sessions_discovered
                WHERE discovered_at > datetime('now', '-7 days')
            ''')
            stats['discovered_last_7_days'] = cursor.fetchone()['count']

            return stats
        finally:
            conn.close()

    async def discover_sessions(
        self,
        headless: bool = True,
        max_sessions: Optional[int] = None,
        since_date: Optional[datetime] = None,
    ) -> DiscoveryResult:
        """
        Discover sessions from Uneekor portal and save to database.

        Args:
            headless: Run browser in headless mode
            max_sessions: Maximum sessions to discover
            since_date: Only discover sessions after this date

        Returns:
            DiscoveryResult with statistics
        """
        start_time = datetime.utcnow()
        errors = []
        new_count = 0
        known_count = 0
        sessions = []

        try:
            # Get already known report IDs
            known_ids = set(self.get_known_report_ids())

            # Discover from portal
            config = BrowserConfig(headless=headless)
            client = PlaywrightClient(config=config)

            async with client:
                login_success = await client.login()
                if not login_success:
                    errors.append("Failed to log in to Uneekor portal")
                    return DiscoveryResult(
                        total_discovered=0,
                        new_sessions=0,
                        already_known=0,
                        sessions=[],
                        errors=errors,
                        duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    )

                navigator = UneekorPortalNavigator(browser_client=client)
                discovered = await navigator.get_all_sessions(
                    max_sessions=max_sessions,
                    since_date=since_date,
                )

                for session in discovered:
                    sessions.append(session)
                    is_new = self.save_discovered_session(session)
                    if is_new:
                        new_count += 1
                    else:
                        known_count += 1

        except Exception as e:
            errors.append(f"Discovery error: {str(e)}")

        duration = (datetime.utcnow() - start_time).total_seconds()

        return DiscoveryResult(
            total_discovered=len(sessions),
            new_sessions=new_count,
            already_known=known_count,
            sessions=sessions,
            errors=errors,
            duration_seconds=duration,
        )

    def start_automation_run(
        self,
        run_type: str,
        trigger_source: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Start tracking an automation run.

        Args:
            run_type: Type of run (discovery, backfill, scheduled)
            trigger_source: What triggered the run (cli, scheduler, manual)
            config: Configuration used for the run

        Returns:
            run_id for the new run
        """
        import uuid
        run_id = str(uuid.uuid4())[:8]

        conn = self._get_connection()
        try:
            conn.execute('''
                INSERT INTO automation_runs
                (run_id, run_type, trigger_source, config_json)
                VALUES (?, ?, ?, ?)
            ''', (
                run_id,
                run_type,
                trigger_source,
                json.dumps(config) if config else None,
            ))
            conn.commit()
            return run_id
        finally:
            conn.close()

    def complete_automation_run(
        self,
        run_id: str,
        sessions_discovered: int = 0,
        sessions_imported: int = 0,
        sessions_skipped: int = 0,
        sessions_failed: int = 0,
        total_shots: int = 0,
        errors: Optional[List[str]] = None,
    ) -> None:
        """Complete an automation run with results."""
        conn = self._get_connection()
        try:
            # Get start time to calculate duration
            cursor = conn.execute(
                'SELECT started_at FROM automation_runs WHERE run_id = ?',
                (run_id,)
            )
            row = cursor.fetchone()
            start_time = datetime.fromisoformat(row['started_at']) if row else datetime.utcnow()
            duration = (datetime.utcnow() - start_time).total_seconds()

            conn.execute('''
                UPDATE automation_runs
                SET completed_at = ?,
                    status = 'completed',
                    sessions_discovered = ?,
                    sessions_imported = ?,
                    sessions_skipped = ?,
                    sessions_failed = ?,
                    total_shots_imported = ?,
                    error_log = ?,
                    duration_seconds = ?
                WHERE run_id = ?
            ''', (
                datetime.utcnow().isoformat(),
                sessions_discovered,
                sessions_imported,
                sessions_skipped,
                sessions_failed,
                total_shots,
                json.dumps(errors) if errors else None,
                duration,
                run_id,
            ))
            conn.commit()
        finally:
            conn.close()

    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent automation runs."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM automation_runs
                ORDER BY started_at DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


# Convenience functions
def get_discovery() -> SessionDiscovery:
    """Get a SessionDiscovery instance."""
    discovery = SessionDiscovery()
    discovery.init_tables()
    return discovery
