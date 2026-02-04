"""
Loading state components for better UX during data fetches.

Provides skeleton loaders, spinners, and progress indicators
to prevent the app from appearing frozen.
"""
import streamlit as st
from typing import Optional


def render_skeleton_card(
    width: str = "100%",
    height: str = "120px",
    count: int = 1,
    key_prefix: str = "skeleton"
) -> None:
    """
    Render pulsing placeholder cards during data load.

    Args:
        width: Card width (CSS value)
        height: Card height (CSS value)
        count: Number of skeleton cards to render
        key_prefix: Unique key prefix for multiple skeletons
    """
    skeleton_css = f"""
    <style>
    @keyframes skeleton-pulse {{
        0% {{ background-color: #e0e0e0; }}
        50% {{ background-color: #f0f0f0; }}
        100% {{ background-color: #e0e0e0; }}
    }}
    .skeleton-card {{
        width: {width};
        height: {height};
        border-radius: 8px;
        animation: skeleton-pulse 1.5s ease-in-out infinite;
        margin-bottom: 8px;
    }}
    </style>
    """

    st.markdown(skeleton_css, unsafe_allow_html=True)

    for i in range(count):
        st.markdown(
            f'<div class="skeleton-card" id="{key_prefix}-{i}"></div>',
            unsafe_allow_html=True
        )


def render_skeleton_metrics(count: int = 5) -> None:
    """
    Render skeleton loader for a row of metric cards.

    Args:
        count: Number of metric placeholders
    """
    cols = st.columns(count)

    skeleton_css = """
    <style>
    .skeleton-metric {
        background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 4px;
        height: 80px;
    }
    @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    </style>
    """
    st.markdown(skeleton_css, unsafe_allow_html=True)

    for i, col in enumerate(cols):
        with col:
            st.markdown(
                f'<div class="skeleton-metric"></div>',
                unsafe_allow_html=True
            )


def render_skeleton_table(rows: int = 5, cols: int = 4) -> None:
    """
    Render skeleton loader for a data table.

    Args:
        rows: Number of placeholder rows
        cols: Number of columns
    """
    skeleton_css = """
    <style>
    .skeleton-row {
        display: flex;
        gap: 8px;
        margin-bottom: 8px;
    }
    .skeleton-cell {
        flex: 1;
        height: 32px;
        background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 4px;
    }
    </style>
    """
    st.markdown(skeleton_css, unsafe_allow_html=True)

    for row in range(rows):
        cells = "".join(['<div class="skeleton-cell"></div>' for _ in range(cols)])
        st.markdown(f'<div class="skeleton-row">{cells}</div>', unsafe_allow_html=True)


def render_loading_spinner(message: str = "Loading...") -> None:
    """
    Render an inline spinner with message.

    Args:
        message: Loading message to display
    """
    st.spinner(message)


def render_progress_bar(
    current: int,
    total: int,
    label: str = "",
    show_percentage: bool = True
) -> None:
    """
    Render a progress indicator for long operations.

    Args:
        current: Current progress value
        total: Total value for completion
        label: Optional label for the progress bar
        show_percentage: Whether to show percentage text
    """
    if total <= 0:
        progress = 0
    else:
        progress = min(current / total, 1.0)

    if label:
        if show_percentage:
            st.caption(f"{label}: {progress * 100:.0f}%")
        else:
            st.caption(f"{label}: {current}/{total}")

    st.progress(progress)


def render_loading_placeholder(
    message: str = "Loading data...",
    submessage: str = None
) -> None:
    """
    Render a centered loading placeholder with optional submessage.

    Args:
        message: Main loading message
        submessage: Optional secondary message
    """
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 40px 0;">
                <div style="font-size: 48px; margin-bottom: 16px;">⏳</div>
                <div style="font-size: 18px; font-weight: 500; color: #424242;">{message}</div>
                {f'<div style="font-size: 14px; color: #757575; margin-top: 8px;">{submessage}</div>' if submessage else ''}
            </div>
            """,
            unsafe_allow_html=True
        )


class LoadingContext:
    """
    Context manager for showing loading state during operations.

    Usage:
        with LoadingContext("Fetching data..."):
            data = fetch_data()
    """

    def __init__(self, message: str = "Loading..."):
        self.message = message
        self.placeholder = None

    def __enter__(self):
        self.placeholder = st.empty()
        with self.placeholder:
            render_loading_placeholder(self.message)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.placeholder:
            self.placeholder.empty()
        return False

    def update(self, message: str) -> None:
        """Update the loading message."""
        if self.placeholder:
            with self.placeholder:
                render_loading_placeholder(message)
