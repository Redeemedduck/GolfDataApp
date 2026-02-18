"""Tests for agent/core.py — Golf Agent core module.

Covers:
- Module is importable
- System prompt contains required keywords
- Agent options have correct defaults (model, tools, MCP servers)
- No dangerous tools are exposed in allowed_tools
"""
from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Pre-import mocks: golf_db and its transitive deps may not be available
# in the test environment.  We inject mocks before importing agent modules.
# ---------------------------------------------------------------------------

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Pre-load modules that other test files also use, so setdefault won't mock them
import exceptions as _real_exceptions  # noqa: E402,F401

_MOCK_DEPS = ("dotenv", "supabase", "automation", "automation.naming_conventions")
_ALL_MOCKED = ("golf_db",) + _MOCK_DEPS
_saved_modules: dict = {}

# Save current state and inject mocks for module-level imports
for _dep in _ALL_MOCKED:
    if _dep in sys.modules:
        _saved_modules[_dep] = sys.modules[_dep]
    else:
        sys.modules[_dep] = MagicMock(name=_dep)


def tearDownModule():
    """Restore original sys.modules entries after tests."""
    for dep in _ALL_MOCKED:
        if dep in _saved_modules:
            sys.modules[dep] = _saved_modules[dep]
        elif dep in sys.modules and isinstance(sys.modules[dep], MagicMock):
            del sys.modules[dep]

# Now safe to import agent code
from agent.core import (  # noqa: E402
    SYSTEM_PROMPT,
    create_golf_agent_options,
    create_golf_mcp_server,
    single_query,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCoreImportable(unittest.TestCase):
    """Verify the module and its key exports are importable."""

    def test_core_importable(self):
        """create_golf_agent_options should be importable."""
        self.assertTrue(callable(create_golf_agent_options))

    def test_single_query_importable(self):
        """single_query should be importable."""
        self.assertTrue(callable(single_query))

    def test_mcp_server_factory_importable(self):
        """create_golf_mcp_server should be importable."""
        self.assertTrue(callable(create_golf_mcp_server))


class TestSystemPrompt(unittest.TestCase):
    """Verify the system prompt contains required domain keywords."""

    def test_system_prompt_present(self):
        """SYSTEM_PROMPT should be a non-empty string."""
        self.assertIsInstance(SYSTEM_PROMPT, str)
        self.assertGreater(len(SYSTEM_PROMPT), 100)

    def test_mentions_golf(self):
        self.assertIn("golf", SYSTEM_PROMPT.lower())

    def test_mentions_big_3(self):
        self.assertIn("Big 3", SYSTEM_PROMPT)

    def test_mentions_uneekor(self):
        self.assertIn("Uneekor", SYSTEM_PROMPT)

    def test_mentions_face_angle(self):
        self.assertIn("Face Angle", SYSTEM_PROMPT)

    def test_mentions_club_path(self):
        self.assertIn("Club Path", SYSTEM_PROMPT)

    def test_mentions_strike_quality(self):
        self.assertIn("Strike Quality", SYSTEM_PROMPT)

    def test_mentions_launch_metrics(self):
        for metric in ("carry", "ball_speed", "smash", "launch_angle", "spin"):
            with self.subTest(metric=metric):
                self.assertIn(metric, SYSTEM_PROMPT)

    def test_mentions_cannot_do(self):
        """Prompt should describe limitations."""
        lower = SYSTEM_PROMPT.lower()
        self.assertIn("cannot", lower)

    def test_mentions_encouraging(self):
        lower = SYSTEM_PROMPT.lower()
        self.assertIn("encouraging", lower)


class TestAgentOptions(unittest.TestCase):
    """Verify create_golf_agent_options returns correct defaults."""

    def setUp(self):
        self.options = create_golf_agent_options()

    def test_options_have_tools(self):
        """mcp_servers should be set and allowed_tools should have items."""
        self.assertIsNotNone(self.options.mcp_servers)
        self.assertIsInstance(self.options.mcp_servers, dict)
        self.assertIn("golf", self.options.mcp_servers)
        self.assertGreater(len(self.options.allowed_tools), 0)

    def test_options_use_sonnet(self):
        """Model should be a Sonnet variant."""
        self.assertIn("sonnet", self.options.model)

    def test_options_have_system_prompt(self):
        """system_prompt should be set to SYSTEM_PROMPT."""
        self.assertEqual(self.options.system_prompt, SYSTEM_PROMPT)

    def test_options_max_turns(self):
        """max_turns should default to 20."""
        self.assertEqual(self.options.max_turns, 20)

    def test_no_dangerous_tools(self):
        """allowed_tools should not contain Bash, Write, or Edit."""
        dangerous = {"Bash", "Write", "Edit"}
        for tool_name in self.options.allowed_tools:
            for d in dangerous:
                self.assertNotIn(
                    d,
                    tool_name,
                    f"Dangerous tool fragment '{d}' found in allowed_tools: {tool_name}",
                )

    def test_overrides_applied(self):
        """Keyword overrides should replace defaults."""
        custom = create_golf_agent_options(max_turns=5)
        self.assertEqual(custom.max_turns, 5)

    def test_override_model(self):
        custom = create_golf_agent_options(model="claude-opus-4-20250514")
        self.assertEqual(custom.model, "claude-opus-4-20250514")


class TestMcpServer(unittest.TestCase):
    """Verify create_golf_mcp_server builds a valid server config."""

    def test_returns_config(self):
        server = create_golf_mcp_server()
        # Should be an McpSdkServerConfig (or at least truthy)
        self.assertIsNotNone(server)


if __name__ == "__main__":
    unittest.main()
