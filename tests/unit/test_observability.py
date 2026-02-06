"""Tests for observability module."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import observability


class TestObservability(unittest.TestCase):
    """Tests for JSONL event logging."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self._orig_log_dir = observability.LOG_DIR
        observability.LOG_DIR = Path(self.temp_dir)

    def tearDown(self):
        observability.LOG_DIR = self._orig_log_dir
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_append_event_creates_file(self):
        result = observability.append_event("test.jsonl", {"action": "test"})
        self.assertTrue((Path(self.temp_dir) / "test.jsonl").exists())
        self.assertEqual(result["action"], "test")
        self.assertIn("timestamp", result)

    def test_append_event_jsonl_format(self):
        observability.append_event("test.jsonl", {"a": 1})
        observability.append_event("test.jsonl", {"b": 2})
        lines = (Path(self.temp_dir) / "test.jsonl").read_text().strip().split("\n")
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["a"], 1)
        self.assertEqual(json.loads(lines[1])["b"], 2)

    def test_read_latest_event(self):
        observability.append_event("test.jsonl", {"seq": 1})
        observability.append_event("test.jsonl", {"seq": 2})
        latest = observability.read_latest_event("test.jsonl")
        self.assertEqual(latest["seq"], 2)

    def test_read_latest_event_missing_file(self):
        result = observability.read_latest_event("nonexistent.jsonl")
        self.assertIsNone(result)

    def test_read_recent_events(self):
        for i in range(10):
            observability.append_event("test.jsonl", {"seq": i})
        recent = observability.read_recent_events("test.jsonl", limit=3)
        self.assertEqual(len(recent), 3)
        # Most recent first (reversed)
        self.assertEqual(recent[0]["seq"], 9)
        self.assertEqual(recent[2]["seq"], 7)

    def test_read_recent_events_missing_file(self):
        result = observability.read_recent_events("nonexistent.jsonl")
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
