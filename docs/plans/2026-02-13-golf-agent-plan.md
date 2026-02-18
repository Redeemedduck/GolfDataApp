# Golf Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an all-in-one golf coaching agent using the Claude Agent SDK, accessible via CLI, Claude Code skill, and Streamlit.

**Architecture:** Agent module inside GolfDataApp. Custom MCP tools wrap `golf_db.py` functions. Three thin interface adapters (CLI, skill, provider) all delegate to `agent/core.py`.

**Tech Stack:** Python, claude-agent-sdk 0.1.35, asyncio, golf_db.py (existing)

**Design Doc:** `docs/plans/2026-02-13-golf-agent-design.md`

---

### Task 1: Install SDK and Create Package Structure

**Files:**
- Create: `agent/__init__.py`
- Modify: `requirements.txt`

**Step 1: Install the Claude Agent SDK**

Run: `pip install claude-agent-sdk==0.1.35`
Expected: Successful install

**Step 2: Verify the installed version**

Run: `pip show claude-agent-sdk`
Expected: Version 0.1.35

**Step 3: Add to requirements.txt**

Add `claude-agent-sdk>=0.1.35` after the existing `anthropic` line in `requirements.txt`.

**Step 4: Create the agent package**

Create `agent/__init__.py`:

```python
"""Golf Agent — Claude Agent SDK powered golf coaching and analysis."""
```

**Step 5: Commit**

```bash
git add agent/__init__.py requirements.txt
git commit -m "feat(agent): initialize agent package and install claude-agent-sdk"
```

---

### Task 2: Define Read Tools

**Files:**
- Create: `agent/tools.py`
- Test: `tests/unit/test_agent_tools.py`

**Step 1: Write failing tests for tool definitions**

Create `tests/unit/test_agent_tools.py`:

```python
"""Tests for agent tool definitions and handlers."""

import asyncio
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd


class TestToolDefinitions(unittest.TestCase):
    """Verify tool objects exist and have correct metadata."""

    def test_tools_importable(self):
        from agent.tools import ALL_TOOLS
        self.assertIsInstance(ALL_TOOLS, list)
        self.assertGreater(len(ALL_TOOLS), 0)

    def test_tool_names_unique(self):
        from agent.tools import ALL_TOOLS
        names = [t.name for t in ALL_TOOLS]
        self.assertEqual(len(names), len(set(names)))

    def test_read_tools_present(self):
        from agent.tools import ALL_TOOLS
        names = [t.name for t in ALL_TOOLS]
        for expected in ["query_shots", "get_session_list", "get_session_summary",
                         "get_club_stats", "get_trends"]:
            self.assertIn(expected, names, f"Missing tool: {expected}")


class TestQueryShotsTool(unittest.TestCase):
    """Test query_shots tool handler."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @patch("agent.tools.golf_db")
    def test_query_shots_by_club(self, mock_db):
        from agent.tools import query_shots

        mock_df = pd.DataFrame({
            "shot_id": ["s1", "s2"],
            "club": ["Driver", "Driver"],
            "carry": [250.0, 260.0],
            "ball_speed": [165.0, 170.0],
        })
        mock_db.get_session_data.return_value = mock_df

        result = self._run(query_shots.handler({"club": "Driver"}))
        self.assertIn("content", result)
        text = result["content"][0]["text"]
        self.assertIn("250", text)

    @patch("agent.tools.golf_db")
    def test_query_shots_empty(self, mock_db):
        from agent.tools import query_shots

        mock_db.get_session_data.return_value = pd.DataFrame()

        result = self._run(query_shots.handler({"club": "Putter"}))
        text = result["content"][0]["text"]
        self.assertIn("No shots found", text)


class TestGetSessionListTool(unittest.TestCase):
    """Test get_session_list tool handler."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @patch("agent.tools.golf_db")
    def test_returns_sessions(self, mock_db):
        from agent.tools import get_session_list

        mock_db.get_unique_sessions.return_value = [
            {"session_id": "s1", "date_added": "2026-02-10", "session_type": "Mixed Practice"},
            {"session_id": "s2", "date_added": "2026-02-12", "session_type": "Driver Focus"},
        ]

        result = self._run(get_session_list.handler({}))
        text = result["content"][0]["text"]
        self.assertIn("s1", text)
        self.assertIn("s2", text)


class TestGetSessionSummaryTool(unittest.TestCase):
    """Test get_session_summary tool handler."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @patch("agent.tools.golf_db")
    def test_returns_summary(self, mock_db):
        from agent.tools import get_session_summary

        mock_df = pd.DataFrame({
            "shot_id": ["s1"],
            "club": ["Driver"],
            "carry": [250.0],
            "ball_speed": [165.0],
            "smash": [1.50],
            "face_angle": [-1.0],
            "club_path": [2.0],
            "impact_x": [0.5],
            "impact_y": [0.3],
        })
        mock_db.get_session_data.return_value = mock_df

        result = self._run(get_session_summary.handler({"session_id": "test_session"}))
        text = result["content"][0]["text"]
        self.assertIn("250", text)


class TestGetClubStatsTool(unittest.TestCase):
    """Test get_club_stats tool handler."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @patch("agent.tools.golf_db")
    def test_returns_club_stats(self, mock_db):
        from agent.tools import get_club_stats

        mock_df = pd.DataFrame({
            "shot_id": ["s1", "s2", "s3"],
            "club": ["Driver", "Driver", "7 Iron"],
            "carry": [250.0, 260.0, 165.0],
            "ball_speed": [165.0, 170.0, 130.0],
            "smash": [1.50, 1.48, 1.42],
        })
        mock_db.get_all_shots.return_value = mock_df

        result = self._run(get_club_stats.handler({"club": "Driver"}))
        text = result["content"][0]["text"]
        self.assertIn("Driver", text)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_agent_tools -v`
Expected: ImportError — `agent.tools` not found

**Step 3: Implement the read tools**

Create `agent/tools.py`:

```python
"""Golf Agent tool definitions.

Each tool wraps golf_db functions and returns MCP-compatible content blocks.
Tools are defined using the Claude Agent SDK @tool decorator.
"""

import json
from typing import Any

import pandas as pd
import numpy as np

from claude_agent_sdk import tool

import golf_db


def _df_to_summary(df: pd.DataFrame, columns: list[str] | None = None) -> str:
    """Convert a DataFrame to a readable text summary."""
    if df.empty:
        return "No data available."
    cols = columns or [c for c in df.columns if c != "shot_id"]
    # Limit to relevant columns that exist
    cols = [c for c in cols if c in df.columns]
    return df[cols].to_string(index=False, max_rows=50)


def _safe_mean(series: pd.Series) -> float | None:
    """Compute mean, filtering out None/NaN/zero for measurement columns."""
    valid = series.dropna()
    valid = valid[valid != 0]
    if valid.empty:
        return None
    return round(float(valid.mean()), 1)


def _safe_std(series: pd.Series) -> float | None:
    """Compute std dev, filtering out None/NaN."""
    valid = series.dropna()
    if len(valid) < 2:
        return None
    return round(float(valid.std()), 1)


# ──────────────────────────────────────────────
# READ TOOLS
# ──────────────────────────────────────────────

@tool(
    "query_shots",
    "Query shot data with optional filters. Returns shot-level data for analysis. "
    "Use this to look at raw shot data for a specific club, session, or date range.",
    {
        "type": "object",
        "properties": {
            "club": {"type": "string", "description": "Filter by club name (e.g. 'Driver', '7 Iron')"},
            "session_id": {"type": "string", "description": "Filter by session ID"},
            "limit": {"type": "integer", "description": "Max rows to return (default 50)"},
        },
        "required": [],
    },
)
async def query_shots(args: dict[str, Any]) -> dict[str, Any]:
    club = args.get("club")
    session_id = args.get("session_id")
    limit = args.get("limit", 50)

    df = golf_db.get_session_data(session_id)

    if df.empty:
        return {"content": [{"type": "text", "text": "No shots found matching those filters."}]}

    if club:
        df = df[df["club"].str.lower() == club.lower()]

    if df.empty:
        return {"content": [{"type": "text", "text": f"No shots found for club '{club}'."}]}

    display_cols = ["club", "carry", "total", "ball_speed", "club_speed", "smash",
                    "launch_angle", "back_spin", "face_angle", "club_path",
                    "session_id", "session_date"]
    summary = _df_to_summary(df.head(limit), display_cols)

    return {"content": [{"type": "text", "text": f"Found {len(df)} shots:\n\n{summary}"}]}


@tool(
    "get_session_list",
    "List all practice sessions with dates, types, and shot counts. "
    "Use this to see what sessions are available before diving into details.",
    {"type": "object", "properties": {}, "required": []},
)
async def get_session_list(args: dict[str, Any]) -> dict[str, Any]:
    sessions = golf_db.get_unique_sessions()

    if not sessions:
        return {"content": [{"type": "text", "text": "No sessions found in the database."}]}

    lines = [f"Found {len(sessions)} sessions:\n"]
    for s in sessions:
        sid = s.get("session_id", "?")
        date = s.get("date_added", "unknown date")
        stype = s.get("session_type", "")
        lines.append(f"- {sid} | {date} | {stype}")

    return {"content": [{"type": "text", "text": "\n".join(lines)}]}


@tool(
    "get_session_summary",
    "Get aggregated stats for a specific session: shot count, clubs used, "
    "average carry, ball speed, smash factor, and Big 3 metrics (face angle, club path, strike quality).",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "The session ID to summarize"},
        },
        "required": ["session_id"],
    },
)
async def get_session_summary(args: dict[str, Any]) -> dict[str, Any]:
    session_id = args["session_id"]
    df = golf_db.get_session_data(session_id)

    if df.empty:
        return {"content": [{"type": "text", "text": f"No data found for session '{session_id}'."}]}

    summary = {
        "session_id": session_id,
        "shot_count": len(df),
        "clubs_used": df["club"].unique().tolist() if "club" in df.columns else [],
        "avg_carry": _safe_mean(df.get("carry")),
        "avg_ball_speed": _safe_mean(df.get("ball_speed")),
        "avg_smash": _safe_mean(df.get("smash")),
        "avg_face_angle": _safe_mean(df.get("face_angle")),
        "avg_club_path": _safe_mean(df.get("club_path")),
    }

    # Compute strike quality if impact data available
    if "impact_x" in df.columns and "impact_y" in df.columns:
        strike_dist = np.sqrt(df["impact_x"] ** 2 + df["impact_y"] ** 2)
        summary["avg_strike_distance"] = round(float(strike_dist.dropna().mean()), 1)

    text = json.dumps(summary, indent=2, default=str)
    return {"content": [{"type": "text", "text": f"Session summary:\n{text}"}]}


@tool(
    "get_club_stats",
    "Get per-club performance stats: average carry, ball speed, smash factor, "
    "consistency (std dev), and shot count. Optionally filter to a single club.",
    {
        "type": "object",
        "properties": {
            "club": {"type": "string", "description": "Specific club to analyze (omit for all clubs)"},
        },
        "required": [],
    },
)
async def get_club_stats(args: dict[str, Any]) -> dict[str, Any]:
    df = golf_db.get_all_shots()

    if df.empty:
        return {"content": [{"type": "text", "text": "No shot data available."}]}

    club_filter = args.get("club")
    if club_filter:
        df = df[df["club"].str.lower() == club_filter.lower()]
        if df.empty:
            return {"content": [{"type": "text", "text": f"No data for club '{club_filter}'."}]}

    stats_rows = []
    for club_name, group in df.groupby("club"):
        stats_rows.append({
            "club": club_name,
            "shots": len(group),
            "avg_carry": _safe_mean(group.get("carry")),
            "carry_std": _safe_std(group.get("carry")),
            "avg_ball_speed": _safe_mean(group.get("ball_speed")),
            "avg_smash": _safe_mean(group.get("smash")),
            "avg_face_angle": _safe_mean(group.get("face_angle")),
            "avg_club_path": _safe_mean(group.get("club_path")),
        })

    text = json.dumps(stats_rows, indent=2, default=str)
    return {"content": [{"type": "text", "text": f"Club statistics:\n{text}"}]}


@tool(
    "get_trends",
    "Analyze how a metric is trending over recent sessions. "
    "Shows per-session averages to identify improvement or regression.",
    {
        "type": "object",
        "properties": {
            "metric": {
                "type": "string",
                "description": "Metric to trend: carry, ball_speed, smash, face_angle, club_path, launch_angle",
            },
            "club": {"type": "string", "description": "Optional club filter"},
            "sessions": {"type": "integer", "description": "Number of recent sessions (default 10)"},
        },
        "required": ["metric"],
    },
)
async def get_trends(args: dict[str, Any]) -> dict[str, Any]:
    metric = args["metric"]
    club_filter = args.get("club")
    num_sessions = args.get("sessions", 10)

    df = golf_db.get_all_shots()

    if df.empty:
        return {"content": [{"type": "text", "text": "No shot data available."}]}

    if metric not in df.columns:
        return {"content": [{"type": "text", "text": f"Unknown metric '{metric}'. Available: {list(df.columns)}"}]}

    if club_filter:
        df = df[df["club"].str.lower() == club_filter.lower()]

    # Group by session and compute mean
    if "session_date" in df.columns:
        sort_col = "session_date"
    else:
        sort_col = "date_added"

    session_avgs = (
        df.groupby("session_id")
        .agg({metric: "mean", sort_col: "first"})
        .sort_values(sort_col, ascending=False)
        .head(num_sessions)
        .round(1)
    )

    text = f"Trend for {metric}" + (f" ({club_filter})" if club_filter else "") + f" over last {len(session_avgs)} sessions:\n\n"
    text += session_avgs.to_string()

    return {"content": [{"type": "text", "text": text}]}


# ──────────────────────────────────────────────
# SAFE WRITE TOOLS
# ──────────────────────────────────────────────

@tool(
    "tag_session",
    "Add or update a tag on all shots in a session. "
    "Tags help categorize sessions for later analysis.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Session to tag"},
            "tag": {"type": "string", "description": "Tag value to apply"},
        },
        "required": ["session_id", "tag"],
    },
)
async def tag_session(args: dict[str, Any]) -> dict[str, Any]:
    session_id = args["session_id"]
    tag = args["tag"]

    # Get shot IDs for this session
    df = golf_db.get_session_data(session_id)
    if df.empty:
        return {"content": [{"type": "text", "text": f"No shots found for session '{session_id}'."}]}

    shot_ids = df["shot_id"].tolist()
    count = golf_db.update_shot_metadata(shot_ids, "shot_tag", tag)

    return {"content": [{"type": "text", "text": f"Tagged {count} shots in session '{session_id}' with '{tag}'."}]}


@tool(
    "update_session_type",
    "Update the session type for all shots in a session. "
    "Valid types: Driver Focus, Iron Work, Short Game, Woods Focus, Mixed Practice, Warmup.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Session to update"},
            "session_type": {"type": "string", "description": "New session type"},
        },
        "required": ["session_id", "session_type"],
    },
)
async def update_session_type(args: dict[str, Any]) -> dict[str, Any]:
    session_id = args["session_id"]
    session_type = args["session_type"]

    df = golf_db.get_session_data(session_id)
    if df.empty:
        return {"content": [{"type": "text", "text": f"No shots found for session '{session_id}'."}]}

    shot_ids = df["shot_id"].tolist()
    count = golf_db.update_shot_metadata(shot_ids, "session_type", session_type)

    return {"content": [{"type": "text", "text": f"Updated {count} shots in session '{session_id}' to type '{session_type}'."}]}


@tool(
    "batch_rename_sessions",
    "Regenerate display names for all sessions based on their shot data. "
    "Names follow the format: 'YYYY-MM-DD SessionType (N shots)'.",
    {"type": "object", "properties": {}, "required": []},
)
async def batch_rename_sessions(args: dict[str, Any]) -> dict[str, Any]:
    count = golf_db.batch_update_session_names()
    return {"content": [{"type": "text", "text": f"Renamed {count} sessions."}]}


# ──────────────────────────────────────────────
# TOOL REGISTRY
# ──────────────────────────────────────────────

ALL_TOOLS = [
    query_shots,
    get_session_list,
    get_session_summary,
    get_club_stats,
    get_trends,
    tag_session,
    update_session_type,
    batch_rename_sessions,
]

TOOL_NAMES = [f"mcp__golf__{t.name}" for t in ALL_TOOLS]
```

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_agent_tools -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add agent/tools.py tests/unit/test_agent_tools.py
git commit -m "feat(agent): add read and write tool definitions with tests"
```

---

### Task 3: Agent Core

**Files:**
- Create: `agent/core.py`
- Test: `tests/unit/test_agent_core.py`

**Step 1: Write failing tests for core**

Create `tests/unit/test_agent_core.py`:

```python
"""Tests for agent core configuration."""

import unittest


class TestAgentCore(unittest.TestCase):
    """Verify agent configuration is correct."""

    def test_core_importable(self):
        from agent.core import create_golf_agent_options
        self.assertTrue(callable(create_golf_agent_options))

    def test_system_prompt_present(self):
        from agent.core import SYSTEM_PROMPT
        self.assertIn("golf", SYSTEM_PROMPT.lower())
        self.assertIn("Big 3", SYSTEM_PROMPT)
        self.assertIn("Uneekor", SYSTEM_PROMPT)

    def test_options_have_tools(self):
        from agent.core import create_golf_agent_options
        options = create_golf_agent_options()
        self.assertIsNotNone(options.mcp_servers)
        self.assertGreater(len(options.allowed_tools), 0)

    def test_options_use_sonnet(self):
        from agent.core import create_golf_agent_options
        options = create_golf_agent_options()
        self.assertIn("sonnet", options.model)

    def test_no_dangerous_tools(self):
        from agent.core import create_golf_agent_options
        options = create_golf_agent_options()
        for tool_name in options.allowed_tools:
            self.assertNotIn("Bash", tool_name)
            self.assertNotIn("Write", tool_name)
            self.assertNotIn("Edit", tool_name)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.unit.test_agent_core -v`
Expected: ImportError

**Step 3: Implement agent core**

Create `agent/core.py`:

```python
"""Golf Agent core — Claude Agent SDK configuration and factory functions.

This is the only module that imports from claude_agent_sdk.
All interfaces (CLI, skill, Streamlit) delegate to this module.
"""

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    create_sdk_mcp_server,
    query,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)

from agent.tools import ALL_TOOLS, TOOL_NAMES


SYSTEM_PROMPT = """\
You are a personal golf coach analyzing real practice data from a Uneekor EYE XO2 launch monitor.

## Your Knowledge

You understand the Big 3 Impact Laws that determine ball flight:
1. **Face Angle** — where the clubface points at impact (open/closed/square)
2. **Club Path** — the direction the club is moving through impact (in-to-out / out-to-in)
3. **Strike Quality** — how centered the impact is on the clubface (measured by impact_x, impact_y)

You know how to interpret launch monitor metrics:
- **Carry** — distance the ball flies through the air (yards)
- **Total** — carry + roll distance
- **Ball Speed** — speed of the ball off the clubface (mph)
- **Club Speed** — speed of the clubhead at impact (mph)
- **Smash Factor** — ball_speed / club_speed (efficiency, ideal ~1.50 for driver)
- **Launch Angle** — vertical angle the ball leaves the clubface (degrees)
- **Back Spin** — rpm of backspin
- **Side Spin** — rpm of sidespin (positive = right for RH golfer)

## Your Style

- Be encouraging but honest — celebrate progress, flag concerns
- Use specific numbers from the data, not vague generalizations
- When suggesting improvements, prioritize the Big 3 — they have the most impact
- Keep responses concise unless asked for detail
- If data is limited, say so rather than over-interpreting

## Your Capabilities

You can query the database for shots, sessions, club stats, and trends.
You can tag sessions and update session types to help with organization.
You CANNOT delete data, trigger automation, or access external services.
If asked to do something outside your capabilities, explain what the user should do manually.
"""


def create_golf_mcp_server():
    """Create the MCP server with all golf tools."""
    return create_sdk_mcp_server(
        name="golf_data",
        version="1.0.0",
        tools=ALL_TOOLS,
    )


def create_golf_agent_options(**overrides) -> ClaudeAgentOptions:
    """Create ClaudeAgentOptions for the golf agent.

    Args:
        **overrides: Any ClaudeAgentOptions fields to override defaults.

    Returns:
        Configured ClaudeAgentOptions.
    """
    server = create_golf_mcp_server()

    defaults = dict(
        system_prompt=SYSTEM_PROMPT,
        model="claude-sonnet-4-5-20250929",
        mcp_servers={"golf": server},
        allowed_tools=TOOL_NAMES,
        max_turns=20,
    )
    defaults.update(overrides)
    return ClaudeAgentOptions(**defaults)


async def single_query(prompt: str, **option_overrides) -> str:
    """Send a single query and return the full text response.

    Used by the Streamlit provider and --single CLI mode.
    """
    options = create_golf_agent_options(**option_overrides)
    response_parts = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_parts.append(block.text)

    return "\n".join(response_parts)
```

**Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.unit.test_agent_core -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add agent/core.py tests/unit/test_agent_core.py
git commit -m "feat(agent): add core module with system prompt and SDK configuration"
```

---

### Task 4: CLI Interface

**Files:**
- Create: `agent/cli.py`

**Step 1: Create the CLI**

Create `agent/cli.py`:

```python
"""Golf Agent CLI — terminal chat interface.

Usage:
    python -m agent.cli                     # Interactive chat
    python -m agent.cli --single "question" # One-shot query
"""

import asyncio
import argparse
import sys

from claude_agent_sdk import (
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)

from agent.core import create_golf_agent_options, single_query


async def interactive_chat():
    """Run an interactive chat loop with the golf agent."""
    options = create_golf_agent_options()

    print("Golf Agent ready. Type 'quit' to exit.\n")

    async with ClaudeSDKClient(options=options) as client:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            await client.query(user_input)

            print("Coach: ", end="", flush=True)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            print(block.text, end="", flush=True)
            print("\n")


async def one_shot(question: str):
    """Send a single question and print the response."""
    response = await single_query(question)
    print(response)


def main():
    parser = argparse.ArgumentParser(description="Golf Agent — AI golf coaching from your data")
    parser.add_argument("--single", "-s", type=str, help="Ask a single question and exit")
    args = parser.parse_args()

    if args.single:
        asyncio.run(one_shot(args.single))
    else:
        asyncio.run(interactive_chat())


if __name__ == "__main__":
    main()
```

**Step 2: Verify syntax compiles**

Run: `python -m py_compile agent/cli.py`
Expected: No output (success)

**Step 3: Commit**

```bash
git add agent/cli.py
git commit -m "feat(agent): add CLI interface with interactive and single-shot modes"
```

---

### Task 5: Streamlit Provider

**Files:**
- Create: `services/ai/providers/claude_provider.py`
- Test: `tests/unit/test_claude_provider.py`

**Step 1: Write failing test**

Create `tests/unit/test_claude_provider.py`:

```python
"""Tests for the Claude AI Coach provider."""

import unittest


class TestClaudeProviderRegistration(unittest.TestCase):
    """Verify provider registers correctly."""

    def test_provider_importable(self):
        from services.ai.providers.claude_provider import ClaudeProvider
        self.assertEqual(ClaudeProvider.PROVIDER_ID, "claude")
        self.assertEqual(ClaudeProvider.DISPLAY_NAME, "Claude Golf Coach")

    def test_provider_registered(self):
        from services.ai import get_provider
        # Force import of claude_provider
        import services.ai.providers.claude_provider  # noqa: F401
        spec = get_provider("claude")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.provider_id, "claude")

    def test_is_configured_checks_env(self):
        from services.ai.providers.claude_provider import ClaudeProvider
        import os
        # Without key set, should return False (or True depending on env)
        result = ClaudeProvider.is_configured()
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.unit.test_claude_provider -v`
Expected: ImportError

**Step 3: Implement the provider**

Create `services/ai/providers/claude_provider.py`:

```python
"""Claude AI Coach Provider for GolfDataApp.

Provides golf coaching via the Claude Agent SDK,
using the same tool-equipped agent as the CLI.
"""

import os
import asyncio
from services.ai.registry import register_provider


@register_provider
class ClaudeProvider:
    """Claude-powered AI golf coach using the Agent SDK."""

    PROVIDER_ID = "claude"
    DISPLAY_NAME = "Claude Golf Coach"

    def __init__(self, model_type: str = "sonnet", thinking_level: str = "medium"):
        self._model_type = model_type
        self._thinking_level = thinking_level
        self._conversation_history = []

    @staticmethod
    def is_configured() -> bool:
        """Check if ANTHROPIC_API_KEY is available."""
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    def chat(self, message: str) -> dict:
        """Process a chat message using the golf agent.

        Args:
            message: User's question or request

        Returns:
            Dict with 'response' and 'function_calls' keys (matching Gemini format)
        """
        from agent.core import single_query

        try:
            response = asyncio.run(single_query(message))
        except Exception as e:
            response = f"Error communicating with Claude: {e}"

        return {
            "response": response,
            "function_calls": [],
        }

    def reset_conversation(self):
        """Reset conversation state."""
        self._conversation_history = []

    def set_model(self, model_type: str):
        """Set model type."""
        self._model_type = model_type

    def set_thinking_level(self, level: str):
        """Set thinking level."""
        self._thinking_level = level

    def get_model_name(self) -> str:
        """Return the model display name."""
        return "Claude Sonnet 4.5"
```

**Step 4: Run tests**

Run: `python -m unittest tests.unit.test_claude_provider -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/ai/providers/claude_provider.py tests/unit/test_claude_provider.py
git commit -m "feat(agent): add Claude provider for Streamlit AI Coach page"
```

---

### Task 6: Claude Code Skill

**Files:**
- Create: `~/.claude/skills/golf/SKILL.md`

**Step 1: Create the skill file**

Create `~/.claude/skills/golf/SKILL.md`:

```markdown
---
name: golf
description: Ask your Golf Agent a question about your practice data, trends, and performance
user_invocable: true
---

# Golf Agent

Query your golf data using the Claude Agent SDK powered golf agent.

## Usage

The user provides a question as $ARGUMENTS. If no arguments given, ask what they want to know.

## Execution

Run the golf agent in single-shot mode from the GolfDataApp directory:

```bash
cd /Users/max1/Documents/GitHub/GolfDataApp && op run --env-file=.env.template -- python -m agent.cli --single "$ARGUMENTS"
```

If the command fails because the agent SDK isn't installed, tell the user to run:
```bash
cd /Users/max1/Documents/GitHub/GolfDataApp && pip install -r requirements.txt
```

## Example Questions

- "How's my driver been this month?"
- "Compare my last two sessions"
- "What clubs should I focus on?"
- "Show me my carry trends for the 7 Iron"
- "Tag my last session as 'range day'"
```

**Step 2: Verify file exists**

Run: `ls -la ~/.claude/skills/golf/SKILL.md`
Expected: File exists

**Step 3: Commit (in GolfDataApp repo — skill file is external but we note it)**

No git commit for external skill file. Instead, add a note about it.

---

### Task 7: Environment Setup

**Files:**
- Create or modify: `.env.template`

**Step 1: Create .env.template**

Create `.env.template` (or update if it exists):

```
# Golf Data App Environment Variables
# Use with: op inject -i .env.template -o .env

# AI Providers
GEMINI_API_KEY=op://Private/Gemini/credential
ANTHROPIC_API_KEY=op://Private/Anthropic/credential

# Cloud Database (optional)
SUPABASE_URL=op://Private/Supabase-GolfData/url
SUPABASE_KEY=op://Private/Supabase-GolfData/key

# Notifications (optional)
SLACK_WEBHOOK_URL=op://Private/Slack-Golf-Webhook/url
```

**Step 2: Update .gitignore if needed**

Ensure `.env` is in `.gitignore` (it likely already is).

**Step 3: Commit**

```bash
git add .env.template
git commit -m "feat(agent): add .env.template with 1Password references"
```

---

### Task 8: Syntax Check and Integration Verification

**Step 1: Compile check all new files**

Run:
```bash
python -m py_compile agent/__init__.py
python -m py_compile agent/tools.py
python -m py_compile agent/core.py
python -m py_compile agent/cli.py
python -m py_compile services/ai/providers/claude_provider.py
```
Expected: No output (all compile cleanly)

**Step 2: Run all tests**

Run: `python -m unittest discover -s tests -v`
Expected: All tests pass

**Step 3: Final commit if any fixes were needed**

---

### Task 9: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add agent documentation to CLAUDE.md**

Add a section under "Core Modules" table:

```markdown
| `agent/` | Claude Agent SDK golf coach: CLI, Streamlit provider, custom tools wrapping golf_db |
```

Add to "Common Commands":

```bash
# Run the Golf Agent (interactive chat)
op run --env-file=.env.template -- python -m agent.cli

# Run a single query
op run --env-file=.env.template -- python -m agent.cli --single "How's my driver?"

# Run agent tests
python -m unittest tests.unit.test_agent_tools tests.unit.test_agent_core tests.unit.test_claude_provider
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add agent module to CLAUDE.md"
```
