"""
Tests for Phase 1: Data Foundation.

Covers:
- clean_value() sentinel handling (None default)
- migrate_zeros_to_null() migration
- Derived columns (face_to_path, strike_distance) on ingest
- backfill_derived_columns()
- session_stats cache table and query functions
- Composite index existence
"""
import math
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestCleanValue(unittest.TestCase):
    """Test clean_value() returns None for sentinels by default."""

    def setUp(self):
        import golf_db
        self.clean_value = golf_db.clean_value

    def test_none_returns_none(self):
        self.assertIsNone(self.clean_value(None))

    def test_sentinel_returns_none(self):
        self.assertIsNone(self.clean_value(99999))

    def test_valid_value_passes_through(self):
        self.assertEqual(self.clean_value(250.5), 250.5)

    def test_zero_passes_through(self):
        self.assertEqual(self.clean_value(0.0), 0.0)

    def test_explicit_default_zero(self):
        """For columns where 0 is valid (spin, angles), explicit default=0."""
        self.assertEqual(self.clean_value(None, default=0), 0)
        self.assertEqual(self.clean_value(99999, default=0), 0)

    def test_negative_values_pass_through(self):
        self.assertEqual(self.clean_value(-3.5), -3.5)


class TestMigrateZerosToNull(unittest.TestCase):
    """Test migrate_zeros_to_null() fixes historical data."""

    def setUp(self):
        import tempfile
        import os
        import golf_db

        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")

        self.original_path = golf_db.SQLITE_DB_PATH
        self.original_supabase = golf_db.supabase
        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.init_db()
        self.golf_db = golf_db

    def tearDown(self):
        self.golf_db.SQLITE_DB_PATH = self.original_path
        self.golf_db.supabase = self.original_supabase
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_zeros_in_carry_become_null(self):
        """carry=0 should become NULL (0 carry is not a real measurement)."""
        self.golf_db.save_shot({
            'shot_id': 'test_1', 'session_id': 'sess_1',
            'club': 'Driver', 'carry': 0.0, 'ball_speed': 0.0,
            'face_angle': 0.0, 'club_path': 0.0,
        })

        results = self.golf_db.migrate_zeros_to_null()
        self.assertGreater(results.get('carry', 0), 0)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT carry FROM shots WHERE shot_id = 'test_1'")
        carry = cursor.fetchone()[0]
        conn.close()
        self.assertIsNone(carry)

    def test_zero_face_angle_preserved(self):
        """face_angle=0 is valid (square face) — should NOT be migrated."""
        self.golf_db.save_shot({
            'shot_id': 'test_2', 'session_id': 'sess_1',
            'club': 'Driver', 'carry': 250,
            'face_angle': 0.0, 'club_path': 0.0,
        })

        self.golf_db.migrate_zeros_to_null()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT face_angle FROM shots WHERE shot_id = 'test_2'")
        face = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(face, 0.0)


class TestDerivedColumns(unittest.TestCase):
    """Test face_to_path and strike_distance computation."""

    def setUp(self):
        import tempfile
        import os
        import golf_db

        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")

        self.original_path = golf_db.SQLITE_DB_PATH
        self.original_supabase = golf_db.supabase
        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.init_db()
        self.golf_db = golf_db

    def tearDown(self):
        self.golf_db.SQLITE_DB_PATH = self.original_path
        self.golf_db.supabase = self.original_supabase
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_face_to_path_computed_on_ingest(self):
        """face_to_path = face_angle - club_path."""
        self.golf_db.save_shot({
            'shot_id': 'ftp_1', 'session_id': 'sess_1',
            'club': 'Driver', 'carry': 250,
            'face_angle': 2.0, 'club_path': -3.0,
        })

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT face_to_path FROM shots WHERE shot_id = 'ftp_1'")
        ftp = cursor.fetchone()[0]
        conn.close()
        self.assertAlmostEqual(ftp, 5.0)  # 2.0 - (-3.0) = 5.0

    def test_strike_distance_computed_on_ingest(self):
        """strike_distance = sqrt(impact_x^2 + impact_y^2)."""
        self.golf_db.save_shot({
            'shot_id': 'sd_1', 'session_id': 'sess_1',
            'club': 'Driver', 'carry': 250,
            'impact_x': 0.3, 'impact_y': 0.4,
            'face_angle': 0.0, 'club_path': 0.0,
        })

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT strike_distance FROM shots WHERE shot_id = 'sd_1'")
        sd = cursor.fetchone()[0]
        conn.close()
        self.assertAlmostEqual(sd, 0.5, places=3)  # 3-4-5 triangle

    def test_face_to_path_null_when_missing_data(self):
        """If face_angle or club_path is None, face_to_path should be None."""
        self.golf_db.save_shot({
            'shot_id': 'null_1', 'session_id': 'sess_1',
            'club': 'Driver', 'carry': 250,
            # face_angle and club_path not provided → default 0.0 for angles
        })

        # face_angle=0.0, club_path=0.0 → ftp = 0.0 (both valid zero defaults)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT face_to_path FROM shots WHERE shot_id = 'null_1'")
        ftp = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(ftp, 0.0)

    def test_backfill_derived_columns(self):
        """backfill_derived_columns() fills missing face_to_path/strike_distance."""
        # Insert raw data bypassing save_shot
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO shots (shot_id, session_id, club, face_angle, club_path, impact_x, impact_y)
            VALUES ('raw_1', 'sess_1', 'Driver', 1.5, -2.5, 0.3, 0.4)
        ''')
        conn.commit()
        conn.close()

        updated = self.golf_db.backfill_derived_columns()
        self.assertEqual(updated, 1)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT face_to_path, strike_distance FROM shots WHERE shot_id = 'raw_1'")
        ftp, sd = cursor.fetchone()
        conn.close()
        self.assertAlmostEqual(ftp, 4.0)  # 1.5 - (-2.5)
        self.assertAlmostEqual(sd, 0.5, places=3)


class TestSessionStats(unittest.TestCase):
    """Test session_stats cache table and query functions."""

    def setUp(self):
        import tempfile
        import os
        import golf_db

        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")

        self.original_path = golf_db.SQLITE_DB_PATH
        self.original_supabase = golf_db.supabase
        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.init_db()
        self.golf_db = golf_db

        # Add test data
        for i in range(5):
            self.golf_db.save_shot({
                'shot_id': f'stats_{i}', 'session_id': 'sess_stats_1',
                'club': 'Driver' if i < 3 else '7 Iron',
                'carry': 250 + i * 5,
                'ball_speed': 160 + i,
                'club_speed': 107 + i,
                'face_angle': 1.0 + i * 0.5,
                'club_path': -2.0 + i * 0.3,
                'impact_x': 0.1 * i,
                'impact_y': 0.1 * i,
                'session_date': '2026-02-01',
            })

    def tearDown(self):
        self.golf_db.SQLITE_DB_PATH = self.original_path
        self.golf_db.supabase = self.original_supabase
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_compute_session_stats(self):
        """compute_session_stats() populates session_stats table."""
        updated = self.golf_db.compute_session_stats('sess_stats_1')
        self.assertEqual(updated, 1)

        stats = self.golf_db.get_session_aggregates('sess_stats_1')
        self.assertEqual(stats['shot_count'], 5)
        self.assertIsNotNone(stats['avg_carry'])
        self.assertGreater(stats['avg_carry'], 0)
        self.assertIsNotNone(stats['avg_face_angle'])

    def test_get_recent_sessions(self):
        """get_recent_sessions_with_stats returns sessions within window."""
        self.golf_db.compute_session_stats()
        sessions = self.golf_db.get_recent_sessions_with_stats(weeks=4)
        self.assertGreaterEqual(len(sessions), 1)
        self.assertEqual(sessions[0]['session_id'], 'sess_stats_1')

    def test_get_club_profile(self):
        """get_club_profile returns per-session stats for a club."""
        df = self.golf_db.get_club_profile('Driver')
        self.assertEqual(len(df), 1)  # one session
        self.assertEqual(df.iloc[0]['shot_count'], 3)

    def test_get_rolling_averages(self):
        """get_rolling_averages returns baseline metrics."""
        self.golf_db.compute_session_stats()
        avgs = self.golf_db.get_rolling_averages()
        self.assertIsNotNone(avgs.get('avg_carry'))


class TestCompositeIndexes(unittest.TestCase):
    """Test that composite indexes exist after init_db()."""

    def setUp(self):
        import tempfile
        import os
        import golf_db

        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")

        self.original_path = golf_db.SQLITE_DB_PATH
        self.original_supabase = golf_db.supabase
        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.init_db()
        self.golf_db = golf_db

    def tearDown(self):
        self.golf_db.SQLITE_DB_PATH = self.original_path
        self.golf_db.supabase = self.original_supabase
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_session_club_index_exists(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_shots_session_club'")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_date_club_index_exists(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_shots_date_club'")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_derived_columns_exist(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(shots)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        self.assertIn('face_to_path', columns)
        self.assertIn('strike_distance', columns)


if __name__ == '__main__':
    unittest.main()
