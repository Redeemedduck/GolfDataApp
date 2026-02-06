"""
My Golf Practice Journal - Home

A journal-style home page built around Adam Young's Big 3 Impact Laws.
Rolling view of recent practice sessions with Big 3 summaries.
"""
import streamlit as st
from datetime import datetime

import golf_db
import observability
from services.data_access import (
    get_unique_sessions,
    get_session_data,
    get_recent_sessions_with_stats,
    get_rolling_averages,
    clear_all_caches,
)
from utils.session_state import get_read_mode
from components import (
    render_shared_sidebar,
    render_documentation_links,
    render_no_data_state,
)
from components.journal_view import render_journal_view
from components.calendar_strip import render_calendar_strip
from utils.responsive import add_responsive_css

st.set_page_config(
    layout="wide",
    page_title="My Golf Lab",
    page_icon="⛳",
    initial_sidebar_state="expanded"
)

add_responsive_css()

# Initialize DB and ensure session stats are fresh
golf_db.init_db()

# Get data
read_mode = get_read_mode()
all_shots = get_session_data(read_mode=read_mode)
all_sessions = get_unique_sessions(read_mode=read_mode)

# Recompute session stats on load (fast — only touches changed sessions)
golf_db.compute_session_stats()

# Fetch journal data
recent_stats = get_recent_sessions_with_stats(weeks=4)
rolling_avg = get_rolling_averages()

# ─── Header ───────────────────────────────────────────────────
st.title("Practice Journal")

# Quick stats hero
total_sessions = len(all_sessions) if all_sessions else 0
total_shots = len(all_shots) if not all_shots.empty else 0

# Calculate days since last practice and streak
practice_dates = set()
if recent_stats:
    for s in recent_stats:
        d = s.get('session_date')
        if d and isinstance(d, str):
            practice_dates.add(d[:10])

days_since = None
streak = 0
if practice_dates:
    today = datetime.now().date()
    sorted_dates = sorted(practice_dates, reverse=True)
    try:
        last_date = datetime.strptime(sorted_dates[0], '%Y-%m-%d').date()
        days_since = (today - last_date).days
    except (ValueError, IndexError):
        pass

    # Calculate streak
    from datetime import timedelta
    check = today
    while check.strftime('%Y-%m-%d') in practice_dates:
        streak += 1
        check -= timedelta(days=1)

# Hero stats — 2x2 grid (works on both desktop and mobile)
r1c1, r1c2 = st.columns(2)
r2c1, r2c2 = st.columns(2)
with r1c1:
    st.metric("Sessions", total_sessions)
with r1c2:
    st.metric("Total Shots", total_shots)
with r2c1:
    if days_since is not None:
        label = "Today!" if days_since == 0 else f"{days_since} day{'s' if days_since != 1 else ''} ago"
        st.metric("Last Practice", label)
    else:
        st.metric("Last Practice", "—")
with r2c2:
    st.metric("Streak", f"{streak} day{'s' if streak != 1 else ''}" if streak > 0 else "Start one!")

# ─── Calendar Strip ───────────────────────────────────────────
render_calendar_strip(practice_dates, weeks=4)

st.divider()

# ─── Journal View ─────────────────────────────────────────────
if total_sessions > 0 and recent_stats:
    render_journal_view(
        sessions=recent_stats,
        rolling_avg=rolling_avg,
        weeks=4,
    )
else:
    render_no_data_state()

# ─── Sidebar ──────────────────────────────────────────────────
render_shared_sidebar(
    show_navigation=False,
    show_data_source=True,
    show_sync_status=True,
    current_page="home"
)

with st.sidebar:
    st.divider()
    render_documentation_links()

    st.divider()

    st.header("Health")
    latest_import = observability.read_latest_event("import_runs.jsonl")
    if latest_import:
        st.caption(f"Last Import: {latest_import.get('status', 'unknown')}")
        st.caption(f"Shots: {latest_import.get('shots_imported', 0)}")
        st.caption(f"Duration: {latest_import.get('duration_sec', 0)}s")
    else:
        st.caption("Last Import: none")

    latest_sync = observability.read_latest_event("sync_runs.jsonl")
    if latest_sync:
        st.caption(f"Last Sync: {latest_sync.get('status', 'unknown')} ({latest_sync.get('mode', 'n/a')})")
        st.caption(f"Shots: {latest_sync.get('shots', 0)}")
        st.caption(f"Duration: {latest_sync.get('duration_sec', 0)}s")
    else:
        st.caption("Last Sync: none")

    st.divider()
    st.caption("Golf Data Lab v3.0 - Practice Journal")
    st.caption("Built around the Big 3 Impact Laws")
