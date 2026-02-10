"""
Dashboard Page - Performance analytics and visualizations
Phase 3: Enhanced with advanced visualizations (heatmaps, trends, radar charts, export)
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import golf_db
from components import (
    render_session_selector,
    render_metrics_row,
    render_impact_heatmap,
    render_trend_chart,
    render_radar_chart,
    render_summary_export,
    render_dispersion_chart,
    render_distance_table,
    render_miss_tendency,
    render_progress_tracker,
    render_session_quality
)
from components.sync_status import render_sync_status

st.set_page_config(layout="wide", page_title="Dashboard - My Golf Lab")

# Initialize DB
golf_db.init_db()

# Cached data access
@st.cache_data(show_spinner=False)
def get_unique_sessions_cached(read_mode="auto"):
    return golf_db.get_unique_sessions(read_mode=read_mode)

@st.cache_data(show_spinner=False)
def get_session_data_cached(session_id=None, read_mode="auto"):
    return golf_db.get_session_data(session_id, read_mode=read_mode)

# Sidebar: Session selector
with st.sidebar:
    st.header("🔗 Navigation")
    st.page_link("pages/1_📥_Data_Import.py", label="📥 Import Data", icon="📥")
    st.page_link("pages/3_🗄️_Database_Manager.py", label="🗄️ Manage Data", icon="🗄️")

    st.divider()
    render_sync_status()
    st.divider()
    st.header("🧭 Data Source")
    if "read_mode" not in st.session_state:
        st.session_state.read_mode = "auto"
    read_mode_options = {
        "Auto (SQLite first)": "auto",
        "SQLite": "sqlite",
        "Supabase": "supabase"
    }
    selected_label = st.selectbox(
        "Read Mode",
        list(read_mode_options.keys()),
        index=list(read_mode_options.values()).index(st.session_state.read_mode),
        help="Auto uses SQLite when available and falls back to Supabase if empty."
    )
    selected_mode = read_mode_options[selected_label]
    if selected_mode != st.session_state.read_mode:
        st.session_state.read_mode = selected_mode
        golf_db.set_read_mode(selected_mode)
        st.cache_data.clear()

    st.info(f"📌 Data Source: {golf_db.get_read_source()}")
    sync_status = golf_db.get_sync_status()
    counts = sync_status["counts"]
    st.caption(f"SQLite shots: {counts['sqlite']}")
    if golf_db.supabase:
        st.caption(f"Supabase shots: {counts['supabase']}")
        if sync_status["drift_exceeds"]:
            st.warning(f"⚠️ SQLite/Supabase drift: {sync_status['drift']} shots")

    read_mode = st.session_state.get("read_mode", "auto")
    selected_session_id, df, selected_clubs = render_session_selector(
        lambda: get_unique_sessions_cached(read_mode=read_mode),
        lambda session_id: get_session_data_cached(session_id, read_mode=read_mode)
    )

# Stop if no data
if df.empty:
    st.info("No data to display. Please import a session first.")
    st.page_link("pages/1_📥_Data_Import.py", label="Go to Data Import", icon="📥")
    st.stop()

# Main content
st.title("⛳ My Golf Data Lab - Advanced Analytics")
st.subheader(f"Session: {selected_session_id}")

st.markdown("""
**Phase 3 Enhanced**: Professional-grade visualizations including impact heatmaps, performance trends,
multi-metric radar charts, and comprehensive export options.
""")

st.divider()

# Create tabs for different views
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Performance Overview",
    "🎯 Impact Analysis",
    "📊 Trends Over Time",
    "🏌️ Shot Analytics",
    "🔍 Shot Viewer",
    "💾 Export Data"
])

# ============================================================================
# TAB 1: PERFORMANCE OVERVIEW
# ============================================================================
with tab1:
    st.header("Performance Metrics")

    # KPI Row
    render_metrics_row(df)

    st.divider()

    # Charts Row
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Carry by Club")
        fig_carry = px.box(
            df,
            x='club',
            y='carry',
            color='club',
            labels={'carry': 'Carry (yds)', 'club': 'Club'},
            title="Carry Distance Distribution"
        )
        fig_carry.update_layout(showlegend=False)
        st.plotly_chart(fig_carry, use_container_width=True)

    with c2:
        st.subheader("Dispersion Plot (Top-Down View)")

        # Create a "driving range" style dispersion plot
        fig_dispersion = go.Figure()

        # Add distance circles/arcs
        for dist in [50, 100, 150, 200, 250]:
            fig_dispersion.add_shape(
                type="circle",
                xref="x", yref="y",
                x0=-dist, y0=0, x1=dist, y1=dist*2,
                line_color="lightgray",
                line_dash="dot"
            )

        # Add shot dots
        fig_dispersion.add_trace(go.Scatter(
            x=df['side_distance'],
            y=df['carry'],
            mode='markers',
            marker=dict(
                size=10,
                color=df['smash'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Smash")
            ),
            text=df['club'],
            hovertemplate="<b>%{text}</b><br>Carry: %{y:.1f} yds<br>Side: %{x:.1f} yds<extra></extra>"
        ))

        fig_dispersion.update_layout(
            xaxis_title="Side Distance (yds)",
            yaxis_title="Carry Distance (yds)",
            xaxis=dict(
                range=[-50, 50],
                zeroline=True,
                zerolinewidth=2,
                zerolinecolor='green'
            ),
            yaxis=dict(range=[0, df['carry'].max() * 1.1 if len(df) > 0 else 250]),
            height=500
        )
        st.plotly_chart(fig_dispersion, use_container_width=True)

    st.divider()

    # Radar Chart for Multi-Metric Comparison
    render_radar_chart(df)


# ============================================================================
# TAB 2: IMPACT ANALYSIS (NEW)
# ============================================================================
with tab2:
    st.header("Impact Location Analysis")

    st.markdown("""
    Analyze where you're striking the ball on the club face. Consistent center-face contact
    produces optimal ball speed and distance. The green circle represents the ideal sweet spot.
    """)

    # Impact Heatmap
    render_impact_heatmap(df, use_optix=True)

    st.divider()

    # Impact Statistics by Club
    st.subheader("Impact Consistency by Club")

    impact_stats = []
    for club in df['club'].unique():
        club_data = df[df['club'] == club]

        # Check which impact data is available
        if 'optix_x' in club_data.columns and 'optix_y' in club_data.columns:
            x_col, y_col = 'optix_x', 'optix_y'
        elif 'impact_x' in club_data.columns and 'impact_y' in club_data.columns:
            x_col, y_col = 'impact_x', 'impact_y'
        else:
            continue

        # Filter valid data
        valid_data = club_data[(club_data[x_col] != 0) & (club_data[y_col] != 0)].dropna(subset=[x_col, y_col])

        if len(valid_data) > 0:
            impact_stats.append({
                'Club': club,
                'Shots': len(valid_data),
                'Avg Horizontal': f"{valid_data[x_col].mean():.3f}",
                'Avg Vertical': f"{valid_data[y_col].mean():.3f}",
                'H Std Dev': f"{valid_data[x_col].std():.3f}",
                'V Std Dev': f"{valid_data[y_col].std():.3f}"
            })

    if impact_stats:
        impact_df = pd.DataFrame(impact_stats)
        st.dataframe(impact_df, use_container_width=True, hide_index=True)
    else:
        st.info("No impact location data available for analysis")


# ============================================================================
# TAB 3: TRENDS OVER TIME (NEW)
# ============================================================================
with tab3:
    st.header("Performance Trends Across Sessions")

    st.markdown("""
    Track your improvement over time. Compare your performance across multiple practice sessions
    to identify trends and measure progress toward your goals.
    """)

    # Get all sessions
    all_sessions = get_unique_sessions_cached(read_mode=read_mode)

    if len(all_sessions) < 2:
        st.info("You need at least 2 sessions to view trends. Import more data to see progress over time.")
    else:
        # Metric selector
        metric_options = {
            'carry': 'Carry Distance',
            'total': 'Total Distance',
            'ball_speed': 'Ball Speed',
            'smash': 'Smash Factor',
            'back_spin': 'Back Spin',
            'launch_angle': 'Launch Angle'
        }

        selected_metric = st.selectbox(
            "Select Metric to Track",
            options=list(metric_options.keys()),
            format_func=lambda x: metric_options[x],
            key="trend_metric"
        )

        # Prepare session data for trend analysis
        session_trends = []
        for session in all_sessions:
            session_data = get_session_data_cached(session['session_id'], read_mode=read_mode)

            if not session_data.empty and selected_metric in session_data.columns:
                avg_value = session_data[selected_metric].mean()

                session_trends.append({
                    'session_id': session['session_id'],
                    'date_added': session['date_added'],
                    selected_metric: avg_value
                })

        # Render trend chart
        if session_trends:
            render_trend_chart(session_trends, metric=selected_metric)
        else:
            st.warning(f"No {metric_options[selected_metric]} data available across sessions")

        st.divider()

        # Per-Club Trends
        st.subheader("Club-Specific Trends")

        # Get all unique clubs across all sessions
        all_shots = get_session_data_cached(read_mode=read_mode)
        if 'club' in all_shots.columns:
            all_clubs = all_shots['club'].unique().tolist()

            selected_club = st.selectbox(
                "Select Club for Detailed Trend",
                all_clubs,
                key="club_trend"
            )

            # Get trends for selected club only
            club_trends = []
            for session in all_sessions:
                session_data = get_session_data_cached(session['session_id'], read_mode=read_mode)
                club_data = session_data[session_data['club'] == selected_club]

                if not club_data.empty and selected_metric in club_data.columns:
                    avg_value = club_data[selected_metric].mean()

                    club_trends.append({
                        'session_id': session['session_id'],
                        'date_added': session['date_added'],
                        selected_metric: avg_value
                    })

            if club_trends:
                render_trend_chart(club_trends, metric=selected_metric)
            else:
                st.info(f"No {selected_club} data available across sessions")

        st.divider()
        st.subheader("Statistical Progress Analysis")
        all_shots_for_progress = get_session_data_cached(read_mode=read_mode)
        if not all_shots_for_progress.empty:
            progress_metric = st.selectbox(
                "Track Metric",
                ['carry', 'total', 'ball_speed', 'smash'],
                format_func=lambda x: {'carry': 'Carry Distance', 'total': 'Total Distance', 'ball_speed': 'Ball Speed', 'smash': 'Smash Factor'}[x],
                key="progress_metric"
            )
            render_progress_tracker(all_shots_for_progress, metric=progress_metric)


# ============================================================================
# TAB 4: SHOT ANALYTICS (NEW)
# ============================================================================
with tab4:
    st.header("Shot Analytics")

    # Club selector dropdown
    clubs_in_data = sorted(df['club'].unique().tolist())
    club_options = ["All Clubs"] + clubs_in_data
    selected_analytics_club = st.selectbox(
        "Filter by Club",
        club_options,
        key="analytics_club_filter"
    )
    analytics_club = None if selected_analytics_club == "All Clubs" else selected_analytics_club

    # Dispersion Chart and Distance Table
    col_disp, col_dist = st.columns(2)
    with col_disp:
        render_dispersion_chart(df, selected_club=analytics_club)
    with col_dist:
        render_distance_table(df)

    # Miss Tendency
    st.divider()
    render_miss_tendency(df, selected_club=analytics_club)

    # Session Quality
    st.divider()
    session_metrics = golf_db.get_session_metrics(selected_session_id)
    if session_metrics:
        render_session_quality(session_metrics)
    else:
        st.info("Session quality score not available. Session metrics may not be computed yet.")


# ============================================================================
# TAB 5: SHOT VIEWER (EXISTING)
# ============================================================================
with tab5:
    st.header("Detailed Shot Analysis")

    # Grid View
    col_table, col_media = st.columns([1, 1])

    with col_table:
        st.write("Click a row to view details")
        display_cols = [
            'club', 'carry', 'total', 'ball_speed', 'club_speed',
            'smash', 'back_spin', 'side_spin', 'face_angle', 'attack_angle'
        ]
        valid_cols = [c for c in display_cols if c in df.columns]

        event = st.dataframe(
            df[valid_cols].round(1),
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True
        )

    with col_media:
        if len(event.selection.rows) > 0:
            selected_row_index = event.selection.rows[0]
            shot = df.iloc[selected_row_index]

            st.subheader(f"{shot['club']} - {shot['carry']:.1f} yds")

            # Display detailed shot metrics in columns
            m1, m2, m3 = st.columns(3)
            m1.metric("Ball Speed", f"{shot['ball_speed']:.1f} mph")
            m2.metric("Club Speed", f"{shot['club_speed']:.1f} mph")
            m3.metric("Smash", f"{shot['smash']:.2f}")

            m4, m5, m6 = st.columns(3)
            m4.metric(
                "Launch",
                f"{shot['launch_angle']:.1f}°" if pd.notna(shot.get('launch_angle')) else "N/A"
            )
            m5.metric(
                "Face Angle",
                f"{shot['face_angle']:.1f}°" if pd.notna(shot.get('face_angle')) and shot.get('face_angle') != 0 else "N/A"
            )
            m6.metric(
                "Attack Angle",
                f"{shot['attack_angle']:.1f}°" if pd.notna(shot.get('attack_angle')) and shot.get('attack_angle') != 0 else "N/A"
            )

            st.divider()

            # Images
            if shot.get('impact_img') or shot.get('swing_img'):
                img_col1, img_col2 = st.columns(2)

                if shot.get('impact_img'):
                    img_col1.image(shot['impact_img'], caption="Impact", use_column_width=True)
                else:
                    img_col1.info("No Impact Image")

                if shot.get('swing_img'):
                    img_col2.image(shot['swing_img'], caption="Swing View", use_column_width=True)
                else:
                    img_col2.info("No Swing Image")
            else:
                st.info("No images available for this shot.")
        else:
            st.info("👈 Select a shot from the table to view details")


# ============================================================================
# TAB 6: EXPORT DATA (NEW)
# ============================================================================
with tab6:
    st.header("Export & Reports")

    st.markdown("""
    Download your session data in various formats for offline analysis, coaching review,
    or record keeping.
    """)

    render_summary_export(df, selected_session_id)

    st.divider()

    # Advanced Export Options
    st.subheader("📦 Export Presets")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("**Coach Review**")
        coach_cols = [
            'session_id', 'date_added', 'club', 'carry', 'total', 'ball_speed',
            'club_speed', 'smash', 'launch_angle', 'back_spin', 'side_spin',
            'face_angle', 'attack_angle', 'shot_type'
        ]
        coach_cols = [c for c in coach_cols if c in df.columns]
        if coach_cols:
            from components.export_tools import export_to_csv
            coach_csv = export_to_csv(df[coach_cols], f"coach_review_{selected_session_id}")
            st.download_button(
                label="📥 Download Coach Review CSV",
                data=coach_csv,
                file_name=f"coach_review_{selected_session_id}.csv",
                mime='text/csv',
                use_container_width=True
            )
        else:
            st.info("No coach review fields available.")

    with col2:
        st.caption("**Equipment Fitting**")
        fit_cols = [
            'session_id', 'date_added', 'club', 'ball_speed', 'club_speed',
            'launch_angle', 'back_spin', 'side_spin', 'carry', 'total',
            'smash', 'club_path', 'face_angle', 'dynamic_loft', 'attack_angle'
        ]
        fit_cols = [c for c in fit_cols if c in df.columns]
        if fit_cols:
            from components.export_tools import export_to_csv
            fit_csv = export_to_csv(df[fit_cols], f"equipment_fitting_{selected_session_id}")
            st.download_button(
                label="📥 Download Equipment Fitting CSV",
                data=fit_csv,
                file_name=f"equipment_fitting_{selected_session_id}.csv",
                mime='text/csv',
                use_container_width=True
            )
        else:
            st.info("No fitting fields available.")

    st.divider()

    st.subheader("📊 Advanced Export Options")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("**Export All Sessions**")
        st.markdown("Download your complete golf data history across all sessions.")

        all_shots = golf_db.get_session_data()

        if not all_shots.empty:
            from components.export_tools import export_to_csv
            csv_all = export_to_csv(all_shots, "all_sessions")

            st.download_button(
                label="📥 Download All Data (CSV)",
                data=csv_all,
                file_name="all_golf_sessions.csv",
                mime='text/csv',
                use_container_width=True
            )

            st.metric("Total Shots", len(all_shots))
        else:
            st.info("No data available")

    with col2:
        st.caption("**Export by Club**")
        st.markdown("Download data for a specific club across all sessions.")

        if 'club' in all_shots.columns:
            export_club = st.selectbox(
                "Select Club",
                all_shots['club'].unique().tolist(),
                key="export_club_select"
            )

            club_data = all_shots[all_shots['club'] == export_club]

            from components.export_tools import export_to_csv
            csv_club = export_to_csv(club_data, f"club_{export_club}")

            st.download_button(
                label=f"📥 Download {export_club} Data",
                data=csv_club,
                file_name=f"club_{export_club.replace(' ', '_')}.csv",
                mime='text/csv',
                use_container_width=True
            )

            st.metric(f"{export_club} Shots", len(club_data))
        else:
            st.info("No club data available")

    st.divider()

    # Data Preview
    with st.expander("📋 Preview Export Data"):
        st.dataframe(df.head(20), use_container_width=True)
        st.caption(f"Showing first 20 of {len(df)} shots in this session")
