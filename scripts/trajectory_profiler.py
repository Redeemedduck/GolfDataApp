#!/usr/bin/env python3
"""Build full trajectory profiles per club from golf_stats.db.

Analyzes launch, peak height, landing, and roll characteristics
for each club in your bag. Includes trajectory grading, roll analysis,
and flight efficiency metrics.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional

EXCLUDED_CLUBS = ("Other", "Putter", "Sim Round")
MIN_CARRY = 10.0
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
BAG_CONFIG_PATH = Path(__file__).resolve().parents[1] / "my_bag.json"

# Optimal trajectory benchmarks per club category
OPTIMAL_BENCHMARKS: Dict[str, Dict[str, tuple]] = {
    "Driver": {
        "launch_angle": (12.0, 15.0),
        "apex": (25.0, 35.0),
        "descent_angle": (35.0, 45.0),
    },
    "wood": {
        "launch_angle": (13.0, 17.0),
        "apex": (25.0, 38.0),
        "descent_angle": (40.0, 50.0),
    },
    "long_iron": {
        "launch_angle": (14.0, 18.0),
        "apex": (22.0, 32.0),
        "descent_angle": (42.0, 52.0),
    },
    "mid_iron": {
        "launch_angle": (18.0, 24.0),
        "apex": (22.0, 35.0),
        "descent_angle": (45.0, 55.0),
    },
    "short_iron": {
        "launch_angle": (24.0, 32.0),
        "apex": (25.0, 38.0),
        "descent_angle": (48.0, 58.0),
    },
    "wedge": {
        "launch_angle": (28.0, 38.0),
        "apex": (22.0, 38.0),
        "descent_angle": (50.0, 60.0),
    },
}

EXCESSIVE_ROLL_THRESHOLD = 20.0  # percent of carry


def _club_category(club: str) -> str:
    """Map a club name to its benchmark category."""
    if club == "Driver":
        return "Driver"
    if "Wood" in club:
        return "wood"
    if club in ("3 Iron", "4 Iron"):
        return "long_iron"
    if club in ("5 Iron", "6 Iron", "7 Iron"):
        return "mid_iron"
    if club in ("8 Iron", "9 Iron"):
        return "short_iron"
    if club in ("PW", "GW", "SW", "LW") or "Wedge" in club:
        return "wedge"
    return "mid_iron"  # fallback


def load_bag_order() -> List[str]:
    """Load bag order from my_bag.json."""
    if BAG_CONFIG_PATH.exists():
        with open(BAG_CONFIG_PATH, "r") as f:
            config = json.load(f)
        return config.get("bag_order", [])
    return []


def get_club_sort_key(club: str, bag_order: List[str]) -> int:
    """Return sort index for a club based on bag order."""
    try:
        return bag_order.index(club)
    except ValueError:
        return len(bag_order)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate trajectory profiles per club from shot data.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--min-shots",
        type=int,
        default=10,
        help="Minimum shots required per club (default: 10).",
    )
    return parser.parse_args()


def to_float(value: Any) -> Optional[float]:
    """Convert a value to float, returning None for NULL/invalid."""
    if value is None:
        return None
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def safe_mean(values: List[float]) -> Optional[float]:
    """Compute mean of non-empty list, or None."""
    if not values:
        return None
    return sum(values) / len(values)


def safe_median(values: List[float]) -> Optional[float]:
    """Compute median of non-empty list, or None."""
    if not values:
        return None
    return median(values)


def safe_max(values: List[float]) -> Optional[float]:
    """Compute max of non-empty list, or None."""
    if not values:
        return None
    return max(values)


def fmt(value: Optional[float], digits: int = 1) -> str:
    """Format a float with given precision, or return N/A."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{value:.{digits}f}"


def build_connection(db_path: Path) -> sqlite3.Connection:
    """Open a read-only SQLite connection."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA query_only = ON")
    return conn


def resolve_carry_column(conn: sqlite3.Connection) -> str:
    """Detect whether the carry column is named carry_distance or carry."""
    cols = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(shots)").fetchall()
    }
    if "carry_distance" in cols:
        return "carry_distance"
    if "carry" in cols:
        return "carry"
    raise RuntimeError("shots table must contain carry_distance or carry column")


@dataclass
class TrajectoryShot:
    """One shot's trajectory-relevant fields."""
    club: str
    carry: float
    total: Optional[float]
    launch_angle: Optional[float]
    ball_speed: Optional[float]
    attack_angle: Optional[float]
    apex: Optional[float]
    descent_angle: Optional[float]
    flight_time: Optional[float]


@dataclass
class ClubTrajectory:
    """Aggregated trajectory profile for one club."""
    club: str
    shot_count: int
    # Launch profile
    avg_launch_angle: Optional[float] = None
    median_launch_angle: Optional[float] = None
    avg_ball_speed: Optional[float] = None
    avg_attack_angle: Optional[float] = None
    # Peak height
    avg_apex: Optional[float] = None
    max_apex: Optional[float] = None
    apex_efficiency: Optional[float] = None  # apex / carry
    # Landing
    avg_descent_angle: Optional[float] = None
    avg_flight_time: Optional[float] = None
    # Roll
    avg_carry: Optional[float] = None
    avg_total: Optional[float] = None
    avg_roll: Optional[float] = None
    roll_ratio: Optional[float] = None  # roll / carry * 100
    # Trajectory grade
    trajectory_grade: str = "Unknown"
    # Flight efficiency
    flight_efficiency: Optional[float] = None  # flight_time / carry


def load_shots(
    conn: sqlite3.Connection,
    carry_column: str,
) -> List[TrajectoryShot]:
    """Load all qualifying shots for trajectory analysis."""
    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            TRIM(club) AS club,
            {carry_column} AS carry_value,
            total,
            launch_angle,
            ball_speed,
            attack_angle,
            apex,
            descent_angle,
            flight_time
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND TRIM(club) NOT IN ({placeholders})
          AND {carry_column} IS NOT NULL
          AND {carry_column} >= ?
    """
    params = (*EXCLUDED_CLUBS, MIN_CARRY)
    rows = conn.execute(query, params).fetchall()

    shots: List[TrajectoryShot] = []
    for row in rows:
        carry = to_float(row["carry_value"])
        if carry is None or carry < MIN_CARRY:
            continue

        club = str(row["club"]).strip()
        if not club:
            continue

        shots.append(
            TrajectoryShot(
                club=club,
                carry=carry,
                total=to_float(row["total"]),
                launch_angle=to_float(row["launch_angle"]),
                ball_speed=to_float(row["ball_speed"]),
                attack_angle=to_float(row["attack_angle"]),
                apex=to_float(row["apex"]),
                descent_angle=to_float(row["descent_angle"]),
                flight_time=to_float(row["flight_time"]),
            )
        )

    return shots


def classify_trajectory(
    apex_efficiency: Optional[float],
    descent_angle: Optional[float],
    avg_apex: Optional[float],
    carry: Optional[float],
    club: str,
) -> str:
    """Rate trajectory as Penetrating, Towering, Optimal, or Ballooning.

    Ballooning = high apex relative to benchmarks BUT short carry (wasted height).
    Towering = high apex relative to benchmarks with proportional carry (good power).
    Penetrating = low apex ratio AND shallow descent (boring, low flight).
    Optimal = metrics within or near benchmark ranges.
    """
    if apex_efficiency is None or descent_angle is None or carry is None:
        return "Insufficient Data"

    category = _club_category(club)
    benchmarks = OPTIMAL_BENCHMARKS.get(category, OPTIMAL_BENCHMARKS["mid_iron"])
    descent_low, descent_high = benchmarks["descent_angle"]
    apex_low, apex_high = benchmarks["apex"]

    # Check apex relative to the benchmark range for this club category
    apex_above_range = avg_apex is not None and avg_apex > apex_high
    apex_below_range = avg_apex is not None and avg_apex < apex_low
    descent_shallow = descent_angle < descent_low
    descent_in_range = descent_low <= descent_angle <= descent_high

    # Ballooning: apex above optimal range AND descent is shallow relative
    # to the height (the ball goes high but comes down too gently = weak flight)
    if apex_above_range and descent_shallow:
        return "Ballooning"

    # Towering: apex above optimal range with adequate descent
    if apex_above_range and not descent_shallow:
        return "Towering"

    # Penetrating: low apex + shallow descent (boring low flight)
    if apex_below_range and descent_shallow:
        return "Penetrating"

    # Optimal: apex and descent are within or near benchmark ranges
    if descent_in_range:
        return "Optimal"

    # Towering: apex in range but descent is steep (dropping out of the sky)
    if not apex_below_range and descent_angle > descent_high:
        return "Towering"

    # Penetrating: descent is shallow regardless of apex
    if descent_shallow:
        return "Penetrating"

    return "Optimal"


def build_club_profiles(
    shots: List[TrajectoryShot],
    min_shots: int,
    bag_order: List[str],
) -> List[ClubTrajectory]:
    """Build trajectory profiles grouped by club."""
    by_club: Dict[str, List[TrajectoryShot]] = {}
    for shot in shots:
        by_club.setdefault(shot.club, []).append(shot)

    profiles: List[ClubTrajectory] = []

    for club, club_shots in by_club.items():
        if len(club_shots) < min_shots:
            continue

        launch_angles = [s.launch_angle for s in club_shots if s.launch_angle is not None]
        ball_speeds = [s.ball_speed for s in club_shots if s.ball_speed is not None]
        attack_angles = [s.attack_angle for s in club_shots if s.attack_angle is not None]
        apexes = [s.apex for s in club_shots if s.apex is not None]
        descent_angles = [s.descent_angle for s in club_shots if s.descent_angle is not None]
        flight_times = [s.flight_time for s in club_shots if s.flight_time is not None]
        carries = [s.carry for s in club_shots]
        totals = [s.total for s in club_shots if s.total is not None]

        avg_carry = safe_mean(carries)
        avg_total = safe_mean(totals)
        avg_apex = safe_mean(apexes)

        # Roll = total - carry (per-shot for accuracy)
        rolls = [
            s.total - s.carry
            for s in club_shots
            if s.total is not None and s.total >= s.carry
        ]
        avg_roll = safe_mean(rolls)
        roll_ratio = None
        if avg_roll is not None and avg_carry is not None and avg_carry > 0:
            roll_ratio = (avg_roll / avg_carry) * 100.0

        # Apex efficiency = apex / carry
        apex_efficiency = None
        if avg_apex is not None and avg_carry is not None and avg_carry > 0:
            apex_efficiency = avg_apex / avg_carry

        # Flight efficiency = flight_time / carry (s/yd)
        avg_flight_time = safe_mean(flight_times)
        flight_efficiency = None
        if avg_flight_time is not None and avg_carry is not None and avg_carry > 0:
            flight_efficiency = avg_flight_time / avg_carry

        avg_descent = safe_mean(descent_angles)

        trajectory_grade = classify_trajectory(
            apex_efficiency, avg_descent, avg_apex, avg_carry, club
        )

        profiles.append(
            ClubTrajectory(
                club=club,
                shot_count=len(club_shots),
                avg_launch_angle=safe_mean(launch_angles),
                median_launch_angle=safe_median(launch_angles),
                avg_ball_speed=safe_mean(ball_speeds),
                avg_attack_angle=safe_mean(attack_angles),
                avg_apex=avg_apex,
                max_apex=safe_max(apexes),
                apex_efficiency=apex_efficiency,
                avg_descent_angle=avg_descent,
                avg_flight_time=avg_flight_time,
                avg_carry=avg_carry,
                avg_total=avg_total,
                avg_roll=avg_roll,
                roll_ratio=roll_ratio,
                trajectory_grade=trajectory_grade,
                flight_efficiency=flight_efficiency,
            )
        )

    # Sort by bag order
    profiles.sort(key=lambda p: get_club_sort_key(p.club, bag_order))
    return profiles


def format_optimal_comparison(profile: ClubTrajectory) -> List[str]:
    """Compare profile to optimal benchmarks and return insight lines."""
    category = _club_category(profile.club)
    benchmarks = OPTIMAL_BENCHMARKS.get(category, OPTIMAL_BENCHMARKS["mid_iron"])
    lines: List[str] = []

    if profile.avg_launch_angle is not None:
        low, high = benchmarks["launch_angle"]
        if profile.avg_launch_angle < low:
            lines.append(
                f"    Launch {fmt(profile.avg_launch_angle)} deg is LOW "
                f"(optimal {fmt(low)}-{fmt(high)} deg) -- consider teeing higher or sweeping more"
            )
        elif profile.avg_launch_angle > high:
            lines.append(
                f"    Launch {fmt(profile.avg_launch_angle)} deg is HIGH "
                f"(optimal {fmt(low)}-{fmt(high)} deg) -- may be hitting up too much or adding loft"
            )

    if profile.avg_apex is not None:
        low, high = benchmarks["apex"]
        if profile.avg_apex < low:
            lines.append(
                f"    Apex {fmt(profile.avg_apex)} yd is LOW "
                f"(optimal {fmt(low)}-{fmt(high)} yd) -- ball not getting enough height"
            )
        elif profile.avg_apex > high:
            lines.append(
                f"    Apex {fmt(profile.avg_apex)} yd is HIGH "
                f"(optimal {fmt(low)}-{fmt(high)} yd) -- may be adding too much spin/loft"
            )

    if profile.avg_descent_angle is not None:
        low, high = benchmarks["descent_angle"]
        if profile.avg_descent_angle < low:
            lines.append(
                f"    Descent {fmt(profile.avg_descent_angle)} deg is SHALLOW "
                f"(optimal {fmt(low)}-{fmt(high)} deg) -- ball won't hold greens"
            )
        elif profile.avg_descent_angle > high:
            lines.append(
                f"    Descent {fmt(profile.avg_descent_angle)} deg is STEEP "
                f"(optimal {fmt(low)}-{fmt(high)} deg) -- losing rollout distance"
            )

    if not lines:
        lines.append("    All trajectory metrics within optimal range")

    return lines


def print_report(profiles: List[ClubTrajectory], carry_column: str, db_path: Path) -> None:
    """Print the full trajectory profiler report to stdout."""
    lines: List[str] = []

    lines.append("=" * 72)
    lines.append("TRAJECTORY PROFILER REPORT")
    lines.append("=" * 72)
    lines.append(f"Database: {db_path}")
    lines.append(
        f"Filters: exclude {', '.join(EXCLUDED_CLUBS)} | "
        f"{carry_column} >= {MIN_CARRY:.0f}"
    )
    lines.append(f"Clubs analyzed: {len(profiles)}")
    lines.append("")

    if not profiles:
        lines.append("No clubs have enough shots for analysis.")
        print("\n".join(lines))
        return

    # --- Per-club profiles ---
    for i, p in enumerate(profiles):
        lines.append("-" * 72)
        lines.append(f"{p.club}  ({p.shot_count} shots)  [{p.trajectory_grade}]")
        lines.append("-" * 72)

        # Launch profile
        lines.append("  LAUNCH PROFILE")
        lines.append(
            f"    Avg launch angle:  {fmt(p.avg_launch_angle)} deg  "
            f"(median {fmt(p.median_launch_angle)} deg)"
        )
        lines.append(f"    Avg ball speed:    {fmt(p.avg_ball_speed)} mph")
        lines.append(f"    Avg attack angle:  {fmt(p.avg_attack_angle)} deg")

        # Peak height
        lines.append("  PEAK HEIGHT")
        lines.append(
            f"    Avg apex:          {fmt(p.avg_apex)} yd  "
            f"(max {fmt(p.max_apex)} yd)"
        )
        lines.append(f"    Apex efficiency:   {fmt(p.apex_efficiency, 3)} (apex/carry ratio)")

        # Landing
        lines.append("  LANDING")
        lines.append(f"    Avg descent angle: {fmt(p.avg_descent_angle)} deg")
        lines.append(f"    Avg flight time:   {fmt(p.avg_flight_time, 2)} sec")

        # Roll
        lines.append("  ROLL")
        lines.append(
            f"    Avg carry:         {fmt(p.avg_carry)} yd  |  "
            f"Avg total: {fmt(p.avg_total)} yd"
        )
        lines.append(
            f"    Avg roll:          {fmt(p.avg_roll)} yd  "
            f"({fmt(p.roll_ratio)}% of carry)"
        )

        # Flight efficiency
        lines.append("  FLIGHT EFFICIENCY")
        if p.flight_efficiency is not None:
            lines.append(
                f"    Hang time / carry: {fmt(p.flight_efficiency, 4)} sec/yd"
            )
        else:
            lines.append("    Hang time / carry: N/A")

        # Optimal comparison
        lines.append("  VS OPTIMAL")
        for insight in format_optimal_comparison(p):
            lines.append(insight)

        lines.append("")

    # --- Roll analysis summary ---
    lines.append("=" * 72)
    lines.append("ROLL ANALYSIS SUMMARY")
    lines.append("=" * 72)

    profiles_with_roll = [p for p in profiles if p.roll_ratio is not None]

    if profiles_with_roll:
        most_roll = max(profiles_with_roll, key=lambda p: p.roll_ratio)  # type: ignore[arg-type]
        least_roll = min(profiles_with_roll, key=lambda p: p.roll_ratio)  # type: ignore[arg-type]

        lines.append(
            f"  Most roll:  {most_roll.club} -- "
            f"{fmt(most_roll.avg_roll)} yd ({fmt(most_roll.roll_ratio)}% of carry)"
        )
        lines.append(
            f"  Least roll: {least_roll.club} -- "
            f"{fmt(least_roll.avg_roll)} yd ({fmt(least_roll.roll_ratio)}% of carry)"
        )

        excessive = [
            p for p in profiles_with_roll
            if p.roll_ratio is not None and p.roll_ratio > EXCESSIVE_ROLL_THRESHOLD
        ]
        if excessive:
            lines.append("")
            lines.append(
                f"  WARNING: {len(excessive)} club(s) with excessive roll "
                f"(>{EXCESSIVE_ROLL_THRESHOLD:.0f}% of carry):"
            )
            for p in excessive:
                lines.append(
                    f"    - {p.club}: {fmt(p.avg_roll)} yd roll "
                    f"({fmt(p.roll_ratio)}%) -- descent may be too shallow"
                )
        else:
            lines.append("  No clubs with excessive roll (all within 20% of carry).")
    else:
        lines.append("  No roll data available (total distance missing).")
    lines.append("")

    # --- Flight efficiency summary ---
    lines.append("=" * 72)
    lines.append("FLIGHT EFFICIENCY SUMMARY")
    lines.append("=" * 72)
    lines.append(
        "  (Lower hang time per yard = more efficient trajectory)"
    )

    profiles_with_eff = [p for p in profiles if p.flight_efficiency is not None]
    if profiles_with_eff:
        most_efficient = min(profiles_with_eff, key=lambda p: p.flight_efficiency)  # type: ignore[arg-type]
        least_efficient = max(profiles_with_eff, key=lambda p: p.flight_efficiency)  # type: ignore[arg-type]

        lines.append(
            f"  Most efficient:  {most_efficient.club} -- "
            f"{fmt(most_efficient.flight_efficiency, 4)} sec/yd"
        )
        lines.append(
            f"  Least efficient: {least_efficient.club} -- "
            f"{fmt(least_efficient.flight_efficiency, 4)} sec/yd"
        )
        lines.append("")

        lines.append("  Club-by-club ranking (best to worst):")
        ranked = sorted(profiles_with_eff, key=lambda p: p.flight_efficiency)  # type: ignore[arg-type]
        for rank, p in enumerate(ranked, start=1):
            lines.append(
                f"    {rank:2d}. {p.club:<20s} "
                f"{fmt(p.flight_efficiency, 4)} sec/yd  "
                f"(carry {fmt(p.avg_carry)} yd, flight {fmt(p.avg_flight_time, 2)} sec)"
            )
    else:
        lines.append("  No flight time data available.")
    lines.append("")

    # --- Trajectory grade summary ---
    lines.append("=" * 72)
    lines.append("TRAJECTORY GRADE SUMMARY")
    lines.append("=" * 72)

    grade_groups: Dict[str, List[str]] = {}
    for p in profiles:
        grade_groups.setdefault(p.trajectory_grade, []).append(p.club)

    for grade in ("Optimal", "Penetrating", "Towering", "Ballooning", "Insufficient Data"):
        clubs = grade_groups.get(grade, [])
        if clubs:
            lines.append(f"  {grade}: {', '.join(clubs)}")

    print("\n".join(lines))


def main() -> int:
    args = parse_args()
    if args.min_shots < 1:
        raise SystemExit("--min-shots must be >= 1")

    bag_order = load_bag_order()

    with build_connection(args.db) as conn:
        carry_column = resolve_carry_column(conn)
        shots = load_shots(conn, carry_column)

    profiles = build_club_profiles(shots, args.min_shots, bag_order)
    print_report(profiles, carry_column, args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
