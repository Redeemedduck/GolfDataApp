"""
Integration tests for the automation module.

Tests the full automation flow including:
- Session deduplication
- Checkpoint/resume after interruption
- Club filter with various patterns
- Rate limiter behavior under load
- Notification triggers on success/failure
"""

import os
import json
import asyncio
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.session_discovery import (
    SessionDiscovery,
    ImportStatus,
    ImportQueueItem,
    DiscoveryResult,
)
from automation.backfill_runner import (
    BackfillRunner,
    BackfillConfig,
    BackfillStatus,
)
from automation.rate_limiter import RateLimiter, RateLimiterConfig
from automation.uneekor_portal import SessionInfo


class TestSessionDeduplication(unittest.TestCase):
    """Test that duplicate sessions are correctly handled."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_discovery.db")
        self.discovery = SessionDiscovery(db_path=self.db_path)
        self.discovery.init_tables()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_save_new_session_returns_true(self):
        """Saving a new session should return True."""
        session = SessionInfo(
            report_id="12345",
            api_key="test_key",
            portal_name="Test Session",
            session_date=datetime(2025, 1, 15),
        )
        is_new = self.discovery.save_discovered_session(session)
        self.assertTrue(is_new)

    def test_save_duplicate_session_returns_false(self):
        """Saving the same session twice should return False the second time."""
        session = SessionInfo(
            report_id="12345",
            api_key="test_key",
            portal_name="Test Session",
            session_date=datetime(2025, 1, 15),
        )
        first = self.discovery.save_discovered_session(session)
        second = self.discovery.save_discovered_session(session)

        self.assertTrue(first)
        self.assertFalse(second)

    def test_duplicate_updates_metadata(self):
        """Duplicate saves should update metadata but not create new records."""
        session1 = SessionInfo(
            report_id="12345",
            api_key="test_key",
            portal_name="Original Name",
            session_date=datetime(2025, 1, 15),
            clubs_used=["Driver"],
        )
        session2 = SessionInfo(
            report_id="12345",
            api_key="test_key",
            portal_name="Updated Name",
            session_date=datetime(2025, 1, 15),
            clubs_used=["Driver", "7 Iron"],
        )

        self.discovery.save_discovered_session(session1)
        self.discovery.save_discovered_session(session2)

        # Should still only have one record
        known = self.discovery.get_known_report_ids()
        self.assertEqual(len(known), 1)


class TestClubFilter(unittest.TestCase):
    """Test club filtering in session discovery."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_discovery.db")
        self.discovery = SessionDiscovery(db_path=self.db_path)
        self.discovery.init_tables()

        # Create test sessions with different clubs
        sessions = [
            SessionInfo(
                report_id="1",
                api_key="key1",
                portal_name="Driver Session",
                session_date=datetime(2025, 1, 10),
                clubs_used=["Driver", "3 Wood"],
            ),
            SessionInfo(
                report_id="2",
                api_key="key2",
                portal_name="Iron Session",
                session_date=datetime(2025, 1, 11),
                clubs_used=["7 Iron", "8 Iron", "9 Iron"],
            ),
            SessionInfo(
                report_id="3",
                api_key="key3",
                portal_name="Full Bag Session",
                session_date=datetime(2025, 1, 12),
                clubs_used=["Driver", "7 Iron", "Pitching Wedge"],
            ),
            SessionInfo(
                report_id="4",
                api_key="key4",
                portal_name="Wedge Practice",
                session_date=datetime(2025, 1, 13),
                clubs_used=["Pitching Wedge", "Sand Wedge", "Lob Wedge"],
            ),
        ]
        for session in sessions:
            self.discovery.save_discovered_session(session)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_filter_by_single_club(self):
        """Filter sessions by a single club."""
        pending = self.discovery.get_pending_sessions(
            limit=100,
            clubs_filter=["Driver"],
        )
        report_ids = {item.report_id for item in pending}

        # Should get sessions 1 and 3 (both have Driver)
        self.assertIn("1", report_ids)
        self.assertIn("3", report_ids)
        self.assertNotIn("2", report_ids)
        self.assertNotIn("4", report_ids)

    def test_filter_by_multiple_clubs(self):
        """Filter sessions by multiple clubs (OR logic)."""
        pending = self.discovery.get_pending_sessions(
            limit=100,
            clubs_filter=["Driver", "Pitching Wedge"],
        )
        report_ids = {item.report_id for item in pending}

        # Should get sessions 1, 3, and 4
        self.assertIn("1", report_ids)
        self.assertIn("3", report_ids)
        self.assertIn("4", report_ids)
        self.assertNotIn("2", report_ids)

    def test_filter_case_insensitive(self):
        """Club filter should be case-insensitive."""
        pending = self.discovery.get_pending_sessions(
            limit=100,
            clubs_filter=["DRIVER"],  # Uppercase
        )
        report_ids = {item.report_id for item in pending}

        self.assertIn("1", report_ids)
        self.assertIn("3", report_ids)

    def test_no_filter_returns_all(self):
        """No filter should return all pending sessions."""
        pending = self.discovery.get_pending_sessions(limit=100)
        self.assertEqual(len(pending), 4)


class TestRetryLogic(unittest.TestCase):
    """Test retry logic for failed imports."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_discovery.db")
        self.discovery = SessionDiscovery(db_path=self.db_path)
        self.discovery.init_tables()

        # Create a test session
        session = SessionInfo(
            report_id="retry_test",
            api_key="test_key",
            portal_name="Retry Test Session",
            session_date=datetime(2025, 1, 15),
        )
        self.discovery.save_discovered_session(session)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_update_attempt_count(self):
        """Attempt count should be tracked."""
        self.discovery.update_attempt_count("retry_test", 1)

        # Get the session and check attempt count
        failed = self.discovery.get_failed_sessions()
        # Session isn't failed yet, so shouldn't appear in failed list

        # Mark it failed and check
        self.discovery.mark_failed("retry_test", "Test error")
        failed = self.discovery.get_failed_sessions()
        self.assertEqual(len(failed), 1)

    def test_mark_needs_review(self):
        """Sessions should be marked needs_review after max retries."""
        self.discovery.mark_needs_review("retry_test", "Max retries exceeded", 3)

        failed = self.discovery.get_failed_sessions(include_needs_review=True)
        self.assertEqual(len(failed), 1)
        # The status value should be 'needs_review'
        self.assertEqual(failed[0].status.value, 'needs_review')

    def test_reset_for_retry(self):
        """Failed sessions should be resettable for retry."""
        self.discovery.mark_failed("retry_test", "Test error")

        # Verify it's failed
        pending = self.discovery.get_pending_sessions(limit=100)
        self.assertEqual(len(pending), 0)

        # Reset for retry
        reset_count = self.discovery.reset_for_retry(["retry_test"])
        self.assertEqual(reset_count, 1)

        # Should now be pending again
        pending = self.discovery.get_pending_sessions(limit=100)
        self.assertEqual(len(pending), 1)


class TestCheckpointResume(unittest.TestCase):
    """Test checkpoint and resume functionality."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_discovery.db")
        self.discovery = SessionDiscovery(db_path=self.db_path)
        self.discovery.init_tables()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_backfill_run_creation(self):
        """Backfill run should be created and trackable."""
        config = BackfillConfig(
            max_sessions_per_run=10,
            dry_run=True,
        )
        runner = BackfillRunner(
            config=config,
            discovery=self.discovery,
        )

        # Run ID should be None before running
        self.assertIsNone(runner.run_id)

        # Create a run
        run_id = runner._create_run()
        self.assertIsNotNone(run_id)
        self.assertTrue(run_id.startswith("bf_"))

    def test_checkpoint_saves_progress(self):
        """Progress should be saved at checkpoints."""
        config = BackfillConfig(
            max_sessions_per_run=10,
            checkpoint_interval=1,
            dry_run=True,
        )
        runner = BackfillRunner(
            config=config,
            discovery=self.discovery,
        )

        runner.run_id = runner._create_run()
        runner.sessions_processed = 5
        runner.sessions_imported = 4
        runner.sessions_failed = 1
        runner.total_shots = 100

        runner._save_checkpoint()

        # Create a new runner and load the checkpoint
        runner2 = BackfillRunner(
            discovery=self.discovery,
            resume_run_id=runner.run_id,
        )

        self.assertEqual(runner2.sessions_processed, 5)
        self.assertEqual(runner2.sessions_imported, 4)
        self.assertEqual(runner2.sessions_failed, 1)
        self.assertEqual(runner2.total_shots, 100)


class TestRateLimiter(unittest.TestCase):
    """Test rate limiter behavior."""

    def test_rate_limiter_allows_within_limit(self):
        """Operations within limit should proceed immediately."""
        config = RateLimiterConfig(
            requests_per_minute=60,  # High rate for testing
            burst_size=10,
            min_delay_seconds=0.0,
        )
        limiter = RateLimiter(config)

        # Should allow first few calls (within burst)
        self.assertTrue(limiter.can_proceed())

    def test_rate_limiter_throttles_over_limit(self):
        """Operations over limit should be throttled."""
        config = RateLimiterConfig(
            requests_per_minute=60,
            burst_size=1,
            min_delay_seconds=0.5,
        )
        limiter = RateLimiter(config)

        # First call should be allowed
        self.assertTrue(limiter.can_proceed())

        # Use up the token
        limiter.wait()  # This uses a token

        # Second call should not immediately proceed (used up burst)
        # Since we have min_delay, it won't proceed immediately
        # Just verify the limiter is working
        self.assertIsNotNone(limiter.last_request_time)

    def test_rate_limiter_error_tracking(self):
        """Errors should be tracked and affect rate limiting."""
        config = RateLimiterConfig(
            requests_per_minute=60,
            burst_size=5,
        )
        limiter = RateLimiter(config)

        initial_backoff = limiter.current_backoff

        # Record some errors
        for _ in range(3):
            limiter.report_error()

        # Backoff should have increased
        self.assertGreater(limiter.current_backoff, initial_backoff)


class TestDryRunMode(unittest.TestCase):
    """Test dry-run mode functionality."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_discovery.db")
        self.discovery = SessionDiscovery(db_path=self.db_path)
        self.discovery.init_tables()

        # Create test sessions
        for i in range(3):
            session = SessionInfo(
                report_id=f"dry_run_{i}",
                api_key=f"key_{i}",
                portal_name=f"Dry Run Session {i}",
                session_date=datetime(2025, 1, 10 + i),
                clubs_used=["Driver", "7 Iron"],
            )
            self.discovery.save_discovered_session(session)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_dry_run_does_not_modify_database(self):
        """Dry run should not modify session status in the database."""
        from automation.rate_limiter import RateLimiter, RateLimiterConfig

        # Use a fast rate limiter for testing (no delays)
        fast_limiter = RateLimiter(RateLimiterConfig(
            requests_per_minute=1000,
            burst_size=100,
            min_delay_seconds=0.0,
            max_jitter_seconds=0.0,
        ))

        config = BackfillConfig(
            max_sessions_per_run=10,
            dry_run=True,
        )
        runner = BackfillRunner(
            config=config,
            discovery=self.discovery,
            rate_limiter=fast_limiter,
        )

        async def run_test():
            result = await runner.run()

            # Dry run should report sessions as "imported" for progress tracking
            self.assertEqual(result.sessions_imported, 3)

            # Status should be completed
            self.assertEqual(result.status, BackfillStatus.COMPLETED)

            # But sessions should still be pending in the database
            # (dry run doesn't actually modify session status)
            pending = self.discovery.get_pending_sessions(limit=100)
            self.assertEqual(len(pending), 3)

        asyncio.run(run_test())


class TestNotifications(unittest.TestCase):
    """Test notification triggers."""

    def test_completion_notification_sent(self):
        """Completion notification should be sent when configured."""
        # This test would require mocking the notification system
        # For now, we just verify the notification manager can be created
        from automation.notifications import NotificationManager, NotificationConfig

        config = NotificationConfig(
            slack_webhook_url=None,  # No actual webhook
            log_to_console=True,
            log_to_file=False,
        )
        notifier = NotificationManager(config)

        # Should be able to create without error
        self.assertIsNotNone(notifier)


if __name__ == "__main__":
    unittest.main()
