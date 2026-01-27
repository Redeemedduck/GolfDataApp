"""
Integration tests for session date reclassification functionality.

Tests the database operations for:
- backfill_session_dates()
- update_session_date_for_shots()
- get_sessions_missing_dates()
"""

import unittest
import sqlite3
import tempfile
import os
from datetime import datetime
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import golf_db


class TestDateReclassification(unittest.TestCase):
    """Test session date reclassification database operations."""

    def setUp(self):
        """Set up test database."""
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_golf.db')

        # Override the database path in golf_db
        self.original_db_path = golf_db.SQLITE_DB_PATH
        golf_db.SQLITE_DB_PATH = self.db_path

        # Initialize database
        golf_db.init_db()

        # Create sessions_discovered table (normally in session_discovery.py)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions_discovered (
                report_id TEXT PRIMARY KEY,
                api_key TEXT NOT NULL,
                portal_name TEXT,
                session_date TIMESTAMP,
                date_source TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def tearDown(self):
        """Clean up test database."""
        golf_db.SQLITE_DB_PATH = self.original_db_path
        try:
            os.unlink(self.db_path)
            os.rmdir(self.temp_dir)
        except:
            pass

    def _insert_test_shot(self, shot_id, session_id, session_date=None):
        """Helper to insert a test shot."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO shots (shot_id, session_id, club, carry, total, session_date)
            VALUES (?, ?, 'Driver', 250.0, 270.0, ?)
        ''', (shot_id, session_id, session_date))
        conn.commit()
        conn.close()

    def _insert_discovered_session(self, report_id, session_date, api_key='test_key'):
        """Helper to insert a discovered session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sessions_discovered (report_id, api_key, session_date, date_source)
            VALUES (?, ?, ?, 'test')
        ''', (report_id, api_key, session_date))
        conn.commit()
        conn.close()

    def test_backfill_session_dates(self):
        """Test backfilling session dates from sessions_discovered to shots."""
        # Insert shots without session_date
        self._insert_test_shot('shot_1', 'session_123')
        self._insert_test_shot('shot_2', 'session_123')
        self._insert_test_shot('shot_3', 'session_456')

        # Insert discovered sessions with dates
        self._insert_discovered_session('session_123', '2026-01-15T10:00:00')
        self._insert_discovered_session('session_456', '2026-01-16T14:30:00')

        # Run backfill
        result = golf_db.backfill_session_dates()

        # Verify results
        self.assertEqual(result['updated'], 3)
        self.assertEqual(result['errors'], 0)

        # Verify shots now have session_date
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT session_date FROM shots WHERE session_id = ?', ('session_123',))
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()

        self.assertEqual(len(dates), 2)
        for d in dates:
            self.assertIsNotNone(d)
            self.assertIn('2026-01-15', d)

    def test_backfill_skips_existing_dates(self):
        """Test that backfill doesn't overwrite existing session dates."""
        # Insert shot with existing session_date
        self._insert_test_shot('shot_1', 'session_123', session_date='2026-01-10T08:00:00')

        # Insert discovered session with different date
        self._insert_discovered_session('session_123', '2026-01-15T10:00:00')

        # Run backfill
        result = golf_db.backfill_session_dates()

        # Should skip since date already exists
        self.assertEqual(result['updated'], 0)
        self.assertEqual(result['skipped'], 1)

        # Verify original date is preserved
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT session_date FROM shots WHERE shot_id = ?', ('shot_1',))
        date = cursor.fetchone()[0]
        conn.close()

        self.assertIn('2026-01-10', date)

    def test_get_sessions_missing_dates(self):
        """Test getting sessions that are missing dates."""
        # Insert shots - some with dates, some without
        self._insert_test_shot('shot_1', 'session_no_date_1')
        self._insert_test_shot('shot_2', 'session_no_date_1')
        self._insert_test_shot('shot_3', 'session_no_date_2')
        self._insert_test_shot('shot_4', 'session_with_date', session_date='2026-01-15T10:00:00')

        # Get sessions missing dates
        missing = golf_db.get_sessions_missing_dates(limit=100)

        # Should find 2 sessions without dates
        session_ids = [s['session_id'] for s in missing]
        self.assertIn('session_no_date_1', session_ids)
        self.assertIn('session_no_date_2', session_ids)
        self.assertNotIn('session_with_date', session_ids)

    def test_update_session_date_for_shots(self):
        """Test manually updating session date for all shots in a session."""
        # Insert shots
        self._insert_test_shot('shot_1', 'session_123')
        self._insert_test_shot('shot_2', 'session_123')
        self._insert_test_shot('shot_3', 'session_456')

        # Update date for session_123
        updated = golf_db.update_session_date_for_shots('session_123', '2026-01-20')

        # Verify
        self.assertEqual(updated, 2)

        # Check the dates
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT session_date FROM shots WHERE session_id = ?', ('session_123',))
        dates = [row[0] for row in cursor.fetchall()]
        for d in dates:
            self.assertEqual(d, '2026-01-20')

        # Session 456 should still be NULL
        cursor.execute('SELECT session_date FROM shots WHERE session_id = ?', ('session_456',))
        date_456 = cursor.fetchone()[0]
        self.assertIsNone(date_456)

        conn.close()


class TestSessionDateInSaveShot(unittest.TestCase):
    """Test that save_shot properly handles session_date."""

    def setUp(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_golf.db')
        self.original_db_path = golf_db.SQLITE_DB_PATH
        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.init_db()

    def tearDown(self):
        """Clean up test database."""
        golf_db.SQLITE_DB_PATH = self.original_db_path
        try:
            os.unlink(self.db_path)
            os.rmdir(self.temp_dir)
        except:
            pass

    def test_save_shot_with_session_date(self):
        """Test saving a shot with session_date included."""
        shot_data = {
            'id': 'test_shot_1',
            'session': 'test_session_1',
            'session_date': '2026-01-15T10:30:00',
            'club': 'Driver',
            'carry_distance': 265.0,
            'total_distance': 285.0,
            'ball_speed': 165.0,
            'club_speed': 115.0,
        }

        golf_db.save_shot(shot_data)

        # Verify the shot was saved with session_date
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT session_date FROM shots WHERE shot_id = ?', ('test_shot_1',))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], '2026-01-15T10:30:00')

    def test_save_shot_without_session_date(self):
        """Test saving a shot without session_date (backwards compatibility)."""
        shot_data = {
            'id': 'test_shot_2',
            'session': 'test_session_2',
            'club': '7 Iron',
            'carry_distance': 165.0,
            'total_distance': 175.0,
        }

        golf_db.save_shot(shot_data)

        # Verify the shot was saved (session_date should be NULL)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT shot_id, session_date FROM shots WHERE shot_id = ?', ('test_shot_2',))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'test_shot_2')
        self.assertIsNone(result[1])  # session_date should be None


if __name__ == '__main__':
    unittest.main()
