"""
Club trends component — distance + Big 3 trend charts per club over time.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from typing import Optional


def render_club_trends(profile_df: pd.DataFrame, club_name: str) -> None:
    """Render distance and Big 3 trends for a club over time.

    Args:
        profile_df: DataFrame from get_club_profile() with per-session aggregates.
        club_name: Name of the club being profiled.
    """
    if profile_df.empty:
        st.info(f"Not enough data to show trends for {club_name}")
        return

    # Prepare x-axis (session dates or index)
    if 'session_date' in profile_df.columns and profile_df['session_date'].notna().any():
        x = pd.to_datetime(profile_df['session_date'], errors='coerce')
        x_title = "Date"
    else:
        x = list(range(len(profile_df)))
        x_title = "Session #"

    # ─── Distance Trend ───
    st.markdown("#### Distance Over Time")

    fig = go.Figure()

    if 'avg_carry' in profile_df.columns:
        fig.add_trace(go.Scatter(
            x=x, y=profile_df['avg_carry'],
            mode='lines+markers',
            name='Avg Carry',
            line=dict(color='#1f77b4', width=2),
        ))

    if 'best_carry' in profile_df.columns:
        fig.add_trace(go.Scatter(
            x=x, y=profile_df['best_carry'],
            mode='lines+markers',
            name='Best Carry',
            line=dict(color='#2ca02c', width=1, dash='dot'),
        ))

    x_layout = {}
    if isinstance(x, pd.Series) and pd.api.types.is_datetime64_any_dtype(x):
        x_layout = dict(tickformat='%b %d', dtick='D7')

    fig.update_layout(
        xaxis_title=x_title,
        xaxis=x_layout,
        yaxis_title="Yards",
        height=350,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ─── Big 3 Trends ───
    st.markdown("#### Big 3 Trends")

    col1, col2 = st.columns(2)

    with col1:
        fig_face = go.Figure()
        if 'avg_face_angle' in profile_df.columns:
            fig_face.add_trace(go.Scatter(
                x=x, y=profile_df['avg_face_angle'],
                mode='lines+markers',
                name='Face Angle',
                line=dict(color='#ff7f0e'),
            ))
            fig_face.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
            fig_face.update_layout(
                title="Face Angle",
                yaxis_title="Degrees",
                height=280,
                template="plotly_dark",
            )
            st.plotly_chart(fig_face, use_container_width=True)

    with col2:
        fig_path = go.Figure()
        if 'avg_club_path' in profile_df.columns:
            fig_path.add_trace(go.Scatter(
                x=x, y=profile_df['avg_club_path'],
                mode='lines+markers',
                name='Club Path',
                line=dict(color='#d62728'),
            ))
            fig_path.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
            fig_path.update_layout(
                title="Club Path",
                yaxis_title="Degrees",
                height=280,
                template="plotly_dark",
            )
            st.plotly_chart(fig_path, use_container_width=True)

    # Strike distance trend
    if 'avg_strike_distance' in profile_df.columns and profile_df['avg_strike_distance'].notna().any():
        fig_strike = go.Figure()
        fig_strike.add_trace(go.Scatter(
            x=x, y=profile_df['avg_strike_distance'],
            mode='lines+markers',
            name='Strike Distance',
            line=dict(color='#9467bd'),
        ))
        fig_strike.add_hline(y=0.25, line_dash="dot", line_color="green",
                             annotation_text="Target (<0.25\")")
        fig_strike.update_layout(
            title="Strike Quality (distance from center)",
            yaxis_title="Inches",
            height=280,
            template="plotly_dark",
        )
        st.plotly_chart(fig_strike, use_container_width=True)
