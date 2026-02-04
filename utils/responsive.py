"""
Responsive layout helpers for mobile-friendly UI.

Provides utilities for creating layouts that work across
desktop, tablet, and mobile viewports.

Note: Streamlit doesn't expose viewport size directly, so we use
mobile-first design with optional column expansion for desktop.
"""
import streamlit as st
from typing import List, Union


def responsive_columns(
    desktop: List[Union[int, float]],
    tablet: List[Union[int, float]] = None,
    mobile: int = 1
) -> List:
    """
    Create responsive column layout.

    Defaults to mobile-first (stacked) layout. On wider viewports,
    Streamlit's st.columns() provides basic responsiveness.

    Args:
        desktop: Column spec for desktop (e.g., [1, 2, 1])
        tablet: Column spec for tablet (optional, falls back to desktop)
        mobile: Number of columns for mobile (typically 1 for stacking)

    Returns:
        List of column containers from st.columns()

    Example:
        cols = responsive_columns([1, 1, 1])  # 3 equal columns on desktop
        with cols[0]:
            st.metric("Shots", 100)
    """
    # Streamlit handles basic responsiveness automatically
    # For mobile-first, we'd need JS to detect viewport
    # This is a foundation for future CSS media query enhancements
    return st.columns(desktop)


def responsive_metrics(
    metrics: List[dict],
    desktop_cols: int = 5,
    tablet_cols: int = 3,
    mobile_cols: int = 2
) -> None:
    """
    Render metrics in a responsive grid.

    Args:
        metrics: List of metric dicts with keys: label, value, delta (optional), help (optional)
        desktop_cols: Columns on desktop
        tablet_cols: Columns on tablet (not yet implemented)
        mobile_cols: Columns on mobile (not yet implemented)

    Example:
        responsive_metrics([
            {"label": "Carry", "value": "245 yds", "delta": "+5"},
            {"label": "Ball Speed", "value": "165 mph"},
        ])
    """
    # Use desktop_cols for now; true responsiveness requires CSS
    cols = st.columns(min(desktop_cols, len(metrics)))

    for i, metric in enumerate(metrics):
        col_idx = i % len(cols)
        with cols[col_idx]:
            st.metric(
                label=metric.get("label", ""),
                value=metric.get("value", ""),
                delta=metric.get("delta"),
                help=metric.get("help")
            )


def stack_on_mobile(content_blocks: List[callable], desktop_cols: int = 2) -> None:
    """
    Render content in columns on desktop, stacked on mobile.

    Args:
        content_blocks: List of functions that render content
        desktop_cols: Number of columns on desktop

    Example:
        stack_on_mobile([
            lambda: st.write("Block 1"),
            lambda: st.write("Block 2"),
        ])
    """
    cols = st.columns(desktop_cols)

    for i, render_fn in enumerate(content_blocks):
        with cols[i % desktop_cols]:
            render_fn()


def add_responsive_css() -> None:
    """
    Inject CSS for enhanced mobile responsiveness.

    Call this once at the top of pages that need extra mobile optimization.
    """
    css = """
    <style>
    /* Mobile-first responsive adjustments */
    @media (max-width: 768px) {
        /* Stack columns on mobile */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }

        /* Reduce padding on mobile */
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        /* Adjust metric cards */
        [data-testid="metric-container"] {
            padding: 0.5rem !important;
        }

        /* Ensure touch targets are at least 44px */
        button, .stButton > button {
            min-height: 44px;
        }

        /* Improve chart readability on small screens */
        .js-plotly-plot {
            max-width: 100% !important;
        }
    }

    /* Tablet adjustments */
    @media (min-width: 769px) and (max-width: 1024px) {
        .block-container {
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
    }

    /* Hide sidebar toggle text on mobile */
    @media (max-width: 640px) {
        [data-testid="collapsedControl"] span {
            display: none;
        }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def get_layout_size() -> str:
    """
    Get estimated layout size based on Streamlit config.

    Returns:
        "wide" or "centered"

    Note: This doesn't detect actual viewport size.
    """
    # Streamlit doesn't expose this directly
    # This is a placeholder for future viewport detection
    return "wide"


def create_card_grid(
    items: List[dict],
    cols: int = 3,
    render_card: callable = None
) -> None:
    """
    Create a grid of cards.

    Args:
        items: List of item data to render
        cols: Number of columns
        render_card: Function to render each card, receives item dict

    Example:
        create_card_grid(
            [{"title": "Session 1"}, {"title": "Session 2"}],
            cols=3,
            render_card=lambda item: st.write(item["title"])
        )
    """
    if not render_card:
        def render_card(item):
            st.write(item)

    columns = st.columns(cols)

    for i, item in enumerate(items):
        with columns[i % cols]:
            render_card(item)
