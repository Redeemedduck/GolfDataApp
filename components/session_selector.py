"""
Session selector component with club filtering.
"""
import streamlit as st
import pandas as pd
from typing import Tuple, List, Callable


def render_session_selector(
    get_unique_sessions: Callable[[], List[dict]],
    get_session_data: Callable[[str], pd.DataFrame]
) -> Tuple[str, pd.DataFrame, List[str]]:
    """
    Render session selector with club filter in sidebar.

    Args:
        get_unique_sessions: Function returning a list of sessions
        get_session_data: Function returning a DataFrame for a session_id

    Returns:
        Tuple of (selected_session_id, filtered_dataframe, selected_clubs)
    """
    st.header("📊 Session")
    unique_sessions = get_unique_sessions()
    session_types = sorted({
        s.get('session_type') for s in unique_sessions
        if s.get('session_type')
    })

    def _format_session_label(session):
        label = f"{session['session_id']} ({session.get('date_added', 'Unknown')})"
        if session.get('session_type'):
            label = f"{label} [{session['session_type']}]"
        return label

    session_options = [
        _format_session_label(s)
        for s in unique_sessions
    ] if unique_sessions else []

    if not session_options:
        st.info("No data yet. Import a report to get started!")
        return None, pd.DataFrame(), []

    # Session selector
    type_filter = "All"
    if session_types:
        type_filter = st.selectbox(
            "Session Type",
            ["All"] + session_types,
            key="session_type_filter"
        )

    search_text = st.text_input(
        "Search sessions",
        placeholder="Type to filter sessions",
        label_visibility="collapsed"
    )
    if type_filter != "All":
        session_options = [
            option for option in session_options if f"[{type_filter}]" in option
        ]
    if search_text:
        session_options = [
            option for option in session_options if search_text.lower() in option.lower()
        ]

    if not session_options:
        st.info("No sessions match that search.")
        return None, pd.DataFrame(), []

    selected_session_str = st.selectbox(
        "Select Session",
        session_options,
        label_visibility="collapsed"
    )
    selected_session_id = selected_session_str.split(" ")[0]
    df = get_session_data(selected_session_id)

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
