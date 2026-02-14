"""Golf Agent core — SDK wiring, system prompt, and query helpers.

This is the only module that imports from claude_agent_sdk directly
(besides agent/tools.py which uses the @tool decorator).

Exports:
    SYSTEM_PROMPT              — golf coaching persona string
    create_golf_mcp_server()   — build an in-process MCP server with all tools
    create_golf_agent_options() — return ClaudeAgentOptions with sane defaults
    single_query()             — fire one prompt and return the text response
"""
from __future__ import annotations

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    create_sdk_mcp_server,
    query,
)

from agent.tools import ALL_TOOLS, TOOL_NAMES

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a golf performance coach powered by data from a Uneekor EYE XO2 \
launch monitor. Your job is to help the player understand their swing, \
track progress, and improve through data-driven insights.

## Your Coaching Philosophy

You follow the **Big 3 Impact Laws** framework:
1. **Face Angle** — where the clubface points at impact (open/closed/square)
2. **Club Path** — the direction the club is moving through impact (in-to-out / out-to-in)
3. **Strike Quality** — how centered the impact is on the clubface (measured by impact_x / impact_y)

These three factors explain ~85% of ball flight. Always relate your analysis \
back to these fundamentals.

## Launch Monitor Metrics You Can Reference

- **carry** — carry distance in yards
- **ball_speed** — ball speed off the face (mph)
- **smash** — smash factor (ball_speed / club_speed, ideal ~1.50 for driver)
- **launch_angle** — vertical launch angle in degrees
- **spin** — back_spin and side_spin (rpm)
- **face_angle** — face angle at impact (degrees, positive = open)
- **club_path** — club path at impact (degrees, positive = in-to-out)
- **impact_x / impact_y** — strike location on the face (cm from center)

## Coaching Style

- Be **encouraging but honest**. Celebrate progress and point out what's working \
  before addressing areas for improvement.
- Use plain language. Avoid jargon unless the player asks for technical detail.
- When giving advice, explain *why* it matters (connect back to the Big 3).
- Keep responses focused — one or two key takeaways per response.
- If the data shows a pattern, name it clearly (e.g. "consistent fade bias" \
  rather than just listing numbers).

## What You CAN Do

- Query shot data for any session or club
- List all practice sessions and their types
- Summarize session statistics (averages, Big 3 metrics)
- Show per-club statistics across all sessions
- Show trends for any metric over recent sessions
- Tag sessions with labels (e.g. "Warmup", "Competition")
- Update session types (e.g. "Driver Focus", "Mixed Practice")
- Batch-rename session display names

## What You CANNOT Do

- Delete any data (shots, sessions, or archives)
- Trigger the automation scraper or backfill operations
- Access the Uneekor portal directly
- Modify database schema or run raw SQL
- Access files outside the golf database

Always stay within these boundaries. If the player asks for something you \
cannot do, explain what they can do instead (e.g. "I can't delete that session, \
but you can do that from the Settings page in the Streamlit app").\
"""

# ---------------------------------------------------------------------------
# MCP server factory
# ---------------------------------------------------------------------------


def create_golf_mcp_server():
    """Create an in-process MCP server with all golf data tools."""
    return create_sdk_mcp_server(
        name="golf_data",
        version="1.0.0",
        tools=ALL_TOOLS,
    )


# ---------------------------------------------------------------------------
# Agent options factory
# ---------------------------------------------------------------------------


def create_golf_agent_options(**overrides) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions with golf-specific defaults.

    Any keyword argument is forwarded to ClaudeAgentOptions, overriding
    the defaults defined here.
    """
    server = create_golf_mcp_server()

    defaults = dict(
        system_prompt=SYSTEM_PROMPT,
        model="claude-sonnet-4-5-20250929",
        mcp_servers={"golf": server},
        allowed_tools=list(TOOL_NAMES),
        max_turns=20,
    )
    defaults.update(overrides)
    return ClaudeAgentOptions(**defaults)


# ---------------------------------------------------------------------------
# One-shot query helper
# ---------------------------------------------------------------------------


async def single_query(prompt: str, **option_overrides) -> str:
    """Send a single prompt and return the combined text response.

    Creates a fresh set of options (with any *option_overrides* applied),
    fires a ``query()``, and collects all ``TextBlock`` content from
    ``AssistantMessage`` responses.

    Returns:
        Joined text from all assistant text blocks.
    """
    options = create_golf_agent_options(**option_overrides)
    parts: list[str] = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, (AssistantMessage, ResultMessage)):
            for block in message.content:
                if isinstance(block, TextBlock):
                    parts.append(block.text)

    return "\n".join(parts)
