"""
Journal view component — rolling timeline of practice sessions.

Groups sessions by week ("This Week", "Last Week", etc.)
and renders journal cards for each.
"""
import streamlit as st
from datetime import date, datetime, timedelta
from typing import List, Optional

from components.journal_card import render_journal_card


def _parse_session_date(value) -> Optional[date]:
    """Parse session_date from ISO datetime/date strings with fallbacks."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return datetime.fromisoformat(raw.split("T", 1)[0]).date()
            except (ValueError, TypeError):
                return None


def _group_by_week(sessions: List[dict]) -> dict:
    """Group sessions into week buckets relative to today."""
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())  # Monday

    groups = {
        "This Week": [],
        "Last Week": [],
        "2 Weeks Ago": [],
        "3 Weeks Ago": [],
        "Older": [],
    }

    for session in sessions:
        session_date = _parse_session_date(session.get('session_date'))
        if session_date is None:
            groups["Older"].append(session)
            continue

        delta = (week_start - session_date).days

        if delta < 0:
            groups["This Week"].append(session)
        elif delta < 7:
            groups["This Week"].append(session) if delta == 0 else groups["Last Week"].append(session)
        elif delta < 14:
            groups["2 Weeks Ago"].append(session)
        elif delta < 21:
            groups["3 Weeks Ago"].append(session)
        else:
            groups["Older"].append(session)

    return groups


def render_journal_view(
    sessions: List[dict],
    rolling_avg: Optional[dict] = None,
    weeks: int = 4,
) -> None:
    """Render the full journal view with sessions grouped by week.

    Args:
        sessions: List of dicts from get_recent_sessions_with_stats().
        rolling_avg: Optional rolling average baseline for trend arrows.
        weeks: Number of weeks to show (for display, data should already be filtered).
    """
    if not sessions:
        st.info("No practice sessions found. Import some data to get started!")
        return

    groups = _group_by_week(sessions)

    total_rendered = 0
    for label, group_sessions in groups.items():
        if label == "Older" and weeks <= 4:
            continue  # Skip older unless explicitly requested

        if not group_sessions:
            continue

        st.markdown(f"### {label}")
        st.caption(f"{len(group_sessions)} session{'s' if len(group_sessions) != 1 else ''}")

        for i, stats in enumerate(group_sessions):
            render_journal_card(
                stats,
                rolling_avg=rolling_avg,
                expanded=(total_rendered == 0),  # Auto-expand most recent
            )
            total_rendered += 1

    if total_rendered == 0:
        st.info("No sessions in the selected time window.")
