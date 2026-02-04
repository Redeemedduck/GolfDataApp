"""
Session summary header component.

Displays session metadata, quick stats, and action buttons
at the top of session-focused pages.
"""
import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any


def render_session_header(
    session_id: str,
    df: pd.DataFrame,
    show_actions: bool = True,
    show_type_badge: bool = True,
    show_tags: bool = True
) -> None:
    """
    Render a session summary header card.

    Args:
        session_id: Session identifier
        df: DataFrame with session shot data
        show_actions: Show action buttons (Export, Compare, Edit)
        show_type_badge: Show session type badge
        show_tags: Show tags if present
    """
    if df.empty:
        st.warning("No data available for this session.")
        return

    # Calculate session stats
    shot_count = len(df)
    club_count = df['club'].nunique() if 'club' in df.columns else 0
    clubs = df['club'].unique().tolist() if 'club' in df.columns else []

    # Get session date
    session_date = "Unknown"
    if 'session_date' in df.columns:
        dates = df['session_date'].dropna()
        if len(dates) > 0:
            date_val = dates.iloc[0]
            if hasattr(date_val, 'strftime'):
                session_date = date_val.strftime('%B %d, %Y')
            else:
                session_date = str(date_val)[:10]
    elif 'date_added' in df.columns:
        dates = df['date_added'].dropna()
        if len(dates) > 0:
            date_val = dates.iloc[0]
            if hasattr(date_val, 'strftime'):
                session_date = date_val.strftime('%B %d, %Y')
            else:
                session_date = str(date_val)[:10]

    # Get session type
    session_type = None
    if 'session_type' in df.columns:
        types = df['session_type'].dropna()
        if len(types) > 0:
            session_type = types.iloc[0]

    # Get tags
    tags = []
    if 'shot_tag' in df.columns:
        tags = df['shot_tag'].dropna().unique().tolist()

    # Calculate quick stats
    avg_carry = 0
    avg_smash = 0
    if 'carry' in df.columns:
        valid_carry = df[df['carry'] > 0]['carry']
        avg_carry = valid_carry.mean() if len(valid_carry) > 0 else 0
    if 'smash' in df.columns:
        valid_smash = df[(df['smash'] > 0) & (df['smash'] < 2)]['smash']
        avg_smash = valid_smash.mean() if len(valid_smash) > 0 else 0

    # Render header card
    col1, col2 = st.columns([3, 1])

    with col1:
        # Session title and date
        st.markdown(f"### {session_id}")
        st.caption(f"📅 {session_date}")

        # Stats row
        stat_cols = st.columns(4)
        with stat_cols[0]:
            st.metric("Shots", shot_count)
        with stat_cols[1]:
            st.metric("Clubs", club_count)
        with stat_cols[2]:
            st.metric("Avg Carry", f"{avg_carry:.1f} yds" if avg_carry > 0 else "N/A")
        with stat_cols[3]:
            st.metric("Avg Smash", f"{avg_smash:.2f}" if avg_smash > 0 else "N/A")

        # Type badge and tags
        badge_row = []
        if show_type_badge and session_type:
            badge_row.append(_get_type_badge_html(session_type))
        if show_tags and tags:
            for tag in tags[:3]:  # Show max 3 tags
                badge_row.append(_get_tag_badge_html(tag))

        if badge_row:
            st.markdown(" ".join(badge_row), unsafe_allow_html=True)

        # Clubs used
        if clubs:
            st.caption(f"Clubs: {', '.join(sorted(clubs))}")

    with col2:
        if show_actions:
            _render_session_actions(session_id, df)


def _get_type_badge_html(session_type: str) -> str:
    """Generate HTML for session type badge."""
    colors = {
        'Practice': ('#4CAF50', '#E8F5E9'),
        'Round': ('#2196F3', '#E3F2FD'),
        'Gapping': ('#FF9800', '#FFF3E0'),
        'Fitting': ('#9C27B0', '#F3E5F5'),
        'Combine': ('#F44336', '#FFEBEE'),
    }
    bg, fg = colors.get(session_type, ('#757575', '#EEEEEE'))

    return f'''
    <span style="
        background: {fg};
        color: {bg};
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 8px;
    ">{session_type}</span>
    '''


def _get_tag_badge_html(tag: str) -> str:
    """Generate HTML for tag badge."""
    return f'''
    <span style="
        background: #F5F5F5;
        color: #616161;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        margin-right: 4px;
    ">{tag}</span>
    '''


def _render_session_actions(session_id: str, df: pd.DataFrame) -> None:
    """Render session action buttons."""
    st.markdown("**Quick Actions**")

    # Export button
    if st.button("Export CSV", key=f"export_{session_id}", use_container_width=True):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download",
            data=csv,
            file_name=f"session_{session_id}.csv",
            mime="text/csv",
            key=f"download_{session_id}"
        )

    # View in Dashboard link
    st.page_link(
        "pages/2_📊_Dashboard.py",
        label="View Dashboard",
        use_container_width=True
    )

    # Edit link
    st.page_link(
        "pages/3_🗄️_Database_Manager.py",
        label="Edit Session",
        use_container_width=True
    )


def render_compact_session_header(
    session_id: str,
    summary: dict,
    is_selected: bool = False
) -> None:
    """
    Render a compact session header for list views.

    Args:
        session_id: Session identifier
        summary: Pre-computed session summary dict
        is_selected: Whether this session is currently selected
    """
    bg_color = "#E8F5E9" if is_selected else "#FAFAFA"
    border_color = "#2D7F3E" if is_selected else "#E0E0E0"

    shot_count = summary.get('shot_count', 0)
    club_count = summary.get('club_count', 0)
    avg_carry = summary.get('avg_carry', 0)

    st.markdown(
        f"""
        <div style="
            padding: 12px 16px;
            background: {bg_color};
            border: 1px solid {border_color};
            border-radius: 8px;
            margin-bottom: 8px;
        ">
            <div style="font-weight: 600;">{session_id}</div>
            <div style="font-size: 13px; color: #666; margin-top: 4px;">
                {shot_count} shots • {club_count} clubs
                {f' • {avg_carry:.0f} yds avg' if avg_carry > 0 else ''}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
