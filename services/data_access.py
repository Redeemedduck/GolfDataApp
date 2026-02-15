"""
Centralized data access layer with caching.

This module provides cached access to golf data, enabling per-function
cache invalidation and consistent data access across all pages.

get_filtered_shots() is the main entry point for pages — it composes
time window + outlier filtering on top of raw data.
"""
import streamlit as st
import pandas as pd
import golf_db
from services.time_window import filter_by_window, DEFAULT_WINDOW
from services.data_quality import filter_outliers, get_outlier_summary


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


@st.cache_data(show_spinner=False, ttl=120)
def get_recent_sessions_with_stats(weeks: int = 4) -> list:
    """Get recent sessions with pre-computed Big 3 stats for journal view.

    Single query against session_stats table — no N+1.
    """
    return golf_db.get_recent_sessions_with_stats(weeks=weeks)


@st.cache_data(show_spinner=False, ttl=300)
def get_club_profile(club_name: str) -> pd.DataFrame:
    """Get per-club performance story over time."""
    return golf_db.get_club_profile(club_name)


@st.cache_data(show_spinner=False, ttl=300)
def get_rolling_averages(club: str = None, window: int = 5) -> dict:
    """Get rolling average baselines for trend comparison."""
    return golf_db.get_rolling_averages(club=club, window=window)


@st.cache_data(show_spinner=False, ttl=120)
def get_session_aggregates(session_id: str) -> dict:
    """Get Big 3 + performance stats for a single session."""
    return golf_db.get_session_aggregates(session_id)


def get_filtered_shots(
    session_id: str = None,
    read_mode: str = "auto",
    time_window: str = None,
    outlier_filter: bool = None,
) -> pd.DataFrame:
    """Get shot data with time window and outlier filtering applied.

    Reads filter settings from st.session_state if not provided explicitly.
    This is the primary data entry point for dashboard pages.

    Args:
        session_id: Specific session or None for all.
        read_mode: Data source mode.
        time_window: Time window key ('3mo', '6mo', '1yr', 'all').
        outlier_filter: Whether to apply outlier filtering.

    Returns:
        Filtered DataFrame.
    """
    if time_window is None:
        time_window = st.session_state.get("time_window", DEFAULT_WINDOW)
    if outlier_filter is None:
        outlier_filter = st.session_state.get("outlier_filter", True)

    df = get_session_data(session_id=session_id, read_mode=read_mode)

    if df.empty:
        return df

    # Apply time window (skip for single-session views)
    if session_id is None:
        df = filter_by_window(df, window=time_window)

    # Apply outlier filtering
    if outlier_filter:
        summary = get_outlier_summary(df)
        st.session_state["outlier_count"] = summary["total_removed"]
        df = filter_outliers(df)
    else:
        st.session_state["outlier_count"] = 0

    return df


@st.cache_data(show_spinner=False, ttl=120)
def get_executive_summary(read_mode: str = "auto", time_window: str = DEFAULT_WINDOW) -> dict:
    """Get executive summary analytics (cached)."""
    from services.analytics.executive_summary import compute_executive_summary
    df = get_session_data(read_mode=read_mode)
    df = filter_by_window(df, window=time_window)
    df = filter_outliers(df)
    return compute_executive_summary(df)


@st.cache_data(show_spinner=False, ttl=120)
def get_session_grades(read_mode: str = "auto", time_window: str = DEFAULT_WINDOW) -> list:
    """Get session quality grades (cached)."""
    from services.analytics.session_grades import compute_session_grades
    df = get_session_data(read_mode=read_mode)
    df = filter_by_window(df, window=time_window)
    df = filter_outliers(df)
    return compute_session_grades(df)


@st.cache_data(show_spinner=False, ttl=120)
def get_progress_trends(read_mode: str = "auto", time_window: str = DEFAULT_WINDOW) -> dict:
    """Get per-club progress trends (cached)."""
    from services.analytics.progress_tracker import compute_progress_trends
    df = get_session_data(read_mode=read_mode)
    df = filter_by_window(df, window=time_window)
    df = filter_outliers(df)
    return compute_progress_trends(df)


def clear_session_cache():
    """Clear all session-related caches."""
    get_unique_sessions.clear()
    get_session_data.clear()
    get_all_shots.clear()
    get_session_summary.clear()
    get_recent_sessions_with_stats.clear()
    get_club_profile.clear()
    get_rolling_averages.clear()
    get_session_aggregates.clear()


def clear_all_caches():
    """Clear all Streamlit data caches."""
    st.cache_data.clear()
