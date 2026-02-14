import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch

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
        )
        self.assertEqual(result.get('status'), 'success')

        df = golf_db.get_session_data("123")
        self.assertEqual(len(df), 1)


@unittest.skipUnless(HAS_DEPS, "requests/pandas not installed")
class TestScraperClubMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        observability.LOG_DIR = Path(tempfile.gettempdir()) / "golfdataapp_test_logs"
        observability.LOG_DIR.mkdir(parents=True, exist_ok=True)

    @patch('golf_scraper.golf_db')
    @patch('golf_scraper.request_with_retries')
    @patch('golf_scraper.upload_shot_images', return_value={})
    def test_scraper_uses_club_name_field(self, mock_images, mock_request, mock_db):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            'id': 89069,
            'name': 'warmup',
            'club_name': 'WEDGE_PITCHING',
            'club': 28,
            'client_created_date': '2026-01-25',
            'shots': [{'id': 1, 'ball_speed': 25.0, 'club_speed': 28.0,
                       'carry_distance': 52.0, 'total_distance': 59.0,
                       'club_path': 0.0, 'club_face_angle': 0.0,
                       'side_spin': 0, 'back_spin': 2600,
                       'launch_angle': 30.0, 'side_angle': 0.0,
                       'dynamic_loft': 40.0, 'attack_angle': -5.0,
                       'impact_x': 0, 'impact_y': 0,
                       'side_distance': 0, 'decent_angle': 40,
                       'apex': 15.0, 'flight_time': 3.5,
                       'type': 'straight', 'optix_x': '0', 'optix_y': '0',
                       'club_lie': 0, 'lie_angle': ''}],
        }]
        mock_request.return_value = mock_response

        result = golf_scraper.run_scraper(
            'https://my.uneekor.com/report?id=99999&key=testkey',
            lambda msg: None
        )

        mock_db.save_shot.assert_called_once()
        shot_data = mock_db.save_shot.call_args[0][0]
        self.assertEqual(shot_data['club'], 'PW')
        self.assertEqual(shot_data['original_club_value'], 'WEDGE_PITCHING')
        self.assertEqual(shot_data['sidebar_label'], 'warmup')
        self.assertEqual(shot_data['session_date'], '2026-01-25')

    @patch('golf_scraper.golf_db')
    @patch('golf_scraper.request_with_retries')
    @patch('golf_scraper.upload_shot_images', return_value={})
    def test_scraper_uses_client_created_date(self, mock_images, mock_request, mock_db):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            'id': 1, 'name': 'Driver', 'club_name': 'DRIVER', 'club': 0,
            'client_created_date': '2026-02-01',
            'shots': [{'id': 1, 'ball_speed': 70, 'club_speed': 48,
                       'carry_distance': 250, 'total_distance': 270,
                       'club_path': 0, 'club_face_angle': 0,
                       'side_spin': 0, 'back_spin': 2000,
                       'launch_angle': 12, 'side_angle': 0,
                       'dynamic_loft': 12, 'attack_angle': 3,
                       'impact_x': 0, 'impact_y': 0,
                       'side_distance': 0, 'decent_angle': 35,
                       'apex': 30, 'flight_time': 6.0,
                       'type': 'straight', 'optix_x': '0', 'optix_y': '0',
                       'club_lie': 0, 'lie_angle': ''}],
        }]
        mock_request.return_value = mock_response

        from datetime import datetime
        result = golf_scraper.run_scraper(
            'https://my.uneekor.com/report?id=99999&key=testkey',
            lambda msg: None,
            session_date=datetime(2025, 12, 31)
        )

        shot_data = mock_db.save_shot.call_args[0][0]
        self.assertEqual(shot_data['session_date'], '2026-02-01')


if __name__ == "__main__":
    unittest.main()
