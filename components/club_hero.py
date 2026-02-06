"""
Club hero card component — headline stats for a selected club.
"""
import streamlit as st
import pandas as pd
from typing import Optional


def render_club_hero(club_name: str, df: pd.DataFrame) -> None:
    """Render a hero card for a selected club.

    Args:
        club_name: Club name (e.g., "Driver", "7 Iron").
        df: DataFrame of all shots for this club.
    """
    if df.empty:
        st.info(f"No data for {club_name}")
        return

    total_shots = len(df)
    sessions = df['session_id'].nunique() if 'session_id' in df.columns else 0

    # Carry stats (filter NULLs, which now correctly represent missing data)
    carry = df['carry'].dropna() if 'carry' in df.columns else pd.Series(dtype=float)
    avg_carry = carry.mean() if len(carry) > 0 else None
    best_carry = carry.max() if len(carry) > 0 else None

    smash = df['smash'].dropna() if 'smash' in df.columns else pd.Series(dtype=float)
    avg_smash = smash.mean() if len(smash) > 0 else None

    ball_speed = df['ball_speed'].dropna() if 'ball_speed' in df.columns else pd.Series(dtype=float)
    avg_ball_speed = ball_speed.mean() if len(ball_speed) > 0 else None

    # Hero layout
    st.markdown(f"## {club_name}")
    st.caption(f"{total_shots} shots across {sessions} sessions")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if avg_carry is not None:
            st.metric("Avg Carry", f"{avg_carry:.1f} yds")
        else:
            st.metric("Avg Carry", "—")

    with col2:
        if best_carry is not None:
            st.metric("Personal Best", f"{best_carry:.1f} yds")
        else:
            st.metric("Personal Best", "—")

    with col3:
        if avg_smash is not None:
            st.metric("Avg Smash", f"{avg_smash:.2f}")
        else:
            st.metric("Avg Smash", "—")

    with col4:
        if avg_ball_speed is not None:
            st.metric("Avg Ball Speed", f"{avg_ball_speed:.1f} mph")
        else:
            st.metric("Avg Ball Speed", "—")
