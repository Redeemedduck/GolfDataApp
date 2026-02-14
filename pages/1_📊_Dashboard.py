"""
Dashboard Page — Session analytics with Big 3 Impact Laws deep dive.

Tabs:
  1. Overview — KPIs, dispersion plot, radar chart, quick CSV export
  2. Big 3 Deep Dive — D-plane, tendencies, enhanced heatmap
  3. Shots — Interactive shot table with detail pane
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

import golf_db
from services.data_access import get_unique_sessions, get_session_data
from utils.session_state import get_read_mode
from utils.responsive import add_responsive_css
from utils.date_helpers import format_session_date
from components import (
    render_metrics_row,
    render_radar_chart,
    render_shared_sidebar,
    render_no_data_state,
)
from components.big3_detail_view import render_big3_detail_view
from components.shot_trends import render_shot_trends
from components.trajectory_view import render_trajectory_view
from components.shot_navigator import render_shot_navigator

st.set_page_config(layout="wide", page_title="Dashboard - My Golf Lab", page_icon="📊")
add_responsive_css()

golf_db.init_db()
read_mode = get_read_mode()

# Sidebar — navigation only, no technical controls
render_shared_sidebar(
    show_navigation=True,
    show_data_source=False,
    show_sync_status=False,
    current_page="dashboard",
)

# ─── Header ────────────────────────────────────────────────────
st.title("Dashboard")

# ─── Date Range Filter ─────────────────────────────────────────
filter_col1, filter_col2, _ = st.columns([1, 1, 2])
with filter_col1:
    range_options = ["All Time", "This Week", "Last 2 Weeks", "Last Month", "Last 3 Months", "Custom"]
    date_range = st.selectbox("Date Range", range_options, index=0, key="dash_date_range")
with filter_col2:
    custom_start = None
    custom_end = None
    if date_range == "Custom":
        custom_start = st.date_input("Start", value=datetime.now().date() - timedelta(days=30), key="dash_start")
        custom_end = st.date_input("End", value=datetime.now().date(), key="dash_end")

# Compute date bounds
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

# ─── Session Selector (main content area) ─────────────────────
unique_sessions = get_unique_sessions(read_mode=read_mode)

if not unique_sessions:
    render_no_data_state()
    st.stop()


def _session_label(s):
    """Build human-readable session label: 'Iron Work — Feb 10 (25 shots)'."""
    stype = s.get('session_type') or 'Practice'
    raw_date = s.get('session_date') or s.get('date_added') or ''
    date_str = format_session_date(raw_date) if raw_date else 'Unknown'
    shot_count = s.get('shot_count', '')
    shot_str = f" ({shot_count} shots)" if shot_count else ""
    return f"{stype} — {date_str}{shot_str}"


def _group_sessions_by_week(sessions):
    """Group sessions by week for dropdown optgroup-style display."""
    week_start = today - timedelta(days=today.weekday())
    groups = {}
    for s in sessions:
        raw = s.get('session_date') or s.get('date_added') or ''
        try:
            d = datetime.strptime(str(raw)[:10], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            d = None

        if d is None:
            label = "Unknown Date"
        elif d >= week_start:
            label = "This Week"
        elif d >= week_start - timedelta(days=7):
            label = "Last Week"
        elif d >= week_start - timedelta(days=14):
            label = "2 Weeks Ago"
        else:
            label = "Older"

        groups.setdefault(label, []).append(s)
    return groups


# Apply date filter to sessions
filtered_sessions = unique_sessions
if date_start:
    filtered_sessions = []
    for s in unique_sessions:
        raw = s.get('session_date') or s.get('date_added') or ''
        try:
            d = datetime.strptime(str(raw)[:10], '%Y-%m-%d').date()
            if d >= date_start and (custom_end is None or d <= custom_end):
                filtered_sessions.append(s)
        except (ValueError, TypeError):
            filtered_sessions.append(s)  # Keep sessions with unknown dates

if not filtered_sessions:
    st.info("No sessions in the selected date range.")
    st.stop()

# Build label -> session_id mapping
label_to_id = {}
session_labels = []
for s in filtered_sessions:
    lbl = _session_label(s)
    sid = s['session_id']
    # Deduplicate labels
    if lbl in label_to_id:
        lbl = f"{lbl} [{sid}]"
    label_to_id[lbl] = sid
    session_labels.append(lbl)

selected_label = st.selectbox("Select Session", session_labels, key="dash_session_selector")
selected_session_id = label_to_id.get(selected_label)
df = get_session_data(selected_session_id, read_mode=read_mode)

if df.empty:
    render_no_data_state()
    st.stop()

# Club filter
all_clubs = sorted(df['club'].dropna().unique().tolist()) if 'club' in df.columns else []
if all_clubs:
    with st.expander("Filter by Club"):
        selected_clubs = st.multiselect("Clubs", all_clubs, default=all_clubs, key="dash_club_filter")
        if selected_clubs:
            df = df[df['club'].isin(selected_clubs)]

st.caption(f"Session: {selected_session_id}")

# ─── Session Notes ─────────────────────────────────────────────
existing_notes = ""
if 'notes' in df.columns:
    notes_vals = df['notes'].dropna().unique()
    if len(notes_vals) > 0:
        existing_notes = str(notes_vals[0])

with st.expander("Session Notes", expanded=bool(existing_notes)):
    new_notes = st.text_area(
        "Notes for this session",
        value=existing_notes,
        placeholder="How did this session feel? What were you working on?",
        key="session_notes_input",
        label_visibility="collapsed",
    )
    if new_notes != existing_notes:
        if st.button("Save Notes", key="save_notes_btn"):
            shot_ids = df['shot_id'].tolist() if 'shot_id' in df.columns else []
            if shot_ids:
                golf_db.update_shot_metadata(shot_ids, 'notes', new_notes)
                st.success("Notes saved!")
                st.rerun()

st.divider()

# ─── Tabs ──────────────────────────────────────────────────────
tab_overview, tab_big3, tab_shots = st.tabs([
    "Overview",
    "Big 3 Deep Dive",
    "Shots",
])

# ================================================================
# TAB 1: OVERVIEW
# ================================================================
with tab_overview:
    st.header("Performance Metrics")
    render_metrics_row(df)

    st.divider()

    # Dispersion plot
    st.subheader("Dispersion Plot")
    fig_disp = go.Figure()

    for dist in [50, 100, 150, 200, 250]:
        fig_disp.add_shape(
            type="circle",
            xref="x", yref="y",
            x0=-dist, y0=0, x1=dist, y1=dist * 2,
            line_color="lightgray",
            line_dash="dot",
        )

    fig_disp.add_trace(go.Scatter(
        x=df["side_distance"],
        y=df["carry"],
        mode="markers",
        marker=dict(
            size=10,
            color=df["smash"],
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title="Smash"),
        ),
        text=df["club"],
        hovertemplate="<b>%{text}</b><br>Carry: %{y:.1f} yds<br>Side: %{x:.1f} yds<extra></extra>",
    ))

    fig_disp.update_layout(
        xaxis_title="Side Distance (yds)",
        yaxis_title="Carry Distance (yds)",
        xaxis=dict(range=[-50, 50], zeroline=True, zerolinewidth=2, zerolinecolor="green"),
        yaxis=dict(range=[0, df["carry"].max() * 1.1 if len(df) > 0 else 250]),
        height=500,
    )
    st.plotly_chart(fig_disp, use_container_width=True)

    st.divider()

    # Trajectory view
    render_trajectory_view(df)

    st.divider()

    # Radar comparison
    render_radar_chart(df)

    st.divider()

    # Quick export
    if not df.empty:
        csv = df.to_csv(index=False)
        st.download_button("Export Session CSV", csv, f"session_{selected_session_id}.csv", "text/csv")


# ================================================================
# TAB 2: BIG 3 DEEP DIVE
# ================================================================
with tab_big3:
    render_big3_detail_view(df)

    st.divider()
    render_shot_trends(df)


# ================================================================
# TAB 3: SHOTS
# ================================================================
with tab_shots:
    st.header("Detailed Shot Analysis")

    col_table, col_media = st.columns([1, 1])

    with col_table:
        st.write("Click a row to view details")
        display_cols = [
            "club", "carry", "total", "ball_speed", "club_speed",
            "smash", "back_spin", "side_spin", "face_angle", "attack_angle",
        ]
        valid_cols = [c for c in display_cols if c in df.columns]

        event = st.dataframe(
            df[valid_cols].round(1),
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True,
        )

    with col_media:
        if len(event.selection.rows) > 0:
            shot = df.iloc[event.selection.rows[0]]

            st.subheader(f"{shot['club']} — {shot['carry']:.1f} yds")

            m1, m2, m3 = st.columns(3)
            m1.metric("Ball Speed", f"{shot['ball_speed']:.1f} mph")
            m2.metric("Club Speed", f"{shot['club_speed']:.1f} mph")
            m3.metric("Smash", f"{shot['smash']:.2f}")

            m4, m5, m6 = st.columns(3)
            m4.metric(
                "Launch",
                f"{shot['launch_angle']:.1f}°" if pd.notna(shot.get("launch_angle")) else "N/A",
            )
            m5.metric(
                "Face Angle",
                f"{shot['face_angle']:.1f}°" if pd.notna(shot.get("face_angle")) else "N/A",
            )
            m6.metric(
                "Attack Angle",
                f"{shot['attack_angle']:.1f}°" if pd.notna(shot.get("attack_angle")) else "N/A",
            )

            st.divider()

            if shot.get("impact_img") or shot.get("swing_img"):
                img1, img2 = st.columns(2)
                if shot.get("impact_img"):
                    img1.image(shot["impact_img"], caption="Impact", use_container_width=True)
                else:
                    img1.info("No Impact Image")
                if shot.get("swing_img"):
                    img2.image(shot["swing_img"], caption="Swing View", use_container_width=True)
                else:
                    img2.info("No Swing Image")
            else:
                st.info("No images available for this shot.")
        else:
            st.info("Select a shot from the table to view details")

    st.divider()
    render_shot_navigator(df)
