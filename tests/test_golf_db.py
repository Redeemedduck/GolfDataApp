import os
import tempfile
import unittest

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


@unittest.skipUnless(HAS_DEPS, "pandas not installed")
class TestSessionMetrics(unittest.TestCase):
    """Test session metrics computation and storage."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test.db")
        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.init_db()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_update_session_metrics_computes_stats(self):
        """Adding shots and calling update_session_metrics should compute stats."""
        # Add 5 shots to a session
        shots = [
            {
                "shot_id": f"s{i}",
                "session_id": "sess1",
                "club": "Driver" if i < 3 else "7 Iron",
                "carry": 250 + i * 5,
                "total": 270 + i * 5,
                "ball_speed": 150 + i,
                "club_speed": 100 + i,
                "smash": 1.5,
                "face_angle": i * 0.5,
                "club_path": i * 0.3,
                "impact_x": i * 2.0,
                "impact_y": i * 1.5,
            }
            for i in range(5)
        ]
        for shot in shots:
            golf_db.save_shot(shot)

        # Update metrics should be called automatically by save_shot,
        # but let's call it explicitly to test
        golf_db.update_session_metrics("sess1")

        # Get metrics
        metrics = golf_db.get_session_metrics("sess1")

        self.assertIsNotNone(metrics)
        self.assertEqual(metrics["shot_count"], 5)
        self.assertIn("Driver", metrics["clubs_used"])
        self.assertIn("7 Iron", metrics["clubs_used"])
        self.assertIsNotNone(metrics["avg_carry"])
        self.assertGreater(metrics["avg_carry"], 250)
        self.assertIsNotNone(metrics["best_carry"])

    def test_get_session_metrics_returns_dict(self):
        """get_session_metrics should return a dict with all metrics."""
        # Add shots
        shots = [
            {
                "shot_id": f"s{i}",
                "session_id": "sess1",
                "club": "Driver",
                "carry": 250,
                "ball_speed": 150,
                "club_speed": 100,
            }
            for i in range(3)
        ]
        for shot in shots:
            golf_db.save_shot(shot)

        # Get metrics
        metrics = golf_db.get_session_metrics("sess1")

        self.assertIsInstance(metrics, dict)
        self.assertIn("session_id", metrics)
        self.assertIn("shot_count", metrics)
        self.assertIn("clubs_used", metrics)
        self.assertIn("avg_carry", metrics)
        self.assertIn("updated_at", metrics)

    def test_metrics_auto_update_after_add_shot(self):
        """Session metrics should auto-update when a shot is added."""
        # Add first shot
        golf_db.save_shot({
            "shot_id": "s1",
            "session_id": "sess1",
            "club": "Driver",
            "carry": 250,
            "ball_speed": 150,
            "club_speed": 100,
        })

        # Check metrics
        metrics1 = golf_db.get_session_metrics("sess1")
        self.assertEqual(metrics1["shot_count"], 1)

        # Add second shot
        golf_db.save_shot({
            "shot_id": "s2",
            "session_id": "sess1",
            "club": "7 Iron",
            "carry": 180,
            "ball_speed": 120,
            "club_speed": 85,
        })

        # Check metrics again
        metrics2 = golf_db.get_session_metrics("sess1")
        self.assertEqual(metrics2["shot_count"], 2)
        self.assertIn("Driver", metrics2["clubs_used"])
        self.assertIn("7 Iron", metrics2["clubs_used"])

    def test_update_all_session_metrics_backfills(self):
        """update_all_session_metrics should backfill all sessions."""
        # Create 3 sessions with shots
        for session_num in range(1, 4):
            for shot_num in range(2):
                golf_db.save_shot({
                    "shot_id": f"s{session_num}_{shot_num}",
                    "session_id": f"sess{session_num}",
                    "club": "Driver",
                    "carry": 250,
                })

        # Clear session_stats to simulate missing data
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM session_stats")
        conn.commit()
        conn.close()

        # Backfill all metrics
        count = golf_db.update_all_session_metrics()

        self.assertEqual(count, 3)

        # Verify all sessions have metrics
        for session_num in range(1, 4):
            metrics = golf_db.get_session_metrics(f"sess{session_num}")
            self.assertIsNotNone(metrics)
            self.assertEqual(metrics["shot_count"], 2)

    def test_metrics_update_after_delete_shot(self):
        """Session metrics should update after a shot is deleted."""
        # Add 3 shots
        for i in range(3):
            golf_db.save_shot({
                "shot_id": f"s{i}",
                "session_id": "sess1",
                "club": "Driver",
                "carry": 250 + i * 10,
            })

        # Check initial metrics
        metrics1 = golf_db.get_session_metrics("sess1")
        self.assertEqual(metrics1["shot_count"], 3)

        # Delete one shot
        golf_db.delete_shot("s1")

        # Check updated metrics
        metrics2 = golf_db.get_session_metrics("sess1")
        self.assertEqual(metrics2["shot_count"], 2)

    def test_metrics_deleted_when_no_shots(self):
        """Session metrics should be deleted when all shots are removed."""
        # Add shot
        golf_db.save_shot({
            "shot_id": "s1",
            "session_id": "sess1",
            "club": "Driver",
            "carry": 250,
        })

        # Verify metrics exist
        metrics1 = golf_db.get_session_metrics("sess1")
        self.assertIsNotNone(metrics1)

        # Delete the shot
        golf_db.delete_shot("s1")

        # Metrics should be deleted
        metrics2 = golf_db.get_session_metrics("sess1")
        self.assertIsNone(metrics2)


if __name__ == "__main__":
    unittest.main()
