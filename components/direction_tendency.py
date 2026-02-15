"""
Direction tendency components — histograms and distribution charts.

- render_face_tendency(): histogram of face angles
- render_path_tendency(): histogram of club paths
- render_shot_shape_distribution(): donut chart of shot shapes
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Optional
from utils.chart_theme import themed_figure, COLOR_NEUTRAL, COLOR_GOOD, COLOR_FAIR, COLOR_POOR, CATEGORICAL


def render_face_tendency(df: pd.DataFrame) -> None:
    """Render histogram of face angle distribution."""
    if 'face_angle' not in df.columns:
        st.info("No face angle data")
        return

    data = df['face_angle'].dropna()
    if data.empty:
        return

    fig = themed_figure()
    fig.add_trace(go.Histogram(
        x=data,
        nbinsx=30,
        marker_color=COLOR_NEUTRAL,
        opacity=0.8,
        name='Face Angle',
    ))

    # Add mean line
    mean_val = data.mean()
    fig.add_vline(x=mean_val, line_dash="dash", line_color="yellow",
                  annotation_text=f"Avg: {mean_val:+.1f}")
    fig.add_vline(x=0, line_dash="solid", line_color="rgba(255,255,255,0.3)")

    fig.update_layout(
        title="Face Angle Distribution",
        xaxis_title="Face Angle (degrees)",
        yaxis_title="Count",
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_path_tendency(df: pd.DataFrame) -> None:
    """Render histogram of club path distribution."""
    if 'club_path' not in df.columns:
        st.info("No club path data")
        return

    data = df['club_path'].dropna()
    if data.empty:
        return

    fig = themed_figure()
    fig.add_trace(go.Histogram(
        x=data,
        nbinsx=30,
        marker_color=COLOR_FAIR,
        opacity=0.8,
        name='Club Path',
    ))

    mean_val = data.mean()
    fig.add_vline(x=mean_val, line_dash="dash", line_color=COLOR_FAIR,
                  annotation_text=f"Avg: {mean_val:+.1f}")
    fig.add_vline(x=0, line_dash="solid", line_color="rgba(255,255,255,0.3)")

    fig.update_layout(
        title="Club Path Distribution",
        xaxis_title="Club Path (degrees)",
        yaxis_title="Count",
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_shot_shape_distribution(df: pd.DataFrame) -> None:
    """Render donut chart of shot shape classification.

    Uses face_to_path to classify shots:
    - Straight: |ftp| < 2
    - Draw/Fade: 2 <= |ftp| < 5
    - Hook/Slice: |ftp| >= 5
    """
    ftp_col = 'face_to_path'
    if ftp_col not in df.columns:
        if 'face_angle' in df.columns and 'club_path' in df.columns:
            ftp = df['face_angle'] - df['club_path']
        else:
            st.info("No face-to-path data for shot shape analysis")
            return
    else:
        ftp = df[ftp_col]

    ftp = ftp.dropna()
    if ftp.empty:
        return

    # Classify
    def classify(val):
        if abs(val) < 2:
            return "Straight"
        if val > 0:
            return "Draw" if val < 5 else "Hook"
        return "Fade" if val > -5 else "Slice"

    shapes = ftp.apply(classify)
    counts = shapes.value_counts()

    # Order and colors
    order = ["Straight", "Draw", "Fade", "Hook", "Slice"]
    colors = {"Straight": "#2ca02c", "Draw": "#1f77b4", "Fade": "#ff7f0e",
              "Hook": "#d62728", "Slice": "#9467bd"}

    labels = [s for s in order if s in counts.index]
    values = [counts[s] for s in labels]
    clrs = [colors[s] for s in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.45,
        marker_colors=clrs,
        textposition='inside',
        textinfo='label+percent',
    )])

    fig.update_layout(
        title="Shot Shape Distribution",
        height=350,
        showlegend=True,
    )

    st.plotly_chart(fig, use_container_width=True)
