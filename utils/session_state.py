"""
Namespaced session state helpers.

This module provides consistent access to session state with namespacing
to prevent key collisions and provide sensible defaults.
"""
import streamlit as st
from typing import Any, Optional


# Namespace prefixes
_SIDEBAR_PREFIX = "sidebar"
_UI_PREFIX = "ui"
_FILTER_PREFIX = "filter"


def _get_key(namespace: str, key: str) -> str:
    """Build namespaced key."""
    return f"{namespace}.{key}"


# =============================================================================
# Sidebar State
# =============================================================================

def get_read_mode() -> str:
    """Get current data read mode."""
    key = _get_key(_SIDEBAR_PREFIX, "read_mode")
    return st.session_state.setdefault(key, "auto")


def set_read_mode(value: str) -> None:
    """Set data read mode and clear caches."""
    import golf_db
    from services.data_access import clear_all_caches

    key = _get_key(_SIDEBAR_PREFIX, "read_mode")
    if st.session_state.get(key) != value:
        st.session_state[key] = value
        golf_db.set_read_mode(value)
        clear_all_caches()


def get_selected_session() -> Optional[str]:
    """Get currently selected session ID."""
    key = _get_key(_SIDEBAR_PREFIX, "selected_session")
    return st.session_state.get(key)


def set_selected_session(session_id: Optional[str]) -> None:
    """Set selected session ID."""
    key = _get_key(_SIDEBAR_PREFIX, "selected_session")
    st.session_state[key] = session_id


# =============================================================================
# UI Preferences State
# =============================================================================

def get_ui_mode() -> str:
    """Get UI mode (simple or advanced)."""
    key = _get_key(_UI_PREFIX, "mode")
    return st.session_state.setdefault(key, "advanced")


def set_ui_mode(mode: str) -> None:
    """Set UI mode."""
    key = _get_key(_UI_PREFIX, "mode")
    st.session_state[key] = mode


def is_simple_mode() -> bool:
    """Check if simple/beginner mode is active."""
    return get_ui_mode() == "simple"


def toggle_ui_mode() -> str:
    """Toggle between simple and advanced mode. Returns new mode."""
    current = get_ui_mode()
    new_mode = "simple" if current == "advanced" else "advanced"
    set_ui_mode(new_mode)
    return new_mode


def get_dark_mode() -> bool:
    """Get dark mode preference (prepared for future use)."""
    key = _get_key(_UI_PREFIX, "dark_mode")
    return st.session_state.setdefault(key, False)


def set_dark_mode(enabled: bool) -> None:
    """Set dark mode preference."""
    key = _get_key(_UI_PREFIX, "dark_mode")
    st.session_state[key] = enabled


# =============================================================================
# Filter State
# =============================================================================

def get_selected_clubs() -> list:
    """Get currently selected clubs for filtering."""
    key = _get_key(_FILTER_PREFIX, "clubs")
    return st.session_state.get(key, [])


def set_selected_clubs(clubs: list) -> None:
    """Set selected clubs filter."""
    key = _get_key(_FILTER_PREFIX, "clubs")
    st.session_state[key] = clubs


def get_date_range() -> tuple:
    """Get selected date range filter."""
    key = _get_key(_FILTER_PREFIX, "date_range")
    return st.session_state.get(key, (None, None))


def set_date_range(start, end) -> None:
    """Set date range filter."""
    key = _get_key(_FILTER_PREFIX, "date_range")
    st.session_state[key] = (start, end)


# =============================================================================
# Generic State Helpers
# =============================================================================

def get_state(namespace: str, key: str, default: Any = None) -> Any:
    """Get value from namespaced session state."""
    full_key = _get_key(namespace, key)
    return st.session_state.get(full_key, default)


def set_state(namespace: str, key: str, value: Any) -> None:
    """Set value in namespaced session state."""
    full_key = _get_key(namespace, key)
    st.session_state[full_key] = value


def init_state(namespace: str, key: str, default: Any) -> Any:
    """Initialize namespaced state if not set, return current value."""
    full_key = _get_key(namespace, key)
    return st.session_state.setdefault(full_key, default)
