"""
Centralized data access layer with caching.

This module provides cached access to golf data, enabling per-function
cache invalidation and consistent data access across all pages.
"""
import streamlit as st
import pandas as pd
import golf_db


@st.cache_data(show_spinner=False, ttl=60)
def get_unique_sessions(read_mode: str = "auto") -> list:
    """
    Get list of unique sessions with caching.

    Args:
        read_mode: Data source mode ("auto", "sqlite", "supabase")

    Returns:
        List of session dictionaries with session_id, date_added, etc.
    """
    return golf_db.get_unique_sessions(read_mode=read_mode)


@st.cache_data(show_spinner=False, ttl=60)
def get_session_data(session_id: str = None, read_mode: str = "auto") -> pd.DataFrame:
    """
    Get shot data for a session (or all sessions) with caching.

    Args:
        session_id: Specific session ID or None for all sessions
        read_mode: Data source mode ("auto", "sqlite", "supabase")

    Returns:
        DataFrame of shot data
    """
    return golf_db.get_session_data(session_id, read_mode=read_mode)


@st.cache_data(show_spinner=False, ttl=60)
def get_all_shots(read_mode: str = "auto") -> pd.DataFrame:
    """
    Get all shots across all sessions with caching.

    Args:
        read_mode: Data source mode

    Returns:
        DataFrame of all shot data
    """
    return golf_db.get_all_shots(read_mode=read_mode)


@st.cache_data(show_spinner=False, ttl=300)
def get_session_summary(session_id: str, read_mode: str = "auto") -> dict:
    """
    Get pre-aggregated summary stats for a session.

    Useful for session comparison views to avoid repeated DataFrame scans.

    Args:
        session_id: Session to summarize
        read_mode: Data source mode

    Returns:
        Dictionary with pre-computed KPIs:
        - shot_count, club_count, unique_clubs
        - avg_carry, avg_ball_speed, avg_smash
        - best_carry, best_smash
        - session_date, session_type
    """
    df = golf_db.get_session_data(session_id, read_mode=read_mode)

    if df.empty:
        return {
            "session_id": session_id,
            "shot_count": 0,
            "club_count": 0,
            "unique_clubs": [],
        }

    summary = {
        "session_id": session_id,
        "shot_count": len(df),
        "club_count": df['club'].nunique() if 'club' in df.columns else 0,
        "unique_clubs": df['club'].unique().tolist() if 'club' in df.columns else [],
    }

    # Carry stats
    if 'carry' in df.columns:
        valid_carry = df[df['carry'] > 0]['carry']
        summary["avg_carry"] = valid_carry.mean() if len(valid_carry) > 0 else 0
        summary["best_carry"] = valid_carry.max() if len(valid_carry) > 0 else 0

    # Ball speed stats
    if 'ball_speed' in df.columns:
        valid_speed = df[df['ball_speed'] > 0]['ball_speed']
        summary["avg_ball_speed"] = valid_speed.mean() if len(valid_speed) > 0 else 0

    # Smash factor stats
    if 'smash' in df.columns:
        valid_smash = df[(df['smash'] > 0) & (df['smash'] < 2)]['smash']
        summary["avg_smash"] = valid_smash.mean() if len(valid_smash) > 0 else 0
        summary["best_smash"] = valid_smash.max() if len(valid_smash) > 0 else 0

    # Session metadata
    if 'session_date' in df.columns:
        dates = df['session_date'].dropna()
        summary["session_date"] = dates.iloc[0] if len(dates) > 0 else None

    if 'session_type' in df.columns:
        types = df['session_type'].dropna()
        summary["session_type"] = types.iloc[0] if len(types) > 0 else None

    return summary


def clear_session_cache():
    """Clear all session-related caches."""
    get_unique_sessions.clear()
    get_session_data.clear()
    get_all_shots.clear()
    get_session_summary.clear()


def clear_all_caches():
    """Clear all Streamlit data caches."""
    st.cache_data.clear()
