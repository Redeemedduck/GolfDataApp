"""
Session comparison component for comparing 2-3 sessions side-by-side.

This is the #1 user-requested feature - allows users to track their
progress and see how their performance has changed between sessions.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict, Optional
from services.data_access import get_session_summary, get_session_data


def render_session_comparison(
    session_ids: List[str],
    metrics: List[str] = None,
    read_mode: str = "auto"
) -> None:
    """
    Compare 2-3 sessions with side-by-side KPIs, overlaid trends, and delta highlighting.

    Args:
        session_ids: List of 2-3 session IDs to compare
        metrics: List of metric keys to compare (defaults to standard set)
        read_mode: Data source mode
    """
    if len(session_ids) < 2:
        st.warning("Select at least 2 sessions to compare.")
        return

    if len(session_ids) > 3:
        session_ids = session_ids[:3]
        st.info("Comparing first 3 selected sessions.")

    # Default metrics to compare
    if metrics is None:
        metrics = ['carry', 'ball_speed', 'smash', 'launch_angle', 'back_spin']

    # Get summaries for all sessions
    summaries = []
    session_data = {}
    for session_id in session_ids:
        summary = get_session_summary(session_id, read_mode=read_mode)
        summaries.append(summary)
        session_data[session_id] = get_session_data(session_id, read_mode=read_mode)

    # Render comparison header
    st.subheader("Session Comparison")

    # Session info cards
    cols = st.columns(len(session_ids))
    for i, (session_id, summary) in enumerate(zip(session_ids, summaries)):
        with cols[i]:
            _render_session_info_card(session_id, summary, is_baseline=(i == 0))

    st.divider()

    # KPI comparison cards
    st.subheader("Key Metrics Comparison")
    _render_kpi_comparison(session_ids, session_data, metrics)

    st.divider()

    # Overlaid trend charts
    st.subheader("Performance Overlay")
    _render_overlaid_chart(session_ids, session_data, "carry", "Carry Distance (yds)")

    st.divider()

    # Club-by-club comparison
    st.subheader("Club-by-Club Comparison")
    _render_club_comparison(session_ids, session_data)


def _render_session_info_card(session_id: str, summary: dict, is_baseline: bool = False) -> None:
    """Render session info card."""
    label = "BASELINE" if is_baseline else "COMPARE"
    badge_color = "#2D7F3E" if is_baseline else "#1976D2"

    st.markdown(
        f"""
        <div style="
            padding: 16px;
            background: {'#E8F5E9' if is_baseline else '#E3F2FD'};
            border-radius: 8px;
            border-left: 4px solid {badge_color};
        ">
            <div style="font-size: 12px; color: {badge_color}; font-weight: bold;">{label}</div>
            <div style="font-size: 18px; font-weight: 600; margin-top: 4px;">{session_id}</div>
            <div style="font-size: 14px; color: #666; margin-top: 8px;">
                {summary.get('shot_count', 0)} shots • {summary.get('club_count', 0)} clubs
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def _render_kpi_comparison(
    session_ids: List[str],
    session_data: Dict[str, pd.DataFrame],
    metrics: List[str]
) -> None:
    """Render KPI cards with comparison deltas."""
    # Calculate averages for each metric
    metric_labels = {
        'carry': ('Avg Carry', 'yds'),
        'ball_speed': ('Ball Speed', 'mph'),
        'smash': ('Smash Factor', ''),
        'launch_angle': ('Launch Angle', '°'),
        'back_spin': ('Back Spin', 'rpm'),
        'club_speed': ('Club Speed', 'mph'),
        'total': ('Total Distance', 'yds'),
    }

    # Show metrics in rows of columns
    for metric in metrics:
        if metric not in metric_labels:
            continue

        label, unit = metric_labels[metric]
        cols = st.columns(len(session_ids))

        # Get baseline value (first session)
        baseline_df = session_data[session_ids[0]]
        baseline_value = None
        if metric in baseline_df.columns:
            valid_data = baseline_df[baseline_df[metric] > 0][metric]
            if len(valid_data) > 0:
                baseline_value = valid_data.mean()

        for i, session_id in enumerate(session_ids):
            df = session_data[session_id]

            if metric in df.columns:
                valid_data = df[df[metric] > 0][metric]
                if len(valid_data) > 0:
                    value = valid_data.mean()

                    # Calculate delta from baseline
                    delta = None
                    delta_str = None
                    if i > 0 and baseline_value is not None and baseline_value > 0:
                        delta = value - baseline_value
                        pct = (delta / baseline_value) * 100
                        if metric == 'smash':
                            delta_str = f"{delta:+.3f}"
                        else:
                            delta_str = f"{delta:+.1f} ({pct:+.1f}%)"

                    with cols[i]:
                        if metric == 'smash':
                            st.metric(
                                label=f"{label}",
                                value=f"{value:.3f}",
                                delta=delta_str
                            )
                        else:
                            st.metric(
                                label=f"{label}",
                                value=f"{value:.1f} {unit}",
                                delta=delta_str
                            )
                else:
                    with cols[i]:
                        st.metric(label=label, value="N/A")
            else:
                with cols[i]:
                    st.metric(label=label, value="N/A")


def _render_overlaid_chart(
    session_ids: List[str],
    session_data: Dict[str, pd.DataFrame],
    metric: str,
    title: str
) -> None:
    """Render overlaid line chart comparing sessions."""
    fig = go.Figure()

    colors = ['#2D7F3E', '#1976D2', '#F57C00']  # Green, Blue, Orange

    for i, session_id in enumerate(session_ids):
        df = session_data[session_id]

        if metric in df.columns:
            valid_data = df[df[metric] > 0][metric].reset_index(drop=True)

            if len(valid_data) > 0:
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(valid_data) + 1)),
                    y=valid_data,
                    mode='lines+markers',
                    name=session_id,
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=6)
                ))

    fig.update_layout(
        title=title,
        xaxis_title="Shot Number",
        yaxis_title=title,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_club_comparison(
    session_ids: List[str],
    session_data: Dict[str, pd.DataFrame]
) -> None:
    """Render club-by-club comparison table."""
    # Get all clubs across all sessions
    all_clubs = set()
    for df in session_data.values():
        if 'club' in df.columns:
            all_clubs.update(df['club'].unique())

    if not all_clubs:
        st.info("No club data available for comparison.")
        return

    # Build comparison data
    comparison_rows = []

    for club in sorted(all_clubs):
        row = {'Club': club}

        for i, session_id in enumerate(session_ids):
            df = session_data[session_id]
            club_data = df[df['club'] == club] if 'club' in df.columns else pd.DataFrame()

            if len(club_data) > 0:
                avg_carry = club_data['carry'].mean() if 'carry' in club_data.columns else 0
                shot_count = len(club_data)
                row[f'{session_id} Carry'] = f"{avg_carry:.1f}" if avg_carry > 0 else "-"
                row[f'{session_id} Shots'] = shot_count
            else:
                row[f'{session_id} Carry'] = "-"
                row[f'{session_id} Shots'] = 0

        comparison_rows.append(row)

    comparison_df = pd.DataFrame(comparison_rows)
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)


def render_comparison_selector(sessions: List[dict], max_sessions: int = 3) -> List[str]:
    """
    Render multi-select for choosing sessions to compare.

    Args:
        sessions: List of session dictionaries
        max_sessions: Maximum number of sessions to compare

    Returns:
        List of selected session IDs
    """
    if not sessions:
        st.info("No sessions available for comparison.")
        return []

    session_options = []
    for session in sessions:
        session_id = session.get('session_id', 'Unknown')
        date = session.get('session_date') or session.get('date_added', 'Unknown')
        if hasattr(date, 'strftime'):
            date = date.strftime('%Y-%m-%d')

        session_type = session.get('session_type', '')
        label = f"{session_id} ({date})"
        if session_type:
            label += f" [{session_type}]"

        session_options.append((label, session_id))

    selected_labels = st.multiselect(
        f"Select Sessions to Compare (max {max_sessions})",
        [label for label, _ in session_options],
        max_selections=max_sessions,
        key="comparison_session_select"
    )

    # Map labels back to session IDs
    label_to_id = {label: sid for label, sid in session_options}
    return [label_to_id[label] for label in selected_labels]
