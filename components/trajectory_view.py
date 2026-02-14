"""Trajectory visualization component for side-view ball flight arcs."""

from __future__ import annotations

import math
from typing import List, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def compute_trajectory_points(
    carry, apex, launch_angle, descent_angle, num_points: int = 50
) -> List[Tuple[float, float]]:
    """
    Compute a 2D side-view trajectory using piecewise quadratic curves.

    Args:
        carry: Carry distance in yards.
        apex: Apex height in yards.
        launch_angle: Launch angle in degrees.
        descent_angle: Descent angle in degrees (reserved for future tuning).
        num_points: Number of points in the generated trajectory.

    Returns:
        List of (x, y) tuples from launch point to landing point.
    """
    if carry is None or apex is None:
        return []

    try:
        carry_value = float(carry)
        apex_value = float(apex)
        launch_value = float(launch_angle) if launch_angle is not None else 0.0
    except (TypeError, ValueError):
        return []

    if carry_value <= 0 or apex_value <= 0:
        return []

    if num_points < 2:
        num_points = 2

    # Descent is intentionally unused in this baseline model but kept in the API.
    _ = descent_angle

    launch_rad = math.radians(launch_value)
    peak_x = carry_value * (
        0.4 + 0.2 * (1 - min(launch_rad / math.radians(20), 1))
    )

    # Guard against degenerate values so the piecewise equations remain stable.
    peak_x = min(max(peak_x, 1e-6), carry_value - 1e-6)

    points: List[Tuple[float, float]] = []
    for i in range(num_points):
        x = carry_value * i / (num_points - 1)

        if x <= peak_x:
            t = x / peak_x
            y = apex_value * (2 * t - (t**2))
        else:
            t = (x - peak_x) / (carry_value - peak_x)
            y = apex_value * (1 - (t**2))

        points.append((x, max(y, 0.0)))

    return points


def render_trajectory_view(
    df: pd.DataFrame, max_shots: int = 5, title: str = "Trajectory View"
) -> None:
    """Render a Plotly side-view chart of up to `max_shots` trajectories."""
    required_columns = {"carry", "apex", "launch_angle"}

    if df is None or df.empty:
        st.info("No shot data available for trajectory view.")
        return

    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        st.info(
            "Trajectory view unavailable: missing "
            + ", ".join(sorted(missing_columns))
            + "."
        )
        return

    max_shots = max(1, int(max_shots))
    shots_to_plot = df.head(max_shots)

    colors = [
        "#00CC96",
        "#19D3F3",
        "#AB63FA",
        "#FFA15A",
        "#EF553B",
    ]

    fig = go.Figure()
    plotted_count = 0
    max_carry = 0.0
    max_apex = 0.0

    for idx, (_, shot) in enumerate(shots_to_plot.iterrows()):
        points = compute_trajectory_points(
            carry=shot.get("carry"),
            apex=shot.get("apex"),
            launch_angle=shot.get("launch_angle"),
            descent_angle=shot.get("descent_angle"),
        )
        if not points:
            continue

        x_vals = [point[0] for point in points]
        y_vals = [point[1] for point in points]
        shot_name = shot.get("club", f"Shot {idx + 1}")

        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="lines",
                name=str(shot_name),
                line=dict(color=colors[idx % len(colors)], width=3),
                hovertemplate=(
                    "X: %{x:.1f} yds<br>"
                    "Y: %{y:.1f} yds<extra>"
                    + str(shot_name)
                    + "</extra>"
                ),
            )
        )

        plotted_count += 1
        max_carry = max(max_carry, max(x_vals))
        max_apex = max(max_apex, max(y_vals))

    if plotted_count == 0:
        st.info("No valid trajectory data available.")
        return

    fig.add_shape(
        type="line",
        x0=0,
        y0=0,
        x1=max_carry * 1.05,
        y1=0,
        line=dict(color="white", width=2),
    )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        xaxis_title="Distance (yds)",
        yaxis_title="Height (yds)",
        xaxis=dict(range=[0, max_carry * 1.05]),
        yaxis=dict(range=[0, max_apex * 1.2]),
        height=420,
        hovermode="closest",
    )

    st.plotly_chart(fig, use_container_width=True)
