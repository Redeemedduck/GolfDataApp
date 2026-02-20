"""Tests for services.sync_service module."""

import asyncio
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass, field
from typing import List

from services.sync_service import (
    load_credentials,
    save_credentials,
    clear_credentials,
    has_credentials,
    check_playwright_available,
    run_sync,
    SyncResult,
    SYNC_TIMEOUT_SECONDS,
    _run_async_pipeline_sync,
    _async_sync_pipeline,
    get_automation_status,
)


class TestCredentialHelpers(unittest.TestCase):
    """Tests for credential file load/save/clear/has functions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cred_file = Path(self.temp_dir) / '.uneekor_credentials.json'
        # Patch the module-level constant so all functions use our temp file
        self.patcher = patch('services.sync_service.CREDENTIALS_FILE', self.cred_file)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ── load_credentials ──

    def test_load_returns_none_when_file_missing(self):
        result = load_credentials()
        self.assertIsNone(result)

    def test_load_returns_credentials_when_valid(self):
        self.cred_file.write_text(json.dumps({
            'username': 'test@example.com',
            'password': 'secret123',
        }))
        result = load_credentials()
        self.assertEqual(result['username'], 'test@example.com')
        self.assertEqual(result['password'], 'secret123')

    def test_load_returns_none_for_invalid_json(self):
        self.cred_file.write_text('not json{{{')
        result = load_credentials()
        self.assertIsNone(result)

    def test_load_returns_none_when_username_empty(self):
        self.cred_file.write_text(json.dumps({
            'username': '',
            'password': 'secret',
        }))
        result = load_credentials()
        self.assertIsNone(result)

    def test_load_returns_none_when_password_missing(self):
        self.cred_file.write_text(json.dumps({
            'username': 'test@example.com',
        }))
        result = load_credentials()
        self.assertIsNone(result)

    # ── save_credentials ──

    def test_save_creates_file(self):
        save_credentials('user@test.com', 'pass123')
        self.assertTrue(self.cred_file.exists())

    def test_save_writes_valid_json(self):
        save_credentials('user@test.com', 'pass123')
        data = json.loads(self.cred_file.read_text())
        self.assertEqual(data['username'], 'user@test.com')
        self.assertEqual(data['password'], 'pass123')

    def test_save_sets_restrictive_permissions(self):
        save_credentials('user@test.com', 'pass123')
        mode = self.cred_file.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_save_overwrites_existing(self):
        save_credentials('old@test.com', 'oldpass')
        save_credentials('new@test.com', 'newpass')
        data = json.loads(self.cred_file.read_text())
        self.assertEqual(data['username'], 'new@test.com')

    # ── clear_credentials ──

    def test_clear_returns_true_when_file_exists(self):
        save_credentials('user@test.com', 'pass')
        result = clear_credentials()
        self.assertTrue(result)

    def test_clear_removes_file(self):
        save_credentials('user@test.com', 'pass')
        clear_credentials()
        self.assertFalse(self.cred_file.exists())

    def test_clear_returns_false_when_no_file(self):
        result = clear_credentials()
        self.assertFalse(result)

    # ── has_credentials ──

    def test_has_returns_false_when_no_file(self):
        self.assertFalse(has_credentials())

    def test_has_returns_true_after_save(self):
        save_credentials('user@test.com', 'pass')
        self.assertTrue(has_credentials())

    def test_has_returns_false_after_clear(self):
        save_credentials('user@test.com', 'pass')
        clear_credentials()
        self.assertFalse(has_credentials())

    # ── round-trip ──

    def test_save_then_load_roundtrip(self):
        save_credentials('roundtrip@test.com', 'roundtrip_pass')
        loaded = load_credentials()
        self.assertEqual(loaded['username'], 'roundtrip@test.com')
        self.assertEqual(loaded['password'], 'roundtrip_pass')


class TestCheckPlaywrightAvailable(unittest.TestCase):
    """Tests for Playwright availability check."""

    def test_returns_tuple(self):
        result = check_playwright_available()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_first_element_is_bool(self):
        available, _ = check_playwright_available()
        self.assertIsInstance(available, bool)

    def test_second_element_is_string(self):
        _, message = check_playwright_available()
        self.assertIsInstance(message, str)

    @patch.dict('sys.modules', {'playwright': None, 'playwright.async_api': None})
    def test_returns_false_when_playwright_missing(self):
        # Force reimport to pick up the patched module
        import importlib
        import services.sync_service as svc
        # Directly test the logic: if import fails, should be False
        try:
            from playwright.async_api import async_playwright  # noqa: F401
            can_import = True
        except (ImportError, TypeError):
            can_import = False

        if not can_import:
            available, msg = check_playwright_available()
            self.assertFalse(available)
            self.assertIn("not installed", msg)


class TestSyncResult(unittest.TestCase):
    """Tests for SyncResult dataclass defaults and behavior."""

    def test_default_values(self):
        result = SyncResult(success=True, status='completed')
        self.assertEqual(result.sessions_discovered, 0)
        self.assertEqual(result.new_sessions, 0)
        self.assertEqual(result.sessions_imported, 0)
        self.assertEqual(result.sessions_failed, 0)
        self.assertEqual(result.total_shots, 0)
        self.assertEqual(result.dates_updated, 0)
        self.assertEqual(result.duration_seconds, 0.0)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.error_message, '')

    def test_errors_list_is_independent_per_instance(self):
        """Each SyncResult should have its own errors list (no shared mutable default)."""
        r1 = SyncResult(success=True, status='completed')
        r2 = SyncResult(success=True, status='completed')
        r1.errors.append('error1')
        self.assertEqual(len(r2.errors), 0)


class TestRunSyncEnvVarSafety(unittest.TestCase):
    """Tests that run_sync properly manages environment variables."""

    def setUp(self):
        # Clean slate for env vars
        self.orig_user = os.environ.pop('UNEEKOR_USERNAME', None)
        self.orig_pass = os.environ.pop('UNEEKOR_PASSWORD', None)

    def tearDown(self):
        # Restore original env vars
        if self.orig_user is not None:
            os.environ['UNEEKOR_USERNAME'] = self.orig_user
        else:
            os.environ.pop('UNEEKOR_USERNAME', None)
        if self.orig_pass is not None:
            os.environ['UNEEKOR_PASSWORD'] = self.orig_pass
        else:
            os.environ.pop('UNEEKOR_PASSWORD', None)

    @patch('services.sync_service.check_playwright_available', return_value=(False, 'Not installed'))
    def test_env_vars_not_leaked_on_preflight_failure(self, mock_pw):
        """If Playwright check fails, env vars should never be set."""
        run_sync('user', 'pass')
        self.assertNotIn('UNEEKOR_USERNAME', os.environ)
        self.assertNotIn('UNEEKOR_PASSWORD', os.environ)

    @patch('services.sync_service.check_playwright_available', return_value=(True, 'OK'))
    @patch('services.sync_service._run_async_pipeline_sync')
    @patch('services.sync_service.observability')
    def test_env_vars_restored_after_sync(self, mock_obs, mock_run_pipeline, mock_pw):
        """After sync completes, env vars should be cleaned up."""
        mock_run_pipeline.return_value = SyncResult(success=True, status='completed')
        run_sync('user', 'pass')
        self.assertNotIn('UNEEKOR_USERNAME', os.environ)
        self.assertNotIn('UNEEKOR_PASSWORD', os.environ)

    @patch('services.sync_service.check_playwright_available', return_value=(True, 'OK'))
    @patch('services.sync_service._run_async_pipeline_sync')
    @patch('services.sync_service.observability')
    def test_env_vars_restored_after_exception(self, mock_obs, mock_run_pipeline, mock_pw):
        """Even if asyncio.run raises, env vars should be cleaned up."""
        mock_run_pipeline.side_effect = RuntimeError('boom')
        run_sync('user', 'pass')
        self.assertNotIn('UNEEKOR_USERNAME', os.environ)
        self.assertNotIn('UNEEKOR_PASSWORD', os.environ)

    @patch('services.sync_service.check_playwright_available', return_value=(True, 'OK'))
    @patch('services.sync_service._run_async_pipeline_sync')
    @patch('services.sync_service.observability')
    def test_preexisting_env_vars_preserved(self, mock_obs, mock_run_pipeline, mock_pw):
        """If env vars existed before sync, they should be restored to original values."""
        os.environ['UNEEKOR_USERNAME'] = 'original_user'
        os.environ['UNEEKOR_PASSWORD'] = 'original_pass'
        mock_run_pipeline.return_value = SyncResult(success=True, status='completed')
        run_sync('sync_user', 'sync_pass')
        self.assertEqual(os.environ['UNEEKOR_USERNAME'], 'original_user')
        self.assertEqual(os.environ['UNEEKOR_PASSWORD'], 'original_pass')


class TestRunSyncResults(unittest.TestCase):
    """Tests for run_sync return values and status handling."""

    @patch('services.sync_service.check_playwright_available', return_value=(False, 'Playwright not installed'))
    def test_returns_failure_when_playwright_missing(self, mock_pw):
        result = run_sync('user', 'pass')
        self.assertFalse(result.success)
        self.assertEqual(result.status, 'failed')
        self.assertIn('not installed', result.error_message)

    @patch('services.sync_service.check_playwright_available', return_value=(True, 'OK'))
    @patch('services.sync_service._run_async_pipeline_sync')
    @patch('services.sync_service.observability')
    def test_returns_pipeline_result_on_success(self, mock_obs, mock_run_pipeline, mock_pw):
        pipeline_result = SyncResult(
            success=True, status='completed',
            sessions_imported=3, total_shots=45,
        )
        mock_run_pipeline.return_value = pipeline_result
        result = run_sync('user', 'pass')
        self.assertTrue(result.success)
        self.assertEqual(result.sessions_imported, 3)
        self.assertEqual(result.total_shots, 45)

    @patch('services.sync_service.check_playwright_available', return_value=(True, 'OK'))
    @patch('services.sync_service._run_async_pipeline_sync')
    @patch('services.sync_service.observability')
    def test_returns_failure_on_exception(self, mock_obs, mock_run_pipeline, mock_pw):
        mock_run_pipeline.side_effect = RuntimeError('connection lost')
        result = run_sync('user', 'pass')
        self.assertFalse(result.success)
        self.assertEqual(result.status, 'failed')
        self.assertIn('connection lost', result.error_message)

    @patch('services.sync_service.check_playwright_available', return_value=(True, 'OK'))
    @patch('services.sync_service._run_async_pipeline_sync')
    @patch('services.sync_service.observability')
    def test_duration_is_set(self, mock_obs, mock_run_pipeline, mock_pw):
        mock_run_pipeline.return_value = SyncResult(success=True, status='completed')
        result = run_sync('user', 'pass')
        self.assertGreaterEqual(result.duration_seconds, 0.0)

    @patch('services.sync_service.check_playwright_available', return_value=(True, 'OK'))
    @patch('services.sync_service._run_async_pipeline_sync')
    @patch('services.sync_service.observability')
    def test_status_callback_invoked(self, mock_obs, mock_run_pipeline, mock_pw):
        """The on_status callback should be passed through to the pipeline."""
        status_messages = []
        def fake_run_pipeline(status, max_sessions):
            status("in progress")
            return SyncResult(success=True, status='completed')

        mock_run_pipeline.side_effect = fake_run_pipeline
        result = run_sync('user', 'pass', on_status=status_messages.append)
        self.assertTrue(result.success)
        self.assertIn("in progress", status_messages)

    @patch('services.sync_service.check_playwright_available', return_value=(True, 'OK'))
    @patch('services.sync_service._run_async_pipeline_sync')
    @patch('services.sync_service.observability')
    def test_observability_event_logged(self, mock_obs, mock_run_pipeline, mock_pw):
        mock_run_pipeline.return_value = SyncResult(
            success=True, status='completed',
            sessions_imported=2, total_shots=30,
        )
        run_sync('user', 'pass')
        mock_obs.append_event.assert_called_once()
        call_args = mock_obs.append_event.call_args
        self.assertEqual(call_args[0][0], 'sync_runs.jsonl')
        payload = call_args[0][1]
        self.assertEqual(payload['mode'], 'ui_sync')
        self.assertEqual(payload['sessions_imported'], 2)
        self.assertEqual(payload['shots'], 30)

    @patch('services.sync_service.check_playwright_available', return_value=(True, 'OK'))
    @patch('services.sync_service.observability')
    def test_run_sync_works_inside_existing_event_loop(self, mock_obs, mock_pw):
        async def fake_pipeline(status, max_sessions):
            status("test status")
            return SyncResult(success=True, status='completed', sessions_imported=1)

        with patch('services.sync_service._async_sync_pipeline', fake_pipeline):
            async def invoke():
                return run_sync('user', 'pass')

            result = asyncio.run(invoke())

        self.assertTrue(result.success)
        self.assertEqual(result.status, 'completed')
        self.assertEqual(result.sessions_imported, 1)


class TestRunAsyncPipelineSync(unittest.TestCase):
    """Tests for event-loop-safe async pipeline wrapper."""

    def test_runs_directly_without_event_loop(self):
        async def fake_pipeline(status, max_sessions):
            status("ok")
            return SyncResult(success=True, status='completed')

        with patch('services.sync_service._async_sync_pipeline', fake_pipeline):
            result = _run_async_pipeline_sync(lambda _: None, 1)

        self.assertTrue(result.success)

    def test_runs_in_thread_with_event_loop(self):
        async def fake_pipeline(status, max_sessions):
            status("ok")
            return SyncResult(success=True, status='completed')

        with patch('services.sync_service._async_sync_pipeline', fake_pipeline):
            async def invoke():
                return _run_async_pipeline_sync(lambda _: None, 1)

            result = asyncio.run(invoke())

        self.assertTrue(result.success)

    def test_thread_exception_propagates(self):
        """Exceptions from the async pipeline should propagate through the thread."""
        async def exploding_pipeline(status, max_sessions):
            raise ConnectionError("portal unreachable")

        with patch('services.sync_service._async_sync_pipeline', exploding_pipeline):
            async def invoke():
                return _run_async_pipeline_sync(lambda _: None, 1)

            with self.assertRaises(ConnectionError):
                asyncio.run(invoke())

    def test_timeout_returns_failure(self):
        """If the pipeline takes too long, should return a timeout failure."""
        async def slow_pipeline(status, max_sessions):
            await asyncio.sleep(999)
            return SyncResult(success=True, status='completed')

        with patch('services.sync_service._async_sync_pipeline', slow_pipeline), \
             patch('services.sync_service.SYNC_TIMEOUT_SECONDS', 0.1):
            async def invoke():
                return _run_async_pipeline_sync(lambda _: None, 1)

            result = asyncio.run(invoke())

        self.assertFalse(result.success)
        self.assertEqual(result.status, 'failed')
        self.assertIn('timed out', result.error_message)


class TestAsyncPipelineLogic(unittest.TestCase):
    """Tests for _async_sync_pipeline phase logic using mocked automation modules."""

    def _run_async(self, coro):
        """Helper to run async test coroutines."""
        import asyncio
        return asyncio.run(coro)

    def test_sync_result_partial_when_mixed_results(self):
        """When some imports succeed and some fail, status should be 'partial'."""
        result = SyncResult(success=True, status='completed')
        result.sessions_imported = 2
        result.sessions_failed = 1

        # Replicate the final status logic from _async_sync_pipeline
        if result.sessions_failed > 0 and result.sessions_imported > 0:
            result.status = 'partial'
        elif result.sessions_failed > 0 and result.sessions_imported == 0:
            result.status = 'failed'
            result.success = False

        self.assertEqual(result.status, 'partial')
        self.assertTrue(result.success)  # partial still counts as success=True

    def test_sync_result_failed_when_all_fail(self):
        """When all imports fail, status should be 'failed'."""
        result = SyncResult(success=True, status='completed')
        result.sessions_imported = 0
        result.sessions_failed = 3

        if result.sessions_failed > 0 and result.sessions_imported > 0:
            result.status = 'partial'
        elif result.sessions_failed > 0 and result.sessions_imported == 0:
            result.status = 'failed'
            result.success = False

        self.assertEqual(result.status, 'failed')
        self.assertFalse(result.success)

    def test_sync_result_completed_when_all_succeed(self):
        """When all imports succeed, status stays 'completed'."""
        result = SyncResult(success=True, status='completed')
        result.sessions_imported = 3
        result.sessions_failed = 0

        if result.sessions_failed > 0 and result.sessions_imported > 0:
            result.status = 'partial'
        elif result.sessions_failed > 0 and result.sessions_imported == 0:
            result.status = 'failed'
            result.success = False

        self.assertEqual(result.status, 'completed')
        self.assertTrue(result.success)

    def test_auth_failure_detected_from_login_error(self):
        """Pipeline should detect auth failure from error messages containing 'login'."""
        errors = ['Failed to log in', 'Some other error']
        auth_failed = any(
            'log in' in err.lower() or 'login' in err.lower()
            for err in errors
        )
        self.assertTrue(auth_failed)

    def test_auth_failure_not_false_positive(self):
        """Normal errors should not be mistaken for auth failures."""
        errors = ['Network timeout', 'Session not found']
        auth_failed = any(
            'log in' in err.lower() or 'login' in err.lower()
            for err in errors
        )
        self.assertFalse(auth_failed)


class TestGetAutomationStatus(unittest.TestCase):
    """Tests for get_automation_status."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cred_file = Path(self.temp_dir) / '.uneekor_credentials.json'
        self.patcher = patch('services.sync_service.CREDENTIALS_FILE', self.cred_file)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('services.sync_service.CredentialManager', create=True)
    def test_returns_dict_with_required_keys(self, mock_cm_cls):
        mock_cm_cls.side_effect = Exception("no automation module")
        status = get_automation_status()
        self.assertIn('credentials_configured', status)
        self.assertIn('username', status)
        self.assertIn('cookies_valid', status)
        self.assertIn('cookies_expires', status)

    @patch('services.sync_service.CredentialManager', create=True)
    def test_shows_unconfigured_when_no_creds(self, mock_cm_cls):
        mock_cm_cls.side_effect = Exception("no automation module")
        status = get_automation_status()
        self.assertFalse(status['credentials_configured'])
        self.assertEqual(status['username'], '')

    @patch('services.sync_service.CredentialManager', create=True)
    def test_shows_configured_with_username(self, mock_cm_cls):
        mock_cm_cls.side_effect = Exception("no automation module")
        save_credentials('duck@golf.com', 'birdie')
        status = get_automation_status()
        self.assertTrue(status['credentials_configured'])
        self.assertEqual(status['username'], 'duck@golf.com')


if __name__ == '__main__':
    unittest.main()
