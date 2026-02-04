"""
Session list view component for card-based session browsing.

Provides a scannable, chronological list of sessions with:
- Session cards (date, shot count, type badge)
- Filter by type/tag/date
- Sort options
- Quick actions (View, Compare, Export)
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional, Callable
from datetime import datetime


def render_session_list(
    sessions: List[dict],
    on_select: Optional[Callable[[str], None]] = None,
    show_filters: bool = True,
    show_actions: bool = True,
    selected_session_id: Optional[str] = None
) -> Optional[str]:
    """
    Render a card-based session browser.

    Args:
        sessions: List of session dictionaries
        on_select: Callback when a session is selected
        show_filters: Show filter controls
        show_actions: Show action buttons on cards
        selected_session_id: Currently selected session ID

    Returns:
        Selected session ID or None
    """
    if not sessions:
        st.info("No sessions available. Import your first session to get started!")
        st.page_link("pages/1_📥_Data_Import.py", label="Import Session", icon="📥")
        return None

    # Filters
    filtered_sessions = sessions
    if show_filters:
        filtered_sessions = _render_filters(sessions)

    # Sort options
    sort_col1, sort_col2 = st.columns([3, 1])
    with sort_col2:
        sort_option = st.selectbox(
            "Sort by",
            ["Newest First", "Oldest First", "Most Shots", "Fewest Shots"],
            label_visibility="collapsed"
        )

    filtered_sessions = _sort_sessions(filtered_sessions, sort_option)

    # Session count
    st.caption(f"Showing {len(filtered_sessions)} of {len(sessions)} sessions")

    # Render session cards
    selected = None
    for session in filtered_sessions:
        session_id = session.get('session_id')
        is_selected = session_id == selected_session_id

        clicked = _render_session_card(
            session,
            is_selected=is_selected,
            show_actions=show_actions
        )

        if clicked:
            selected = session_id
            if on_select:
                on_select(session_id)

    return selected


def _render_filters(sessions: List[dict]) -> List[dict]:
    """Render filter controls and return filtered sessions."""
    col1, col2, col3 = st.columns(3)

    # Type filter
    with col1:
        session_types = list(set(
            s.get('session_type') for s in sessions
            if s.get('session_type')
        ))
        session_types = ['All'] + sorted(session_types)

        type_filter = st.selectbox(
            "Session Type",
            session_types,
            key="session_list_type_filter"
        )

    # Date filter
    with col2:
        date_options = ['All Time', 'Last 7 Days', 'Last 30 Days', 'Last 90 Days']
        date_filter = st.selectbox(
            "Date Range",
            date_options,
            key="session_list_date_filter"
        )

    # Search
    with col3:
        search_term = st.text_input(
            "Search",
            placeholder="Session ID...",
            key="session_list_search"
        )

    # Apply filters
    filtered = sessions

    if type_filter != 'All':
        filtered = [s for s in filtered if s.get('session_type') == type_filter]

    if date_filter != 'All Time':
        days = {'Last 7 Days': 7, 'Last 30 Days': 30, 'Last 90 Days': 90}
        cutoff = days.get(date_filter, 0)
        if cutoff > 0:
            now = datetime.now()
            filtered = [
                s for s in filtered
                if _session_within_days(s, cutoff, now)
            ]

    if search_term:
        filtered = [
            s for s in filtered
            if search_term.lower() in str(s.get('session_id', '')).lower()
        ]

    return filtered


def _session_within_days(session: dict, days: int, now: datetime) -> bool:
    """Check if session is within the specified number of days."""
    date_val = session.get('session_date') or session.get('date_added')

    if date_val is None:
        return True  # Include sessions without dates

    try:
        if isinstance(date_val, datetime):
            session_date = date_val
        elif isinstance(date_val, str):
            session_date = datetime.fromisoformat(date_val[:10])
        else:
            return True

        delta = (now - session_date).days
        return delta <= days
    except:
        return True


def _sort_sessions(sessions: List[dict], sort_option: str) -> List[dict]:
    """Sort sessions based on the selected option."""
    if sort_option == "Newest First":
        return sorted(
            sessions,
            key=lambda s: s.get('session_date') or s.get('date_added') or '',
            reverse=True
        )
    elif sort_option == "Oldest First":
        return sorted(
            sessions,
            key=lambda s: s.get('session_date') or s.get('date_added') or ''
        )
    elif sort_option == "Most Shots":
        return sorted(
            sessions,
            key=lambda s: s.get('shot_count', 0),
            reverse=True
        )
    elif sort_option == "Fewest Shots":
        return sorted(
            sessions,
            key=lambda s: s.get('shot_count', 0)
        )
    return sessions


def _render_session_card(
    session: dict,
    is_selected: bool = False,
    show_actions: bool = True
) -> bool:
    """
    Render a session card.

    Returns True if the card was clicked.
    """
    session_id = session.get('session_id', 'Unknown')

    # Format date
    date_val = session.get('session_date') or session.get('date_added')
    if date_val:
        if hasattr(date_val, 'strftime'):
            display_date = date_val.strftime('%b %d, %Y')
        else:
            display_date = str(date_val)[:10]
    else:
        display_date = 'No date'

    # Session type badge
    session_type = session.get('session_type')
    type_badge = ""
    if session_type:
        badge_colors = {
            'Practice': '#4CAF50',
            'Round': '#2196F3',
            'Gapping': '#FF9800',
            'Fitting': '#9C27B0',
        }
        color = badge_colors.get(session_type, '#757575')
        type_badge = f'<span style="background: {color}20; color: {color}; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;">{session_type}</span>'

    # Shot count
    shot_count = session.get('shot_count', '?')

    # Card styling
    border_color = '#2D7F3E' if is_selected else '#E0E0E0'
    bg_color = '#E8F5E9' if is_selected else '#FFFFFF'

    # Create the card
    card_html = f"""
    <div style="
        padding: 16px;
        background: {bg_color};
        border: 1px solid {border_color};
        border-radius: 8px;
        margin-bottom: 12px;
        {'border-left: 4px solid #2D7F3E;' if is_selected else ''}
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <div style="font-weight: 600; font-size: 16px;">{session_id}</div>
                <div style="color: #666; font-size: 14px; margin-top: 4px;">{display_date}</div>
            </div>
            <div style="text-align: right;">
                {type_badge}
                <div style="color: #999; font-size: 13px; margin-top: 4px;">{shot_count} shots</div>
            </div>
        </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)

    # Action buttons
    clicked = False
    if show_actions:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("View", key=f"view_{session_id}", use_container_width=True):
                clicked = True
        with col2:
            st.button("Compare", key=f"compare_{session_id}", use_container_width=True)
        with col3:
            st.button("Export", key=f"export_{session_id}", use_container_width=True)

    return clicked


def render_session_timeline(
    sessions: List[dict],
    max_sessions: int = 10
) -> None:
    """
    Render a visual timeline of sessions.

    Args:
        sessions: List of session dictionaries
        max_sessions: Maximum sessions to show
    """
    if not sessions:
        st.info("No sessions to display.")
        return

    # Sort by date and limit
    sorted_sessions = sorted(
        sessions,
        key=lambda s: s.get('session_date') or s.get('date_added') or '',
        reverse=True
    )[:max_sessions]

    st.markdown("### Recent Sessions")

    for i, session in enumerate(sorted_sessions):
        session_id = session.get('session_id', 'Unknown')

        # Format date
        date_val = session.get('session_date') or session.get('date_added')
        if date_val:
            if hasattr(date_val, 'strftime'):
                display_date = date_val.strftime('%b %d')
            else:
                display_date = str(date_val)[:10]
        else:
            display_date = ''

        # Timeline marker
        is_latest = i == 0

        st.markdown(
            f"""
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <div style="
                    width: 12px;
                    height: 12px;
                    background: {'#2D7F3E' if is_latest else '#E0E0E0'};
                    border-radius: 50%;
                    margin-right: 12px;
                "></div>
                <div style="flex: 1;">
                    <span style="font-weight: {'600' if is_latest else '400'};">{session_id}</span>
                    <span style="color: #999; margin-left: 8px;">{display_date}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
