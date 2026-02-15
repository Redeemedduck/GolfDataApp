"""Data quality filtering: hard caps + z-score outlier detection.

Two-layer filtering approach:
  Layer 1 — Hard caps per club from my_bag.json (catches impossible shots)
  Layer 2 — Per-club z-score > 3 (catches statistical outliers)

Universal guards catch extreme smash factors and tiny carry values.
"""
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

_BAG_CONFIG_PATH = Path(__file__).resolve().parent.parent / "my_bag.json"

# Fallback caps if my_bag.json is missing
_DEFAULT_CAP = 400


def _load_carry_caps() -> dict:
    """Load per-club carry caps from my_bag.json."""
    try:
        with open(_BAG_CONFIG_PATH) as f:
            config = json.load(f)
        return config.get("carry_caps", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def compute_carry_caps() -> dict:
    """Return carry cap dict from my_bag.json, keyed by canonical club name."""
    return _load_carry_caps()


def filter_outliers(df: pd.DataFrame, method: str = "caps+zscore") -> pd.DataFrame:
    """Filter outlier shots from a DataFrame.

    Args:
        df: Shot DataFrame with at least 'club' and 'carry' columns.
        method: Filtering method — 'caps', 'zscore', or 'caps+zscore' (default).

    Returns:
        DataFrame with outliers removed.
    """
    if df.empty:
        return df

    mask = pd.Series(True, index=df.index)

    # Universal guards (always applied)
    if "carry" in df.columns:
        mask &= (df["carry"].isna()) | (df["carry"] >= 10)
    if "smash" in df.columns:
        mask &= (df["smash"].isna()) | ((df["smash"] >= 0.3) & (df["smash"] <= 2.0))

    if method in ("caps", "caps+zscore"):
        mask &= _apply_hard_caps(df)

    if method in ("zscore", "caps+zscore"):
        mask &= _apply_zscore(df)

    return df[mask].copy()


def _apply_hard_caps(df: pd.DataFrame) -> pd.Series:
    """Return boolean mask: True = passes hard cap check."""
    caps = _load_carry_caps()
    if not caps or "carry" not in df.columns or "club" not in df.columns:
        return pd.Series(True, index=df.index)

    mask = pd.Series(True, index=df.index)
    for club, cap in caps.items():
        club_mask = df["club"] == club
        if club_mask.any():
            mask.loc[club_mask] = (
                df.loc[club_mask, "carry"].isna() | (df.loc[club_mask, "carry"] <= cap)
            )

    # Catch any club not in caps dict with a generous default
    known_clubs = set(caps.keys())
    unknown_mask = ~df["club"].isin(known_clubs)
    if unknown_mask.any():
        mask.loc[unknown_mask] = (
            df.loc[unknown_mask, "carry"].isna() | (df.loc[unknown_mask, "carry"] <= _DEFAULT_CAP)
        )

    return mask


def _apply_zscore(df: pd.DataFrame, threshold: float = 3.0) -> pd.Series:
    """Return boolean mask: True = passes z-score check (per club)."""
    if "carry" not in df.columns or "club" not in df.columns:
        return pd.Series(True, index=df.index)

    mask = pd.Series(True, index=df.index)

    for club in df["club"].dropna().unique():
        club_idx = df.index[df["club"] == club]
        carry = df.loc[club_idx, "carry"].dropna()

        if len(carry) < 5:
            continue

        mean = carry.mean()
        std = carry.std()
        if std == 0 or pd.isna(std):
            continue

        z_scores = ((carry - mean) / std).abs()
        outlier_idx = z_scores[z_scores > threshold].index
        mask.loc[outlier_idx] = False

    return mask


def get_outlier_summary(df: pd.DataFrame) -> dict:
    """Return counts of outliers that would be removed.

    Args:
        df: Unfiltered shot DataFrame.

    Returns:
        Dict with 'total_removed', 'by_caps', 'by_zscore', 'by_universal'.
    """
    if df.empty:
        return {"total_removed": 0, "by_caps": 0, "by_zscore": 0, "by_universal": 0}

    total = len(df)

    # Universal
    universal_mask = pd.Series(True, index=df.index)
    if "carry" in df.columns:
        universal_mask &= (df["carry"].isna()) | (df["carry"] >= 10)
    if "smash" in df.columns:
        universal_mask &= (df["smash"].isna()) | ((df["smash"] >= 0.3) & (df["smash"] <= 2.0))
    by_universal = (~universal_mask).sum()

    # Caps
    caps_mask = _apply_hard_caps(df)
    by_caps = (~caps_mask).sum()

    # Z-score
    zscore_mask = _apply_zscore(df)
    by_zscore = (~zscore_mask).sum()

    # Combined
    combined_mask = universal_mask & caps_mask & zscore_mask
    total_removed = (~combined_mask).sum()

    return {
        "total_removed": int(total_removed),
        "by_caps": int(by_caps),
        "by_zscore": int(by_zscore),
        "by_universal": int(by_universal),
    }
