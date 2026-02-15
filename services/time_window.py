"""Time window filtering for shot data.

Default window is 6 months (not all-time) to focus on recent performance.
"""
from datetime import datetime, timedelta

import pandas as pd

TIME_WINDOWS = {
    "3mo": 90,
    "6mo": 180,
    "1yr": 365,
    "all": None,
}

# Display labels for UI
TIME_WINDOW_LABELS = {
    "3 months": "3mo",
    "6 months": "6mo",
    "1 year": "1yr",
    "All time": "all",
}

DEFAULT_WINDOW = "6mo"


def filter_by_window(df: pd.DataFrame, window: str = DEFAULT_WINDOW) -> pd.DataFrame:
    """Filter DataFrame to shots within the time window.

    Uses 'session_date' column if available, falls back to 'date_added'.

    Args:
        df: Shot DataFrame.
        window: Key from TIME_WINDOWS ('3mo', '6mo', '1yr', 'all').

    Returns:
        Filtered DataFrame.
    """
    if df.empty or window == "all":
        return df

    days = TIME_WINDOWS.get(window)
    if days is None:
        return df

    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    # Prefer session_date, fall back to date_added
    date_col = None
    if "session_date" in df.columns and df["session_date"].notna().any():
        date_col = "session_date"
    elif "date_added" in df.columns:
        date_col = "date_added"

    if date_col is None:
        return df

    # Convert to string comparison (YYYY-MM-DD sorts correctly)
    date_series = df[date_col].astype(str).str[:10]
    mask = (date_series >= cutoff_str) | df[date_col].isna()

    return df[mask].copy()
