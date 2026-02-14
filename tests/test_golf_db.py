import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta

try:
    import pandas as pd
    import golf_db
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "pandas not installed")
class TestGolfDB(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test.db")
        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.init_db()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_save_and_get_session_data(self):
        shot = {
            "shot_id": "s1",
            "session_id": "sess1",
            "club": "Driver",
            "carry": 250,
            "total": 270,
            "ball_speed": 150,
            "club_speed": 100,
            "smash": 0,
        }
        golf_db.save_shot(shot)

        df = golf_db.get_session_data("sess1")
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["shot_id"], "s1")

    def test_save_shot_normalizes_club(self):
        """save_shot() should normalize club names and preserve original."""
        shot_data = {
            "id": "test_norm_001",
            "session": "session_norm",
            "club": "Warmup Pw",
            "carry_distance": 120,
        }
        golf_db.save_shot(shot_data)

        conn = sqlite3.connect(golf_db.SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT club, original_club_value FROM shots WHERE shot_id = ?",
            ("test_norm_001",),
        )
        row = cursor.fetchone()
        conn.close()

        self.assertEqual(row[0], "PW")
        self.assertEqual(row[1], "Warmup Pw")

    def test_save_shot_preserves_standard_club(self):
        """save_shot() should not alter already-standard club names."""
        shot_data = {
            "id": "test_norm_002",
            "session": "session_norm",
            "club": "7 Iron",
            "carry_distance": 165,
        }
        golf_db.save_shot(shot_data)

        conn = sqlite3.connect(golf_db.SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT club, original_club_value FROM shots WHERE shot_id = ?",
            ("test_norm_002",),
        )
        row = cursor.fetchone()
        conn.close()

        self.assertEqual(row[0], "7 Iron")
        self.assertEqual(row[1], "7 Iron")

    def test_save_shot_unknown_session_name(self):
        """save_shot() should set club=None for unresolvable session names."""
        shot_data = {
            "id": "test_norm_003",
            "session": "session_norm",
            "club": "Sgt Rd1",
            "carry_distance": 250,
        }
        golf_db.save_shot(shot_data)

        conn = sqlite3.connect(golf_db.SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT club, original_club_value FROM shots WHERE shot_id = ?",
            ("test_norm_003",),
        )
        row = cursor.fetchone()
        conn.close()

        self.assertIsNone(row[0])
        self.assertEqual(row[1], "Sgt Rd1")

    def test_recalculate_metrics_updates_smash(self):
        shot = {
            "shot_id": "s2",
            "session_id": "sess1",
            "club": "Driver",
            "carry": 250,
            "total": 270,
            "ball_speed": 150,
            "club_speed": 100,
            "smash": 0,
        }
        golf_db.save_shot(shot)

        updated = golf_db.recalculate_metrics("sess1")
        self.assertEqual(updated, 1)

        df = golf_db.get_session_data("sess1")
        self.assertAlmostEqual(df.iloc[0]["smash"], 1.5, places=2)

    def test_find_outliers_flags_bad_values(self):
        shots = [
            {
                "shot_id": "ok1",
                "session_id": "sess1",
                "club": "Driver",
                "carry": 250,
                "total": 270,
                "ball_speed": 150,
                "club_speed": 100,
                "smash": 1.5,
            },
            {
                "shot_id": "bad1",
                "session_id": "sess1",
                "club": "Driver",
                "carry": 500,
                "total": 520,
                "ball_speed": 210,
                "club_speed": 100,
                "smash": 1.7,
            },
        ]
        for shot in shots:
            golf_db.save_shot(shot)

        outliers = golf_db.find_outliers("sess1")
        self.assertIn("bad1", outliers["shot_id"].tolist())

    def test_merge_shots_prefers_local(self):
        local_df = pd.DataFrame(
            [
                {"shot_id": "s1", "carry": 250},
                {"shot_id": "s2", "carry": 200},
            ]
        )
        cloud_df = pd.DataFrame(
            [
                {"shot_id": "s1", "carry": 240},
                {"shot_id": "s3", "carry": 190},
            ]
        )
        merged = golf_db._merge_shots(local_df, cloud_df)
        merged_row = merged[merged["shot_id"] == "s1"].iloc[0]
        self.assertEqual(merged_row["carry"], 250)
        self.assertEqual(len(merged), 3)

    def test_update_shot_metadata_rejects_invalid_field(self):
        """SQL injection should be prevented by field allowlist."""
        shot = {
            "shot_id": "s1",
            "session_id": "sess1",
            "club": "Driver",
            "carry": 250,
        }
        golf_db.save_shot(shot)

        # Attempt SQL injection via field parameter
        with self.assertRaises(ValueError) as ctx:
            golf_db.update_shot_metadata(
                ["s1"],
                "club; DROP TABLE shots; --",  # Injection attempt
                "Hacked"
            )
        self.assertIn("Invalid field", str(ctx.exception))
        self.assertIn("Allowed fields", str(ctx.exception))

    def test_update_shot_metadata_allows_valid_field(self):
        """Valid fields should work correctly."""
        shot = {
            "shot_id": "s1",
            "session_id": "sess1",
            "club": "Driver",
            "carry": 250,
        }
        golf_db.save_shot(shot)

        # Update with valid field
        updated = golf_db.update_shot_metadata(["s1"], "shot_tag", "Warmup")
        self.assertEqual(updated, 1)

        # Verify the update
        df = golf_db.get_session_data("sess1")
        self.assertEqual(df.iloc[0]["shot_tag"], "Warmup")

    def test_update_session_date_rejects_future_dates(self):
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        with self.assertRaisesRegex(ValueError, "future"):
            golf_db.update_session_date_for_shots("sess1", future_date)

    def test_get_sync_drift_returns_meaningful_data(self):
        """Verify drift detection identifies local-only records."""
        for i in range(5):
            shot = {
                "shot_id": f"drift_test_{i}",
                "session_id": "sess1",
                "club": "Driver",
                "carry": 250,
                "total": 270,
                "ball_speed": 150,
                "club_speed": 100,
                "smash": 0,
            }
            golf_db.save_shot(shot)

        status = golf_db.get_detailed_sync_status()

        self.assertIn("local_only_count", status)
        self.assertIn("last_sync", status)
        self.assertGreaterEqual(status["local_only_count"], 5)

    def test_sync_audit_table_exists(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sync_audit'"
        )
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_sync_to_supabase_creates_audit_record(self):
        golf_db.sync_to_supabase(dry_run=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM sync_audit WHERE sync_type = 'to_supabase'"
        )
        count = cursor.fetchone()[0]
        conn.close()

        self.assertGreaterEqual(count, 1)


class TestNewSchemaColumns(unittest.TestCase):
    def setUp(self):
        self.db_path = tempfile.mktemp(suffix='.db')
        golf_db.SQLITE_DB_PATH = self.db_path
        os.environ.pop('SUPABASE_URL', None)
        golf_db._supabase = None
        golf_db.init_db()

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_sidebar_label_column_exists(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(shots)')
        columns = [row[1] for row in cursor.fetchall()]
        self.assertIn('sidebar_label', columns)
        self.assertIn('uneekor_club_id', columns)
        conn.close()

    def test_save_shot_with_sidebar_label(self):
        shot = {
            'id': 'test_schema_1_1_1',
            'session': 'test_schema_1',
            'club': 'Driver',
            'sidebar_label': 'driver practice',
            'uneekor_club_id': 0,
            'original_club_value': 'DRIVER',
            'carry_distance': 250.0,
            'ball_speed': 150.0,
        }
        golf_db.save_shot(shot)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sidebar_label, uneekor_club_id FROM shots WHERE shot_id = 'test_schema_1_1_1'")
        row = cursor.fetchone()
        self.assertEqual(row[0], 'driver practice')
        self.assertEqual(row[1], 0)
        conn.close()

    def test_allowed_update_fields_includes_new_columns(self):
        from golf_db import ALLOWED_UPDATE_FIELDS
        self.assertIn('sidebar_label', ALLOWED_UPDATE_FIELDS)
        self.assertIn('uneekor_club_id', ALLOWED_UPDATE_FIELDS)
        self.assertIn('original_club_value', ALLOWED_UPDATE_FIELDS)


class TestSessionNotes(unittest.TestCase):
    def setUp(self):
        self.original_db_path = golf_db.SQLITE_DB_PATH
        self.original_supabase = golf_db.supabase
        self.db_path = tempfile.mktemp(suffix=".db")
        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.init_db()

    def tearDown(self):
        golf_db.SQLITE_DB_PATH = self.original_db_path
        golf_db.supabase = self.original_supabase
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_session_notes_column_exists(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(shots)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        self.assertIn("session_notes", columns)

    def test_session_notes_in_allowed_fields(self):
        self.assertIn("session_notes", golf_db.ALLOWED_UPDATE_FIELDS)


if __name__ == "__main__":
    unittest.main()
