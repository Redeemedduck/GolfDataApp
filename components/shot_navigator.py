"""
Shot-by-shot navigation component.

Arrow button navigation through individual shots within a session,
showing full shot details and mini trajectory.
"""
import streamlit as st
import pandas as pd
from typing import Optional


def render_shot_navigator(df: pd.DataFrame, session_key: str = "shot_nav") -> None:
    """Render shot-by-shot navigator with prev/next buttons.

    Args:
        df: DataFrame of shots within a session.
        session_key: Unique key prefix for session state.
    """
    if df.empty:
        st.info("No shots to navigate")
        return

    plot_df = df.reset_index(drop=True)
    n_shots = len(plot_df)

    # Session state for current shot index
    idx_key = f"{session_key}_idx"
    if idx_key not in st.session_state:
        st.session_state[idx_key] = 0

    current_idx = st.session_state[idx_key]
    current_idx = max(0, min(current_idx, n_shots - 1))

    st.markdown("#### Shot Navigator")

    # Navigation row
    nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])
    with nav_col1:
        if st.button("< Prev", key=f"{session_key}_prev", disabled=current_idx <= 0):
            st.session_state[idx_key] = current_idx - 1
            st.rerun()
    with nav_col2:
        st.markdown(
            f"<div style='text-align:center;font-size:1.1em'>"
            f"Shot {current_idx + 1} of {n_shots}</div>",
            unsafe_allow_html=True,
        )
    with nav_col3:
        if st.button("Next >", key=f"{session_key}_next", disabled=current_idx >= n_shots - 1):
            st.session_state[idx_key] = current_idx + 1
            st.rerun()

    # Shot details
    shot = plot_df.iloc[current_idx]
    club = shot.get('club', 'Unknown')

    st.markdown(f"**{club}**")

    # Primary metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        val = shot.get('carry')
        st.metric("Carry", f"{val:.1f} yds" if pd.notna(val) else "—")
    with m2:
        val = shot.get('total')
        st.metric("Total", f"{val:.1f} yds" if pd.notna(val) else "—")
    with m3:
        val = shot.get('ball_speed')
        st.metric("Ball Speed", f"{val:.1f} mph" if pd.notna(val) else "—")
    with m4:
        val = shot.get('smash')
        st.metric("Smash", f"{val:.2f}" if pd.notna(val) else "—")

    # Secondary metrics
    m5, m6, m7, m8 = st.columns(4)
    with m5:
        val = shot.get('launch_angle')
        st.metric("Launch", f"{val:.1f}" if pd.notna(val) else "—")
    with m6:
        val = shot.get('face_angle')
        st.metric("Face", f"{val:+.1f}" if pd.notna(val) else "—")
    with m7:
        val = shot.get('club_path')
        st.metric("Path", f"{val:+.1f}" if pd.notna(val) else "—")
    with m8:
        val = shot.get('attack_angle')
        st.metric("Attack", f"{val:+.1f}" if pd.notna(val) else "—")

    # Spin row
    s1, s2, s3 = st.columns(3)
    with s1:
        val = shot.get('back_spin')
        st.metric("Back Spin", f"{val:.0f} rpm" if pd.notna(val) else "—")
    with s2:
        val = shot.get('side_spin')
        st.metric("Side Spin", f"{val:.0f} rpm" if pd.notna(val) else "—")
    with s3:
        val = shot.get('apex')
        st.metric("Apex", f"{val:.0f} ft" if pd.notna(val) else "—")
