"""
Expose backfill rate limit bug: WRONG is 6 req/min = 360/hour, RIGHT is 0.1 req/min = 6/hour.
"""

import tempfile
import unittest

from automation.backfill_runner import BackfillRunner, BackfillConfig
from automation.session_discovery import SessionDiscovery


class TestBackfillRateLimiterConfig(unittest.TestCase):
    """Tests for BackfillRunner rate limiter configuration."""

    def test_max_sessions_per_hour_is_converted_to_per_minute(self):
        config = BackfillConfig(max_sessions_per_hour=6)
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery = SessionDiscovery(db_path=f"{tmpdir}/test.db")
            runner = BackfillRunner(config=config, discovery=discovery)

        requests_per_minute = runner.rate_limiter.config.requests_per_minute
        self.assertAlmostEqual(requests_per_minute, 0.1, places=3)
        self.assertNotEqual(requests_per_minute, 6)
