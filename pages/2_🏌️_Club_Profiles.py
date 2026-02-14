"""
Club Profiles Page — per-club performance story over time.

Select a club to see its hero stats, distance trends, Big 3 tendencies,
and comparison radar chart.
"""
import streamlit as st
import golf_db
from services.data_access import (
    get_session_data,
    get_club_profile,
)
from utils.session_state import get_read_mode
from components import (
    render_shared_sidebar,
    render_radar_chart,
)
from components.club_hero import render_club_hero
from components.club_trends import render_club_trends
from components.big3_summary import render_big3_summary
from utils.responsive import add_responsive_css
from utils.bag_config import get_club_sort_key, get_adjacent_clubs
from components.date_range_filter import render_date_range_filter, filter_by_date_range
from components.goal_tracker import render_goal_tracker

st.set_page_config(layout="wide", page_title="Club Profiles", page_icon="🏌️")
add_responsive_css()

golf_db.init_db()
read_mode = get_read_mode()
all_shots = get_session_data(read_mode=read_mode)

st.title("Club Profiles")
st.caption("Deep dive into each club's performance story")

# Date range filter
start_date, end_date = render_date_range_filter(key_prefix="club_date")
if start_date or end_date:
    all_shots = filter_by_date_range(all_shots, start_date, end_date)

if all_shots.empty or 'club' not in all_shots.columns:
    st.info("No shot data available. Import some data first!")
    st.stop()

# Sidebar
render_shared_sidebar(current_page="club_profiles")

# Club selector in main area (ordered by bag config)
clubs = sorted(all_shots['club'].dropna().unique().tolist(), key=get_club_sort_key)
selected_club = st.selectbox("Select Club", clubs, key="club_profile_selector")

if not selected_club:
    st.info("Select a club to view its profile")
    st.stop()

# Filter data for selected club
club_shots = all_shots[all_shots['club'] == selected_club].copy()

# ─── Hero Card ────────────────────────────────────────────────
render_club_hero(selected_club, club_shots)

# ─── Smash Factor Goal ────────────────────────────────────────
render_goal_tracker(club_shots, selected_club)

st.divider()

# ─── Distance & Big 3 Trends ─────────────────────────────────
profile_df = get_club_profile(selected_club)
render_club_trends(profile_df, selected_club)

st.divider()

# ─── Big 3 Summary for this club ─────────────────────────────
render_big3_summary(club_shots, title=f"Big 3 — {selected_club}")

st.divider()

# ─── Session Comparison ─────────────────────────────────────
with st.expander("Compare Sessions for This Club"):
    # Get unique sessions that used this club
    if 'session_id' in club_shots.columns:
        club_sessions = sorted(club_shots['session_id'].unique().tolist())
        if len(club_sessions) >= 2:
            comp_c1, comp_c2 = st.columns(2)
            with comp_c1:
                session_a = st.selectbox("Session A", club_sessions, index=0, key="compare_session_a")
            with comp_c2:
                session_b = st.selectbox("Session B", club_sessions, index=min(1, len(club_sessions)-1), key="compare_session_b")

            if session_a != session_b:
                shots_a = club_shots[club_shots['session_id'] == session_a]
                shots_b = club_shots[club_shots['session_id'] == session_b]

                m1, m2 = st.columns(2)
                with m1:
                    st.markdown(f"**Session {session_a}** ({len(shots_a)} shots)")
                    if 'carry' in shots_a.columns:
                        st.metric("Avg Carry", f"{shots_a['carry'].mean():.1f} yds")
                    if 'smash_factor' in shots_a.columns:
                        st.metric("Avg Smash", f"{shots_a['smash_factor'].mean():.2f}")
                with m2:
                    st.markdown(f"**Session {session_b}** ({len(shots_b)} shots)")
                    if 'carry' in shots_b.columns:
                        st.metric("Avg Carry", f"{shots_b['carry'].mean():.1f} yds")
                    if 'smash_factor' in shots_b.columns:
                        st.metric("Avg Smash", f"{shots_b['smash_factor'].mean():.2f}")
            else:
                st.info("Select two different sessions to compare.")
        else:
            st.info(f"Only {len(club_sessions)} session(s) with {selected_club}. Need at least 2 to compare.")
    else:
        st.info("No session data available for comparison.")

st.divider()

# ─── Club Comparison Radar ────────────────────────────────────
st.markdown("#### Compare with Other Clubs")
other_clubs = [c for c in clubs if c != selected_club]
suggested = [c for c in get_adjacent_clubs(selected_club) if c in other_clubs]
default_compare = suggested[:2] if suggested else other_clubs[:2]
compare_clubs = st.multiselect(
    "Compare with:",
    other_clubs,
    default=default_compare,
    max_selections=3,
    key="radar_compare_clubs",
)
render_radar_chart(all_shots, clubs=[selected_club] + compare_clubs)
