"""
Big 3 Impact Laws summary panel.

At-a-glance panel with color-coded indicators for each law:
- Face Angle: avg +/- std, tendency (open/closed/neutral)
- Club Path: avg +/- std, tendency (in-to-out/out-to-in/neutral)
- Strike Location: avg distance from center, consistency %

Thresholds from Adam Young + ml/classifiers.py.
"""
import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional

from utils.big3_constants import (
    FACE_STD_GREEN, FACE_STD_YELLOW,
    PATH_STD_GREEN, PATH_STD_YELLOW,
    STRIKE_DIST_GREEN, STRIKE_DIST_YELLOW,
    color_for_threshold,
)


def _face_tendency(avg):
    """Describe face angle tendency."""
    if avg is None:
        return "Unknown"
    if abs(avg) < 1.0:
        return "Neutral"
    return "Open" if avg > 0 else "Closed"


def _path_tendency(avg):
    """Describe club path tendency."""
    if avg is None:
        return "Unknown"
    if abs(avg) < 1.5:
        return "Neutral"
    return "In-to-Out" if avg > 0 else "Out-to-In"


def render_big3_summary(
    df: pd.DataFrame,
    title: str = "Big 3 Impact Laws",
) -> None:
    """Render the Big 3 summary panel.

    Args:
        df: DataFrame with face_angle, club_path, impact_x, impact_y,
            face_to_path, strike_distance columns.
        title: Optional section title.
    """
    if df.empty:
        st.info("No data available for Big 3 analysis")
        return

    st.markdown(f"#### {title}")

    # Compute stats
    face = df['face_angle'].dropna() if 'face_angle' in df.columns else pd.Series(dtype=float)
    path = df['club_path'].dropna() if 'club_path' in df.columns else pd.Series(dtype=float)

    if 'strike_distance' in df.columns:
        strike = df['strike_distance'].dropna()
    elif 'impact_x' in df.columns and 'impact_y' in df.columns:
        valid = df.dropna(subset=['impact_x', 'impact_y'])
        strike = np.sqrt(valid['impact_x'] ** 2 + valid['impact_y'] ** 2)
    else:
        strike = pd.Series(dtype=float)

    face_avg = face.mean() if len(face) > 0 else None
    face_std = face.std() if len(face) > 1 else None
    path_avg = path.mean() if len(path) > 0 else None
    path_std = path.std() if len(path) > 1 else None
    strike_avg = strike.mean() if len(strike) > 0 else None
    strike_std = strike.std() if len(strike) > 1 else None

    # Three columns
    col1, col2, col3 = st.columns(3)

    with col1:
        color = color_for_threshold(face_std, FACE_STD_GREEN, FACE_STD_YELLOW)
        tendency = _face_tendency(face_avg)
        avg_str = f"{face_avg:+.1f}" if face_avg is not None else "—"
        std_str = f"{face_std:.1f}" if face_std is not None else "—"

        st.markdown(
            f"<div style='background:#f0f2f6;border-left:4px solid {color};"
            f"padding:12px;border-radius:6px;margin-bottom:8px'>"
            f"<div style='font-size:0.8em;color:#555;margin-bottom:4px'>"
            f"Face Angle (75% of start direction)</div>"
            f"<div style='font-size:1.6em;font-weight:bold;color:#1a1a2e'>{avg_str}&deg;</div>"
            f"<div style='font-size:0.9em;color:{color}'>{tendency}</div>"
            f"<div style='font-size:0.75em;color:#666;margin-top:4px'>"
            f"Consistency: &pm;{std_str}&deg;</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col2:
        color = color_for_threshold(path_std, PATH_STD_GREEN, PATH_STD_YELLOW)
        tendency = _path_tendency(path_avg)
        avg_str = f"{path_avg:+.1f}" if path_avg is not None else "—"
        std_str = f"{path_std:.1f}" if path_std is not None else "—"

        st.markdown(
            f"<div style='background:#f0f2f6;border-left:4px solid {color};"
            f"padding:12px;border-radius:6px;margin-bottom:8px'>"
            f"<div style='font-size:0.8em;color:#555;margin-bottom:4px'>"
            f"Club Path (25% of direction, determines curve)</div>"
            f"<div style='font-size:1.6em;font-weight:bold;color:#1a1a2e'>{avg_str}&deg;</div>"
            f"<div style='font-size:0.9em;color:{color}'>{tendency}</div>"
            f"<div style='font-size:0.75em;color:#666;margin-top:4px'>"
            f"Consistency: &pm;{std_str}&deg;</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col3:
        color = color_for_threshold(strike_avg, STRIKE_DIST_GREEN, STRIKE_DIST_YELLOW)
        avg_str = f"{strike_avg:.2f}\"" if strike_avg is not None else "—"
        std_str = f"{strike_std:.2f}\"" if strike_std is not None else "—"

        # Consistency % (shots within 0.25" of center)
        if len(strike) > 0:
            pct_center = (strike <= STRIKE_DIST_GREEN).sum() / len(strike) * 100
            pct_str = f"{pct_center:.0f}%"
        else:
            pct_str = "—"

        st.markdown(
            f"<div style='background:#f0f2f6;border-left:4px solid {color};"
            f"padding:12px;border-radius:6px;margin-bottom:8px'>"
            f"<div style='font-size:0.8em;color:#555;margin-bottom:4px'>"
            f"Strike Location (biggest factor in distance)</div>"
            f"<div style='font-size:1.6em;font-weight:bold;color:#1a1a2e'>{avg_str}</div>"
            f"<div style='font-size:0.9em;color:{color}'>"
            f"{pct_str} centered</div>"
            f"<div style='font-size:0.75em;color:#666;margin-top:4px'>"
            f"Spread: &pm;{std_str}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
