import os
import tempfile
import unittest

import pandas as pd

import golf_db


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


if __name__ == "__main__":
    unittest.main()
