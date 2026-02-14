"""
Shot-by-shot trend lines within a session.

Shows face angle and club path progression across shot numbers,
with a warmup/fatigue analysis.
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


def render_shot_trends(df: pd.DataFrame) -> None:
    """Render shot-by-shot trend lines for face angle and club path.

    Args:
        df: DataFrame of shots within a single session, ordered by shot number.
    """
    if df.empty:
        st.info("No shot data for trend analysis")
        return

    # Assign shot numbers
    plot_df = df.reset_index(drop=True)
    plot_df['shot_num'] = range(1, len(plot_df) + 1)

    st.markdown("#### Shot-by-Shot Trends")

    # Face Angle + Club Path on same chart
    has_face = 'face_angle' in plot_df.columns and plot_df['face_angle'].notna().any()
    has_path = 'club_path' in plot_df.columns and plot_df['club_path'].notna().any()

    if not has_face and not has_path:
        st.info("No face angle or club path data available")
        return

    fig = make_subplots(rows=1, cols=1)

    if has_face:
        face = plot_df['face_angle'].values
        fig.add_trace(go.Scatter(
            x=plot_df['shot_num'], y=face,
            mode='lines+markers',
            name='Face Angle',
            line=dict(color='#ff7f0e', width=2),
            marker=dict(size=6),
        ))

    if has_path:
        path = plot_df['club_path'].values
        fig.add_trace(go.Scatter(
            x=plot_df['shot_num'], y=path,
            mode='lines+markers',
            name='Club Path',
            line=dict(color='#d62728', width=2),
            marker=dict(size=6),
        ))

    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")

    fig.update_layout(
        xaxis_title="Shot #",
        yaxis_title="Degrees",
        height=350,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Warmup / fatigue analysis
    if len(plot_df) >= 6:
        _render_warmup_analysis(plot_df)


def _render_warmup_analysis(df: pd.DataFrame) -> None:
    """Analyze warmup vs fatigue patterns."""
    n = len(df)
    first_third = df.iloc[:n // 3]
    last_third = df.iloc[-(n // 3):]

    metrics = []

    for col, label in [('face_angle', 'Face Angle Std'), ('club_path', 'Club Path Std')]:
        if col not in df.columns:
            continue
        early = first_third[col].dropna()
        late = last_third[col].dropna()
        if len(early) < 2 or len(late) < 2:
            continue
        early_std = early.std()
        late_std = late.std()
        delta = late_std - early_std
        metrics.append((label, early_std, late_std, delta))

    if not metrics:
        return

    # Determine overall trend
    total_delta = sum(m[3] for m in metrics)

    if abs(total_delta) < 0.3:
        verdict = "Consistent throughout the session"
        icon = "="
    elif total_delta > 0:
        verdict = "Consistency decreased later in the session (possible fatigue)"
        icon = ">"
    else:
        verdict = "Consistency improved later in the session (warmup effect)"
        icon = "<"

    st.markdown(f"**Warmup/Fatigue:** {verdict}")

    cols = st.columns(len(metrics))
    for i, (label, early, late, delta) in enumerate(metrics):
        with cols[i]:
            direction = "worse" if delta > 0 else "better"
            st.metric(
                label,
                f"{late:.1f}",
                delta=f"{delta:+.1f} ({direction})",
                delta_color="inverse",
            )
