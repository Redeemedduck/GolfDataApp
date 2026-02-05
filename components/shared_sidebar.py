"""
Unified sidebar component for consistent navigation and data source management.

This component eliminates the 70+ lines of duplicated sidebar code across pages.
"""
import streamlit as st
import golf_db
from utils.session_state import get_read_mode, set_read_mode, get_ui_mode, set_ui_mode


def render_shared_sidebar(
    show_navigation: bool = True,
    show_data_source: bool = True,
    show_sync_status: bool = True,
    show_mode_toggle: bool = False,
    current_page: str = None
) -> None:
    """
    Render the unified sidebar with all standard sections.

    Args:
        show_navigation: Show navigation links
        show_data_source: Show data source selector
        show_sync_status: Show database sync status
        show_mode_toggle: Show simple/advanced mode toggle
        current_page: Current page name for active state highlighting
    """
    with st.sidebar:
        if show_mode_toggle:
            render_mode_toggle()
            st.divider()

        if show_navigation:
            render_navigation(current_page)
            st.divider()

        if show_data_source:
            render_data_source()

        if show_sync_status:
            render_sync_status()

        render_appearance_toggle()


def render_navigation(current_page: str = None) -> None:
    """
    Render consistent navigation links with active state.

    Args:
        current_page: Name of current page to highlight
    """
    st.header("Navigation")

    pages = [
        ("pages/1_📥_Data_Import.py", "Import Data", "📥"),
        ("pages/2_📊_Dashboard.py", "Dashboard", "📊"),
        ("pages/5_🔄_Session_Compare.py", "Compare Sessions", "🔄"),
        ("pages/3_🗄️_Database_Manager.py", "Manage Data", "🗄️"),
        ("pages/4_🤖_AI_Coach.py", "AI Coach", "🤖"),
    ]

    for page_path, label, icon in pages:
        # Determine if this is the current page
        is_current = current_page and current_page.lower() in page_path.lower()

        if is_current:
            st.markdown(f"**{icon} {label}** ←")
        else:
            st.page_link(page_path, label=f"{icon} {label}")


def render_data_source() -> None:
    """Render data source selector using namespaced session state."""
    st.header("Data Source")

    read_mode = get_read_mode()

    read_mode_options = {
        "Auto (SQLite first)": "auto",
        "SQLite": "sqlite",
        "Supabase": "supabase"
    }

    # Find current index
    current_index = list(read_mode_options.values()).index(read_mode) if read_mode in read_mode_options.values() else 0

    selected_label = st.selectbox(
        "Read Mode",
        list(read_mode_options.keys()),
        index=current_index,
        help="Auto uses SQLite when available and falls back to Supabase if empty.",
        key="shared_sidebar_read_mode"
    )

    selected_mode = read_mode_options[selected_label]
    if selected_mode != read_mode:
        set_read_mode(selected_mode)
        st.rerun()


def render_sync_status() -> None:
    """Render database connection and sync status."""
    st.info(f"📌 Data Source: {golf_db.get_read_source()}")

    sync_status = golf_db.get_sync_status()
    counts = sync_status["counts"]

    st.caption(f"SQLite shots: {counts['sqlite']}")

    if golf_db.supabase:
        st.caption(f"Supabase shots: {counts['supabase']}")
        if sync_status["drift_exceeds"]:
            st.warning(f"⚠️ SQLite/Supabase drift: {sync_status['drift']} shots")
    else:
        st.caption("Supabase: Not configured")


def render_mode_toggle() -> None:
    """Render simple/advanced mode toggle."""
    current_mode = get_ui_mode()

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Simple",
            use_container_width=True,
            type="primary" if current_mode == "simple" else "secondary",
            key="mode_simple_btn"
        ):
            set_ui_mode("simple")
            st.rerun()

    with col2:
        if st.button(
            "Advanced",
            use_container_width=True,
            type="primary" if current_mode == "advanced" else "secondary",
            key="mode_advanced_btn"
        ):
            set_ui_mode("advanced")
            st.rerun()

    if current_mode == "simple":
        st.caption("Showing key metrics only")
    else:
        st.caption("Showing all metrics and options")


def render_appearance_toggle() -> None:
    """Render appearance controls."""
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = False

    st.divider()
    st.subheader("Appearance")

    current_mode = st.session_state.get("dark_mode", False)
    dark_mode = st.toggle(
        "Dark Mode",
        value=current_mode,
        key="dark_mode_toggle"
    )

    if dark_mode != current_mode:
        st.session_state["dark_mode"] = dark_mode
        st.rerun()

    mode_label = "Dark" if st.session_state.get("dark_mode", False) else "Light"
    st.caption(f"Current mode: {mode_label}")
    st.caption("Toggle between light and dark themes")


def render_session_stats(sessions: list, shots_df) -> None:
    """
    Render session statistics in sidebar.

    Args:
        sessions: List of session dictionaries
        shots_df: DataFrame of shots
    """
    st.header("Stats")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Sessions", len(sessions) if sessions else 0)

    with col2:
        st.metric("Shots", len(shots_df) if not shots_df.empty else 0)

    if not shots_df.empty and 'club' in shots_df.columns:
        st.metric("Clubs", shots_df['club'].nunique())


def render_documentation_links() -> None:
    """Render documentation links."""
    st.header("Documentation")
    st.markdown("""
    - [README](README.md)
    - [Setup Guide](SETUP_GUIDE.md)
    - [Roadmap](IMPROVEMENT_ROADMAP.md)
    """)
