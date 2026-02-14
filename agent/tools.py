"""Golf Agent SDK tool definitions.

Provides read and write tools that wrap golf_db functions for use
with the Claude Agent SDK MCP server.

Exports:
    ALL_TOOLS  — list of SdkMcpTool objects
    TOOL_NAMES — list of "mcp__golf__{name}" strings
"""
from __future__ import annotations

import json
import sys
import os
from typing import Any

from claude_agent_sdk import tool

# Ensure project root is importable
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import golf_db  # noqa: E402
import pandas as pd  # noqa: E402


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _safe_mean(series: pd.Series) -> float | None:
    """Mean of non-null, non-zero values, rounded to 1 decimal."""
    filtered = series.dropna()
    filtered = filtered[filtered != 0]
    if filtered.empty:
        return None
    return round(float(filtered.mean()), 1)


def _safe_std(series: pd.Series) -> float | None:
    """Std dev of non-null values, rounded to 1 decimal."""
    filtered = series.dropna()
    if len(filtered) < 2:
        return None
    return round(float(filtered.std()), 1)


def _df_to_summary(df: pd.DataFrame, columns: list[str]) -> str:
    """Convert a DataFrame to a readable text table.

    Selects only the requested columns (that exist), formats each row
    as a pipe-delimited line, and returns the whole thing as a string.
    """
    available = [c for c in columns if c in df.columns]
    if not available or df.empty:
        return "(no data)"
    subset = df[available].copy()
    # Round numeric columns for readability
    for col in subset.select_dtypes(include=["number"]).columns:
        subset[col] = subset[col].round(1)
    lines = [" | ".join(str(c) for c in available)]
    lines.append("-" * len(lines[0]))
    for _, row in subset.iterrows():
        lines.append(" | ".join(str(row[c]) if pd.notna(row[c]) else "-" for c in available))
    return "\n".join(lines)


def _text_result(text: str) -> dict[str, Any]:
    """Convenience wrapper for a text content block."""
    return {"content": [{"type": "text", "text": text}]}


def _json_result(obj: Any) -> dict[str, Any]:
    """Convenience wrapper for a JSON content block."""
    return {"content": [{"type": "text", "text": json.dumps(obj, default=str)}]}


# ---------------------------------------------------------------------------
# Read Tools
# ---------------------------------------------------------------------------

@tool(
    "query_shots",
    "Query shot data for a session. Optionally filter by club and limit rows.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Session ID to query"},
            "club": {"type": "string", "description": "Optional club filter (e.g. 'Driver', '7 Iron')"},
            "limit": {"type": "integer", "description": "Max rows to return (default 50)"},
        },
        "required": ["session_id"],
    },
)
async def query_shots(args: dict[str, Any]) -> dict[str, Any]:
    """Return readable shot data for a session."""
    session_id = args["session_id"]
    club_filter = args.get("club")
    limit = args.get("limit", 50)

    df = golf_db.get_session_data(session_id=session_id, read_mode="sqlite")
    if df.empty:
        return _text_result(f"No shots found for session {session_id}.")

    if club_filter:
        df = df[df["club"].str.lower() == club_filter.lower()]
        if df.empty:
            return _text_result(f"No shots found for club '{club_filter}' in session {session_id}.")

    df = df.head(limit)

    display_cols = [
        "shot_id", "club", "carry", "total", "ball_speed", "club_speed",
        "smash", "launch_angle", "back_spin", "side_spin",
        "face_angle", "club_path", "impact_x", "impact_y",
    ]
    text = _df_to_summary(df, display_cols)
    return _text_result(f"Session {session_id} — {len(df)} shots:\n{text}")


@tool(
    "get_session_list",
    "List all practice sessions with IDs, dates, and types.",
    {
        "type": "object",
        "properties": {},
        "required": [],
    },
)
async def get_session_list(args: dict[str, Any]) -> dict[str, Any]:
    """Return a list of all sessions."""
    sessions = golf_db.get_unique_sessions(read_mode="sqlite")
    if not sessions:
        return _text_result("No sessions found.")

    lines = [f"Found {len(sessions)} sessions:\n"]
    for s in sessions:
        sid = s.get("session_id", "?")
        date = s.get("date_added", "?")
        stype = s.get("session_type") or "—"
        lines.append(f"  {sid}  |  {date}  |  {stype}")
    return _text_result("\n".join(lines))


@tool(
    "get_session_summary",
    "Get aggregate statistics for a session: avg carry, ball speed, smash, Big 3 metrics.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Session ID to summarize"},
        },
        "required": ["session_id"],
    },
)
async def get_session_summary(args: dict[str, Any]) -> dict[str, Any]:
    """Compute and return aggregate stats for a session."""
    session_id = args["session_id"]
    df = golf_db.get_session_data(session_id=session_id, read_mode="sqlite")
    if df.empty:
        return _text_result(f"No data found for session {session_id}.")

    summary: dict[str, Any] = {
        "session_id": session_id,
        "shot_count": len(df),
        "clubs": sorted(df["club"].dropna().unique().tolist()) if "club" in df.columns else [],
    }

    metric_cols = {
        "avg_carry": "carry",
        "avg_total": "total",
        "avg_ball_speed": "ball_speed",
        "avg_club_speed": "club_speed",
        "avg_smash": "smash",
    }
    for key, col in metric_cols.items():
        if col in df.columns:
            summary[key] = _safe_mean(df[col])

    # Big 3 metrics
    big3 = {}
    if "face_angle" in df.columns:
        big3["avg_face_angle"] = _safe_mean(df["face_angle"])
        big3["std_face_angle"] = _safe_std(df["face_angle"])
    if "club_path" in df.columns:
        big3["avg_club_path"] = _safe_mean(df["club_path"])
        big3["std_club_path"] = _safe_std(df["club_path"])
    if "strike_distance" in df.columns:
        big3["avg_strike_distance"] = _safe_mean(df["strike_distance"])
        big3["std_strike_distance"] = _safe_std(df["strike_distance"])
    elif "impact_x" in df.columns and "impact_y" in df.columns:
        import math
        ix = df["impact_x"].fillna(0)
        iy = df["impact_y"].fillna(0)
        strike = (ix**2 + iy**2).apply(math.sqrt)
        big3["avg_strike_distance"] = _safe_mean(strike)
        big3["std_strike_distance"] = _safe_std(strike)
    summary["big3"] = big3

    return _json_result(summary)


@tool(
    "get_club_stats",
    "Get per-club average statistics across all sessions. Optionally filter to one club.",
    {
        "type": "object",
        "properties": {
            "club": {"type": "string", "description": "Optional club filter (e.g. 'Driver')"},
        },
        "required": [],
    },
)
async def get_club_stats(args: dict[str, Any]) -> dict[str, Any]:
    """Group all shots by club and compute averages."""
    club_filter = args.get("club")

    df = golf_db.get_all_shots(read_mode="sqlite")
    if df.empty:
        return _text_result("No shot data available.")

    if club_filter:
        df = df[df["club"].str.lower() == club_filter.lower()]
        if df.empty:
            return _text_result(f"No shots found for club '{club_filter}'.")

    if "club" not in df.columns:
        return _text_result("No club data in shots.")

    stats: list[dict[str, Any]] = []
    for club_name, group in df.groupby("club"):
        entry: dict[str, Any] = {
            "club": club_name,
            "shot_count": len(group),
        }
        for col in ["carry", "total", "ball_speed", "club_speed", "smash"]:
            if col in group.columns:
                entry[f"avg_{col}"] = _safe_mean(group[col])
        if "face_angle" in group.columns:
            entry["avg_face_angle"] = _safe_mean(group["face_angle"])
        if "club_path" in group.columns:
            entry["avg_club_path"] = _safe_mean(group["club_path"])
        stats.append(entry)

    return _json_result(stats)


@tool(
    "get_trends",
    "Show how a metric trends over recent sessions. Default metric is 'carry'.",
    {
        "type": "object",
        "properties": {
            "metric": {
                "type": "string",
                "description": "Column to trend (carry, ball_speed, smash, face_angle, club_path, etc.)",
            },
            "sessions": {
                "type": "integer",
                "description": "Number of recent sessions to include (default 10)",
            },
        },
        "required": [],
    },
)
async def get_trends(args: dict[str, Any]) -> dict[str, Any]:
    """Return per-session averages of a metric for recent sessions."""
    metric = args.get("metric", "carry")
    num_sessions = args.get("sessions", 10)

    df = golf_db.get_all_shots(read_mode="sqlite")
    if df.empty:
        return _text_result("No shot data available.")

    if metric not in df.columns:
        return _text_result(f"Unknown metric '{metric}'. Available: {', '.join(df.columns.tolist())}")

    # Determine session order column
    date_col = "session_date" if "session_date" in df.columns else "date_added"

    grouped = (
        df.groupby("session_id")
        .agg(
            date=(date_col, "max"),
            value=(metric, "mean"),
            count=(metric, "count"),
        )
        .dropna(subset=["value"])
        .sort_values("date", ascending=False)
        .head(num_sessions)
        .sort_values("date")
    )

    if grouped.empty:
        return _text_result(f"No valid data for metric '{metric}'.")

    lines = [f"Trend: {metric} over last {len(grouped)} sessions\n"]
    lines.append("Session | Date | Avg | Shots")
    lines.append("-" * 50)
    for sid, row in grouped.iterrows():
        avg = round(row["value"], 1) if pd.notna(row["value"]) else "-"
        lines.append(f"{sid} | {row['date']} | {avg} | {int(row['count'])}")

    return _text_result("\n".join(lines))


# ---------------------------------------------------------------------------
# Write Tools (safe)
# ---------------------------------------------------------------------------

@tool(
    "tag_session",
    "Tag all shots in a session with a label (e.g. 'Warmup', 'Practice').",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Session ID to tag"},
            "tag": {"type": "string", "description": "Tag label to apply"},
        },
        "required": ["session_id", "tag"],
    },
)
async def tag_session(args: dict[str, Any]) -> dict[str, Any]:
    """Apply a tag to all shots in a session."""
    session_id = args["session_id"]
    tag = args["tag"]

    df = golf_db.get_session_data(session_id=session_id, read_mode="sqlite")
    if df.empty:
        return _text_result(f"No shots found for session {session_id}.")

    shot_ids = df["shot_id"].tolist()
    updated = golf_db.update_shot_metadata(shot_ids, "shot_tag", tag)
    return _text_result(f"Tagged {updated} shots in session {session_id} as '{tag}'.")


@tool(
    "update_session_type",
    "Set the session type for all shots in a session (e.g. 'Driver Focus', 'Mixed Practice').",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Session ID to update"},
            "session_type": {"type": "string", "description": "Session type label"},
        },
        "required": ["session_id", "session_type"],
    },
)
async def update_session_type_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Set session_type for all shots in a session."""
    session_id = args["session_id"]
    session_type = args["session_type"]

    df = golf_db.get_session_data(session_id=session_id, read_mode="sqlite")
    if df.empty:
        return _text_result(f"No shots found for session {session_id}.")

    shot_ids = df["shot_id"].tolist()
    updated = golf_db.update_shot_metadata(shot_ids, "session_type", session_type)
    return _text_result(
        f"Updated session type to '{session_type}' for {updated} shots in session {session_id}."
    )


@tool(
    "batch_rename_sessions",
    "Auto-generate display names for all imported sessions based on their shot data.",
    {
        "type": "object",
        "properties": {},
        "required": [],
    },
)
async def batch_rename_sessions(args: dict[str, Any]) -> dict[str, Any]:
    """Trigger batch rename of all session display names."""
    updated = golf_db.batch_update_session_names()
    return _text_result(f"Renamed {updated} sessions with auto-generated display names.")


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

ALL_TOOLS: list = [
    query_shots,
    get_session_list,
    get_session_summary,
    get_club_stats,
    get_trends,
    tag_session,
    update_session_type_tool,
    batch_rename_sessions,
]

TOOL_NAMES: list[str] = [f"mcp__golf__{t.name}" for t in ALL_TOOLS]
