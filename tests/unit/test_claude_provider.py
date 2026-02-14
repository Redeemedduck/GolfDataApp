"""Tests for the Claude AI Coach provider class.

Loads claude_provider.py directly via importlib to avoid the
services.ai package auto-import chain (streamlit, supabase, etc.).
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Module-level mock setup/teardown — loads claude_provider.py by file path
# to avoid the services.ai.providers package auto-import chain, while
# ensuring sys.modules is restored after this file runs.
# ---------------------------------------------------------------------------
_ORIGINAL_MODULES = {}
ClaudeProvider = None


def setUpModule():
    global ClaudeProvider
    _deps = ["services", "services.ai", "services.ai.registry"]
    for dep in _deps:
        _ORIGINAL_MODULES[dep] = sys.modules.get(dep, None)

    _mock_registry = MagicMock()
    _mock_registry.register_provider = lambda cls: cls
    sys.modules["services"] = MagicMock()
    sys.modules["services.ai"] = MagicMock()
    sys.modules["services.ai.registry"] = _mock_registry

    _provider_path = (
        Path(__file__).resolve().parent.parent.parent
        / "services" / "ai" / "providers" / "claude_provider.py"
    )
    _spec = importlib.util.spec_from_file_location("claude_provider", _provider_path)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    ClaudeProvider = _mod.ClaudeProvider


def tearDownModule():
    for dep, original in _ORIGINAL_MODULES.items():
        if original is None:
            sys.modules.pop(dep, None)
        else:
            sys.modules[dep] = original


class TestClaudeProvider(unittest.TestCase):
    """Verify ClaudeProvider class behavior."""

    def test_provider_id(self):
        self.assertEqual(ClaudeProvider.PROVIDER_ID, "claude")

    def test_display_name(self):
        self.assertEqual(ClaudeProvider.DISPLAY_NAME, "Claude Golf Coach")

    def test_is_configured_without_key(self):
        old = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            self.assertFalse(ClaudeProvider.is_configured())
        finally:
            if old is not None:
                os.environ["ANTHROPIC_API_KEY"] = old

    def test_is_configured_with_key(self):
        os.environ["ANTHROPIC_API_KEY"] = "test-key"
        try:
            self.assertTrue(ClaudeProvider.is_configured())
        finally:
            del os.environ["ANTHROPIC_API_KEY"]

    def test_get_model_name(self):
        provider = ClaudeProvider()
        self.assertIn("Claude", provider.get_model_name())

    def test_constructor_defaults(self):
        provider = ClaudeProvider()
        self.assertEqual(provider._model_type, "sonnet")
        self.assertEqual(provider._thinking_level, "medium")

    def test_reset_conversation(self):
        provider = ClaudeProvider()
        provider.reset_conversation()  # Should not raise

    def test_set_model(self):
        provider = ClaudeProvider()
        provider.set_model("opus")
        self.assertEqual(provider._model_type, "opus")

    def test_set_thinking_level(self):
        provider = ClaudeProvider()
        provider.set_thinking_level("high")
        self.assertEqual(provider._thinking_level, "high")


if __name__ == "__main__":
    unittest.main()
