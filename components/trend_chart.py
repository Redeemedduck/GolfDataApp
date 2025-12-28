"""
Trend chart component for performance over time.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime


def render_trend_chart(all_sessions_data: list, metric: str = 'carry') -> None:
    """
    Render a trend chart showing metric performance over multiple sessions.

    Args:
        all_sessions_data: List of dicts with session_id, date_added, and metric values
        metric: Metric to display (carry, smash, ball_speed, etc.)
    """
    st.subheader(f"{metric.replace('_', ' ').title()} Trend Over Time")

    if not all_sessions_data:
        st.info("No session data available for trend analysis")
        return

    # Convert to DataFrame
    df = pd.DataFrame(all_sessions_data)

    if df.empty or metric not in df.columns:
        st.warning(f"No {metric} data available")
        return

    # Sort by date
    df['date_added'] = pd.to_datetime(df['date_added'])
    df = df.sort_values('date_added')

    # Create figure
    fig = go.Figure()

    # Add line chart
    fig.add_trace(go.Scatter(
        x=df['date_added'],
        y=df[metric],
        mode='lines+markers',
        name=metric.replace('_', ' ').title(),
        line=dict(color='royalblue', width=3),
        marker=dict(size=10, color='darkblue', line=dict(width=2, color='white')),
        hovertemplate=(
            "<b>Session: %{text}</b><br>" +
            "Date: %{x|%Y-%m-%d %H:%M}<br>" +
            f"{metric.replace('_', ' ').title()}: %{{y:.2f}}<extra></extra>"
        ),
        text=df['session_id']
    ))

    # Add trend line (linear regression)
    if len(df) > 1:
        z = np.polyfit(range(len(df)), df[metric], 1)
        p = np.poly1d(z)
        trend_y = p(range(len(df)))

        fig.add_trace(go.Scatter(
            x=df['date_added'],
            y=trend_y,
            mode='lines',
            name='Trend',
            line=dict(color='red', width=2, dash='dash'),
            hovertemplate="Trend Line<extra></extra>"
        ))

    # Calculate improvement
    if len(df) >= 2:
        first_value = df[metric].iloc[0]
        last_value = df[metric].iloc[-1]
        improvement = last_value - first_value
        improvement_pct = (improvement / first_value * 100) if first_value != 0 else 0

        # Add annotation for improvement
        fig.add_annotation(
            x=df['date_added'].iloc[-1],
            y=last_value,
            text=f"Change: {improvement:+.1f} ({improvement_pct:+.1f}%)",
            showarrow=True,
            arrowhead=2,
            ax=50,
            ay=-40,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="black",
            borderwidth=1
        )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=metric.replace('_', ' ').title(),
        hovermode='x unified',
        height=400
    )

    st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Best", f"{df[metric].max():.2f}")
    col2.metric("Worst", f"{df[metric].min():.2f}")
    col3.metric("Average", f"{df[metric].mean():.2f}")
    col4.metric("Latest", f"{df[metric].iloc[-1]:.2f}")
