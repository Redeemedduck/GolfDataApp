"""Tests for automation.credential_manager module."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

from automation.credential_manager import CredentialManager


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography not installed")
class TestCredentialManager(unittest.TestCase):
    """Tests for CredentialManager with encryption."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Remove env vars that could interfere
        self.env_patcher = patch.dict(os.environ, {}, clear=False)
        self.env_patcher.start()
        os.environ.pop("K_SERVICE", None)
        os.environ.pop("UNEEKOR_COOKIE_KEY", None)
        os.environ.pop("UNEEKOR_USERNAME", None)
        os.environ.pop("UNEEKOR_PASSWORD", None)

        self.cm = CredentialManager(base_dir=self.temp_dir)

    def tearDown(self):
        self.env_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generates_key_file(self):
        self.assertTrue(Path(self.temp_dir, ".uneekor_key").exists())

    def test_save_and_load_roundtrip(self):
        storage_state = {
            "cookies": [{"name": "session", "value": "abc123"}],
            "origins": [],
        }
        self.assertTrue(self.cm.save_storage_state(storage_state, username="test"))
        loaded = self.cm.load_storage_state()
        self.assertEqual(loaded["cookies"][0]["value"], "abc123")

    def test_has_valid_credentials_after_save(self):
        storage_state = {"cookies": [], "origins": []}
        self.cm.save_storage_state(storage_state)
        self.assertTrue(self.cm.has_valid_credentials())

    def test_no_credentials_initially(self):
        self.assertFalse(self.cm.has_valid_credentials())

    def test_clear_credentials(self):
        storage_state = {"cookies": [], "origins": []}
        self.cm.save_storage_state(storage_state)
        self.assertTrue(self.cm.clear_credentials())
        self.assertFalse(self.cm.has_valid_credentials())

    def test_clear_nonexistent(self):
        self.assertFalse(self.cm.clear_credentials())

    def test_get_credential_info(self):
        info = self.cm.get_credential_info()
        self.assertIn("has_env_credentials", info)
        self.assertIn("has_stored_cookies", info)
        self.assertFalse(info["is_cloud_run"])

    def test_get_auth_method_interactive(self):
        self.assertEqual(self.cm.get_auth_method(), "interactive")

    def test_get_auth_method_cookies(self):
        self.cm.save_storage_state({"cookies": [], "origins": []})
        self.assertEqual(self.cm.get_auth_method(), "cookies")

    @patch.dict(os.environ, {"UNEEKOR_USERNAME": "user", "UNEEKOR_PASSWORD": "pass"})
    def test_get_auth_method_credentials(self):
        cm = CredentialManager(base_dir=self.temp_dir)
        self.assertEqual(cm.get_auth_method(), "credentials")

    @patch.dict(os.environ, {"UNEEKOR_USERNAME": "user", "UNEEKOR_PASSWORD": "pass"})
    def test_has_login_credentials(self):
        cm = CredentialManager(base_dir=self.temp_dir)
        self.assertTrue(cm.has_login_credentials())

    def test_no_login_credentials(self):
        self.assertFalse(self.cm.has_login_credentials())


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "cryptography not installed")
class TestCredentialManagerCloudRun(unittest.TestCase):
    """Tests for Cloud Run behavior."""

    @patch.dict(os.environ, {"K_SERVICE": "my-service"})
    def test_cloud_run_detected(self):
        cm = CredentialManager(base_dir=tempfile.mkdtemp())
        self.assertTrue(cm.is_cloud_run)

    @patch.dict(os.environ, {"K_SERVICE": "my-service"})
    def test_cloud_run_no_cookie_persistence(self):
        cm = CredentialManager(base_dir=tempfile.mkdtemp())
        self.assertFalse(cm.save_storage_state({"cookies": [], "origins": []}))
        self.assertFalse(cm.has_valid_credentials())


if __name__ == "__main__":
    unittest.main()
