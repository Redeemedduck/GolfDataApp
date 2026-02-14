"""
2D trajectory visualization — side-view of ball flight.

X-axis: horizontal distance (yards)
Y-axis: height (yards), estimated from apex, launch angle, and carry.
Multiple shots overlaid for consistency visualization.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import Optional


def _estimate_trajectory(carry, launch_angle, apex, descent_angle=None, n_points=50):
    """Estimate a 2D trajectory curve from known endpoints.

    Uses a parametric approach:
    - Parabolic arc from launch angle, apex height, and carry distance.

    Args:
        carry: Carry distance in yards.
        launch_angle: Launch angle in degrees.
        apex: Maximum height in feet (converted to yards internally).
        descent_angle: Optional descent angle in degrees.
        n_points: Number of points for the curve.

    Returns:
        Tuple of (x_array, y_array) in yards.
    """
    if carry is None or carry <= 0 or apex is None or apex <= 0:
        return None, None

    apex_yards = apex / 3.0  # Convert feet to yards for display

    # Simple parametric model: ball follows a skewed parabola
    # Peak occurs at roughly 60% of carry for typical golf shots
    peak_ratio = 0.6
    if launch_angle is not None and launch_angle > 0:
        # Higher launch = peak closer to midpoint
        peak_ratio = min(0.7, max(0.4, 0.5 + launch_angle / 100))

    t = np.linspace(0, 1, n_points)
    x = carry * t

    # Piecewise parabola: ascent to peak, descent from peak
    y = np.where(
        t <= peak_ratio,
        apex_yards * (1 - ((t - peak_ratio) / peak_ratio) ** 2),
        apex_yards * (1 - ((t - peak_ratio) / (1 - peak_ratio)) ** 2),
    )
    y = np.maximum(y, 0)

    return x, y


def render_trajectory_view(
    df: pd.DataFrame,
    max_shots: int = 10,
    title: str = "Ball Flight Trajectories",
) -> None:
    """Render 2D side-view trajectory overlay.

    Args:
        df: DataFrame with carry, launch_angle, apex columns.
        max_shots: Maximum number of shots to overlay.
        title: Chart title.
    """
    if df.empty:
        st.info("No data for trajectory visualization")
        return

    required = ['carry', 'launch_angle', 'apex']
    available = [c for c in required if c in df.columns]
    if len(available) < 3:
        st.info(f"Trajectory requires carry, launch_angle, and apex data")
        return

    plot_df = df.dropna(subset=required).copy()
    # Filter valid values
    plot_df = plot_df[(plot_df['carry'] > 0) & (plot_df['apex'] > 0)]

    if plot_df.empty:
        st.info("No valid trajectory data (need carry, launch angle, and apex)")
        return

    # Limit to max_shots (most recent)
    if len(plot_df) > max_shots:
        plot_df = plot_df.tail(max_shots)

    st.markdown(f"#### {title}")

    fig = go.Figure()

    # Color scale based on carry distance for visual distinction
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

    for i, (_, shot) in enumerate(plot_df.iterrows()):
        x, y = _estimate_trajectory(
            carry=shot['carry'],
            launch_angle=shot.get('launch_angle'),
            apex=shot['apex'],
            descent_angle=shot.get('descent_angle'),
        )
        if x is None:
            continue

        club = shot.get('club', f'Shot {i+1}')
        color = colors[i % len(colors)]

        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode='lines',
            name=f"{club}: {shot['carry']:.0f}yds",
            line=dict(color=color, width=2),
            hovertemplate=(
                f"<b>{club}</b><br>"
                "Distance: %{x:.0f} yds<br>"
                "Height: %{y:.0f} yds<br>"
                "<extra></extra>"
            ),
        ))

    # Ground line
    max_carry = plot_df['carry'].max() * 1.1
    fig.add_trace(go.Scatter(
        x=[0, max_carry], y=[0, 0],
        mode='lines',
        line=dict(color='rgba(100,200,100,0.3)', width=1),
        showlegend=False,
        hoverinfo='skip',
    ))

    fig.update_layout(
        xaxis_title="Distance (yards)",
        yaxis_title="Height (yards)",
        height=400,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis=dict(scaleanchor=None, rangemode="tozero"),
        xaxis=dict(rangemode="tozero"),
    )

    st.plotly_chart(fig, use_container_width=True)
