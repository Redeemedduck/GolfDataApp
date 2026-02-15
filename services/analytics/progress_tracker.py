"""Progress tracking — per-club trends over time.

Adapted from scripts/progress_tracker.py for DataFrame input.
"""
from __future__ import annotations

import math

import pandas as pd

EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
MIN_CARRY = 10.0


def _safe_mean(vals):
    clean = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return sum(clean) / len(clean) if clean else None


def compute_progress_trends(df: pd.DataFrame) -> dict:
    """Compute per-club progress trends.

    Args:
        df: Filtered shot DataFrame.

    Returns:
        Dict with:
        - clubs: list of per-club trend dicts (club, sessions, sparkline_data,
          carry_trend, direction, most_recent_avg)
        - most_improved: club name
        - needs_attention: club name
    """
    if df.empty:
        return {"clubs": [], "most_improved": None, "needs_attention": None}

    # Filter
    mask = pd.Series(True, index=df.index)
    if "club" in df.columns:
        mask &= ~df["club"].isin(EXCLUDED_CLUBS)
    if "carry" in df.columns:
        mask &= (df["carry"].isna()) | (df["carry"] >= MIN_CARRY)
    df = df[mask].copy()

    if df.empty or "club" not in df.columns or "session_id" not in df.columns:
        return {"clubs": [], "most_improved": None, "needs_attention": None}

    # Determine date column
    date_col = "session_date" if "session_date" in df.columns and df["session_date"].notna().any() else "date_added"

    club_trends = []
    for club in df["club"].dropna().unique():
        club_df = df[df["club"] == club].copy()
        if len(club_df) < 5:
            continue

        # Per-session averages
        if date_col in club_df.columns:
            club_df["_sort"] = club_df[date_col].astype(str).str[:10]
        else:
            club_df["_sort"] = club_df.index

        session_avgs = []
        for session_id, group in club_df.groupby("session_id"):
            carry_avg = group["carry"].dropna().mean() if "carry" in group.columns else None
            sort_key = group["_sort"].iloc[0] if "_sort" in group.columns else ""
            if carry_avg is not None and not math.isnan(carry_avg):
                session_avgs.append({"session_id": session_id, "sort": sort_key, "carry_avg": carry_avg})

        if len(session_avgs) < 2:
            continue

        session_avgs.sort(key=lambda x: x["sort"])
        sparkline = [round(s["carry_avg"], 1) for s in session_avgs]

        # Trend direction: compare first half avg to second half avg
        mid = len(sparkline) // 2
        first_half = _safe_mean(sparkline[:mid]) if mid > 0 else None
        second_half = _safe_mean(sparkline[mid:]) if mid < len(sparkline) else None

        if first_half is not None and second_half is not None:
            delta = second_half - first_half
            if delta > 2:
                direction = "improving"
            elif delta < -2:
                direction = "declining"
            else:
                direction = "stable"
        else:
            direction = "insufficient"
            delta = 0

        club_trends.append({
            "club": club,
            "sessions": len(session_avgs),
            "total_shots": len(club_df),
            "sparkline_data": sparkline,
            "most_recent_avg": sparkline[-1],
            "oldest_avg": sparkline[0],
            "delta": round(delta, 1) if delta else 0,
            "direction": direction,
        })

    club_trends.sort(key=lambda c: c.get("delta", 0), reverse=True)

    most_improved = club_trends[0]["club"] if club_trends and club_trends[0]["delta"] > 0 else None
    needs_attention = club_trends[-1]["club"] if club_trends and club_trends[-1]["delta"] < 0 else None

    return {
        "clubs": club_trends,
        "most_improved": most_improved,
        "needs_attention": needs_attention,
    }
