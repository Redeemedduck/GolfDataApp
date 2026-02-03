import os
import tempfile
import unittest

try:
    import golf_db
    from tests.e2e.fixtures import build_shot_payload
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "Required dependencies not installed")
class TestDataFlow(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "golf_stats.db")

        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.set_read_mode("sqlite")
        golf_db.init_db()

        shots = [
            build_shot_payload(
                shot_id="s1-1",
                session_id="session-1",
                club="Driver",
                carry=250,
                total=265,
                ball_speed=165,
                club_speed=110,
                smash=1.5,
                launch_angle=12.0,
            ),
            build_shot_payload(
                shot_id="s1-2",
                session_id="session-1",
                club="Driver",
                carry=255,
                total=270,
                ball_speed=168,
                club_speed=112,
                smash=1.5,
                launch_angle=12.5,
            ),
            build_shot_payload(
                shot_id="s2-1",
                session_id="session-2",
                club="7 Iron",
                carry=155,
                total=160,
                ball_speed=115,
                club_speed=83,
                smash=1.38,
                launch_angle=18.0,
            ),
        ]

        for shot in shots:
            golf_db.save_shot(shot)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_dashboard_retrieval_flow(self):
        counts = golf_db.get_shot_counts()
        self.assertEqual(counts["sqlite"], 3)

        sessions = golf_db.get_unique_sessions()
        self.assertEqual(len(sessions), 2)
        session_ids = [session["session_id"] for session in sessions]
        self.assertIn("session-1", session_ids)
        self.assertIn("session-2", session_ids)

        session_df = golf_db.get_session_data("session-1")
        self.assertEqual(len(session_df), 2)
        self.assertTrue((session_df["club"] == "Driver").all())


if __name__ == "__main__":
    unittest.main()
