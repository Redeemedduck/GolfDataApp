import unittest
import sqlite3
import tempfile
import os
from unittest.mock import patch, MagicMock

import golf_db


class TestReimportAll(unittest.TestCase):
    def setUp(self):
        self.db_path = tempfile.mktemp(suffix='.db')
        self._orig_db_path = golf_db.SQLITE_DB_PATH
        self._orig_supabase = golf_db.supabase
        golf_db.SQLITE_DB_PATH = self.db_path
        os.environ.pop('SUPABASE_URL', None)
        golf_db.supabase = None
        golf_db.init_db()

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sessions_discovered (
                     report_id TEXT PRIMARY KEY,
                     api_key TEXT,
                     import_status TEXT
                  )''')
        c.execute('''INSERT INTO sessions_discovered
                     (report_id, api_key, import_status)
                     VALUES ('99999', 'testkey', 'imported')''')
        conn.commit()
        conn.close()

    def tearDown(self):
        golf_db.SQLITE_DB_PATH = self._orig_db_path
        golf_db.supabase = self._orig_supabase
        for f in [self.db_path] + [self.db_path + ext for ext in ['-wal', '-shm']]:
            if os.path.exists(f):
                os.unlink(f)
        import glob
        for bak in glob.glob(self.db_path + '.bak-*'):
            os.unlink(bak)

    @patch('golf_scraper.observability')
    @patch('golf_scraper.upload_shot_images', return_value={})
    @patch('golf_scraper.request_with_retries')
    def test_reimport_clears_and_rebuilds(self, mock_request, mock_images, mock_obs):
        from automation_runner import reimport_all

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{
            'id': 1, 'name': 'test', 'club_name': 'DRIVER', 'club': 0,
            'client_created_date': '2026-01-01',
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
        mock_response.raise_for_status = MagicMock()

        result = reimport_all(db_path=self.db_path, dry_run=False)

        self.assertTrue(result['success'], f"Reimport failed: {result.get('errors')}")
        self.assertEqual(result['sessions_processed'], 1)
        self.assertEqual(result['shots_imported'], 1)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT club, original_club_value, sidebar_label FROM shots')
        row = c.fetchone()
        self.assertEqual(row[0], 'Driver')
        self.assertEqual(row[1], 'DRIVER')
        self.assertEqual(row[2], 'test')
        conn.close()

    def test_reimport_dry_run(self):
        from automation_runner import reimport_all
        result = reimport_all(db_path=self.db_path, dry_run=True)
        self.assertTrue(result['success'])
        self.assertEqual(result['sessions_processed'], 1)
        self.assertEqual(result['shots_imported'], 0)


if __name__ == '__main__':
    unittest.main()
