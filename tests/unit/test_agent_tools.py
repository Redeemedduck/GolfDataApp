"""Tests for agent/tools.py — Golf Agent SDK tool definitions.

Covers:
- Helper functions (_safe_mean, _safe_std, _df_to_summary)
- Read tools return correct content format and handle filtering
- Write tools call the correct golf_db functions
- Empty/missing data returns appropriate messages
- ALL_TOOLS and TOOL_NAMES exports
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest
from unittest.mock import MagicMock

import pandas as pd

# Ensure project root is importable
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ---------------------------------------------------------------------------
# Module-level mock setup/teardown — ensures sys.modules is restored after
# this test file runs so other test files aren't affected.
# ---------------------------------------------------------------------------
_DEPS = ["golf_db", "dotenv", "supabase", "automation",
         "automation.naming_conventions", "exceptions"]
_ORIGINAL_MODULES = {}
_golf_db_mock = MagicMock(name="golf_db")
tools_module = None  # Set by setUpModule


def setUpModule():
    global tools_module
    for dep in _DEPS:
        _ORIGINAL_MODULES[dep] = sys.modules.get(dep, None)
    # Force-inject mocks (NOT setdefault — must override any real imports)
    sys.modules["golf_db"] = _golf_db_mock
    for dep in _DEPS[1:]:
        sys.modules[dep] = MagicMock(name=dep)
    # Evict any cached agent.* so agent.tools re-imports with our mocks
    for key in list(sys.modules):
        if key.startswith("agent."):
            del sys.modules[key]
    import agent.tools as _tools
    globals()["tools_module"] = _tools


def tearDownModule():
    for dep, original in _ORIGINAL_MODULES.items():
        if original is None:
            sys.modules.pop(dep, None)
        else:
            sys.modules[dep] = original
    # Clean up agent.* so subsequent tests get a fresh import
    for key in list(sys.modules):
        if key.startswith("agent."):
            del sys.modules[key]


def run_async(coro):
    """Helper to run an async function in tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Sample data factory
# ---------------------------------------------------------------------------

def _make_shots_df(n: int = 5, session_id: str = "sess_1", club: str = "Driver") -> pd.DataFrame:
    """Create a realistic shots DataFrame for testing."""
    rows = []
    for i in range(n):
        rows.append({
            "shot_id": f"shot_{i}",
            "session_id": session_id,
            "club": club,
            "carry": 250.0 + i * 5,
            "total": 270.0 + i * 5,
            "ball_speed": 160.0 + i,
            "club_speed": 107.0 + i,
            "smash": 1.49 + i * 0.01,
            "launch_angle": 12.0 + i * 0.5,
            "back_spin": 2500 + i * 100,
            "side_spin": -200 + i * 50,
            "face_angle": 1.0 + i * 0.5,
            "club_path": -2.0 + i * 0.3,
            "impact_x": 0.1 * i,
            "impact_y": 0.1 * i,
            "strike_distance": 0.1414 * i,
            "session_date": "2026-02-01",
            "date_added": "2026-02-01 10:00:00",
            "session_type": "Mixed Practice",
            "shot_tag": None,
        })
    return pd.DataFrame(rows)


def _make_multi_club_df() -> pd.DataFrame:
    """Create a DataFrame with multiple clubs."""
    driver = _make_shots_df(3, club="Driver")
    iron = _make_shots_df(4, club="7 Iron")
    iron["carry"] = [170.0, 172.0, 168.0, 175.0]
    iron["shot_id"] = ["shot_i0", "shot_i1", "shot_i2", "shot_i3"]
    return pd.concat([driver, iron], ignore_index=True)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestSafeMean(unittest.TestCase):
    """Test _safe_mean helper."""

    def test_normal_series(self):
        s = pd.Series([10.0, 20.0, 30.0])
        self.assertEqual(tools_module._safe_mean(s), 20.0)

    def test_ignores_zeros(self):
        s = pd.Series([0.0, 10.0, 20.0])
        self.assertEqual(tools_module._safe_mean(s), 15.0)

    def test_ignores_nan(self):
        s = pd.Series([10.0, float("nan"), 20.0])
        self.assertEqual(tools_module._safe_mean(s), 15.0)

    def test_all_zeros_returns_none(self):
        s = pd.Series([0.0, 0.0, 0.0])
        self.assertIsNone(tools_module._safe_mean(s))

    def test_empty_series_returns_none(self):
        s = pd.Series([], dtype=float)
        self.assertIsNone(tools_module._safe_mean(s))

    def test_rounds_to_one_decimal(self):
        s = pd.Series([1.0, 2.0, 3.0])  # mean = 2.0
        self.assertEqual(tools_module._safe_mean(s), 2.0)
        s2 = pd.Series([1.111, 2.222, 3.333])  # mean = 2.222
        self.assertEqual(tools_module._safe_mean(s2), 2.2)


class TestSafeStd(unittest.TestCase):
    """Test _safe_std helper."""

    def test_normal_series(self):
        s = pd.Series([10.0, 10.0, 10.0])
        self.assertEqual(tools_module._safe_std(s), 0.0)

    def test_single_value_returns_none(self):
        s = pd.Series([10.0])
        self.assertIsNone(tools_module._safe_std(s))

    def test_empty_returns_none(self):
        s = pd.Series([], dtype=float)
        self.assertIsNone(tools_module._safe_std(s))


class TestDfToSummary(unittest.TestCase):
    """Test _df_to_summary helper."""

    def test_normal_df(self):
        df = pd.DataFrame({"club": ["Driver", "7 Iron"], "carry": [250.0, 170.0]})
        result = tools_module._df_to_summary(df, ["club", "carry"])
        self.assertIn("Driver", result)
        self.assertIn("170.0", result)

    def test_empty_df(self):
        df = pd.DataFrame()
        result = tools_module._df_to_summary(df, ["club", "carry"])
        self.assertEqual(result, "(no data)")

    def test_missing_columns_handled(self):
        df = pd.DataFrame({"club": ["Driver"]})
        result = tools_module._df_to_summary(df, ["club", "nonexistent"])
        self.assertIn("Driver", result)


# ---------------------------------------------------------------------------
# Read tool tests
# ---------------------------------------------------------------------------

class TestQueryShots(unittest.TestCase):
    """Test query_shots tool."""

    def setUp(self):
        self.mock_db = _golf_db_mock
        self.mock_db.reset_mock()

    def test_returns_shots(self):
        self.mock_db.get_session_data.return_value = _make_shots_df(3)
        result = run_async(tools_module.query_shots.handler({"session_id": "sess_1"}))
        self.assertIn("content", result)
        text = result["content"][0]["text"]
        self.assertIn("3 shots", text)
        self.assertIn("sess_1", text)

    def test_empty_session(self):
        self.mock_db.get_session_data.return_value = pd.DataFrame()
        result = run_async(tools_module.query_shots.handler({"session_id": "missing"}))
        text = result["content"][0]["text"]
        self.assertIn("No shots found", text)

    def test_club_filter(self):
        self.mock_db.get_session_data.return_value = _make_multi_club_df()
        result = run_async(tools_module.query_shots.handler({"session_id": "sess_1", "club": "7 Iron"}))
        text = result["content"][0]["text"]
        self.assertIn("4 shots", text)

    def test_club_filter_no_match(self):
        self.mock_db.get_session_data.return_value = _make_shots_df(3, club="Driver")
        result = run_async(tools_module.query_shots.handler({"session_id": "sess_1", "club": "Putter"}))
        text = result["content"][0]["text"]
        self.assertIn("No shots found for club", text)

    def test_limit(self):
        self.mock_db.get_session_data.return_value = _make_shots_df(10)
        result = run_async(tools_module.query_shots.handler({"session_id": "sess_1", "limit": 3}))
        text = result["content"][0]["text"]
        self.assertIn("3 shots", text)


class TestGetSessionList(unittest.TestCase):
    """Test get_session_list tool."""

    def setUp(self):
        self.mock_db = _golf_db_mock
        self.mock_db.reset_mock()

    def test_returns_sessions(self):
        self.mock_db.get_unique_sessions.return_value = [
            {"session_id": "s1", "date_added": "2026-02-01", "session_type": "Mixed Practice"},
            {"session_id": "s2", "date_added": "2026-02-02", "session_type": None},
        ]
        result = run_async(tools_module.get_session_list.handler({}))
        text = result["content"][0]["text"]
        self.assertIn("2 sessions", text)
        self.assertIn("s1", text)
        self.assertIn("s2", text)

    def test_no_sessions(self):
        self.mock_db.get_unique_sessions.return_value = []
        result = run_async(tools_module.get_session_list.handler({}))
        text = result["content"][0]["text"]
        self.assertIn("No sessions found", text)


class TestGetSessionSummary(unittest.TestCase):
    """Test get_session_summary tool."""

    def setUp(self):
        self.mock_db = _golf_db_mock
        self.mock_db.reset_mock()

    def test_returns_json_summary(self):
        self.mock_db.get_session_data.return_value = _make_shots_df(5)
        result = run_async(tools_module.get_session_summary.handler({"session_id": "sess_1"}))
        text = result["content"][0]["text"]
        summary = json.loads(text)
        self.assertEqual(summary["session_id"], "sess_1")
        self.assertEqual(summary["shot_count"], 5)
        self.assertIn("avg_carry", summary)
        self.assertIn("big3", summary)
        self.assertIn("avg_face_angle", summary["big3"])

    def test_empty_session(self):
        self.mock_db.get_session_data.return_value = pd.DataFrame()
        result = run_async(tools_module.get_session_summary.handler({"session_id": "missing"}))
        text = result["content"][0]["text"]
        self.assertIn("No data found", text)


class TestGetClubStats(unittest.TestCase):
    """Test get_club_stats tool."""

    def setUp(self):
        self.mock_db = _golf_db_mock
        self.mock_db.reset_mock()

    def test_returns_all_clubs(self):
        self.mock_db.get_all_shots.return_value = _make_multi_club_df()
        result = run_async(tools_module.get_club_stats.handler({}))
        text = result["content"][0]["text"]
        stats = json.loads(text)
        club_names = [s["club"] for s in stats]
        self.assertIn("Driver", club_names)
        self.assertIn("7 Iron", club_names)

    def test_single_club_filter(self):
        self.mock_db.get_all_shots.return_value = _make_multi_club_df()
        result = run_async(tools_module.get_club_stats.handler({"club": "Driver"}))
        stats = json.loads(result["content"][0]["text"])
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]["club"], "Driver")

    def test_no_data(self):
        self.mock_db.get_all_shots.return_value = pd.DataFrame()
        result = run_async(tools_module.get_club_stats.handler({}))
        self.assertIn("No shot data", result["content"][0]["text"])

    def test_unknown_club_filter(self):
        self.mock_db.get_all_shots.return_value = _make_multi_club_df()
        result = run_async(tools_module.get_club_stats.handler({"club": "Putter"}))
        self.assertIn("No shots found for club", result["content"][0]["text"])


class TestGetTrends(unittest.TestCase):
    """Test get_trends tool."""

    def setUp(self):
        self.mock_db = _golf_db_mock
        self.mock_db.reset_mock()

    def test_carry_trend(self):
        # Create data spanning two sessions
        df1 = _make_shots_df(3, session_id="s1")
        df1["session_date"] = "2026-02-01"
        df2 = _make_shots_df(3, session_id="s2")
        df2["session_date"] = "2026-02-02"
        df2["shot_id"] = ["shot_a", "shot_b", "shot_c"]
        df2["carry"] = [260.0, 265.0, 270.0]
        combined = pd.concat([df1, df2], ignore_index=True)
        self.mock_db.get_all_shots.return_value = combined

        result = run_async(tools_module.get_trends.handler({"metric": "carry"}))
        text = result["content"][0]["text"]
        self.assertIn("Trend: carry", text)
        self.assertIn("s1", text)
        self.assertIn("s2", text)

    def test_no_data(self):
        self.mock_db.get_all_shots.return_value = pd.DataFrame()
        result = run_async(tools_module.get_trends.handler({}))
        self.assertIn("No shot data", result["content"][0]["text"])

    def test_unknown_metric(self):
        self.mock_db.get_all_shots.return_value = _make_shots_df(3)
        result = run_async(tools_module.get_trends.handler({"metric": "nonexistent"}))
        self.assertIn("Unknown metric", result["content"][0]["text"])


# ---------------------------------------------------------------------------
# Write tool tests
# ---------------------------------------------------------------------------

class TestTagSession(unittest.TestCase):
    """Test tag_session tool."""

    def setUp(self):
        self.mock_db = _golf_db_mock
        self.mock_db.reset_mock()

    def test_tags_shots(self):
        self.mock_db.get_session_data.return_value = _make_shots_df(3)
        self.mock_db.update_shot_metadata.return_value = 3

        result = run_async(tools_module.tag_session.handler({"session_id": "sess_1", "tag": "Warmup"}))
        text = result["content"][0]["text"]
        self.assertIn("Tagged 3 shots", text)
        self.assertIn("Warmup", text)

        # Verify correct golf_db call
        self.mock_db.update_shot_metadata.assert_called_once()
        call_args = self.mock_db.update_shot_metadata.call_args
        self.assertEqual(call_args[0][0], ["shot_0", "shot_1", "shot_2"])
        self.assertEqual(call_args[0][1], "shot_tag")
        self.assertEqual(call_args[0][2], "Warmup")

    def test_empty_session(self):
        self.mock_db.get_session_data.return_value = pd.DataFrame()
        result = run_async(tools_module.tag_session.handler({"session_id": "missing", "tag": "Warmup"}))
        self.assertIn("No shots found", result["content"][0]["text"])
        self.mock_db.update_shot_metadata.assert_not_called()


class TestUpdateSessionType(unittest.TestCase):
    """Test update_session_type tool."""

    def setUp(self):
        self.mock_db = _golf_db_mock
        self.mock_db.reset_mock()

    def test_updates_type(self):
        self.mock_db.get_session_data.return_value = _make_shots_df(4)
        self.mock_db.update_shot_metadata.return_value = 4

        result = run_async(tools_module.update_session_type_tool.handler({
            "session_id": "sess_1",
            "session_type": "Driver Focus",
        }))
        text = result["content"][0]["text"]
        self.assertIn("Driver Focus", text)
        self.assertIn("4 shots", text)

        self.mock_db.update_shot_metadata.assert_called_once()
        call_args = self.mock_db.update_shot_metadata.call_args
        self.assertEqual(call_args[0][1], "session_type")
        self.assertEqual(call_args[0][2], "Driver Focus")

    def test_empty_session(self):
        self.mock_db.get_session_data.return_value = pd.DataFrame()
        result = run_async(tools_module.update_session_type_tool.handler({
            "session_id": "missing",
            "session_type": "X",
        }))
        self.assertIn("No shots found", result["content"][0]["text"])


class TestBatchRenameSessions(unittest.TestCase):
    """Test batch_rename_sessions tool."""

    def setUp(self):
        self.mock_db = _golf_db_mock
        self.mock_db.reset_mock()

    def test_renames(self):
        self.mock_db.batch_update_session_names.return_value = 5
        result = run_async(tools_module.batch_rename_sessions.handler({}))
        text = result["content"][0]["text"]
        self.assertIn("Renamed 5 sessions", text)
        self.mock_db.batch_update_session_names.assert_called_once()


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------

class TestExports(unittest.TestCase):
    """Test ALL_TOOLS and TOOL_NAMES exports."""

    def test_all_tools_count(self):
        self.assertEqual(len(tools_module.ALL_TOOLS), 8)

    def test_tool_names_format(self):
        self.assertEqual(len(tools_module.TOOL_NAMES), 8)
        for name in tools_module.TOOL_NAMES:
            self.assertTrue(name.startswith("mcp__golf__"), f"Bad prefix: {name}")

    def test_tool_names_match_tools(self):
        expected_names = [f"mcp__golf__{t.name}" for t in tools_module.ALL_TOOLS]
        self.assertEqual(tools_module.TOOL_NAMES, expected_names)

    def test_all_tools_have_names(self):
        expected = {
            "query_shots",
            "get_session_list",
            "get_session_summary",
            "get_club_stats",
            "get_trends",
            "tag_session",
            "update_session_type",
            "batch_rename_sessions",
        }
        actual = {t.name for t in tools_module.ALL_TOOLS}
        self.assertEqual(actual, expected)

    def test_all_tools_are_sdk_mcp_tools(self):
        from claude_agent_sdk import SdkMcpTool
        for t in tools_module.ALL_TOOLS:
            self.assertIsInstance(t, SdkMcpTool, f"{t} is not an SdkMcpTool")


# ---------------------------------------------------------------------------
# Content format tests
# ---------------------------------------------------------------------------

class TestContentFormat(unittest.TestCase):
    """Verify all tools return the expected content block structure."""

    def setUp(self):
        self.mock_db = _golf_db_mock
        self.mock_db.reset_mock()

    def test_text_result_format(self):
        self.mock_db.get_unique_sessions.return_value = []
        result = run_async(tools_module.get_session_list.handler({}))
        self.assertIn("content", result)
        self.assertIsInstance(result["content"], list)
        self.assertEqual(len(result["content"]), 1)
        block = result["content"][0]
        self.assertEqual(block["type"], "text")
        self.assertIsInstance(block["text"], str)

    def test_json_result_format(self):
        self.mock_db.get_session_data.return_value = _make_shots_df(2)
        result = run_async(tools_module.get_session_summary.handler({"session_id": "s1"}))
        block = result["content"][0]
        self.assertEqual(block["type"], "text")
        # Should be valid JSON
        parsed = json.loads(block["text"])
        self.assertIsInstance(parsed, dict)


if __name__ == "__main__":
    unittest.main()
