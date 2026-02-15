"""Executive summary analytics — pure computation on DataFrames.

Adapted from scripts/executive_summary.py for use in Streamlit dashboard.
Returns structured dicts instead of text reports.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import stdev
from typing import Any

import pandas as pd

_BAG_PATH = Path(__file__).resolve().parents[2] / "my_bag.json"
EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
MIN_CARRY = 10.0

# Quality score weights (same as weekly_digest.py)
W_SMASH = 0.35
W_FACE = 0.30
W_STRIKE = 0.25
W_CARRY_CV = 0.10


def _load_smash_targets() -> dict:
    try:
        with open(_BAG_PATH) as f:
            data = json.load(f)
        return data.get("smash_targets", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _safe_mean(values):
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return sum(vals) / len(vals) if vals else None


def _safe_stdev(values):
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return stdev(vals) if len(vals) >= 2 else 0.0


def _normalize_lower(value, best, worst):
    if value is None:
        return 0.5
    if value <= best:
        return 1.0
    if value >= worst:
        return 0.0
    return (worst - value) / (worst - best)


def _normalize_higher(value, floor, ceiling):
    if value is None:
        return 0.5
    if value <= floor:
        return 0.0
    if value >= ceiling:
        return 1.0
    return (value - floor) / (ceiling - floor)


def _quality_score(carries, smash_vals, face_vals, strike_vals):
    """Compute quality score 0-100."""
    smash_avg = _safe_mean(smash_vals)
    face_abs_avg = _safe_mean([abs(v) for v in face_vals if v is not None])
    strike_abs_avg = _safe_mean([abs(v) for v in strike_vals if v is not None])

    carry_cv = None
    carry_list = [c for c in carries if c is not None]
    if len(carry_list) >= 2:
        carry_avg = _safe_mean(carry_list)
        if carry_avg and carry_avg > 0:
            carry_cv = _safe_stdev(carry_list) / carry_avg

    smash_c = _normalize_higher(smash_avg, 1.05, 1.45)
    face_c = _normalize_lower(face_abs_avg, 0.5, 6.0)
    strike_c = _normalize_lower(strike_abs_avg, 3.0, 15.0)
    carry_c = _normalize_lower(carry_cv, 0.06, 0.28)

    score = (W_SMASH * smash_c + W_FACE * face_c + W_STRIKE * strike_c + W_CARRY_CV * carry_c) * 100
    return round(max(0, min(100, score)), 1)


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


def _rate_metric(label, value):
    """Rate as Good/Fair/Poor."""
    if value is None:
        return "N/A"
    if label == "face":
        return "Good" if abs(value) <= 2.0 else ("Fair" if abs(value) <= 4.0 else "Poor")
    if label == "path":
        return "Good" if abs(value) <= 2.0 else ("Fair" if abs(value) <= 4.0 else "Poor")
    if label == "strike":
        return "Good" if value <= 6.0 else ("Fair" if value <= 12.0 else "Poor")
    return "N/A"


def compute_executive_summary(df: pd.DataFrame) -> dict:
    """Compute executive summary from a shot DataFrame.

    Args:
        df: Filtered shot DataFrame with standard columns.

    Returns:
        Dict with keys: overview, big3, top_clubs, bottom_clubs,
        quality_score, grade, strengths, weaknesses, actions.
    """
    if df.empty:
        return {"empty": True}

    # Filter excluded clubs and low carry
    mask = pd.Series(True, index=df.index)
    if "club" in df.columns:
        mask &= ~df["club"].isin(EXCLUDED_CLUBS)
    if "carry" in df.columns:
        mask &= (df["carry"].isna()) | (df["carry"] >= MIN_CARRY)
    df = df[mask].copy()

    if df.empty:
        return {"empty": True}

    smash_targets = _load_smash_targets()

    # Overview
    total_shots = len(df)
    clubs = sorted(df["club"].dropna().unique().tolist()) if "club" in df.columns else []
    sessions = df["session_id"].nunique() if "session_id" in df.columns else 0

    # Big 3
    face_vals = df["face_to_path"].dropna().tolist() if "face_to_path" in df.columns else []
    path_vals = df["club_path"].dropna().tolist() if "club_path" in df.columns else []
    strike_vals = df["strike_distance"].dropna().tolist() if "strike_distance" in df.columns else []

    avg_abs_face = _safe_mean([abs(v) for v in face_vals]) if face_vals else None
    avg_path = _safe_mean(path_vals) if path_vals else None
    avg_abs_strike = _safe_mean([abs(v) for v in strike_vals]) if strike_vals else None

    big3 = {
        "face_to_path": {"value": avg_abs_face, "rating": _rate_metric("face", avg_abs_face)},
        "club_path": {"value": avg_path, "rating": _rate_metric("path", avg_path)},
        "strike_distance": {"value": avg_abs_strike, "rating": _rate_metric("strike", avg_abs_strike)},
    }

    # Club stats with composite scoring
    club_stats = []
    if "club" in df.columns:
        for club in df["club"].dropna().unique():
            club_df = df[df["club"] == club]
            if len(club_df) < 5:
                continue

            carry_vals = club_df["carry"].dropna().tolist() if "carry" in club_df.columns else []
            carry_avg = _safe_mean(carry_vals) or 0
            carry_std = _safe_stdev(carry_vals)
            smash_vals = club_df["smash"].dropna().tolist() if "smash" in club_df.columns else []
            smash_avg = _safe_mean(smash_vals)
            target = smash_targets.get(club, 1.33)

            face = club_df["face_to_path"].dropna().tolist() if "face_to_path" in club_df.columns else []
            face_abs_avg = _safe_mean([abs(v) for v in face]) if face else None

            # Composite: smash vs target (40%) + carry consistency (30%) + face control (30%)
            smash_c = _normalize_lower(abs(smash_avg - target) if smash_avg else None, 0, 0.2)
            carry_cv = (carry_std / carry_avg) if carry_avg > 0 else 1.0
            carry_c = _normalize_lower(carry_cv, 0.03, 0.20)
            face_c = _normalize_lower(face_abs_avg, 0.5, 5.0)
            composite = round((0.40 * smash_c + 0.30 * carry_c + 0.30 * face_c) * 100, 1)

            club_stats.append({
                "club": club,
                "shots": len(club_df),
                "carry_avg": round(carry_avg, 1),
                "smash_avg": round(smash_avg, 3) if smash_avg else None,
                "smash_target": target,
                "face_abs_avg": round(face_abs_avg, 2) if face_abs_avg else None,
                "composite": composite,
            })

    club_stats.sort(key=lambda c: c["composite"], reverse=True)

    # Quality score
    carries = df["carry"].dropna().tolist() if "carry" in df.columns else []
    smash = df["smash"].dropna().tolist() if "smash" in df.columns else []
    score = _quality_score(carries, smash, face_vals, strike_vals)

    # Strengths / Weaknesses / Actions
    smash_avg = _safe_mean(smash)
    strengths = []
    weaknesses = []
    actions = []

    if smash_avg and smash_avg >= 1.30:
        strengths.append(f"Strong smash factor ({smash_avg:.3f})")
    if avg_abs_face is not None and avg_abs_face <= 2.5:
        strengths.append(f"Excellent face control ({avg_abs_face:.2f} deg)")
    if avg_abs_strike is not None and avg_abs_strike <= 6.0:
        strengths.append(f"Solid strike centering ({avg_abs_strike:.2f} mm)")
    if club_stats and club_stats[0]["composite"] >= 70:
        strengths.append(f"{club_stats[0]['club']} is most reliable (score {club_stats[0]['composite']:.0f})")

    if avg_abs_face is not None and avg_abs_face > 3.5:
        weaknesses.append(f"Face control needs work ({avg_abs_face:.2f} deg, target < 3.0)")
    if avg_abs_strike is not None and avg_abs_strike > 9.0:
        weaknesses.append(f"Strike centering is loose ({avg_abs_strike:.2f} mm, target < 6.0)")
    if smash_avg and smash_avg < 1.20:
        weaknesses.append(f"Low smash factor ({smash_avg:.3f})")
    if club_stats and club_stats[-1]["composite"] < 50:
        weaknesses.append(f"{club_stats[-1]['club']} is weakest (score {club_stats[-1]['composite']:.0f})")

    if avg_abs_face is not None and avg_abs_face > 3.0:
        actions.append("Run 30-ball face-to-path gate drill each session")
    if avg_abs_strike is not None and avg_abs_strike > 8.0:
        actions.append("Add centered-strike work (spray/impact tape) for 20 reps")
    if club_stats and club_stats[-1]["composite"] < 60:
        actions.append(f"Dedicate 15 min to {club_stats[-1]['club']} focusing on tempo")
    if not actions:
        actions.append("Maintain trajectory — add random-practice blocks for transfer")

    return {
        "empty": False,
        "overview": {"total_shots": total_shots, "clubs": clubs, "sessions": sessions},
        "big3": big3,
        "top_clubs": club_stats[:3],
        "bottom_clubs": list(reversed(club_stats[-3:])) if len(club_stats) >= 3 else [],
        "quality_score": score,
        "grade": _grade(score),
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "actions": actions[:3],
    }
