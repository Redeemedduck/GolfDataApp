"""
Dashboard Page — Session analytics with Big 3 Impact Laws deep dive.

Tabs:
  1. Overview — KPIs, Big 3 summary, carry box plot, dispersion plot
  2. Big 3 Deep Dive — D-plane, tendencies, enhanced heatmap
  3. Shots — Interactive shot table with detail pane
  4. Compare — Side-by-side session comparison (absorbed from Session Compare)
  5. Export — CSV downloads + presets
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import golf_db
from services.data_access import get_unique_sessions, get_session_data
from utils.session_state import get_read_mode
from utils.responsive import add_responsive_css
from components import (
    render_session_selector,
    render_metrics_row,
    render_impact_heatmap,
    render_radar_chart,
    render_summary_export,
    render_shared_sidebar,
    render_no_data_state,
    render_section_empty_state,
    render_comparison_empty_state,
)
from components.big3_summary import render_big3_summary
from components.face_path_diagram import render_face_path_diagram
from components.direction_tendency import (
    render_face_tendency,
    render_path_tendency,
    render_shot_shape_distribution,
)
from components.big3_detail_view import render_big3_detail_view
from components.session_comparison import (
    render_session_comparison,
    render_comparison_selector,
)

st.set_page_config(layout="wide", page_title="Dashboard - My Golf Lab", page_icon="📊")
add_responsive_css()

golf_db.init_db()
read_mode = get_read_mode()

# Shared sidebar
render_shared_sidebar(
    show_navigation=True,
    show_data_source=True,
    show_sync_status=True,
    current_page="dashboard",
)

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

st.divider()

# ─── Tabs ──────────────────────────────────────────────────────
tab_overview, tab_big3, tab_shots, tab_compare, tab_export = st.tabs([
    "Overview",
    "Big 3 Deep Dive",
    "Shots",
    "Compare",
    "Export",
])

# ================================================================
# TAB 1: OVERVIEW
# ================================================================
with tab_overview:
    st.header("Performance Metrics")
    render_metrics_row(df)

    st.divider()

    # Big 3 summary at-a-glance
    render_big3_summary(df, title="Big 3 — This Session")

    st.divider()

    # Charts
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Carry by Club")
        fig_carry = px.box(
            df,
            x="club",
            y="carry",
            color="club",
            labels={"carry": "Carry (yds)", "club": "Club"},
            title="Carry Distance Distribution",
        )
        fig_carry.update_layout(showlegend=False)
        st.plotly_chart(fig_carry, use_container_width=True)

    with c2:
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


# ================================================================
# TAB 4: COMPARE
# ================================================================
with tab_compare:
    st.header("Session Comparison")
    st.markdown("Compare your performance across 2–3 sessions side-by-side.")

    sessions = get_unique_sessions(read_mode=read_mode)

    compare_col1, compare_col2 = st.columns([1, 3])

    with compare_col1:
        st.subheader("Select Sessions")
        selected_sessions = render_comparison_selector(sessions, max_sessions=3)

        if len(selected_sessions) >= 2:
            st.success(f"Comparing {len(selected_sessions)} sessions")
        elif len(selected_sessions) == 1:
            st.info("Select 1 more session")
        else:
            st.info("Select 2–3 sessions")

        st.divider()

        st.subheader("Metrics")
        available_metrics = {
            "carry": "Carry Distance",
            "ball_speed": "Ball Speed",
            "smash": "Smash Factor",
            "launch_angle": "Launch Angle",
            "back_spin": "Back Spin",
            "club_speed": "Club Speed",
            "total": "Total Distance",
        }
        selected_metrics = st.multiselect(
            "Choose metrics",
            options=list(available_metrics.keys()),
            default=["carry", "ball_speed", "smash"],
            format_func=lambda x: available_metrics[x],
            key="comparison_metrics",
        )

    with compare_col2:
        if len(selected_sessions) < 2:
            render_comparison_empty_state()
        else:
            render_session_comparison(
                session_ids=selected_sessions,
                metrics=selected_metrics if selected_metrics else None,
                read_mode=read_mode,
            )

            st.divider()

            with st.expander("Detailed Statistics"):
                for session_id in selected_sessions:
                    st.subheader(f"Session: {session_id}")
                    sdf = get_session_data(session_id, read_mode=read_mode)
                    if not sdf.empty:
                        cols = st.columns(4)
                        with cols[0]:
                            st.metric("Total Shots", len(sdf))
                        with cols[1]:
                            if "club" in sdf.columns:
                                st.metric("Clubs Used", sdf["club"].nunique())
                        with cols[2]:
                            if "carry" in sdf.columns:
                                valid = sdf["carry"].dropna()
                                valid = valid[valid > 0]
                                if len(valid) > 0:
                                    st.metric("Best Carry", f"{valid.max():.1f} yds")
                        with cols[3]:
                            if "smash" in sdf.columns:
                                valid = sdf["smash"].dropna()
                                valid = valid[(valid > 0) & (valid < 2)]
                                if len(valid) > 0:
                                    st.metric("Best Smash", f"{valid.max():.2f}")
                        st.divider()


# ================================================================
# TAB 5: EXPORT
# ================================================================
with tab_export:
    st.header("Export & Reports")
    st.markdown("Download session data for offline analysis or coaching review.")

    render_summary_export(df, selected_session_id)

    st.divider()

    st.subheader("Export Presets")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("**Coach Review**")
        coach_cols = [
            "session_id", "date_added", "club", "carry", "total", "ball_speed",
            "club_speed", "smash", "launch_angle", "back_spin", "side_spin",
            "face_angle", "attack_angle", "shot_type",
        ]
        coach_cols = [c for c in coach_cols if c in df.columns]
        if coach_cols:
            from components.export_tools import export_to_csv
            coach_csv = export_to_csv(df[coach_cols], f"coach_review_{selected_session_id}")
            st.download_button(
                label="Download Coach Review CSV",
                data=coach_csv,
                file_name=f"coach_review_{selected_session_id}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with col2:
        st.caption("**Equipment Fitting**")
        fit_cols = [
            "session_id", "date_added", "club", "ball_speed", "club_speed",
            "launch_angle", "back_spin", "side_spin", "carry", "total",
            "smash", "club_path", "face_angle", "dynamic_loft", "attack_angle",
        ]
        fit_cols = [c for c in fit_cols if c in df.columns]
        if fit_cols:
            from components.export_tools import export_to_csv
            fit_csv = export_to_csv(df[fit_cols], f"equipment_fitting_{selected_session_id}")
            st.download_button(
                label="Download Equipment Fitting CSV",
                data=fit_csv,
                file_name=f"equipment_fitting_{selected_session_id}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.divider()

    st.subheader("Advanced Export Options")
    col1, col2 = st.columns(2)

    with col1:
        st.caption("**Export All Sessions**")
        all_shots = golf_db.get_session_data()
        if not all_shots.empty:
            from components.export_tools import export_to_csv
            csv_all = export_to_csv(all_shots, "all_sessions")
            st.download_button(
                label="Download All Data (CSV)",
                data=csv_all,
                file_name="all_golf_sessions.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.metric("Total Shots", len(all_shots))
        else:
            st.info("No data available")

    with col2:
        st.caption("**Export by Club**")
        if not all_shots.empty and "club" in all_shots.columns:
            export_club = st.selectbox(
                "Select Club",
                all_shots["club"].unique().tolist(),
                key="export_club_select",
            )
            club_data = all_shots[all_shots["club"] == export_club]
            from components.export_tools import export_to_csv
            csv_club = export_to_csv(club_data, f"club_{export_club}")
            st.download_button(
                label=f"Download {export_club} Data",
                data=csv_club,
                file_name=f"club_{export_club.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
            st.metric(f"{export_club} Shots", len(club_data))
        else:
            st.info("No club data available")

    st.divider()

    with st.expander("Preview Export Data"):
        st.dataframe(df.head(20), use_container_width=True)
        st.caption(f"Showing first 20 of {len(df)} shots in this session")
