import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    import golf_db
    import golf_scraper
    import observability
    from tests.e2e.fixtures import (
        FakeResponse,
        TEST_REPORT_ID,
        TEST_REPORT_URL,
        build_mock_sessions,
    )
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


@unittest.skipUnless(HAS_DEPS, "Required dependencies not installed")
class TestImportFlow(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "golf_stats.db")

        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.set_read_mode("sqlite")
        golf_db.init_db()

        golf_scraper.supabase = None
        observability.LOG_DIR = Path(self.tmpdir.name) / "logs"

    def tearDown(self):
        self.tmpdir.cleanup()

    @mock.patch("golf_scraper.request_with_retries")
    def test_import_flow_persists_shots(self, mock_request):
        sessions_data = build_mock_sessions()
        mock_request.return_value = FakeResponse(sessions_data)

        progress_updates = []

        result = golf_scraper.run_scraper(
            TEST_REPORT_URL,
            lambda msg: progress_updates.append(msg),
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["report_id"], TEST_REPORT_ID)
        self.assertEqual(result["total_shots_imported"], 3)
        self.assertTrue(any("Import complete" in msg for msg in progress_updates))

        session_df = golf_db.get_session_data(TEST_REPORT_ID)
        self.assertEqual(len(session_df), 3)
        self.assertIn("club", session_df.columns)


if __name__ == "__main__":
    unittest.main()
