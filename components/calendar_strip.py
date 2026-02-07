"""
Calendar strip component — horizontal date strip with dots on practice days.

Rendered as HTML/CSS via st.markdown for a lightweight, fast visual.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Set

from utils.date_helpers import parse_session_date


def _normalize_practice_dates(practice_dates):
    """Normalize incoming dates to canonical YYYY-MM-DD strings."""
    normalized = set()
    for value in practice_dates or set():
        parsed = parse_session_date(value)
        if parsed is not None:
            normalized.add(parsed.isoformat())
    return normalized


def render_calendar_strip(practice_dates: Set[str], weeks: int = 4) -> None:
    """Render a horizontal calendar strip showing practice frequency.

    Args:
        practice_dates: Set of date strings (YYYY-MM-DD) when user practiced.
        weeks: Number of weeks to display (default 4).
    """
    normalized_practice_dates = _normalize_practice_dates(practice_dates)
    today = datetime.now().date()
    total_days = weeks * 7
    start_date = today - timedelta(days=total_days - 1)

    # Build day cells
    cells = []
    for i in range(total_days):
        day = start_date + timedelta(days=i)
        date_str = day.strftime('%Y-%m-%d')
        is_practice = date_str in normalized_practice_dates
        is_today = day == today

        # Color coding
        if is_today:
            bg = "#1f77b4"
            border = "2px solid #1f77b4"
        elif is_practice:
            bg = "#2ca02c"
            border = "1px solid #2ca02c"
        else:
            bg = "#333" if day.weekday() < 5 else "#2a2a2a"
            border = "1px solid #444"

        tooltip = f"{day.strftime('%b %d')}"
        if is_practice:
            tooltip += " (practiced)"

        cells.append(
            f'<div title="{tooltip}" style="'
            f'width:min(18px, 3%);height:18px;border-radius:3px;'
            f'background:{bg};border:{border};'
            f'flex:0 0 auto;margin:1px;'
            f'"></div>'
        )

    # Week labels
    week_labels = []
    for w in range(weeks):
        week_start = start_date + timedelta(weeks=w)
        label = week_start.strftime('%b %d')
        week_labels.append(
            f'<span style="flex:1 1 auto;min-width:80px;'
            f'font-size:0.7em;color:#888;text-align:left">{label}</span>'
        )

    # Streak calculation
    streak = 0
    check_date = today
    while check_date.strftime('%Y-%m-%d') in normalized_practice_dates:
        streak += 1
        check_date -= timedelta(days=1)

    practice_count = len([d for d in normalized_practice_dates
                          if start_date.strftime('%Y-%m-%d') <= d <= today.strftime('%Y-%m-%d')])

    html = f"""
    <div style="margin:0.5em 0 1em 0">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
            <span style="font-size:0.85em;color:#aaa">Last {weeks} weeks</span>
            <span style="font-size:0.85em;color:#aaa">
                {practice_count} sessions | {'Streak: ' + str(streak) + ' day' + ('s' if streak != 1 else '') if streak > 0 else 'No streak'}
            </span>
        </div>
        <div style="display:flex;flex-wrap:wrap;max-width:100%">{''.join(week_labels)}</div>
        <div style="display:flex;flex-wrap:wrap;gap:1px;max-width:100%">{''.join(cells)}</div>
        <div style="margin-top:6px;font-size:0.7em;color:#666">
            <span style="display:inline-block;width:10px;height:10px;background:#2ca02c;border-radius:2px;margin-right:3px"></span> Practiced
            <span style="display:inline-block;width:10px;height:10px;background:#1f77b4;border-radius:2px;margin-left:10px;margin-right:3px"></span> Today
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)
