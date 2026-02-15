"""Session quality grading — A-F grades per session.

Adapted from scripts/session_quality_scorer.py for DataFrame input.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean, stdev

import pandas as pd

_BAG_PATH = Path(__file__).resolve().parents[2] / "my_bag.json"
EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
MIN_CARRY = 10.0

WEIGHTS = {
    "carry": 0.30,
    "smash": 0.20,
    "face": 0.20,
    "strike": 0.15,
    "path": 0.15,
}


def _load_smash_targets() -> dict:
    try:
        with open(_BAG_PATH) as f:
            return json.load(f).get("smash_targets", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _safe_mean(vals):
    clean = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return mean(clean) if clean else None


def _safe_stdev(vals):
    clean = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return stdev(clean) if len(clean) >= 2 else 0.0


def _normalize_lower(value, best, worst):
    if value is None:
        return 0.5
    return max(0, min(1, (worst - value) / (worst - best))) if worst != best else 0.5


def _normalize_higher(value, floor, ceiling):
    if value is None:
        return 0.5
    return max(0, min(1, (value - floor) / (ceiling - floor))) if ceiling != floor else 0.5


def _grade(score):
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def compute_session_grades(df: pd.DataFrame) -> list[dict]:
    """Grade each session in the DataFrame.

    Args:
        df: Filtered shot DataFrame with session_id, session_date, etc.

    Returns:
        List of dicts sorted by date (newest first), each with:
        session_id, session_date, shot_count, scores (carry, smash, face, strike, path),
        total_score (0-100), grade (A-F).
    """
    if df.empty or "session_id" not in df.columns:
        return []

    # Filter
    mask = pd.Series(True, index=df.index)
    if "club" in df.columns:
        mask &= ~df["club"].isin(EXCLUDED_CLUBS)
    if "carry" in df.columns:
        mask &= (df["carry"].isna()) | (df["carry"] >= MIN_CARRY)
    df = df[mask].copy()

    if df.empty:
        return []

    smash_targets = _load_smash_targets()
    results = []

    for session_id, group in df.groupby("session_id"):
        if len(group) < 3:
            continue

        # Carry consistency
        carries = group["carry"].dropna().tolist() if "carry" in group.columns else []
        carry_avg = _safe_mean(carries)
        carry_cv = (_safe_stdev(carries) / carry_avg) if carry_avg and carry_avg > 0 else None
        carry_score = _normalize_lower(carry_cv, 0.03, 0.20)

        # Smash vs target
        smash_deviations = []
        if "smash" in group.columns and "club" in group.columns:
            for _, row in group.iterrows():
                smash = row.get("smash")
                club = row.get("club")
                if smash is not None and not (isinstance(smash, float) and math.isnan(smash)):
                    target = smash_targets.get(club, 1.33)
                    smash_deviations.append(abs(smash - target))
        smash_dev_avg = _safe_mean(smash_deviations)
        smash_score = _normalize_lower(smash_dev_avg, 0.0, 0.20)

        # Face angle control
        face_vals = group["face_to_path"].dropna().tolist() if "face_to_path" in group.columns else []
        face_abs = _safe_mean([abs(v) for v in face_vals]) if face_vals else None
        face_score = _normalize_lower(face_abs, 0.5, 5.0)

        # Strike centering
        strike_vals = group["strike_distance"].dropna().tolist() if "strike_distance" in group.columns else []
        strike_abs = _safe_mean([abs(v) for v in strike_vals]) if strike_vals else None
        strike_score = _normalize_lower(strike_abs, 3.0, 20.0)

        # Club path neutrality
        path_vals = group["club_path"].dropna().tolist() if "club_path" in group.columns else []
        path_abs = _safe_mean([abs(v) for v in path_vals]) if path_vals else None
        path_score = _normalize_lower(path_abs, 0.8, 6.0)

        # Weighted total
        total = (
            WEIGHTS["carry"] * carry_score
            + WEIGHTS["smash"] * smash_score
            + WEIGHTS["face"] * face_score
            + WEIGHTS["strike"] * strike_score
            + WEIGHTS["path"] * path_score
        ) * 100
        total = round(max(0, min(100, total)), 1)

        session_date = None
        if "session_date" in group.columns:
            dates = group["session_date"].dropna()
            if len(dates) > 0:
                session_date = str(dates.iloc[0])[:10]

        results.append({
            "session_id": session_id,
            "session_date": session_date,
            "shot_count": len(group),
            "scores": {
                "carry": round(carry_score * 100, 1),
                "smash": round(smash_score * 100, 1),
                "face": round(face_score * 100, 1),
                "strike": round(strike_score * 100, 1),
                "path": round(path_score * 100, 1),
            },
            "total_score": total,
            "grade": _grade(total),
        })

    results.sort(key=lambda r: r["session_date"] or "", reverse=True)

    # Trajectory detection
    if len(results) >= 3:
        recent_scores = [r["total_score"] for r in results[:5]]
        first_half = _safe_mean(recent_scores[len(recent_scores) // 2:])
        second_half = _safe_mean(recent_scores[:len(recent_scores) // 2 + 1])
        if first_half is not None and second_half is not None:
            diff = second_half - first_half
            if diff > 2:
                trajectory = "IMPROVING"
            elif diff < -2:
                trajectory = "DECLINING"
            else:
                trajectory = "FLAT"
        else:
            trajectory = "INSUFFICIENT DATA"
    else:
        trajectory = "INSUFFICIENT DATA"

    # Attach trajectory to first result for easy access
    for r in results:
        r["trajectory"] = trajectory

    return results
