"""
Date range filter component and DataFrame filtering helper.
"""

from datetime import date, timedelta
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

from utils.date_helpers import parse_session_date


def filter_by_date_range(
    df: pd.DataFrame,
    start: Optional[date],
    end: Optional[date],
) -> pd.DataFrame:
    """Filter a DataFrame by inclusive session_date bounds.

    Args:
        df: Input DataFrame containing a session_date column.
        start: Lower bound (inclusive). None means no lower bound.
        end: Upper bound (inclusive). None means no upper bound.
    """
    if df.empty or "session_date" not in df.columns:
        return df.copy()
    if start is None and end is None:
        return df.copy()

    parsed_dates = df["session_date"].apply(parse_session_date)
    mask = pd.Series(True, index=df.index)

    if start is not None:
        mask &= parsed_dates.apply(lambda value: value is not None and value >= start)
    if end is not None:
        mask &= parsed_dates.apply(lambda value: value is not None and value <= end)

    return df.loc[mask].copy()


def _get_preset_range(
    preset: str,
    today: date,
) -> Tuple[Optional[date], Optional[date]]:
    """Return date bounds for a preset label."""
    if preset == "All Time":
        return None, None
    if preset == "This Week":
        return today - timedelta(days=6), today
    if preset == "Last 2 Weeks":
        return today - timedelta(days=13), today
    if preset == "Last Month":
        return today - timedelta(days=30), today
    if preset == "Last 3 Months":
        return today - timedelta(days=90), today
    if preset == "Custom":
        return None, None
    raise ValueError(f"Unknown date range preset: {preset}")


def render_date_range_filter(key_prefix: str) -> Tuple[Optional[date], Optional[date]]:
    """Render date range selection UI and return selected bounds."""
    preset_options = [
        "All Time",
        "This Week",
        "Last 2 Weeks",
        "Last Month",
        "Last 3 Months",
        "Custom",
    ]
    preset_key = f"{key_prefix}_date_range_preset"
    selected_preset = st.radio(
        "Date Range",
        options=preset_options,
        horizontal=True,
        key=preset_key,
        label_visibility="collapsed",
    )

    today = date.today()
    start_date, end_date = _get_preset_range(selected_preset, today)

    if selected_preset == "Custom":
        start_col, end_col = st.columns(2)
        start_key = f"{key_prefix}_date_range_custom_start"
        end_key = f"{key_prefix}_date_range_custom_end"

        if start_key not in st.session_state:
            st.session_state[start_key] = today - timedelta(days=30)
        if end_key not in st.session_state:
            st.session_state[end_key] = today

        with start_col:
            start_date = st.date_input(
                "Start Date",
                key=start_key,
            )
        with end_col:
            end_date = st.date_input(
                "End Date",
                key=end_key,
            )

        if start_date is not None and end_date is not None and start_date > end_date:
            st.warning("Start date cannot be after end date. Swapping dates.")
            start_date, end_date = end_date, start_date

    return start_date, end_date
