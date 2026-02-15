"""Practice planner — generate structured practice plans from shot data.

Adapted from scripts/practice_planner.py for DataFrame input.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from statistics import stdev

import pandas as pd

_BAG_PATH = Path(__file__).resolve().parents[2] / "my_bag.json"
EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
MIN_CARRY = 10.0

# Weakness detection thresholds
SIDE_DIST_THRESHOLD = 15.0    # yards
FACE_TO_PATH_THRESHOLD = 3.0  # degrees
STRIKE_DIST_THRESHOLD = 8.0   # mm
CARRY_CV_THRESHOLD = 0.12     # 12%
SMASH_GAP_THRESHOLD = 0.04

DRILL_MAP = {
    "face_control": {
        "name": "Face Gate Drill",
        "description": "Alignment sticks as gate, goal |face-to-path| < 2.5 deg",
        "reps": 20,
    },
    "strike_quality": {
        "name": "Centered Contact Drill",
        "description": "Foot spray on face, goal |strike_distance| < 8mm",
        "reps": 20,
    },
    "consistency": {
        "name": "Block Practice",
        "description": "Same club 20 shots, track carry CV%",
        "reps": 20,
    },
    "efficiency": {
        "name": "Smash Factor Ladder",
        "description": "70/85/100% effort, focus on strike quality",
        "reps": 15,
    },
    "accuracy": {
        "name": "Target Corridor Drill",
        "description": "+/-10 yd corridor, goal 70%+ inside",
        "reps": 15,
    },
}


def _load_smash_targets() -> dict:
    try:
        with open(_BAG_PATH) as f:
            return json.load(f).get("smash_targets", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _safe_mean(vals):
    clean = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return sum(clean) / len(clean) if clean else None


def _safe_stdev(vals):
    clean = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return stdev(clean) if len(clean) >= 2 else 0.0


def _detect_weaknesses(df: pd.DataFrame) -> list[dict]:
    """Detect weaknesses across clubs."""
    smash_targets = _load_smash_targets()
    weaknesses = []

    if "club" not in df.columns:
        return weaknesses

    for club in df["club"].dropna().unique():
        club_df = df[df["club"] == club]
        if len(club_df) < 5:
            continue

        # Face control
        if "face_to_path" in club_df.columns:
            face_abs = club_df["face_to_path"].dropna().abs().mean()
            if face_abs > FACE_TO_PATH_THRESHOLD:
                weaknesses.append({
                    "club": club, "type": "face_control",
                    "metric": f"|face-to-path| = {face_abs:.1f} deg",
                    "severity": min((face_abs - FACE_TO_PATH_THRESHOLD) / 3.0, 1.0),
                })

        # Strike quality
        if "strike_distance" in club_df.columns:
            strike_avg = club_df["strike_distance"].dropna().abs().mean()
            if strike_avg > STRIKE_DIST_THRESHOLD:
                weaknesses.append({
                    "club": club, "type": "strike_quality",
                    "metric": f"|strike_dist| = {strike_avg:.1f} mm",
                    "severity": min((strike_avg - STRIKE_DIST_THRESHOLD) / 10.0, 1.0),
                })

        # Carry consistency
        if "carry" in club_df.columns:
            carries = club_df["carry"].dropna().tolist()
            if len(carries) >= 5:
                avg = _safe_mean(carries)
                if avg and avg > 0:
                    cv = _safe_stdev(carries) / avg
                    if cv > CARRY_CV_THRESHOLD:
                        weaknesses.append({
                            "club": club, "type": "consistency",
                            "metric": f"carry CV = {cv:.1%}",
                            "severity": min((cv - CARRY_CV_THRESHOLD) / 0.10, 1.0),
                        })

        # Smash efficiency
        if "smash" in club_df.columns:
            smash_avg = club_df["smash"].dropna().mean()
            target = smash_targets.get(club, 1.33)
            gap = target - smash_avg
            if gap > SMASH_GAP_THRESHOLD:
                weaknesses.append({
                    "club": club, "type": "efficiency",
                    "metric": f"smash gap = {gap:.3f} (target {target:.2f})",
                    "severity": min(gap / 0.15, 1.0),
                })

        # Accuracy (side distance)
        if "side_distance" in club_df.columns:
            side_avg = club_df["side_distance"].dropna().abs().mean()
            if side_avg > SIDE_DIST_THRESHOLD:
                weaknesses.append({
                    "club": club, "type": "accuracy",
                    "metric": f"|side_dist| = {side_avg:.1f} yd",
                    "severity": min((side_avg - SIDE_DIST_THRESHOLD) / 15.0, 1.0),
                })

    # Sort by severity descending, take top weaknesses with club diversity
    weaknesses.sort(key=lambda w: w["severity"], reverse=True)
    return weaknesses


def generate_practice_plan(df: pd.DataFrame, duration_minutes: int = 60) -> dict:
    """Generate a structured practice plan.

    Args:
        df: Filtered shot DataFrame.
        duration_minutes: Target session length.

    Returns:
        Dict with: weaknesses, warmup, drill_blocks, cooldown, total_shots, duration.
    """
    if df.empty:
        return {"empty": True}

    # Filter
    mask = pd.Series(True, index=df.index)
    if "club" in df.columns:
        mask &= ~df["club"].isin(EXCLUDED_CLUBS)
    if "carry" in df.columns:
        mask &= (df["carry"].isna()) | (df["carry"] >= MIN_CARRY)
    df = df[mask].copy()

    if df.empty:
        return {"empty": True}

    weaknesses = _detect_weaknesses(df)

    # Select top 2-3 weaknesses with club diversity
    selected = []
    used_clubs = set()
    used_types = set()
    for w in weaknesses:
        if w["club"] not in used_clubs or w["type"] not in used_types:
            selected.append(w)
            used_clubs.add(w["club"])
            used_types.add(w["type"])
        if len(selected) >= 3:
            break

    # If not enough weaknesses, just use what we have
    if not selected and weaknesses:
        selected = weaknesses[:2]

    # Scale shots to duration
    # ~80 shots per 60 minutes
    total_target = max(30, int(80 * duration_minutes / 60))
    warmup_shots = 7
    cooldown_shots = min(15, max(10, total_target // 6))
    drill_budget = total_target - warmup_shots - cooldown_shots
    shots_per_drill = max(10, drill_budget // max(len(selected), 1))

    # Build plan
    # Warmup: mid-iron
    mid_irons = [c for c in df["club"].dropna().unique() if "Iron" in str(c) and c not in ("3 Iron", "4 Iron")]
    warmup_club = mid_irons[len(mid_irons) // 2] if mid_irons else "7 Iron"

    warmup = {
        "type": "warmup",
        "club": warmup_club,
        "shots": warmup_shots,
        "goal": "Easy swings at 70% effort, find rhythm",
    }

    drill_blocks = []
    for w in selected:
        drill_info = DRILL_MAP.get(w["type"], DRILL_MAP["consistency"])
        drill_blocks.append({
            "type": "drill",
            "club": w["club"],
            "weakness": w["type"],
            "metric": w["metric"],
            "severity": round(w["severity"], 2),
            "drill_name": drill_info["name"],
            "description": drill_info["description"],
            "shots": shots_per_drill,
        })

    cooldown = {
        "type": "game_simulation",
        "shots": cooldown_shots,
        "goal": "Random club selection, simulate on-course scenarios",
    }

    return {
        "empty": False,
        "weaknesses": [{"club": w["club"], "type": w["type"], "metric": w["metric"]} for w in selected],
        "warmup": warmup,
        "drill_blocks": drill_blocks,
        "cooldown": cooldown,
        "total_shots": warmup_shots + sum(d["shots"] for d in drill_blocks) + cooldown_shots,
        "duration": duration_minutes,
    }
