"""
Metrics card components for displaying KPIs.

Enhanced in Wave 2 with:
- Hero KPI cards with trends and sparklines
- Benchmark comparison
- Color-coded status indicators
- Tooltips for metric explanations
"""
import streamlit as st
import pandas as pd
from typing import Optional, List


def render_metrics_row(df: pd.DataFrame, show_trends: bool = False) -> None:
    """
    Render a row of key performance metrics.

    This is the backward-compatible wrapper that uses the enhanced KPI cards.

    Args:
        df: DataFrame containing shot data with columns: carry, smash
        show_trends: Whether to show trend indicators (requires session history)
    """
    col1, col2, col3 = st.columns(3)

    # Total Shots
    with col1:
        render_kpi_card(
            label="Total Shots",
            value=len(df),
            unit="",
            tooltip="Number of shots in this session"
        )

    # Average Carry
    with col2:
        avg_carry = df['carry'].mean() if len(df) > 0 and 'carry' in df.columns else 0
        render_kpi_card(
            label="Avg Carry",
            value=avg_carry,
            unit="yds",
            tooltip="Average carry distance (air distance before landing)"
        )

    # Average Smash Factor
    with col3:
        avg_smash = 0
        if len(df) > 0 and 'smash' in df.columns:
            valid_smash = df[(df['smash'] > 0) & (df['smash'] < 2)]['smash']
            avg_smash = valid_smash.mean() if len(valid_smash) > 0 else 0
        render_kpi_card(
            label="Avg Smash",
            value=avg_smash,
            unit="",
            format_str=".2f",
            benchmark=1.50,
            tooltip="Ball speed / Club speed. Tour average is ~1.50. Higher is better!"
        )


def render_kpi_card(
    label: str,
    value: float,
    unit: str = "",
    trend: Optional[float] = None,
    sparkline_data: Optional[List[float]] = None,
    benchmark: Optional[float] = None,
    status: str = "neutral",
    tooltip: Optional[str] = None,
    format_str: str = ".1f"
) -> None:
    """
    Render a hero KPI card with optional trend and benchmark.

    Args:
        label: Metric label
        value: Metric value
        unit: Unit of measurement (e.g., "yds", "mph")
        trend: Change from previous period (positive = improvement)
        sparkline_data: List of historical values for mini chart
        benchmark: Reference value for comparison
        status: "good", "warning", "bad", or "neutral"
        tooltip: Help text explaining the metric
        format_str: Format string for the value (e.g., ".1f", ".2f", ".0f")
    """
    # Format the value
    if value == 0 or value is None:
        formatted_value = "N/A"
    elif isinstance(value, int) or format_str == ".0f":
        formatted_value = str(int(value))
    else:
        formatted_value = f"{value:{format_str}}"

    if unit and formatted_value != "N/A":
        formatted_value = f"{formatted_value} {unit}"

    # Determine delta string
    delta_str = None
    delta_color = "normal"
    if trend is not None:
        if trend > 0:
            delta_str = f"+{trend:{format_str}}"
            delta_color = "normal"  # Green (positive delta in Streamlit)
        elif trend < 0:
            delta_str = f"{trend:{format_str}}"
            delta_color = "inverse"  # Red
        else:
            delta_str = "→"

    # Use Streamlit metric with optional help
    st.metric(
        label=label,
        value=formatted_value,
        delta=delta_str,
        delta_color=delta_color if delta_str else "off",
        help=tooltip
    )

    # Benchmark indicator (if provided and value is valid)
    if benchmark is not None and value and value != 0:
        _render_benchmark_bar(value, benchmark, label)


def _render_benchmark_bar(value: float, benchmark: float, label: str) -> None:
    """Render a mini benchmark comparison bar."""
    if benchmark == 0:
        return

    # Calculate percentage of benchmark
    pct = min(value / benchmark, 1.5)  # Cap at 150%

    # Determine color based on performance
    if pct >= 1.0:
        bar_color = "#4CAF50"  # Green - at or above benchmark
    elif pct >= 0.9:
        bar_color = "#FFC107"  # Yellow - close to benchmark
    else:
        bar_color = "#F44336"  # Red - below benchmark

    # Render simple progress-like bar
    st.markdown(
        f"""
        <div style="margin-top: -8px;">
            <div style="
                width: 100%;
                height: 4px;
                background: #E0E0E0;
                border-radius: 2px;
                overflow: hidden;
            ">
                <div style="
                    width: {min(pct * 100, 100):.0f}%;
                    height: 100%;
                    background: {bar_color};
                    border-radius: 2px;
                "></div>
            </div>
            <div style="font-size: 10px; color: #999; margin-top: 2px;">
                vs {benchmark:.2f} target
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_kpi_grid(
    metrics: List[dict],
    columns: int = 5
) -> None:
    """
    Render a grid of KPI cards.

    Args:
        metrics: List of metric dicts with keys:
            - label: Metric name
            - value: Metric value
            - unit: Optional unit
            - trend: Optional delta value
            - tooltip: Optional help text
        columns: Number of columns in the grid
    """
    cols = st.columns(min(columns, len(metrics)))

    for i, metric in enumerate(metrics):
        col_idx = i % len(cols)
        with cols[col_idx]:
            render_kpi_card(
                label=metric.get('label', ''),
                value=metric.get('value', 0),
                unit=metric.get('unit', ''),
                trend=metric.get('trend'),
                benchmark=metric.get('benchmark'),
                tooltip=metric.get('tooltip'),
                format_str=metric.get('format', '.1f')
            )


def render_club_kpi_cards(df: pd.DataFrame, club: str) -> None:
    """
    Render KPI cards for a specific club.

    Args:
        df: Full DataFrame
        club: Club name to filter by
    """
    club_data = df[df['club'] == club] if 'club' in df.columns else df

    if club_data.empty:
        st.info(f"No data for {club}")
        return

    metrics = []

    # Shot count
    metrics.append({
        'label': 'Shots',
        'value': len(club_data),
        'unit': '',
        'format': '.0f'
    })

    # Carry
    if 'carry' in club_data.columns:
        valid_carry = club_data[club_data['carry'] > 0]['carry']
        if len(valid_carry) > 0:
            metrics.append({
                'label': 'Avg Carry',
                'value': valid_carry.mean(),
                'unit': 'yds',
                'tooltip': f'Best: {valid_carry.max():.0f} yds'
            })

    # Ball Speed
    if 'ball_speed' in club_data.columns:
        valid_speed = club_data[club_data['ball_speed'] > 0]['ball_speed']
        if len(valid_speed) > 0:
            metrics.append({
                'label': 'Ball Speed',
                'value': valid_speed.mean(),
                'unit': 'mph'
            })

    # Smash Factor
    if 'smash' in club_data.columns:
        valid_smash = club_data[(club_data['smash'] > 0) & (club_data['smash'] < 2)]['smash']
        if len(valid_smash) > 0:
            metrics.append({
                'label': 'Smash',
                'value': valid_smash.mean(),
                'unit': '',
                'format': '.2f',
                'benchmark': 1.50
            })

    # Launch Angle
    if 'launch_angle' in club_data.columns:
        valid_launch = club_data[club_data['launch_angle'] > 0]['launch_angle']
        if len(valid_launch) > 0:
            metrics.append({
                'label': 'Launch',
                'value': valid_launch.mean(),
                'unit': '°',
                'tooltip': 'Launch angle in degrees'
            })

    render_kpi_grid(metrics, columns=len(metrics))
