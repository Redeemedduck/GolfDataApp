"""
Progress tracker component for session-over-session trend analysis.

Tracks metric improvements across sessions with statistical significance testing
using scipy.stats.linregress.
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict


def _calculate_trend(values: list) -> Dict:
    """
    Calculate trend statistics using linear regression.

    Args:
        values: List of numeric values (session medians in chronological order)

    Returns:
        Dictionary with trend statistics:
            - slope: Change per session
            - intercept: Y-intercept
            - r_squared: R² value (goodness of fit)
            - p_value: Statistical significance (p < 0.05 is significant)
            - is_significant: True if p < 0.05 AND n >= 5
            - improvement_pct: Percentage change from first to last
            - message: Human-readable trend message
            - note: Informational message if insufficient data
    """
    n = len(values)

    # Need at least 3 sessions for any trend
    if n < 3:
        return {
            'slope': 0,
            'intercept': 0,
            'r_squared': 0,
            'p_value': 1.0,
            'is_significant': False,
            'improvement_pct': 0,
            'message': "Not enough data for trend analysis",
            'note': f"Need 3+ sessions (have {n})"
        }

    # Create x values (session indices)
    x = np.arange(n)

    # Perform linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
    r_squared = r_value ** 2

    # Calculate improvement percentage
    first_value = values[0]
    last_value = values[-1]
    if first_value != 0:
        improvement_pct = ((last_value - first_value) / first_value) * 100
    else:
        improvement_pct = 0

    # Determine significance (need p < 0.05 AND at least 5 sessions)
    is_significant = (p_value < 0.05) and (n >= 5)

    # Generate message
    if is_significant:
        direction = "improving" if slope > 0 else "declining"
        message = f"Statistically significant {direction} trend (p={p_value:.3f})"
        note = None
    elif n < 5:
        message = "Trend detected but not yet statistically significant"
        note = f"Need 5+ sessions for significance (have {n})"
    else:
        message = "No statistically significant trend detected"
        note = "Keep practicing to establish a clear trend"

    return {
        'slope': slope,
        'intercept': intercept,
        'r_squared': r_squared,
        'p_value': p_value,
        'is_significant': is_significant,
        'improvement_pct': improvement_pct,
        'message': message,
        'note': note
    }


def render_progress_tracker(df: pd.DataFrame, metric: str = 'carry') -> None:
    """
    Render progress tracker showing session-over-session trends with statistical significance.

    Args:
        df: DataFrame containing shot data
        metric: Metric to track (carry, ball_speed, smash, face_angle, club_path, etc.)

    Required columns: session_id, metric column, session_date (or date_added)

    Displays:
        - Scatter + line chart of session medians over time
        - Trend line with color coding (green=improving significant, red=declining significant, gray=not significant)
        - Metrics row: Sessions count, Change %, R², Significance status
        - Contextual messages about progress
    """
    st.subheader("Progress Tracker")

    # Empty check
    if df.empty:
        st.info("No data available for progress tracking")
        return

    # Check required columns
    if metric not in df.columns:
        st.warning(f"Metric '{metric}' not found in data")
        return

    if 'session_id' not in df.columns:
        st.warning("Session ID column required for progress tracking")
        return

    # Validate metric
    valid_metrics = ['carry', 'total', 'ball_speed', 'club_speed', 'smash',
                     'face_angle', 'club_path', 'launch_angle', 'back_spin', 'side_spin']
    metric_labels = {
        'carry': 'Carry Distance (yds)',
        'total': 'Total Distance (yds)',
        'ball_speed': 'Ball Speed (mph)',
        'club_speed': 'Club Speed (mph)',
        'smash': 'Smash Factor',
        'face_angle': 'Face Angle (deg)',
        'club_path': 'Club Path (deg)',
        'launch_angle': 'Launch Angle (deg)',
        'back_spin': 'Back Spin (rpm)',
        'side_spin': 'Side Spin (rpm)'
    }

    if metric not in valid_metrics:
        st.warning(f"Unsupported metric: {metric}. Supported: {', '.join(valid_metrics)}")
        return

    metric_label = metric_labels.get(metric, metric.replace('_', ' ').title())

    # Aggregate per session: median of metric per session
    session_groups = df.groupby('session_id').agg({
        metric: 'median',
        'session_date': 'first',  # Use first non-null session_date
        'date_added': 'first'
    }).reset_index()

    # Use session_date if available, fall back to date_added
    if 'session_date' in session_groups.columns and session_groups['session_date'].notna().any():
        session_groups['display_date'] = pd.to_datetime(
            session_groups['session_date'].fillna(session_groups.get('date_added', pd.NaT)),
            format='mixed',
            dayfirst=False,
        )
    else:
        session_groups['display_date'] = pd.to_datetime(session_groups['date_added'], format='mixed', dayfirst=False)

    # Sort by date
    session_groups = session_groups.sort_values('display_date')

    # Check minimum sessions
    n_sessions = len(session_groups)
    if n_sessions < 3:
        st.info(f"Need at least 3 sessions for trend analysis (currently have {n_sessions})")
        return

    # Calculate trend
    session_values = session_groups[metric].tolist()
    trend_stats = _calculate_trend(session_values)

    # Create figure
    fig = go.Figure()

    # Add actual session values (scatter + line)
    fig.add_trace(go.Scatter(
        x=session_groups['display_date'],
        y=session_groups[metric],
        mode='lines+markers',
        name='Actual',
        line=dict(color='royalblue', width=2),
        marker=dict(size=10, color='darkblue', line=dict(width=2, color='white')),
        hovertemplate=(
            "<b>Session %{customdata[0]}</b><br>" +
            "Date: %{x|%Y-%m-%d}<br>" +
            f"{metric_label}: %{{y:.2f}}<extra></extra>"
        ),
        customdata=session_groups[['session_id']].values
    ))

    # Add trend line if we have at least 2 sessions
    if n_sessions >= 2:
        # Calculate trend line values
        x_indices = np.arange(n_sessions)
        trend_y = trend_stats['slope'] * x_indices + trend_stats['intercept']

        # Determine trend line color based on significance and direction
        if trend_stats['is_significant']:
            if trend_stats['slope'] > 0:
                # Improving metrics (carry, ball_speed, smash, etc.)
                if metric in ['face_angle', 'club_path']:
                    # For angles, closer to zero is often better (context-dependent)
                    trend_color = 'gray'  # Neutral for angles
                else:
                    trend_color = '#4CAF50'  # green
                trend_label = f"Improving (p={trend_stats['p_value']:.3f})"
            else:
                # Declining metrics
                if metric in ['face_angle', 'club_path']:
                    trend_color = 'gray'  # Neutral for angles
                else:
                    trend_color = '#F44336'  # red
                trend_label = f"Declining (p={trend_stats['p_value']:.3f})"
        else:
            trend_color = '#BDBDBD'  # gray
            trend_label = "Trend not significant"

        fig.add_trace(go.Scatter(
            x=session_groups['display_date'],
            y=trend_y,
            mode='lines',
            name=trend_label,
            line=dict(color=trend_color, width=2, dash='dash'),
            hovertemplate=f"{trend_label}<br>R²: {trend_stats['r_squared']:.3f}<extra></extra>"
        ))

    # Update layout
    fig.update_layout(
        title=f"{metric_label} - Session Progress ({n_sessions} sessions)",
        xaxis_title="Date",
        yaxis_title=metric_label,
        hovermode='x unified',
        height=400,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Sessions", n_sessions)

    with col2:
        # Determine if improvement is positive or negative based on metric
        # For most metrics (carry, ball_speed, smash), higher is better
        # For some metrics (std deviation of angles), lower might be better
        improvement_val = trend_stats['improvement_pct']
        if metric in ['carry', 'total', 'ball_speed', 'club_speed', 'smash']:
            delta_color = "normal"  # Streamlit uses green for positive, red for negative
        else:
            delta_color = "off"  # Neutral for angles (context-dependent)

        st.metric(
            "Change",
            f"{improvement_val:+.1f}%",
            delta=f"{improvement_val:+.1f}%",
            delta_color=delta_color
        )

    with col3:
        st.metric("R²", f"{trend_stats['r_squared']:.3f}",
                  help="Goodness of fit (1.0 = perfect fit)")

    with col4:
        if trend_stats['is_significant']:
            sig_text = f"✅ Yes (p={trend_stats['p_value']:.3f})"
            sig_help = "Statistically significant trend detected"
        else:
            sig_text = f"Not yet (n={n_sessions})"
            sig_help = "Need more sessions for statistical significance"

        st.metric("Significant", sig_text, help=sig_help)

    # Show contextual messages
    if not trend_stats['is_significant'] and n_sessions < 5:
        st.info(f"ℹ️ Keep practicing! Need 5+ sessions for statistically significant trend detection (currently have {n_sessions}).")
    elif trend_stats['is_significant'] and trend_stats['slope'] > 0:
        if metric in ['carry', 'total', 'ball_speed', 'club_speed', 'smash']:
            st.success(f"🎯 {trend_stats['message']} — Great progress!")
        else:
            st.info(f"📊 {trend_stats['message']}")
    elif trend_stats['is_significant'] and trend_stats['slope'] < 0:
        if metric in ['carry', 'total', 'ball_speed', 'club_speed', 'smash']:
            st.warning(f"⚠️ {trend_stats['message']} — Review recent changes to your setup or swing.")
        else:
            st.info(f"📊 {trend_stats['message']}")
    else:
        st.write(f"📊 {trend_stats['message']}")
        if trend_stats['note']:
            st.caption(f"💡 {trend_stats['note']}")
