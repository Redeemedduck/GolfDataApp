"""
Empty state components for friendly user guidance.

Provides consistent empty state patterns with illustrations,
helpful messages, and clear calls-to-action.
"""
import streamlit as st
from typing import Optional, Tuple, Callable


def render_empty_state(
    icon: str,
    title: str,
    description: str,
    primary_action: Optional[Tuple[str, str]] = None,
    secondary_action: Optional[Tuple[str, Callable]] = None,
    help_link: Optional[Tuple[str, str]] = None
) -> None:
    """
    Render a friendly empty state with illustration and CTAs.

    Args:
        icon: Emoji or icon to display
        title: Main heading
        description: Helpful description text
        primary_action: Tuple of (label, page_path) for primary button
        secondary_action: Tuple of (label, callback) for secondary button
        help_link: Tuple of (text, url) for help documentation
    """
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 48px 24px; background: #f8f9fa; border-radius: 12px; margin: 24px 0;">
                <div style="font-size: 64px; margin-bottom: 16px;">{icon}</div>
                <h3 style="margin-bottom: 12px; color: #2D7F3E;">{title}</h3>
                <p style="color: #616161; max-width: 400px; margin: 0 auto 24px auto;">{description}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Actions row
        if primary_action or secondary_action:
            action_cols = st.columns(2 if secondary_action else 1)

            if primary_action:
                with action_cols[0]:
                    label, page_path = primary_action
                    st.page_link(page_path, label=label, icon="🚀", use_container_width=True)

            if secondary_action:
                with action_cols[1]:
                    label, callback = secondary_action
                    if st.button(label, use_container_width=True, key=f"empty_state_{label}"):
                        callback()

        if help_link:
            text, url = help_link
            st.markdown(
                f'<p style="text-align: center; margin-top: 16px;"><a href="{url}" target="_blank">{text}</a></p>',
                unsafe_allow_html=True
            )


def render_no_data_state() -> None:
    """Render empty state for no data imported yet."""
    render_empty_state(
        icon="📊",
        title="No Data Yet",
        description="Import your first golf session to start tracking your progress and get AI-powered insights.",
        primary_action=("Import Your First Session", "pages/1_📥_Data_Import.py"),
        help_link=("Learn how to import data", "#")
    )


def render_no_sessions_state() -> None:
    """Render empty state for no sessions found."""
    render_empty_state(
        icon="🗓️",
        title="No Sessions Found",
        description="You haven't imported any practice sessions yet. Start by importing data from your Uneekor reports.",
        primary_action=("Go to Import", "pages/1_📥_Data_Import.py")
    )


def render_no_shots_for_filter_state(filter_type: str = "filter") -> None:
    """
    Render empty state when filters return no results.

    Args:
        filter_type: Description of what was filtered (e.g., "club", "date range")
    """
    render_empty_state(
        icon="🔍",
        title="No Shots Found",
        description=f"No shots match your current {filter_type}. Try adjusting your filters or selecting a different option.",
        secondary_action=("Clear Filters", lambda: st.rerun())
    )


def render_no_club_data_state(club_name: str) -> None:
    """
    Render empty state for a specific club with no data.

    Args:
        club_name: Name of the club
    """
    render_empty_state(
        icon="🏌️",
        title=f"No {club_name} Data",
        description=f"You haven't recorded any shots with {club_name} yet. Hit some shots and import your session!",
        primary_action=("Import Session", "pages/1_📥_Data_Import.py")
    )


def render_error_state(
    title: str = "Something went wrong",
    description: str = "An error occurred while loading your data.",
    retry_callback: Optional[Callable] = None,
    error_details: Optional[str] = None
) -> None:
    """
    Render an error state with optional retry.

    Args:
        title: Error title
        description: Error description
        retry_callback: Optional callback function for retry button
        error_details: Optional technical error details
    """
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 48px 24px; background: #fff3e0; border-radius: 12px; margin: 24px 0; border: 1px solid #ffcc02;">
                <div style="font-size: 64px; margin-bottom: 16px;">⚠️</div>
                <h3 style="margin-bottom: 12px; color: #e65100;">{title}</h3>
                <p style="color: #616161; max-width: 400px; margin: 0 auto;">{description}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if retry_callback:
            if st.button("🔄 Try Again", use_container_width=True, type="primary"):
                retry_callback()

        if error_details:
            with st.expander("Technical Details"):
                st.code(error_details)


def render_ai_unavailable_state() -> None:
    """Render empty state when AI coach is not available."""
    render_empty_state(
        icon="🤖",
        title="AI Coach Unavailable",
        description="The AI coach needs to be configured before you can chat. Check that your API key is set correctly.",
        help_link=("View Setup Guide", "SETUP_GUIDE.md")
    )


def render_comparison_empty_state() -> None:
    """Render empty state for session comparison with no sessions selected."""
    render_empty_state(
        icon="⚖️",
        title="Select Sessions to Compare",
        description="Choose 2-3 sessions from the sidebar to see how your performance has changed over time.",
    )


def render_section_empty_state(
    section_name: str,
    reason: str = "No data available"
) -> None:
    """
    Render a compact empty state for a specific section.

    Args:
        section_name: Name of the section
        reason: Reason for empty state
    """
    st.info(f"**{section_name}**: {reason}")
