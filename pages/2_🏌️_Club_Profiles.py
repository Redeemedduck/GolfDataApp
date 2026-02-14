"""
Club Profiles Page — per-club performance story over time.

Select a club to see its hero stats, distance trends, Big 3 tendencies,
and comparison radar chart. Only shows clubs from my_bag.json.
"""
import streamlit as st
from datetime import datetime, timedelta
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
from utils.bag_config import get_bag_order, is_in_bag, get_adjacent_clubs, get_smash_target
from utils.goal_tracker import get_goals, add_goal, remove_goal, compute_progress

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

# Sidebar — navigation only
render_shared_sidebar(
    show_navigation=True,
    show_data_source=False,
    current_page="club_profiles",
)

# ─── Date Range Filter ─────────────────────────────────────────
filter_col1, filter_col2, _ = st.columns([1, 1, 2])
with filter_col1:
    range_options = ["All Time", "This Week", "Last 2 Weeks", "Last Month", "Last 3 Months", "Custom"]
    date_range = st.selectbox("Date Range", range_options, index=0, key="cp_date_range")
with filter_col2:
    custom_start = None
    custom_end = None
    if date_range == "Custom":
        custom_start = st.date_input("Start", value=datetime.now().date() - timedelta(days=30), key="cp_start")
        custom_end = st.date_input("End", value=datetime.now().date(), key="cp_end")

# Compute date bounds and filter
today = datetime.now().date()
date_start = None
if date_range == "This Week":
    date_start = today - timedelta(days=today.weekday())
elif date_range == "Last 2 Weeks":
    date_start = today - timedelta(days=14)
elif date_range == "Last Month":
    date_start = today - timedelta(days=30)
elif date_range == "Last 3 Months":
    date_start = today - timedelta(days=90)
elif date_range == "Custom" and custom_start:
    date_start = custom_start

filtered_shots = all_shots
if date_start and 'session_date' in all_shots.columns:
    try:
        dates = all_shots['session_date'].astype(str).str[:10]
        mask = dates >= date_start.strftime('%Y-%m-%d')
        if custom_end:
            mask = mask & (dates <= custom_end.strftime('%Y-%m-%d'))
        filtered_shots = all_shots[mask | all_shots['session_date'].isna()]
    except Exception:
        filtered_shots = all_shots

# Club selector: only clubs from my_bag.json, in bag order
bag_order = get_bag_order()
# Only show bag clubs that actually have data
clubs_with_data = set(filtered_shots['club'].dropna().unique())
available_clubs = [c for c in bag_order if c in clubs_with_data]

if not available_clubs:
    st.info("No shot data for clubs in your bag. Check your data or bag configuration.")
    st.stop()

selected_club = st.selectbox("Select Club", available_clubs, key="club_profile_selector")

if not selected_club:
    st.info("Select a club to view its profile")
    st.stop()

# Filter data for selected club
club_shots = filtered_shots[filtered_shots['club'] == selected_club].copy()

# ─── Hero Card ────────────────────────────────────────────────
render_club_hero(selected_club, club_shots)

# Show smash factor target if available
smash_target = get_smash_target(selected_club)
if smash_target and 'smash' in club_shots.columns:
    valid_smash = club_shots['smash'].dropna()
    valid_smash = valid_smash[(valid_smash > 0) & (valid_smash < 2)]
    if len(valid_smash) > 0:
        avg_smash = valid_smash.mean()
        target_low, target_high = smash_target
        target_mid = (target_low + target_high) / 2
        if avg_smash >= target_low:
            st.success(f"Smash Factor {avg_smash:.2f} — on target ({target_low:.2f}-{target_high:.2f})")
        else:
            gap = target_mid - avg_smash
            st.info(f"Smash Factor {avg_smash:.2f} — target: {target_low:.2f}-{target_high:.2f} (gap: {gap:+.2f})")

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
                    if 'smash' in shots_a.columns:
                        st.metric("Avg Smash", f"{shots_a['smash'].mean():.2f}")
                with m2:
                    st.markdown(f"**Session {session_b}** ({len(shots_b)} shots)")
                    if 'carry' in shots_b.columns:
                        st.metric("Avg Carry", f"{shots_b['carry'].mean():.1f} yds")
                    if 'smash' in shots_b.columns:
                        st.metric("Avg Smash", f"{shots_b['smash'].mean():.2f}")
            else:
                st.info("Select two different sessions to compare.")
        else:
            st.info(f"Only {len(club_sessions)} session(s) with {selected_club}. Need at least 2 to compare.")
    else:
        st.info("No session data available for comparison.")

st.divider()

# ─── Club Comparison Radar (smart defaults) ──────────────────
st.markdown("#### Compare with Other Clubs")

# Smart comparison: suggest adjacent clubs in the bag
adjacent = get_adjacent_clubs(selected_club)
other_clubs = [c for c in available_clubs if c != selected_club]

# Default to adjacent clubs that have data, falling back to first 2 others
default_compare = [c for c in adjacent if c in other_clubs]
if not default_compare and other_clubs:
    default_compare = other_clubs[:2]

compare_clubs = st.multiselect(
    "Compare with:",
    other_clubs,
    default=default_compare[:3],
    max_selections=3,
    key="radar_compare_clubs",
)
render_radar_chart(filtered_shots, clubs=[selected_club] + compare_clubs)

st.divider()

# ─── Goal Tracking ────────────────────────────────────────────
st.markdown("#### Goals")

club_goals = get_goals(club=selected_club)

# Show existing goals with progress
if club_goals:
    for goal in club_goals:
        metric = goal['metric']
        target = goal['target']

        # Compute current value
        current_value = None
        if metric in club_shots.columns:
            valid = club_shots[metric].dropna()
            if metric == 'carry':
                valid = valid[valid > 0]
            elif metric == 'smash':
                valid = valid[(valid > 0) & (valid < 2)]
            if len(valid) > 0:
                current_value = valid.mean()

        progress = compute_progress(goal, current_value)

        g_col1, g_col2, g_col3 = st.columns([3, 1, 1])
        with g_col1:
            desc = goal.get('description') or f"{selected_club} {metric}"
            pct = progress['progress_pct']
            st.progress(min(pct / 100.0, 1.0), text=f"{desc}: {current_value:.1f} / {target:.1f}" if current_value else desc)
        with g_col2:
            gap = progress.get('gap')
            if gap is not None:
                st.metric("Gap", f"{gap:+.1f}")
        with g_col3:
            if st.button("X", key=f"rm_goal_{goal['id']}"):
                remove_goal(goal['id'])
                st.rerun()
else:
    st.caption("No goals set for this club.")

# Add new goal
with st.expander("Add Goal"):
    goal_metric = st.selectbox("Metric", ["carry", "smash", "ball_speed"], key="goal_metric")
    goal_target = st.number_input("Target Value", min_value=0.0, step=1.0, key="goal_target")
    goal_desc = st.text_input("Description (optional)", key="goal_desc",
                               placeholder=f"e.g., Get {selected_club} carry to {goal_target}")
    if st.button("Add Goal", key="add_goal_btn"):
        if goal_target > 0:
            add_goal(selected_club, goal_metric, goal_target, goal_desc)
            st.success(f"Goal added: {goal_metric} -> {goal_target}")
            st.rerun()
        else:
            st.error("Target must be greater than 0")
