#!/usr/bin/env python3
"""Generate a structured practice plan based on data-driven weakness identification.

Analyzes shot data from golf_stats.db to identify weaknesses in accuracy,
consistency, efficiency, and distance, then builds a session plan with warmup,
focused drill blocks, and a random/game block.  Total: ~60-80 shots, ~45-60 min.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXCLUDED_CLUBS = ("Other", "Putter", "Sim Round")
MIN_CARRY = 10.0
MIN_SHOTS_PER_CLUB = 10
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
BAG_JSON_PATH = Path(__file__).resolve().parents[1] / "my_bag.json"
RECENT_DAYS = 30
RECENCY_WEIGHT = 2.0  # multiplier for shots within RECENT_DAYS
WARMUP_SHOTS = 7  # per warmup analyzer findings


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Shot:
    """A single qualifying shot with analysis-relevant metrics."""
    club: str
    carry: float
    smash: Optional[float]
    face_to_path: Optional[float]
    strike_distance: Optional[float]
    side_distance: Optional[float]
    session_date: Optional[date]


@dataclass
class ClubProfile:
    """Aggregated statistics for a single club."""
    club: str
    shot_count: int
    recent_count: int
    carry_mean: float
    carry_std: float
    carry_cv: float
    side_abs_mean: float
    ftp_abs_mean: float
    smash_mean: Optional[float]
    strike_mean: Optional[float]
    # Weighted versions (recent sessions count double)
    w_carry_cv: float
    w_side_abs_mean: float
    w_ftp_abs_mean: float
    w_smash_mean: Optional[float]
    w_strike_mean: Optional[float]


@dataclass
class Weakness:
    """An identified weakness area with severity and supporting data."""
    category: str          # accuracy, consistency, efficiency, distance
    club: str
    severity: float        # 0-10 scale
    metric_name: str
    metric_value: float
    threshold: float
    description: str


@dataclass
class DrillBlock:
    """A practice block with a specific focus."""
    title: str
    club: str
    goal: str
    metric_to_track: str
    reps: int
    drill_description: str
    evidence: str
    estimated_minutes: int


@dataclass
class PracticePlan:
    """Complete practice plan for a session."""
    generated: date
    duration_target: int
    warmup: DrillBlock
    focus_blocks: List[DrillBlock]
    game_block: DrillBlock
    total_shots: int
    total_minutes: int
    weaknesses: List[Weakness]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_float(value: Any) -> Optional[float]:
    """Convert to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_mean(values: List[float]) -> float:
    """Mean that returns nan for empty lists."""
    if not values:
        return math.nan
    return statistics.fmean(values)


def safe_stdev(values: List[float]) -> float:
    """Stdev that handles edge cases."""
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def coeff_var(values: List[float]) -> float:
    """Coefficient of variation (CV%)."""
    if len(values) < 2:
        return math.nan
    avg = safe_mean(values)
    if avg <= 0:
        return math.nan
    return safe_stdev(values) / avg


def fmt(value: Optional[float], digits: int = 2) -> str:
    """Format a float for display."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{value:.{digits}f}"


def weighted_mean(values: List[float], weights: List[float]) -> float:
    """Weighted mean, returns nan if empty."""
    if not values or not weights:
        return math.nan
    total_w = sum(weights)
    if total_w <= 0:
        return math.nan
    return sum(v * w for v, w in zip(values, weights)) / total_w


# ---------------------------------------------------------------------------
# Bag configuration
# ---------------------------------------------------------------------------

def load_smash_targets() -> Dict[str, float]:
    """Load smash factor targets from my_bag.json."""
    if not BAG_JSON_PATH.exists():
        return {}
    try:
        with open(BAG_JSON_PATH, "r") as f:
            bag = json.load(f)
        return dict(bag.get("smash_targets", {}))
    except (json.JSONDecodeError, IOError):
        return {}


def load_bag_order() -> List[str]:
    """Load club ordering from my_bag.json."""
    if not BAG_JSON_PATH.exists():
        return []
    try:
        with open(BAG_JSON_PATH, "r") as f:
            bag = json.load(f)
        return list(bag.get("bag_order", []))
    except (json.JSONDecodeError, IOError):
        return []


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def build_connection(db_path: Path) -> sqlite3.Connection:
    """Open read-only connection with safety pragmas."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA query_only = ON")
    return conn


def resolve_carry_column(conn: sqlite3.Connection) -> str:
    """Auto-detect carry column name."""
    cols = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(shots)").fetchall()
    }
    if "carry_distance" in cols:
        return "carry_distance"
    if "carry" in cols:
        return "carry"
    raise RuntimeError("shots table must contain carry_distance or carry column")


def check_column_exists(conn: sqlite3.Connection, column: str) -> bool:
    """Check if a column exists in the shots table."""
    cols = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(shots)").fetchall()
    }
    return column in cols


def load_shots(conn: sqlite3.Connection, carry_col: str) -> List[Shot]:
    """Load all qualifying shots from the database."""
    has_side = check_column_exists(conn, "side_distance")
    has_side_total = check_column_exists(conn, "side_total")
    # Use side_total if side_distance is absent (some schemas differ)
    side_expr = "side_distance" if has_side else ("side_total" if has_side_total else "NULL")

    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            TRIM(club) AS club,
            {carry_col} AS carry_value,
            smash,
            face_to_path,
            strike_distance,
            {side_expr} AS side_dist,
            session_date
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND TRIM(club) NOT IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
          AND session_date IS NOT NULL
        ORDER BY session_date
    """
    params = (*EXCLUDED_CLUBS, MIN_CARRY)
    rows = conn.execute(query, params).fetchall()

    shots: List[Shot] = []
    for row in rows:
        carry = safe_float(row["carry_value"])
        if carry is None or carry < MIN_CARRY:
            continue
        club = str(row["club"]).strip()
        if not club:
            continue

        # Parse session_date
        session_dt: Optional[date] = None
        raw_date = row["session_date"]
        if raw_date:
            for fmt_str in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
                try:
                    session_dt = datetime.strptime(str(raw_date)[:19], fmt_str).date()
                    break
                except ValueError:
                    continue

        shots.append(Shot(
            club=club,
            carry=carry,
            smash=safe_float(row["smash"]),
            face_to_path=safe_float(row["face_to_path"]),
            strike_distance=safe_float(row["strike_distance"]),
            side_distance=safe_float(row["side_dist"]),
            session_date=session_dt,
        ))

    return shots


# ---------------------------------------------------------------------------
# Analysis: build club profiles with recency weighting
# ---------------------------------------------------------------------------

def build_club_profiles(shots: List[Shot]) -> List[ClubProfile]:
    """Aggregate shot data into per-club profiles with recency weighting."""
    today = date.today()
    cutoff = today - timedelta(days=RECENT_DAYS)

    # Bucket shots by club
    buckets: Dict[str, List[Shot]] = {}
    for shot in shots:
        buckets.setdefault(shot.club, []).append(shot)

    profiles: List[ClubProfile] = []
    for club, club_shots in buckets.items():
        if len(club_shots) < MIN_SHOTS_PER_CLUB:
            continue

        recent_shots = [s for s in club_shots if s.session_date and s.session_date >= cutoff]
        recent_count = len(recent_shots)

        # Assign weights: recent shots get RECENCY_WEIGHT, older get 1.0
        carries: List[float] = []
        weights: List[float] = []
        side_abs: List[float] = []
        side_weights: List[float] = []
        ftp_abs: List[float] = []
        ftp_weights: List[float] = []
        smash_vals: List[float] = []
        smash_weights: List[float] = []
        strike_vals: List[float] = []
        strike_weights: List[float] = []

        for s in club_shots:
            w = RECENCY_WEIGHT if (s.session_date and s.session_date >= cutoff) else 1.0

            carries.append(s.carry)
            weights.append(w)

            if s.side_distance is not None:
                side_abs.append(abs(s.side_distance))
                side_weights.append(w)

            if s.face_to_path is not None:
                ftp_abs.append(abs(s.face_to_path))
                ftp_weights.append(w)

            if s.smash is not None:
                smash_vals.append(s.smash)
                smash_weights.append(w)

            if s.strike_distance is not None:
                strike_vals.append(s.strike_distance)
                strike_weights.append(w)

        # Unweighted stats
        carry_vals = [s.carry for s in club_shots]
        carry_mean = safe_mean(carry_vals)
        carry_std = safe_stdev(carry_vals)
        carry_cv_val = coeff_var(carry_vals)

        plain_side = [abs(s.side_distance) for s in club_shots if s.side_distance is not None]
        plain_ftp = [abs(s.face_to_path) for s in club_shots if s.face_to_path is not None]
        plain_smash = [s.smash for s in club_shots if s.smash is not None]
        plain_strike = [s.strike_distance for s in club_shots if s.strike_distance is not None]

        # Weighted carry CV: approximate by weighting recent values more
        # We compute CV on recent-only vs all to blend
        recent_carries = [s.carry for s in recent_shots]
        if len(recent_carries) >= 5:
            w_cv = coeff_var(recent_carries)
        else:
            w_cv = carry_cv_val

        profiles.append(ClubProfile(
            club=club,
            shot_count=len(club_shots),
            recent_count=recent_count,
            carry_mean=carry_mean,
            carry_std=carry_std,
            carry_cv=carry_cv_val,
            side_abs_mean=safe_mean(plain_side),
            ftp_abs_mean=safe_mean(plain_ftp),
            smash_mean=safe_mean(plain_smash) if plain_smash else None,
            strike_mean=safe_mean(plain_strike) if plain_strike else None,
            w_carry_cv=w_cv,
            w_side_abs_mean=weighted_mean(side_abs, side_weights),
            w_ftp_abs_mean=weighted_mean(ftp_abs, ftp_weights),
            w_smash_mean=weighted_mean(smash_vals, smash_weights) if smash_vals else None,
            w_strike_mean=weighted_mean(strike_vals, strike_weights) if strike_vals else None,
        ))

    return profiles


# ---------------------------------------------------------------------------
# Analysis: detect weaknesses
# ---------------------------------------------------------------------------

def detect_weaknesses(
    profiles: List[ClubProfile],
    smash_targets: Dict[str, float],
) -> List[Weakness]:
    """Score each club across four weakness categories and return sorted list."""
    weaknesses: List[Weakness] = []

    if not profiles:
        return weaknesses

    # Compute cross-club averages for relative comparison
    all_carry_means = [p.carry_mean for p in profiles if not math.isnan(p.carry_mean)]
    global_carry_avg = safe_mean(all_carry_means) if all_carry_means else math.nan

    # --- Accuracy: highest avg |side_distance| or |face_to_path| ---
    SIDE_THRESHOLD = 15.0   # yards, above this is a concern
    FTP_THRESHOLD = 3.0     # degrees

    for p in profiles:
        # Side distance accuracy
        val = p.w_side_abs_mean
        if not math.isnan(val) and val > SIDE_THRESHOLD:
            ratio = val / SIDE_THRESHOLD
            severity = min(10.0, ratio * 4.0)
            weaknesses.append(Weakness(
                category="accuracy",
                club=p.club,
                severity=severity,
                metric_name="avg |side_distance|",
                metric_value=val,
                threshold=SIDE_THRESHOLD,
                description=f"Directional dispersion too wide ({fmt(val, 1)} yd avg offline)",
            ))

        # Face-to-path accuracy
        val = p.w_ftp_abs_mean
        if not math.isnan(val) and val > FTP_THRESHOLD:
            ratio = val / FTP_THRESHOLD
            severity = min(10.0, ratio * 3.5)
            weaknesses.append(Weakness(
                category="accuracy",
                club=p.club,
                severity=severity,
                metric_name="avg |face_to_path|",
                metric_value=val,
                threshold=FTP_THRESHOLD,
                description=f"Face-to-path gap too large ({fmt(val)}deg avg)",
            ))

    # --- Consistency: highest carry CV% ---
    CV_THRESHOLD = 0.12  # 12% CV is a concern

    for p in profiles:
        val = p.w_carry_cv
        if not math.isnan(val) and val > CV_THRESHOLD:
            ratio = val / CV_THRESHOLD
            severity = min(10.0, ratio * 4.0)
            weaknesses.append(Weakness(
                category="consistency",
                club=p.club,
                severity=severity,
                metric_name="carry CV%",
                metric_value=val * 100,
                threshold=CV_THRESHOLD * 100,
                description=f"Carry distance too variable (CV {fmt(val * 100, 1)}%)",
            ))

    # --- Efficiency: lowest smash vs target ---
    SMASH_DEFICIT_THRESHOLD = 0.04  # missing target by > 0.04

    for p in profiles:
        if p.w_smash_mean is None or math.isnan(p.w_smash_mean):
            continue
        target = smash_targets.get(p.club)
        if target is None:
            continue
        deficit = target - p.w_smash_mean
        if deficit > SMASH_DEFICIT_THRESHOLD:
            ratio = deficit / SMASH_DEFICIT_THRESHOLD
            severity = min(10.0, ratio * 3.0)
            weaknesses.append(Weakness(
                category="efficiency",
                club=p.club,
                severity=severity,
                metric_name="smash deficit",
                metric_value=p.w_smash_mean,
                threshold=target,
                description=(
                    f"Smash factor {fmt(p.w_smash_mean, 3)} vs "
                    f"target {fmt(target, 3)} (deficit {fmt(deficit, 3)})"
                ),
            ))

    # --- Distance: below-average carry for category ---
    # Group by category: woods, irons, wedges
    CATEGORY_CLUBS = {
        "woods": {"Driver", "3 Wood (Cobra)", "3 Wood (TM)", "7 Wood"},
        "irons": {"3 Iron", "4 Iron", "5 Iron", "6 Iron", "7 Iron", "8 Iron", "9 Iron"},
        "wedges": {"PW", "GW", "SW", "LW"},
    }

    for cat_name, cat_clubs in CATEGORY_CLUBS.items():
        cat_profiles = [p for p in profiles if p.club in cat_clubs]
        if len(cat_profiles) < 2:
            continue
        cat_avg = safe_mean([p.carry_mean for p in cat_profiles])
        if math.isnan(cat_avg):
            continue
        for p in cat_profiles:
            # Flag if >10% below category average (relative shortfall)
            if p.carry_mean < cat_avg * 0.90:
                gap = cat_avg - p.carry_mean
                ratio = gap / (cat_avg * 0.10) if cat_avg > 0 else 0
                severity = min(10.0, ratio * 3.0)
                weaknesses.append(Weakness(
                    category="distance",
                    club=p.club,
                    severity=severity,
                    metric_name="carry vs category avg",
                    metric_value=p.carry_mean,
                    threshold=cat_avg,
                    description=(
                        f"Carry {fmt(p.carry_mean, 1)} yd vs "
                        f"{cat_name} avg {fmt(cat_avg, 1)} yd "
                        f"(gap {fmt(gap, 1)} yd)"
                    ),
                ))

    # --- Strike quality ---
    STRIKE_THRESHOLD = 8.0  # mm from center

    for p in profiles:
        val = p.w_strike_mean
        if val is not None and not math.isnan(val) and val > STRIKE_THRESHOLD:
            ratio = val / STRIKE_THRESHOLD
            severity = min(10.0, ratio * 3.5)
            weaknesses.append(Weakness(
                category="accuracy",
                club=p.club,
                severity=severity,
                metric_name="avg strike_distance",
                metric_value=val,
                threshold=STRIKE_THRESHOLD,
                description=f"Strike quality poor ({fmt(val, 1)}mm avg from center)",
            ))

    # Sort by severity descending
    weaknesses.sort(key=lambda w: w.severity, reverse=True)
    return weaknesses


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------

DRILL_TEMPLATES = {
    "accuracy_ftp": {
        "title": "Face Gate Drill",
        "goal": "Reduce face-to-path gap below 2.5 degrees",
        "metric": "|face_to_path|",
        "drill": (
            "Place two alignment sticks as a gate 2 feet ahead of the ball, "
            "just wider than a ball. Hit shots through the gate. "
            "Goal: |face_to_path| < 2.5 deg on 7/10 shots."
        ),
    },
    "accuracy_side": {
        "title": "Target Corridor Drill",
        "goal": "Reduce offline dispersion below 15 yards",
        "metric": "|side_distance|",
        "drill": (
            "Pick a target and set a mental corridor +/-10 yards. "
            "Hit 15-20 shots tracking how many land inside the corridor. "
            "Goal: 70%+ inside the corridor."
        ),
    },
    "accuracy_strike": {
        "title": "Centered Contact Drill",
        "goal": "Reduce strike distance below 8mm from center",
        "metric": "strike_distance",
        "drill": (
            "Use foot spray or impact tape on the face. "
            "Hit 15 shots focusing on centered contact. "
            "Goal: |strike_distance| < 8mm on 70%+ of shots."
        ),
    },
    "consistency": {
        "title": "Block Practice",
        "goal": "Reduce carry CV% below 12%",
        "metric": "carry CV%",
        "drill": (
            "Same club, same target, 20 consecutive shots. "
            "Focus on repeating tempo and ball position. "
            "Track carry after each shot. Goal: CV% < 12%."
        ),
    },
    "efficiency": {
        "title": "Smash Factor Ladder",
        "goal": "Close smash deficit to target",
        "metric": "smash factor",
        "drill": (
            "Hit 3-shot ladders at 70%, 85%, 100% effort. "
            "Focus on strike quality over speed. "
            "Goal: avg smash within 0.03 of target by set 3."
        ),
    },
    "distance": {
        "title": "Carry Ladder Combine",
        "goal": "Close carry gap to category average",
        "metric": "carry distance",
        "drill": (
            "Alternate between two carry targets (short/full) with the same club. "
            "Commit to one stock shape and track each carry. "
            "Goal: avg carry increases 3-5 yards over baseline."
        ),
    },
}


def pick_drill_template(weakness: Weakness) -> dict:
    """Select the best drill template for a given weakness."""
    if weakness.category == "accuracy":
        if "face_to_path" in weakness.metric_name:
            return DRILL_TEMPLATES["accuracy_ftp"]
        if "strike" in weakness.metric_name:
            return DRILL_TEMPLATES["accuracy_strike"]
        return DRILL_TEMPLATES["accuracy_side"]
    if weakness.category == "consistency":
        return DRILL_TEMPLATES["consistency"]
    if weakness.category == "efficiency":
        return DRILL_TEMPLATES["efficiency"]
    if weakness.category == "distance":
        return DRILL_TEMPLATES["distance"]
    return DRILL_TEMPLATES["consistency"]  # fallback


def build_warmup_block(profiles: List[ClubProfile]) -> DrillBlock:
    """Build warmup block: 7 shots with a comfortable mid-iron."""
    # Pick a mid-iron with reasonable data
    preferred = ["7 Iron", "8 Iron", "9 Iron", "PW", "6 Iron"]
    warmup_club = "7 Iron"
    for club_name in preferred:
        if any(p.club == club_name for p in profiles):
            warmup_club = club_name
            break

    return DrillBlock(
        title="Warmup",
        club=warmup_club,
        goal="Establish rhythm and feel before focused work",
        metric_to_track="tempo and contact quality (subjective)",
        reps=WARMUP_SHOTS,
        drill_description=(
            f"Start with {WARMUP_SHOTS} easy swings ({warmup_club}). "
            f"Focus on smooth tempo, not distance. "
            f"Per warmup analysis, ~7 shots to reach stable performance."
        ),
        evidence="Warmup analyzer finding: performance stabilizes around shot 7",
        estimated_minutes=5,
    )


def build_game_block(profiles: List[ClubProfile], shots_budget: int) -> DrillBlock:
    """Build a random/game block mixing clubs."""
    available = [p.club for p in profiles]
    reps = max(10, min(15, shots_budget))

    if len(available) >= 3:
        sample_clubs = random.sample(available, min(4, len(available)))
        club_str = ", ".join(sample_clubs)
    else:
        club_str = ", ".join(available)

    return DrillBlock(
        title="Random / On-Course Simulation",
        club=f"Rotate: {club_str}",
        goal="Transfer practice gains to course-like conditions",
        metric_to_track="shot quality (subjective score 1-5 per shot)",
        reps=reps,
        drill_description=(
            f"Cycle through {club_str}, changing target each shot. "
            f"No two consecutive shots with the same club. "
            f"Simulate on-course decision-making."
        ),
        evidence="Research: random practice improves transfer to playing conditions",
        estimated_minutes=max(8, reps),
    )


def deduplicate_clubs(weaknesses: List[Weakness], max_blocks: int) -> List[Weakness]:
    """Select top weaknesses ensuring club diversity in the plan."""
    selected: List[Weakness] = []
    seen_clubs: set = set()
    seen_categories: set = set()

    # First pass: pick highest-severity weakness per unique club
    for w in weaknesses:
        if len(selected) >= max_blocks:
            break
        if w.club not in seen_clubs:
            selected.append(w)
            seen_clubs.add(w.club)
            seen_categories.add(w.category)

    # If we still have room and missed a category, backfill
    if len(selected) < max_blocks:
        for w in weaknesses:
            if len(selected) >= max_blocks:
                break
            if w.category not in seen_categories and w not in selected:
                selected.append(w)
                seen_categories.add(w.category)

    return selected[:max_blocks]


def allocate_reps(num_blocks: int, total_budget: int) -> List[int]:
    """Distribute reps across drill blocks."""
    if num_blocks == 0:
        return []
    base = total_budget // num_blocks
    remainder = total_budget % num_blocks
    reps = [base] * num_blocks
    for i in range(remainder):
        reps[i] += 1
    # Clamp each block to 15-20
    return [max(15, min(20, r)) for r in reps]


def generate_plan(
    profiles: List[ClubProfile],
    weaknesses: List[Weakness],
    duration_minutes: int,
) -> PracticePlan:
    """Generate a complete practice plan from weakness analysis."""
    today = date.today()

    # Budget: ~60-80 shots for 45-60 min; scale if duration differs
    scale = duration_minutes / 60.0
    total_shot_budget = int(70 * scale)

    # Reserve shots for warmup and game block
    warmup = build_warmup_block(profiles)
    game_reps = max(10, min(15, int(12 * scale)))
    drill_budget = total_shot_budget - warmup.reps - game_reps

    # Pick top 2-3 weaknesses for drill blocks
    num_focus = 3 if duration_minutes >= 50 else 2
    if drill_budget < num_focus * 15:
        num_focus = max(1, drill_budget // 15)

    top_weaknesses = deduplicate_clubs(weaknesses, num_focus)
    rep_alloc = allocate_reps(len(top_weaknesses), drill_budget)

    focus_blocks: List[DrillBlock] = []
    for i, weakness in enumerate(top_weaknesses):
        template = pick_drill_template(weakness)
        reps = rep_alloc[i] if i < len(rep_alloc) else 15
        est_min = max(8, int(reps * 0.8))

        focus_blocks.append(DrillBlock(
            title=f"Focus {i + 1}: {template['title']}",
            club=weakness.club,
            goal=template["goal"],
            metric_to_track=template["metric"],
            reps=reps,
            drill_description=template["drill"],
            evidence=(
                f"[{weakness.category.upper()}] {weakness.description} "
                f"({weakness.metric_name}={fmt(weakness.metric_value)}, "
                f"threshold={fmt(weakness.threshold)})"
            ),
            estimated_minutes=est_min,
        ))

    game_block = build_game_block(profiles, game_reps)

    actual_total = warmup.reps + sum(b.reps for b in focus_blocks) + game_block.reps
    actual_minutes = warmup.estimated_minutes + sum(b.estimated_minutes for b in focus_blocks) + game_block.estimated_minutes

    return PracticePlan(
        generated=today,
        duration_target=duration_minutes,
        warmup=warmup,
        focus_blocks=focus_blocks,
        game_block=game_block,
        total_shots=actual_total,
        total_minutes=actual_minutes,
        weaknesses=weaknesses,
    )


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_plan(plan: PracticePlan, db_path: Path, carry_col: str, shot_count: int, club_count: int) -> str:
    """Render the practice plan as a formatted text report."""
    lines: List[str] = []
    sep = "=" * 64

    lines.append(sep)
    lines.append("  DATA-DRIVEN PRACTICE PLAN")
    lines.append(sep)
    lines.append(f"Generated:     {plan.generated.isoformat()}")
    lines.append(f"Database:      {db_path}")
    lines.append(f"Carry column:  {carry_col}")
    lines.append(f"Shots in DB:   {shot_count}")
    lines.append(f"Clubs analyzed:{club_count}")
    lines.append(f"Target time:   ~{plan.duration_target} min")
    lines.append(f"Planned shots: {plan.total_shots}")
    lines.append(f"Est. duration: ~{plan.total_minutes} min")
    lines.append("")

    # Weakness summary
    lines.append("-" * 64)
    lines.append("  WEAKNESS ANALYSIS (top findings)")
    lines.append("-" * 64)
    shown = plan.weaknesses[:8]
    if not shown:
        lines.append("  No significant weaknesses detected. Nice work!")
        lines.append("  Plan will focus on maintenance and game simulation.")
    else:
        for i, w in enumerate(shown, start=1):
            lines.append(
                f"  {i}. [{w.category.upper():12s}] {w.club:18s} "
                f"severity={fmt(w.severity, 1)}/10"
            )
            lines.append(f"     {w.description}")
    lines.append("")

    # Warmup
    lines.append("-" * 64)
    lines.append(f"  BLOCK 1: {plan.warmup.title.upper()}")
    lines.append(f"  Club: {plan.warmup.club}  |  Shots: {plan.warmup.reps}  |  ~{plan.warmup.estimated_minutes} min")
    lines.append("-" * 64)
    lines.append(f"  Goal:    {plan.warmup.goal}")
    lines.append(f"  Track:   {plan.warmup.metric_to_track}")
    lines.append(f"  Detail:  {plan.warmup.drill_description}")
    lines.append(f"  Why:     {plan.warmup.evidence}")
    lines.append("")

    # Focus blocks
    for idx, block in enumerate(plan.focus_blocks, start=2):
        lines.append("-" * 64)
        lines.append(f"  BLOCK {idx}: {block.title.upper()}")
        lines.append(f"  Club: {block.club}  |  Shots: {block.reps}  |  ~{block.estimated_minutes} min")
        lines.append("-" * 64)
        lines.append(f"  Goal:    {block.goal}")
        lines.append(f"  Track:   {block.metric_to_track}")
        lines.append(f"  Detail:  {block.drill_description}")
        lines.append(f"  Why:     {block.evidence}")
        lines.append("")

    # Game block
    block_num = len(plan.focus_blocks) + 2
    lines.append("-" * 64)
    lines.append(f"  BLOCK {block_num}: {plan.game_block.title.upper()}")
    lines.append(
        f"  Club: {plan.game_block.club}  |  Shots: {plan.game_block.reps}  "
        f"|  ~{plan.game_block.estimated_minutes} min"
    )
    lines.append("-" * 64)
    lines.append(f"  Goal:    {plan.game_block.goal}")
    lines.append(f"  Track:   {plan.game_block.metric_to_track}")
    lines.append(f"  Detail:  {plan.game_block.drill_description}")
    lines.append(f"  Why:     {plan.game_block.evidence}")
    lines.append("")

    # Summary
    lines.append(sep)
    lines.append("  SESSION SUMMARY")
    lines.append(sep)
    lines.append(f"  Total blocks: {2 + len(plan.focus_blocks)}")
    lines.append(f"  Total shots:  {plan.total_shots}")
    lines.append(f"  Est. time:    ~{plan.total_minutes} min")
    lines.append("")
    lines.append("  Tip: Log this session in your Uneekor portal and re-run")
    lines.append("  this script afterward to see if the targeted metrics improved.")
    lines.append(sep)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a data-driven practice plan from golf shot data.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Target session duration in minutes (default: 60).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.duration < 20:
        print("Error: --duration must be at least 20 minutes.")
        return 1

    with build_connection(args.db) as conn:
        carry_col = resolve_carry_column(conn)
        shots = load_shots(conn, carry_col)

    if not shots:
        print("No qualifying shots found after applying filters.")
        print(f"  Excluded clubs: {', '.join(EXCLUDED_CLUBS)}")
        print(f"  Minimum carry: {MIN_CARRY}")
        return 1

    smash_targets = load_smash_targets()
    profiles = build_club_profiles(shots)

    if not profiles:
        print(f"No clubs met the minimum sample size ({MIN_SHOTS_PER_CLUB} shots).")
        return 1

    weaknesses = detect_weaknesses(profiles, smash_targets)
    plan = generate_plan(profiles, weaknesses, args.duration)
    report = render_plan(plan, args.db, carry_col, len(shots), len(profiles))
    print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
