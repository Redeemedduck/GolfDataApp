"""
Interactive shot table component.
"""
import streamlit as st
import pandas as pd
from typing import Optional


def render_shot_table(df: pd.DataFrame, display_cols: list = None) -> Optional[pd.Series]:
    """
    Render interactive shot data table with row selection.

    Args:
        df: DataFrame containing shot data
        display_cols: List of columns to display (uses defaults if None)

    Returns:
        Selected shot as pd.Series, or None if no selection
    """
    if display_cols is None:
        display_cols = [
            'club', 'carry', 'total', 'ball_speed', 'club_speed',
            'smash', 'back_spin', 'side_spin', 'face_angle', 'attack_angle'
        ]

    # Filter to only existing columns
    valid_cols = [c for c in display_cols if c in df.columns]

    st.write("Click a row to view details")
    event = st.dataframe(
        df[valid_cols].round(1),
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True
    )

    # Return selected shot if any
    if len(event.selection.rows) > 0:
        selected_row_index = event.selection.rows[0]
        return df.iloc[selected_row_index]

    return None
