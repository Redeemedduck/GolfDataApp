"""
D-Plane scatter plot — Face Angle vs Club Path.

The fundamental relationship in golf ball flight:
- X axis = Club Path (negative = out-to-in)
- Y axis = Face Angle (positive = open)
- Diagonal = face_to_path = 0 (straight shots)
- Quadrants labeled: Draw, Fade, Push-Draw, Pull-Fade
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Optional


def render_face_path_diagram(
    df: pd.DataFrame,
    color_by: str = "carry",
    title: str = "D-Plane: Face Angle vs Club Path",
) -> None:
    """Render the D-Plane scatter plot.

    Args:
        df: DataFrame with face_angle, club_path columns.
        color_by: Column to color points by ("carry", "shot_shape", or None).
        title: Chart title.
    """
    if df.empty:
        st.info("No data for D-Plane diagram")
        return

    required = ['face_angle', 'club_path']
    for col in required:
        if col not in df.columns:
            st.warning(f"Missing column: {col}")
            return

    # Filter valid data
    plot_df = df.dropna(subset=required).copy()
    if plot_df.empty:
        st.info("No valid face angle / club path data")
        return

    fig = go.Figure()

    # Color mapping
    if color_by == "carry" and 'carry' in plot_df.columns:
        color_data = plot_df['carry']
        colorbar_title = "Carry (yds)"
        colorscale = 'Viridis'
    elif color_by == "face_to_path" and 'face_to_path' in plot_df.columns:
        color_data = plot_df['face_to_path']
        colorbar_title = "Face-to-Path"
        colorscale = 'RdBu_r'
    else:
        color_data = '#1f77b4'
        colorbar_title = None
        colorscale = None

    # Main scatter
    fig.add_trace(go.Scatter(
        x=plot_df['club_path'],
        y=plot_df['face_angle'],
        mode='markers',
        marker=dict(
            size=10,
            color=color_data,
            colorscale=colorscale,
            showscale=colorbar_title is not None,
            colorbar=dict(title=colorbar_title) if colorbar_title else None,
            line=dict(width=0.5, color='white'),
            opacity=0.75,
        ),
        text=plot_df['club'] if 'club' in plot_df.columns else None,
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Path: %{x:+.1f}&deg;<br>"
            "Face: %{y:+.1f}&deg;<br>"
            "<extra></extra>"
        ),
        name="Shots",
    ))

    # Diagonal line: face = path (straight shots, face_to_path = 0)
    axis_range = max(
        abs(plot_df['club_path'].quantile(0.02)),
        abs(plot_df['club_path'].quantile(0.98)),
        abs(plot_df['face_angle'].quantile(0.02)),
        abs(plot_df['face_angle'].quantile(0.98)),
        5,
    ) * 1.2

    fig.add_trace(go.Scatter(
        x=[-axis_range, axis_range],
        y=[-axis_range, axis_range],
        mode='lines',
        line=dict(color='rgba(255,255,255,0.3)', dash='dash', width=1),
        showlegend=False,
        hoverinfo='skip',
    ))

    # Quadrant labels — bold primary shape, subtle full description
    offset = axis_range * 0.75
    annotations = [
        dict(x=offset, y=offset * 0.7, text="<b>Draw</b>",
             showarrow=False, font=dict(size=13, color='rgba(255,255,255,0.7)')),
        dict(x=offset, y=offset * 0.5, text="Push-Draw",
             showarrow=False, font=dict(size=10, color='rgba(255,255,255,0.4)')),
        dict(x=-offset, y=offset * 0.7, text="<b>Fade</b>",
             showarrow=False, font=dict(size=13, color='rgba(255,255,255,0.7)')),
        dict(x=-offset, y=offset * 0.5, text="Pull-Fade",
             showarrow=False, font=dict(size=10, color='rgba(255,255,255,0.4)')),
        dict(x=offset, y=-offset * 0.7, text="<b>Fade</b>",
             showarrow=False, font=dict(size=13, color='rgba(255,255,255,0.7)')),
        dict(x=offset, y=-offset * 0.5, text="Push-Fade",
             showarrow=False, font=dict(size=10, color='rgba(255,255,255,0.4)')),
        dict(x=-offset, y=-offset * 0.7, text="<b>Draw</b>",
             showarrow=False, font=dict(size=13, color='rgba(255,255,255,0.7)')),
        dict(x=-offset, y=-offset * 0.5, text="Pull-Draw",
             showarrow=False, font=dict(size=10, color='rgba(255,255,255,0.4)')),
    ]

    # Average point
    avg_path = plot_df['club_path'].mean()
    avg_face = plot_df['face_angle'].mean()
    fig.add_trace(go.Scatter(
        x=[avg_path],
        y=[avg_face],
        mode='markers',
        marker=dict(size=14, color='yellow', symbol='diamond',
                    line=dict(width=2, color='black')),
        name='Average',
        hovertemplate=f"Average<br>Path: {avg_path:+.1f}&deg;<br>Face: {avg_face:+.1f}&deg;<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Club Path (+ = In-to-Out)",
        yaxis_title="Face Angle (+ = Open)",
        xaxis=dict(
            range=[-axis_range, axis_range],
            zeroline=True, zerolinewidth=2, zerolinecolor='rgba(255,255,255,0.2)',
        ),
        yaxis=dict(
            range=[-axis_range, axis_range],
            zeroline=True, zerolinewidth=2, zerolinecolor='rgba(255,255,255,0.2)',
            scaleanchor="x", scaleratio=1,
        ),
        annotations=annotations,
        height=500,
        showlegend=True,
        template="plotly_dark",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Quick stats below — compute from raw columns to avoid NaN when derived col not backfilled
    ftp = plot_df['face_angle'] - plot_df['club_path']
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Face-to-Path", f"{ftp.mean():+.1f}")
    col2.metric("Avg Path", f"{avg_path:+.1f}")
    col3.metric("Avg Face", f"{avg_face:+.1f}")
