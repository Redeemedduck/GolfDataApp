#!/usr/bin/env python3
"""Generate a single comprehensive 'state of your game' executive summary.

This is THE single report you run for a quick health check of your game.
It covers volume, Big 3, club rankings, trends, strengths, weaknesses,
and actionable recommendations -- all in one scannable text report.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import stdev
from typing import Any

EXCLUDED_CLUBS = ("Other", "Putter", "Sim Round")
MIN_CARRY = 10.0
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
DEFAULT_BAG_PATH = Path(__file__).resolve().parents[1] / "my_bag.json"

# Quality score weights (same as weekly_digest.py)
W_SMASH = 0.35
W_FACE = 0.30
W_STRIKE = 0.25
W_CARRY_CV = 0.10


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Shot:
    session_day: date
    session_id: str
    club: str
    carry: float
    smash: float | None
    face_to_path: float | None
    strike_distance: float | None
    club_path: float | None


@dataclass
class ClubStats:
    club: str
    shot_count: int = 0
    carry_avg: float = 0.0
    carry_std: float = 0.0
    smash_avg: float | None = None
    smash_target: float = 1.33
    face_abs_avg: float | None = None
    strike_abs_avg: float | None = None
    composite_score: float = 0.0


@dataclass
class PeriodSummary:
    shots: list[Shot] = field(default_factory=list)
    carry_avg: float | None = None
    smash_avg: float | None = None
    face_abs_avg: float | None = None
    strike_abs_avg: float | None = None


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def safe_stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return stdev(values)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_lower_better(value: float | None, best: float, worst: float) -> float:
    if value is None:
        return 0.5
    if value <= best:
        return 1.0
    if value >= worst:
        return 0.0
    return (worst - value) / (worst - best)


def normalize_higher_better(value: float | None, floor: float, ceiling: float) -> float:
    if value is None:
        return 0.5
    if value <= floor:
        return 0.0
    if value >= ceiling:
        return 1.0
    return (value - floor) / (ceiling - floor)


def fmt(value: float | None, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{value:.{digits}f}"


def rate_big3(label: str, value: float | None) -> str:
    """Rate a Big 3 metric as Good / Fair / Poor."""
    if value is None:
        return "N/A"
    if label == "face_to_path":
        if abs(value) <= 2.0:
            return "Good"
        if abs(value) <= 4.0:
            return "Fair"
        return "Poor"
    if label == "club_path":
        if abs(value) <= 2.0:
            return "Good"
        if abs(value) <= 4.0:
            return "Fair"
        return "Poor"
    if label == "strike_distance":
        if value <= 5.0:
            return "Good"
        if value <= 10.0:
            return "Fair"
        return "Poor"
    return "N/A"


def trend_arrow(current: float | None, previous: float | None, higher_is_better: bool) -> str:
    """Return an arrow + delta string comparing two values."""
    if current is None or previous is None:
        return "  --"
    delta = current - previous
    if abs(delta) < 0.01:
        return "  = (flat)"
    improved = delta > 0 if higher_is_better else delta < 0
    arrow = "  ^ " if improved else "  v "
    return f"{arrow}{delta:+.2f} ({'better' if improved else 'worse'})"


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def build_connection(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA query_only = ON")
    return conn


def resolve_carry_column(conn: sqlite3.Connection) -> str:
    cols = {str(row["name"]) for row in conn.execute("PRAGMA table_info(shots)").fetchall()}
    if "carry_distance" in cols:
        return "carry_distance"
    if "carry" in cols:
        return "carry"
    raise RuntimeError("shots table must contain carry_distance or carry column")


def load_smash_targets(bag_path: Path) -> dict[str, float]:
    fallback: dict[str, float] = {
        "Driver": 1.49, "3 Wood": 1.45, "7 Wood": 1.42,
        "3 Iron": 1.36, "4 Iron": 1.35, "5 Iron": 1.34,
        "6 Iron": 1.34, "7 Iron": 1.33, "8 Iron": 1.31,
        "9 Iron": 1.29, "PW": 1.24, "GW": 1.22, "SW": 1.20, "LW": 1.18,
    }
    if not bag_path.exists():
        return fallback
    try:
        with bag_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        targets = data.get("smash_targets", {})
        if isinstance(targets, dict):
            for club, val in targets.items():
                try:
                    fallback[str(club).strip()] = float(val)
                except (TypeError, ValueError):
                    continue
    except (OSError, json.JSONDecodeError):
        pass
    return fallback


def load_shots(
    conn: sqlite3.Connection,
    carry_col: str,
    start_day: date | None = None,
    end_day: date | None = None,
) -> list[Shot]:
    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    where_clauses = [
        "session_date IS NOT NULL",
        "club IS NOT NULL",
        "TRIM(club) != ''",
        f"TRIM(club) NOT IN ({placeholders})",
        f"{carry_col} IS NOT NULL",
        f"{carry_col} >= ?",
    ]
    params: list[Any] = list(EXCLUDED_CLUBS) + [MIN_CARRY]

    if start_day is not None:
        where_clauses.append("DATE(session_date) >= ?")
        params.append(start_day.isoformat())
    if end_day is not None:
        where_clauses.append("DATE(session_date) <= ?")
        params.append(end_day.isoformat())

    query = f"""
        SELECT
            DATE(session_date) AS session_day,
            COALESCE(CAST(session_id AS TEXT), '') AS session_id,
            TRIM(club) AS club,
            {carry_col} AS carry_value,
            smash,
            face_to_path,
            strike_distance,
            club_path
        FROM shots
        WHERE {' AND '.join(where_clauses)}
        ORDER BY session_day, session_id
    """
    rows = conn.execute(query, params).fetchall()

    shots: list[Shot] = []
    for row in rows:
        day_text = row["session_day"]
        if day_text is None:
            continue
        try:
            shot_day = datetime.strptime(str(day_text), "%Y-%m-%d").date()
        except ValueError:
            continue
        carry = to_float(row["carry_value"])
        if carry is None or carry < MIN_CARRY:
            continue
        club = str(row["club"]).strip()
        if not club:
            continue
        shots.append(Shot(
            session_day=shot_day,
            session_id=str(row["session_id"] or "").strip(),
            club=club,
            carry=carry,
            smash=to_float(row["smash"]),
            face_to_path=to_float(row["face_to_path"]),
            strike_distance=to_float(row["strike_distance"]),
            club_path=to_float(row["club_path"]),
        ))
    return shots


# ---------------------------------------------------------------------------
# Quality score (same formula as weekly_digest.py)
# ---------------------------------------------------------------------------

def quality_score(shots: list[Shot]) -> float:
    smash_avg = safe_mean([s.smash for s in shots if s.smash is not None])
    face_abs_avg = safe_mean([abs(s.face_to_path) for s in shots if s.face_to_path is not None])
    strike_abs_avg = safe_mean([abs(s.strike_distance) for s in shots if s.strike_distance is not None])

    carries = [s.carry for s in shots]
    carry_cv: float | None = None
    if len(carries) >= 2:
        carry_avg = safe_mean(carries)
        if carry_avg is not None and carry_avg > 0:
            carry_cv = safe_stdev(carries) / carry_avg

    smash_c = normalize_higher_better(smash_avg, floor=1.05, ceiling=1.45)
    face_c = normalize_lower_better(face_abs_avg, best=0.5, worst=6.0)
    strike_c = normalize_lower_better(strike_abs_avg, best=3.0, worst=15.0)
    carry_c = normalize_lower_better(carry_cv, best=0.06, worst=0.28)

    weighted = (
        W_SMASH * smash_c
        + W_FACE * face_c
        + W_STRIKE * strike_c
        + W_CARRY_CV * carry_c
    )
    return round(clamp(weighted * 100.0, 0.0, 100.0), 1)


def grade_for_score(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


# ---------------------------------------------------------------------------
# Club-level composite scoring
# ---------------------------------------------------------------------------

def compute_club_stats(
    shots: list[Shot],
    smash_targets: dict[str, float],
) -> list[ClubStats]:
    by_club: dict[str, list[Shot]] = defaultdict(list)
    for shot in shots:
        by_club[shot.club].append(shot)

    results: list[ClubStats] = []
    for club, club_shots in by_club.items():
        cs = ClubStats(club=club, shot_count=len(club_shots))

        carries = [s.carry for s in club_shots]
        cs.carry_avg = safe_mean(carries) or 0.0
        cs.carry_std = safe_stdev(carries)

        smash_vals = [s.smash for s in club_shots if s.smash is not None]
        cs.smash_avg = safe_mean(smash_vals)
        cs.smash_target = smash_targets.get(club, 1.33)

        face_vals = [abs(s.face_to_path) for s in club_shots if s.face_to_path is not None]
        cs.face_abs_avg = safe_mean(face_vals)

        strike_vals = [abs(s.strike_distance) for s in club_shots if s.strike_distance is not None]
        cs.strike_abs_avg = safe_mean(strike_vals)

        # Composite: smash vs target (40%) + carry consistency (30%) + face control (30%)
        smash_component = 0.5
        if cs.smash_avg is not None:
            deviation = abs(cs.smash_avg - cs.smash_target)
            smash_component = normalize_lower_better(deviation, best=0.0, worst=0.20)

        carry_cv = (cs.carry_std / cs.carry_avg) if cs.carry_avg > 0 else 1.0
        carry_component = normalize_lower_better(carry_cv, best=0.03, worst=0.20)

        face_component = normalize_lower_better(cs.face_abs_avg, best=0.5, worst=5.0)

        cs.composite_score = round(
            (0.40 * smash_component + 0.30 * carry_component + 0.30 * face_component) * 100.0,
            1,
        )
        results.append(cs)

    results.sort(key=lambda c: c.composite_score, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Period summary helper
# ---------------------------------------------------------------------------

def summarize_period(shots: list[Shot]) -> PeriodSummary:
    ps = PeriodSummary(shots=shots)
    if not shots:
        return ps
    ps.carry_avg = safe_mean([s.carry for s in shots])
    ps.smash_avg = safe_mean([s.smash for s in shots if s.smash is not None])
    ps.face_abs_avg = safe_mean([abs(s.face_to_path) for s in shots if s.face_to_path is not None])
    ps.strike_abs_avg = safe_mean([abs(s.strike_distance) for s in shots if s.strike_distance is not None])
    return ps


# ---------------------------------------------------------------------------
# Strengths / weaknesses / action items detection
# ---------------------------------------------------------------------------

def detect_strengths(
    club_stats: list[ClubStats],
    all_shots: list[Shot],
    smash_avg: float | None,
    face_abs: float | None,
    strike_abs: float | None,
) -> list[str]:
    strengths: list[str] = []

    # Check smash factor efficiency
    if smash_avg is not None and smash_avg >= 1.30:
        strengths.append(
            f"Strong smash factor ({smash_avg:.3f}) -- you transfer energy efficiently."
        )

    # Check face control
    if face_abs is not None and face_abs <= 2.5:
        strengths.append(
            f"Excellent face control (avg |face-to-path| = {face_abs:.2f} deg)."
        )

    # Check strike quality
    if strike_abs is not None and strike_abs <= 6.0:
        strengths.append(
            f"Solid strike centering (avg |strike_distance| = {strike_abs:.2f} mm)."
        )

    # Check for standout clubs
    if club_stats:
        top = club_stats[0]
        if top.composite_score >= 70:
            strengths.append(
                f"{top.club} is your most reliable club (score {top.composite_score:.0f}/100)."
            )

    # Check carry consistency
    carries = [s.carry for s in all_shots]
    if len(carries) >= 10:
        avg = safe_mean(carries)
        if avg and avg > 0:
            cv = safe_stdev(carries) / avg
            if cv <= 0.10:
                strengths.append(
                    f"Consistent carry distances (CV = {cv:.2%}) across all clubs."
                )

    return strengths[:3]


def detect_weaknesses(
    club_stats: list[ClubStats],
    all_shots: list[Shot],
    smash_avg: float | None,
    face_abs: float | None,
    strike_abs: float | None,
) -> list[str]:
    weaknesses: list[str] = []

    if face_abs is not None and face_abs > 3.5:
        weaknesses.append(
            f"Face control needs work (avg |face-to-path| = {face_abs:.2f} deg, target < 3.0)."
        )

    if strike_abs is not None and strike_abs > 9.0:
        weaknesses.append(
            f"Strike centering is loose (avg |strike_distance| = {strike_abs:.2f} mm, target < 6.0)."
        )

    if smash_avg is not None and smash_avg < 1.20:
        weaknesses.append(
            f"Low smash factor ({smash_avg:.3f}) -- energy transfer needs improvement."
        )

    # Check for inconsistent clubs
    if len(club_stats) >= 3:
        bottom = club_stats[-1]
        if bottom.composite_score < 50:
            weaknesses.append(
                f"{bottom.club} is your weakest club (score {bottom.composite_score:.0f}/100, "
                f"{bottom.shot_count} shots)."
            )

    # Check path bias
    path_vals = [s.club_path for s in all_shots if s.club_path is not None]
    if path_vals:
        avg_path = safe_mean(path_vals)
        if avg_path is not None and abs(avg_path) > 3.0:
            direction = "out-to-in" if avg_path < 0 else "in-to-out"
            weaknesses.append(
                f"Persistent {direction} path bias (avg club_path = {avg_path:+.2f} deg)."
            )

    return weaknesses[:3]


def generate_action_items(
    weaknesses: list[str],
    club_stats: list[ClubStats],
    face_abs: float | None,
    strike_abs: float | None,
    smash_avg: float | None,
) -> list[str]:
    actions: list[str] = []

    # Priority 1: face control if poor
    if face_abs is not None and face_abs > 3.0:
        actions.append(
            "PRIORITY: Run 30-ball face-to-path gate drill each session. "
            "Goal: avg |face-to-path| under 3.0 deg within 2 weeks."
        )

    # Priority 2: strike centering if poor
    if strike_abs is not None and strike_abs > 8.0:
        actions.append(
            "Add centered-strike work (spray/impact tape) for 20 reps per session. "
            "Goal: avg |strike_distance| under 7.0 mm."
        )

    # Priority 3: weakest club
    if len(club_stats) >= 3:
        bottom = club_stats[-1]
        if bottom.composite_score < 60:
            actions.append(
                f"Dedicate 15 minutes per session to {bottom.club} "
                f"(current score {bottom.composite_score:.0f}/100). "
                f"Focus on tempo and contact, not distance."
            )

    # Priority 4: smash if low
    if smash_avg is not None and smash_avg < 1.25 and len(actions) < 3:
        actions.append(
            "Add strike-first speed blocks: 10 shots at 80% effort focusing purely on "
            "center contact to lift smash factor."
        )

    # Fallback
    if not actions:
        actions.append(
            "Maintain current trajectory. Consider adding random-practice blocks "
            "(switching clubs every 3 shots) to build transfer."
        )

    return actions[:3]


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(
    db_path: Path,
    bag_path: Path,
    overall_days: int,
) -> str:
    with build_connection(db_path) as conn:
        carry_col = resolve_carry_column(conn)
        today = date.today()
        window_start = today - timedelta(days=overall_days - 1)
        all_shots = load_shots(conn, carry_col, window_start, today)

        # Also load ALL shots for overview stats (total lifetime)
        lifetime_shots = load_shots(conn, carry_col)

    if not all_shots:
        return (
            "EXECUTIVE SUMMARY\n"
            "=================\n\n"
            f"No qualifying shots found in the last {overall_days} days.\n"
            f"Database: {db_path}\n"
            "Filters: exclude Other, Putter, Sim Round | carry >= 10"
        )

    smash_targets = load_smash_targets(bag_path)

    # -- Session / date bookkeeping --
    session_keys: set[str] = set()
    session_days: set[date] = set()
    for s in all_shots:
        key = f"{s.session_day.isoformat()}::{s.session_id or 'unknown'}"
        session_keys.add(key)
        session_days.add(s.session_day)

    clubs_in_window = sorted(set(s.club for s in all_shots))

    # Lifetime counts
    lifetime_session_days = set(s.session_day for s in lifetime_shots)
    first_day = min(s.session_day for s in lifetime_shots)
    last_day = max(s.session_day for s in lifetime_shots)
    total_span_days = (last_day - first_day).days + 1

    # Practice frequency
    if total_span_days > 0:
        sessions_per_week = len(lifetime_session_days) / (total_span_days / 7.0)
    else:
        sessions_per_week = 0.0

    # -- Big 3 overall --
    face_vals = [s.face_to_path for s in all_shots if s.face_to_path is not None]
    path_vals = [s.club_path for s in all_shots if s.club_path is not None]
    strike_vals = [s.strike_distance for s in all_shots if s.strike_distance is not None]

    avg_face_to_path = safe_mean(face_vals)
    avg_abs_face = safe_mean([abs(v) for v in face_vals]) if face_vals else None
    avg_club_path = safe_mean(path_vals)
    avg_abs_path = safe_mean([abs(v) for v in path_vals]) if path_vals else None
    avg_strike = safe_mean([abs(v) for v in strike_vals]) if strike_vals else None

    # -- Club stats --
    club_stats = compute_club_stats(all_shots, smash_targets)

    # -- Recent trend: last 30 days vs prior 30 days --
    mid_point = today - timedelta(days=30)
    recent_shots = [s for s in all_shots if s.session_day > mid_point]
    prior_shots = [s for s in all_shots if s.session_day <= mid_point]
    recent_summary = summarize_period(recent_shots)
    prior_summary = summarize_period(prior_shots)

    # -- Session quality trend: last 5 sessions --
    sessions_by_key: dict[str, list[Shot]] = defaultdict(list)
    for s in all_shots:
        key = f"{s.session_day.isoformat()}::{s.session_id or 'unknown'}"
        sessions_by_key[key].append(s)

    session_scores: list[tuple[str, date, int, float, str]] = []
    for key, sess_shots in sessions_by_key.items():
        score = quality_score(sess_shots)
        day = sess_shots[0].session_day
        session_scores.append((key, day, len(sess_shots), score, grade_for_score(score)))
    session_scores.sort(key=lambda x: x[1], reverse=True)
    last_5 = session_scores[:5]

    # Trajectory detection
    if len(last_5) >= 3:
        scores_oldest_first = [s[3] for s in reversed(last_5)]
        first_half_avg = safe_mean(scores_oldest_first[:len(scores_oldest_first) // 2 + 1])
        second_half_avg = safe_mean(scores_oldest_first[len(scores_oldest_first) // 2:])
        if first_half_avg is not None and second_half_avg is not None:
            diff = second_half_avg - first_half_avg
            if diff > 2.0:
                trajectory = "IMPROVING"
            elif diff < -2.0:
                trajectory = "DECLINING"
            else:
                trajectory = "FLAT"
        else:
            trajectory = "INSUFFICIENT DATA"
    else:
        trajectory = "INSUFFICIENT DATA"

    # -- Strengths / weaknesses --
    overall_smash = safe_mean([s.smash for s in all_shots if s.smash is not None])
    strengths = detect_strengths(club_stats, all_shots, overall_smash, avg_abs_face, avg_strike)
    weaknesses = detect_weaknesses(club_stats, all_shots, overall_smash, avg_abs_face, avg_strike)
    actions = generate_action_items(weaknesses, club_stats, avg_abs_face, avg_strike, overall_smash)

    # ======================================================================
    # Format the report
    # ======================================================================

    lines: list[str] = []
    divider = "=" * 60

    lines.append(divider)
    lines.append("  EXECUTIVE SUMMARY -- STATE OF YOUR GAME")
    lines.append(divider)
    lines.append(f"  Generated: {today.isoformat()}")
    lines.append(f"  Window: last {overall_days} days ({window_start.isoformat()} to {today.isoformat()})")
    lines.append(f"  Database: {db_path.name}")
    lines.append(f"  Filters: exclude {', '.join(EXCLUDED_CLUBS)} | carry >= {MIN_CARRY:.0f}")
    lines.append("")

    # --- A. OVERVIEW ---
    lines.append("-" * 60)
    lines.append("  A. OVERVIEW")
    lines.append("-" * 60)
    lines.append(f"  Total shots (lifetime):    {len(lifetime_shots):,}")
    lines.append(f"  Total sessions (lifetime): {len(lifetime_session_days)}")
    lines.append(f"  Date range:                {first_day.isoformat()} to {last_day.isoformat()}")
    lines.append(f"  Clubs in bag:              {len(clubs_in_window)} ({', '.join(clubs_in_window[:6])}{'...' if len(clubs_in_window) > 6 else ''})")
    lines.append(f"  Practice frequency:        {sessions_per_week:.1f} sessions/week")
    lines.append(f"  Shots this window:         {len(all_shots):,} across {len(session_keys)} sessions")
    lines.append("")

    # --- B. BIG 3 SNAPSHOT ---
    lines.append("-" * 60)
    lines.append("  B. BIG 3 SNAPSHOT (last {0} days)".format(overall_days))
    lines.append("-" * 60)
    face_rating = rate_big3("face_to_path", avg_abs_face)
    path_rating = rate_big3("club_path", avg_abs_path)
    strike_rating = rate_big3("strike_distance", avg_strike)
    lines.append(f"  Face Control  |face-to-path|:  {fmt(avg_abs_face)} deg    [{face_rating}]")
    lines.append(f"  Club Path     avg club_path:   {fmt(avg_club_path, 2)} deg  (|avg| = {fmt(avg_abs_path)} deg)  [{path_rating}]")
    lines.append(f"  Strike Center |strike_dist|:   {fmt(avg_strike)} mm     [{strike_rating}]")
    lines.append("")

    # --- C. TOP 3 CLUBS ---
    lines.append("-" * 60)
    lines.append("  C. TOP 3 CLUBS (by composite score)")
    lines.append("-" * 60)
    top_clubs = [c for c in club_stats if c.shot_count >= 5][:3]
    if top_clubs:
        for i, cs in enumerate(top_clubs, 1):
            smash_str = fmt(cs.smash_avg, 3) if cs.smash_avg is not None else "N/A"
            lines.append(
                f"  {i}. {cs.club:<18s}  score={cs.composite_score:.0f}/100  "
                f"carry={cs.carry_avg:.1f}yd  smash={smash_str}  "
                f"|f2p|={fmt(cs.face_abs_avg)}  ({cs.shot_count} shots)"
            )
    else:
        lines.append("  Not enough data (need 5+ shots per club).")
    lines.append("")

    # --- D. BOTTOM 3 CLUBS ---
    lines.append("-" * 60)
    lines.append("  D. BOTTOM 3 CLUBS (need most work)")
    lines.append("-" * 60)
    bottom_clubs = [c for c in reversed(club_stats) if c.shot_count >= 5][:3]
    if bottom_clubs:
        for i, cs in enumerate(bottom_clubs, 1):
            smash_str = fmt(cs.smash_avg, 3) if cs.smash_avg is not None else "N/A"
            lines.append(
                f"  {i}. {cs.club:<18s}  score={cs.composite_score:.0f}/100  "
                f"carry={cs.carry_avg:.1f}yd  smash={smash_str}  "
                f"|f2p|={fmt(cs.face_abs_avg)}  ({cs.shot_count} shots)"
            )
    else:
        lines.append("  Not enough data (need 5+ shots per club).")
    lines.append("")

    # --- E. RECENT TREND ---
    lines.append("-" * 60)
    lines.append("  E. RECENT TREND (last 30 days vs prior 30 days)")
    lines.append("-" * 60)
    lines.append(f"  {'Metric':<22s}  {'Last 30d':>10s}  {'Prior 30d':>10s}  {'Change'}")
    lines.append(f"  {'-'*22}  {'-'*10}  {'-'*10}  {'-'*24}")

    trend_rows = [
        ("Carry avg (yd)", recent_summary.carry_avg, prior_summary.carry_avg, True, 1),
        ("Smash avg", recent_summary.smash_avg, prior_summary.smash_avg, True, 3),
        ("|Face-to-path| (deg)", recent_summary.face_abs_avg, prior_summary.face_abs_avg, False, 2),
        ("|Strike dist| (mm)", recent_summary.strike_abs_avg, prior_summary.strike_abs_avg, False, 2),
    ]
    for label, curr, prev, higher_better, prec in trend_rows:
        c_str = fmt(curr, prec) if curr is not None else "N/A"
        p_str = fmt(prev, prec) if prev is not None else "N/A"
        arrow = trend_arrow(curr, prev, higher_better)
        lines.append(f"  {label:<22s}  {c_str:>10s}  {p_str:>10s}  {arrow}")
    lines.append("")

    # --- F. SESSION QUALITY TREND ---
    lines.append("-" * 60)
    lines.append("  F. SESSION QUALITY TREND (last 5 sessions)")
    lines.append("-" * 60)
    if last_5:
        for key, day, count, score, grade in last_5:
            lines.append(f"  {day.isoformat()}  {count:>3d} shots  score={score:5.1f}  grade={grade}")
        lines.append(f"  Trajectory: {trajectory}")
    else:
        lines.append("  No sessions found in window.")
    lines.append("")

    # --- G. KEY STRENGTHS ---
    lines.append("-" * 60)
    lines.append("  G. KEY STRENGTHS")
    lines.append("-" * 60)
    if strengths:
        for s in strengths:
            lines.append(f"  + {s}")
    else:
        lines.append("  + Not enough data to identify clear strengths yet.")
    lines.append("")

    # --- H. KEY WEAKNESSES ---
    lines.append("-" * 60)
    lines.append("  H. KEY WEAKNESSES")
    lines.append("-" * 60)
    if weaknesses:
        for w in weaknesses:
            lines.append(f"  - {w}")
    else:
        lines.append("  - No major weaknesses detected -- keep it up!")
    lines.append("")

    # --- I. ACTION ITEMS ---
    lines.append("-" * 60)
    lines.append("  I. ACTION ITEMS")
    lines.append("-" * 60)
    for i, action in enumerate(actions, 1):
        lines.append(f"  {i}. {action}")
    lines.append("")

    lines.append(divider)
    lines.append("  End of Executive Summary")
    lines.append(divider)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a single comprehensive 'state of your game' executive summary. "
            "This is THE report for a quick health check."
        ),
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--bag-config",
        type=Path,
        default=DEFAULT_BAG_PATH,
        help=f"Path to my_bag.json for smash targets (default: {DEFAULT_BAG_PATH})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Overall analysis window in days (default: 90).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.days < 1:
        print("Error: --days must be >= 1")
        return 1
    try:
        report = build_report(args.db, args.bag_config, args.days)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    except (sqlite3.Error, RuntimeError) as exc:
        print(f"Database error: {exc}")
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
