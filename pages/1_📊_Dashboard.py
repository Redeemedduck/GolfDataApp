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

import golf_db
from services.data_access import get_unique_sessions, get_session_data
from utils.session_state import get_read_mode
from utils.responsive import add_responsive_css
from components import (
    render_session_selector,
    render_metrics_row,
    render_radar_chart,
    render_shared_sidebar,
    render_no_data_state,
)
from components.big3_detail_view import render_big3_detail_view
from components.date_range_filter import render_date_range_filter, filter_by_date_range

st.set_page_config(layout="wide", page_title="Dashboard - My Golf Lab", page_icon="📊")
add_responsive_css()

golf_db.init_db()
read_mode = get_read_mode()

# Shared sidebar
render_shared_sidebar(current_page="dashboard")

# Session selector in sidebar
with st.sidebar:
    st.divider()
    selected_session_id, df, selected_clubs = render_session_selector(
        lambda: get_unique_sessions(read_mode=read_mode),
        lambda session_id: get_session_data(session_id, read_mode=read_mode),
    )

if df.empty:
    render_no_data_state()
    st.stop()

# ─── Header ────────────────────────────────────────────────────
st.title("Dashboard")
st.caption(f"Session: {selected_session_id}")

# Date range filter
start_date, end_date = render_date_range_filter(key_prefix="dash_date")
if start_date or end_date:
    df = filter_by_date_range(df, start_date, end_date)
    if df.empty:
        st.info("No shots in selected date range.")
        st.stop()

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
