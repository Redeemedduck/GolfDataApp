"""Goal tracking component — smash factor progress toward per-club targets."""

from __future__ import annotations

from typing import Dict, Optional

import pandas as pd
import streamlit as st

from utils.bag_config import get_smash_target


def compute_goal_progress(
    avg_smash: Optional[float],
    target_smash: Optional[float],
) -> Optional[float]:
    """Compute progress toward a smash factor target as a 0-1 ratio.

    Returns None if either value is missing or target is zero.
    Clamps to [0, 1] — values exceeding the target are reported as 1.0.
    """
    if avg_smash is None or target_smash is None or target_smash <= 0:
        return None
    return min(max(avg_smash / target_smash, 0.0), 1.0)


def render_goal_tracker(
    df: pd.DataFrame,
    club_name: str,
) -> None:
    """Render a smash factor goal progress bar for the given club.

    Args:
        df: Shot data filtered to a single club.
        club_name: Canonical club name (used to look up target).
    """
    target = get_smash_target(club_name)
    if target is None:
        return

    if df is None or df.empty or "smash" not in df.columns:
        st.info("Not enough data to track smash goal.")
        return

    avg_smash = df["smash"].mean()
    progress = compute_goal_progress(avg_smash, target)
    if progress is None:
        return

    pct = int(progress * 100)

    if pct >= 100:
        color = "#00CC96"
        label = "Target met!"
    elif pct >= 85:
        color = "#FFA15A"
        label = "Almost there"
    else:
        color = "#EF553B"
        label = "Working toward target"

    st.markdown(f"**Smash Factor Goal:** {avg_smash:.3f} / {target:.2f} ({pct}%)")
    st.progress(progress, text=label)
