"""
Dashboard Page - Performance analytics and visualizations
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
from components import render_session_selector, render_metrics_row

st.set_page_config(layout="wide", page_title="Dashboard - My Golf Lab")

# Initialize DB
golf_db.init_db()

# Sidebar: Session selector
with st.sidebar:
    st.header("🔗 Navigation")
    st.page_link("pages/1_📥_Data_Import.py", label="📥 Import Data", icon="📥")
    st.page_link("pages/3_🗄️_Database_Manager.py", label="🗄️ Manage Data", icon="🗄️")

    st.divider()

    selected_session_id, df, selected_clubs = render_session_selector(golf_db)

# Stop if no data
if df.empty:
    st.info("No data to display. Please import a session first.")
    st.page_link("pages/1_📥_Data_Import.py", label="Go to Data Import", icon="📥")
    st.stop()

# Main content
st.title("⛳ My Golf Data Lab")
st.subheader(f"Session: {selected_session_id}")

# Create tabs for different views
tab1, tab2 = st.tabs(["📈 Performance Overview", "🔍 Shot Viewer"])

# TAB 1: PERFORMANCE OVERVIEW
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

# TAB 2: SHOT VIEWER
with tab2:
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
