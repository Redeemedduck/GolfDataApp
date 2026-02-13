import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

try:
    import requests
    import golf_db
    import golf_scraper
    import observability
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@unittest.skipUnless(HAS_DEPS, "requests/pandas not installed")
class TestScraper(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test.db")
        golf_db.SQLITE_DB_PATH = self.db_path
        golf_db.supabase = None
        golf_db.init_db()

        golf_scraper.supabase = None
        observability.LOG_DIR = Path(self.tmpdir.name) / "logs"

    def tearDown(self):
        self.tmpdir.cleanup()


    def test_build_session_id_prefers_date(self):
        session_id = golf_scraper.build_session_id('123', datetime(2026, 2, 1))
        self.assertEqual(session_id, '2026-02-01')

    @mock.patch("golf_scraper.request_with_retries")
    def test_run_scraper_imports_shot(self, mock_request):
        sessions_data = [
            {
                "name": "Driver",
                "id": "session-1",
                "shots": [
                    {
                        "id": 1,
                        "ball_speed": 50,
                        "club_speed": 40,
                        "carry_distance": 200,
                        "total_distance": 210,
                    }
                ],
            }
        ]

        mock_request.return_value = FakeResponse(sessions_data)

        result = golf_scraper.run_scraper(
            "https://myuneekor.com/report?id=123&key=abc",
            lambda _: None,
            session_date=datetime(2026, 2, 2),
        )
        self.assertEqual(result.get('status'), 'success')

        df = golf_db.get_session_data("2026-02-02")
        self.assertEqual(len(df), 1)


if __name__ == "__main__":
    unittest.main()
