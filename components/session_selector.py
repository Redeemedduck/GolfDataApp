"""
Session selector component with club filtering.
"""
import streamlit as st
import pandas as pd
from typing import Tuple, List


def render_session_selector(golf_db) -> Tuple[str, pd.DataFrame, List[str]]:
    """
    Render session selector with club filter in sidebar.

    Args:
        golf_db: Database module with get_unique_sessions() and get_session_data() functions

    Returns:
        Tuple of (selected_session_id, filtered_dataframe, selected_clubs)
    """
    st.header("📊 Session")
    unique_sessions = golf_db.get_unique_sessions()
    session_options = [
        f"{s['session_id']} ({s.get('date_added', 'Unknown')})"
        for s in unique_sessions
    ] if unique_sessions else []

    if not session_options:
        st.info("No data yet. Import a report to get started!")
        return None, pd.DataFrame(), []

    # Session selector
    selected_session_str = st.selectbox(
        "Select Session",
        session_options,
        label_visibility="collapsed"
    )
    selected_session_id = selected_session_str.split(" ")[0]
    df = golf_db.get_session_data(selected_session_id)

    if df.empty:
        st.warning("Selected session has no data.")
        return selected_session_id, pd.DataFrame(), []

    # Club filter
    st.header("🏌️ Filter by Club")
    all_clubs = df['club'].unique().tolist()
    selected_clubs = st.multiselect(
        "Select Clubs",
        all_clubs,
        default=all_clubs,
        label_visibility="collapsed"
    )

    # Filter dataframe
    if selected_clubs:
        df = df[df['club'].isin(selected_clubs)]

    return selected_session_id, df, selected_clubs
