"""Shot-by-shot navigator component with prev/next controls."""

from __future__ import annotations

import streamlit as st
import pandas as pd


def clamp_index(idx: int, total: int) -> int:
    """Clamp *idx* to the range [0, total - 1].

    Args:
        idx: Requested index.
        total: Total number of items (must be >= 1).

    Returns:
        Clamped index within bounds.
    """
    if total <= 0:
        return 0
    return max(0, min(idx, total - 1))


def render_shot_navigator(
    df: pd.DataFrame,
    key_prefix: str = "shot_nav",
) -> int | None:
    """Render prev/next shot navigation controls.

    Displays the current shot index, total shots, and prev/next buttons.
    Stores the selected index in ``st.session_state[key_prefix + '_idx']``.

    Args:
        df: DataFrame of shots to navigate.
        key_prefix: Unique key prefix to avoid widget collisions.

    Returns:
        The currently selected row index, or ``None`` if the DataFrame is empty.
    """
    if df is None or df.empty:
        st.info("No shots to navigate.")
        return None

    total = len(df)
    state_key = f"{key_prefix}_idx"

    if state_key not in st.session_state:
        st.session_state[state_key] = 0

    current = clamp_index(st.session_state[state_key], total)

    col_prev, col_label, col_next = st.columns([1, 2, 1])

    with col_prev:
        if st.button("← Prev", key=f"{key_prefix}_prev", disabled=(current <= 0)):
            current = clamp_index(current - 1, total)
            st.session_state[state_key] = current
            st.rerun()

    with col_label:
        st.markdown(
            f"<div style='text-align:center; padding-top:6px;'>"
            f"Shot {current + 1} of {total}"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_next:
        if st.button("Next →", key=f"{key_prefix}_next", disabled=(current >= total - 1)):
            current = clamp_index(current + 1, total)
            st.session_state[state_key] = current
            st.rerun()

    return current
