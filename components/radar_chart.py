"""
Radar chart component for multi-metric club comparison.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def render_radar_chart(df: pd.DataFrame, clubs: list = None) -> None:
    """
    Render a radar chart comparing multiple metrics across clubs.

    Args:
        df: DataFrame containing shot data
        clubs: List of clubs to compare (defaults to all clubs)
    """
    st.subheader("Multi-Metric Club Comparison")

    if df.empty:
        st.info("No data available for radar chart")
        return

    # Define metrics to compare (must be numeric and comparable)
    metrics = {
        'carry': 'Carry Distance',
        'ball_speed': 'Ball Speed',
        'smash': 'Smash Factor',
        'back_spin': 'Back Spin',
        'launch_angle': 'Launch Angle'
    }

    # Filter to only available metrics
    available_metrics = {k: v for k, v in metrics.items() if k in df.columns}

    if not available_metrics:
        st.warning("No comparable metrics available")
        return

    # Get clubs to compare
    if clubs is None:
        clubs = df['club'].unique().tolist()

    if len(clubs) == 0:
        st.info("No clubs selected for comparison")
        return

    # User selection
    selected_clubs = st.multiselect(
        "Select Clubs to Compare (max 5)",
        clubs,
        default=clubs[:min(3, len(clubs))],
        max_selections=5,
        key="radar_clubs_select"
    )

    if len(selected_clubs) == 0:
        st.info("Please select at least one club")
        return

    # Calculate averages for each club
    fig = go.Figure()

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    for idx, club in enumerate(selected_clubs):
        club_data = df[df['club'] == club]

        if club_data.empty:
            continue

        # Calculate normalized values (0-100 scale for better visualization)
        values = []
        labels = []

        for metric_key, metric_label in available_metrics.items():
            avg_value = club_data[metric_key].mean()

            # Normalize to 0-100 scale based on global min/max
            global_min = df[metric_key].min()
            global_max = df[metric_key].max()

            if global_max > global_min:
                normalized = ((avg_value - global_min) / (global_max - global_min)) * 100
            else:
                normalized = 50  # Default if no variance

            values.append(normalized)
            labels.append(metric_label)

        # Close the radar chart (repeat first value)
        values.append(values[0])
        labels_with_close = labels + [labels[0]]

        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=labels_with_close,
            fill='toself',
            name=club,
            line=dict(color=colors[idx % len(colors)], width=2),
            fillcolor=f'rgba{tuple(list(int(colors[idx % len(colors)].lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + [0.1])}'
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=True,
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    # Detailed comparison table
    st.subheader("Detailed Comparison")

    comparison_data = []
    for club in selected_clubs:
        club_data = df[df['club'] == club]
        if club_data.empty:
            continue

        row = {'Club': club}
        for metric_key, metric_label in available_metrics.items():
            row[metric_label] = f"{club_data[metric_key].mean():.2f}"

        row['Shots'] = len(club_data)
        comparison_data.append(row)

    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)

    st.caption("📊 Values are normalized to 0-100 scale for visualization. See table below for actual values.")
