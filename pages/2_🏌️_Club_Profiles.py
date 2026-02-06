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

st.set_page_config(layout="wide", page_title="Club Profiles", page_icon="🏌️")
add_responsive_css()

golf_db.init_db()
read_mode = get_read_mode()
all_shots = get_session_data(read_mode=read_mode)

st.title("Club Profiles")
st.caption("Deep dive into each club's performance story")

if all_shots.empty or 'club' not in all_shots.columns:
    st.info("No shot data available. Import some data first!")
    st.stop()

# Sidebar club selector
clubs = sorted(all_shots['club'].dropna().unique().tolist())

with st.sidebar:
    selected_club = st.selectbox("Select Club", clubs, key="club_profile_selector")

    st.divider()
    render_shared_sidebar(
        show_navigation=True,
        show_data_source=True,
        current_page="club_profiles",
    )

if not selected_club:
    st.info("Select a club from the sidebar")
    st.stop()

# Filter data for selected club
club_shots = all_shots[all_shots['club'] == selected_club].copy()

# ─── Hero Card ────────────────────────────────────────────────
render_club_hero(selected_club, club_shots)

st.divider()

# ─── Distance & Big 3 Trends ─────────────────────────────────
profile_df = get_club_profile(selected_club)
render_club_trends(profile_df, selected_club)

st.divider()

# ─── Big 3 Summary for this club ─────────────────────────────
render_big3_summary(club_shots, title=f"Big 3 — {selected_club}")

st.divider()

# ─── Club Comparison Radar ────────────────────────────────────
st.markdown("#### Compare with Other Clubs")
render_radar_chart(all_shots, clubs=[selected_club] + [c for c in clubs if c != selected_club][:4])
