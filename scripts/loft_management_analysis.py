#!/usr/bin/env python3
"""Analyze dynamic loft and attack angle patterns per club from golf_stats.db.

Examines loft management efficiency: how well you deloft irons, whether
driver attack angle is positive, spin loft proximity to optimal ranges,
and flags clubs that violate expected attack angle patterns.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from statistics import stdev
from typing import Any, Dict, List, Optional

EXCLUDED_CLUBS = ("Other", "Putter", "Sim Round")
MIN_CARRY = 10.0
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
BAG_CONFIG_PATH = Path(__file__).resolve().parents[1] / "my_bag.json"

# Expected static loft per club (degrees) -- used for deloft/add-loft detection.
# These are approximate modern stock lofts; adjust to match your actual set.
EXPECTED_LOFTS: Dict[str, float] = {
    "Driver": 10.5,
    "3 Wood (Cobra)": 15.0,
    "3 Wood (TM)": 15.0,
    "7 Wood": 21.0,
    "3 Iron": 20.0,
    "4 Iron": 22.0,
    "5 Iron": 25.0,
    "6 Iron": 28.0,
    "7 Iron": 31.0,
    "8 Iron": 35.0,
    "9 Iron": 39.0,
    "PW": 43.0,
    "GW": 50.0,
    "SW": 56.0,
    "LW": 60.0,
}

# Optimal spin loft ranges by club category (degrees).
# Spin loft = dynamic_loft - attack_angle.
# Lower spin loft = more compressed / penetrating.
OPTIMAL_SPIN_LOFT: Dict[str, tuple] = {
    "driver": (12.0, 17.0),
    "wood": (14.0, 20.0),
    "long_iron": (14.0, 20.0),
    "mid_iron": (16.0, 22.0),
    "short_iron": (20.0, 28.0),
    "wedge": (28.0, 40.0),
}

# Expected attack angle direction by club category.
# "positive" = hitting up, "negative" = descending blow.
EXPECTED_ATTACK: Dict[str, str] = {
    "driver": "positive",
    "wood": "negative",      # slight negative OK
    "long_iron": "negative",
    "mid_iron": "negative",
    "short_iron": "negative",
    "wedge": "negative",
}


def _club_category(club: str) -> str:
    """Map a club name to its analysis category."""
    if club == "Driver":
        return "driver"
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
        description="Analyze dynamic loft and attack angle patterns per club.",
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


def safe_stdev(values: List[float]) -> Optional[float]:
    """Compute stdev of list with 2+ items, or None."""
    if len(values) < 2:
        return None
    return stdev(values)


def fmt(value: Optional[float], digits: int = 1, sign: bool = False) -> str:
    """Format a float with given precision, or return N/A."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    if sign:
        return f"{value:+.{digits}f}"
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
class LoftShot:
    """One shot's loft-management-relevant fields."""
    club: str
    carry: float
    attack_angle: Optional[float]
    dynamic_loft: Optional[float]
    launch_angle: Optional[float]


@dataclass
class ClubLoftProfile:
    """Aggregated loft management profile for one club."""
    club: str
    category: str
    shot_count: int
    # Coverage
    attack_angle_count: int = 0
    dynamic_loft_count: int = 0
    launch_angle_count: int = 0
    # Attack angle
    avg_attack_angle: Optional[float] = None
    std_attack_angle: Optional[float] = None
    # Dynamic loft
    avg_dynamic_loft: Optional[float] = None
    std_dynamic_loft: Optional[float] = None
    # Spin loft = dynamic_loft - attack_angle (per-shot, then averaged)
    avg_spin_loft: Optional[float] = None
    std_spin_loft: Optional[float] = None
    spin_loft_count: int = 0
    # Launch angle
    avg_launch_angle: Optional[float] = None
    # Loft delta = launch_angle - attack_angle (proxy when dynamic_loft missing)
    avg_loft_delta: Optional[float] = None
    loft_delta_count: int = 0
    # Carry
    avg_carry: Optional[float] = None
    # Efficiency indicators
    loft_assessment: str = ""
    attack_assessment: str = ""
    spin_loft_score: Optional[float] = None  # 0-100
    # Flags
    flags: List[str] = field(default_factory=list)


def load_shots(conn: sqlite3.Connection, carry_column: str) -> List[LoftShot]:
    """Load all qualifying shots for loft management analysis."""
    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            TRIM(club) AS club,
            {carry_column} AS carry_value,
            attack_angle,
            dynamic_loft,
            launch_angle
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND TRIM(club) NOT IN ({placeholders})
          AND {carry_column} IS NOT NULL
          AND {carry_column} >= ?
    """
    params = (*EXCLUDED_CLUBS, MIN_CARRY)
    rows = conn.execute(query, params).fetchall()

    shots: List[LoftShot] = []
    for row in rows:
        carry = to_float(row["carry_value"])
        if carry is None or carry < MIN_CARRY:
            continue

        club = str(row["club"]).strip()
        if not club:
            continue

        shots.append(
            LoftShot(
                club=club,
                carry=carry,
                attack_angle=to_float(row["attack_angle"]),
                dynamic_loft=to_float(row["dynamic_loft"]),
                launch_angle=to_float(row["launch_angle"]),
            )
        )

    return shots


def compute_spin_loft_score(avg_spin_loft: float, category: str) -> float:
    """Rate spin loft proximity to optimal range on a 0-100 scale.

    100 = dead center of optimal range.
    Decays linearly outside the range, reaching 0 at +/- 10 degrees beyond.
    """
    optimal = OPTIMAL_SPIN_LOFT.get(category, OPTIMAL_SPIN_LOFT["mid_iron"])
    low, high = optimal
    mid = (low + high) / 2.0
    half_range = (high - low) / 2.0

    if low <= avg_spin_loft <= high:
        # Within optimal: score based on distance from center
        dist_from_center = abs(avg_spin_loft - mid)
        if half_range == 0:
            return 100.0
        return max(0.0, 100.0 - (dist_from_center / half_range) * 20.0)

    # Outside optimal: decay over 10 degrees
    if avg_spin_loft < low:
        overshoot = low - avg_spin_loft
    else:
        overshoot = avg_spin_loft - high

    decay_range = 10.0
    score = max(0.0, 80.0 * (1.0 - overshoot / decay_range))
    return score


def assess_loft_management(
    avg_dynamic_loft: Optional[float],
    club: str,
    category: str,
) -> str:
    """Assess whether the player is delofting, adding loft, or neutral."""
    if avg_dynamic_loft is None:
        return "No dynamic loft data"

    expected = EXPECTED_LOFTS.get(club)
    if expected is None:
        return "No reference loft"

    delta = avg_dynamic_loft - expected
    # Thresholds: +/- 3 degrees is significant
    if category == "driver":
        # Driver: slightly above static loft is normal (hitting up adds loft)
        if delta > 5.0:
            return "Adding loft (high launch/spin risk)"
        elif delta < -2.0:
            return "Delofting (may lose launch)"
        else:
            return "Neutral (typical)"
    else:
        # Irons: delofting is generally good (compression)
        if delta < -3.0:
            return "Delofting (good compression)"
        elif delta < -1.0:
            return "Slight deloft (solid)"
        elif delta > 3.0:
            return "Adding loft (scoopy contact)"
        elif delta > 1.0:
            return "Slight add loft (check low point)"
        else:
            return "Neutral"


def assess_attack_angle(
    avg_attack: Optional[float],
    club: str,
    category: str,
) -> str:
    """Assess whether attack angle matches expectations for club type."""
    if avg_attack is None:
        return "No attack angle data"

    expected_dir = EXPECTED_ATTACK.get(category, "negative")

    if category == "driver":
        if avg_attack > 0:
            if avg_attack > 6.0:
                return f"Positive ({fmt(avg_attack, 1, True)} deg) -- very steep upward, risk of sky ball"
            return f"Positive ({fmt(avg_attack, 1, True)} deg) -- good, hitting up on driver"
        elif avg_attack > -2.0:
            return f"Slightly negative ({fmt(avg_attack, 1, True)} deg) -- nearly level, acceptable"
        else:
            return f"Negative ({fmt(avg_attack, 1, True)} deg) -- hitting down on driver, losing launch"
    else:
        if avg_attack < 0:
            steepness = abs(avg_attack)
            if category == "wedge" and steepness > 8.0:
                return f"Very steep ({fmt(avg_attack, 1, True)} deg) -- digging, check divots"
            return f"Descending ({fmt(avg_attack, 1, True)} deg) -- correct pattern"
        elif avg_attack > 2.0:
            return f"Positive ({fmt(avg_attack, 1, True)} deg) -- scooping/flipping, should be negative"
        else:
            return f"Nearly level ({fmt(avg_attack, 1, True)} deg) -- could be steeper"


def build_club_profiles(
    shots: List[LoftShot],
    min_shots: int,
    bag_order: List[str],
) -> List[ClubLoftProfile]:
    """Build loft management profiles grouped by club."""
    by_club: Dict[str, List[LoftShot]] = {}
    for shot in shots:
        by_club.setdefault(shot.club, []).append(shot)

    profiles: List[ClubLoftProfile] = []

    for club, club_shots in by_club.items():
        if len(club_shots) < min_shots:
            continue

        category = _club_category(club)

        attack_angles = [s.attack_angle for s in club_shots if s.attack_angle is not None]
        dynamic_lofts = [s.dynamic_loft for s in club_shots if s.dynamic_loft is not None]
        launch_angles = [s.launch_angle for s in club_shots if s.launch_angle is not None]
        carries = [s.carry for s in club_shots]

        # Spin loft: computed per-shot where both fields exist
        spin_lofts = [
            s.dynamic_loft - s.attack_angle
            for s in club_shots
            if s.dynamic_loft is not None and s.attack_angle is not None
        ]

        # Loft delta: launch - attack (proxy for spin loft when dynamic_loft missing)
        loft_deltas = [
            s.launch_angle - s.attack_angle
            for s in club_shots
            if s.launch_angle is not None and s.attack_angle is not None
        ]

        avg_attack = safe_mean(attack_angles)
        avg_dynamic_loft = safe_mean(dynamic_lofts)
        avg_spin_loft = safe_mean(spin_lofts)

        # Spin loft efficiency score
        spin_loft_score = None
        if avg_spin_loft is not None:
            spin_loft_score = round(compute_spin_loft_score(avg_spin_loft, category), 1)

        # Assessments
        loft_assessment = assess_loft_management(avg_dynamic_loft, club, category)
        attack_assessment = assess_attack_angle(avg_attack, club, category)

        # Flags
        flags: List[str] = []
        expected_dir = EXPECTED_ATTACK.get(category, "negative")
        if avg_attack is not None:
            if expected_dir == "positive" and avg_attack < -2.0:
                flags.append("WRONG DIRECTION: attack angle should be positive for driver")
            elif expected_dir == "negative" and avg_attack > 2.0:
                flags.append(f"WRONG DIRECTION: attack angle should be negative for {club}")

        if avg_spin_loft is not None:
            optimal = OPTIMAL_SPIN_LOFT.get(category, OPTIMAL_SPIN_LOFT["mid_iron"])
            if avg_spin_loft < optimal[0] - 5:
                flags.append("Spin loft very low -- may be thinning/topping shots")
            elif avg_spin_loft > optimal[1] + 5:
                flags.append("Spin loft very high -- excessive spin, distance loss likely")

        profiles.append(
            ClubLoftProfile(
                club=club,
                category=category,
                shot_count=len(club_shots),
                attack_angle_count=len(attack_angles),
                dynamic_loft_count=len(dynamic_lofts),
                launch_angle_count=len(launch_angles),
                avg_attack_angle=avg_attack,
                std_attack_angle=safe_stdev(attack_angles),
                avg_dynamic_loft=avg_dynamic_loft,
                std_dynamic_loft=safe_stdev(dynamic_lofts),
                avg_spin_loft=avg_spin_loft,
                std_spin_loft=safe_stdev(spin_lofts),
                spin_loft_count=len(spin_lofts),
                avg_launch_angle=safe_mean(launch_angles),
                avg_loft_delta=safe_mean(loft_deltas),
                loft_delta_count=len(loft_deltas),
                avg_carry=safe_mean(carries),
                loft_assessment=loft_assessment,
                attack_assessment=attack_assessment,
                spin_loft_score=spin_loft_score,
                flags=flags,
            )
        )

    # Sort by bag order
    profiles.sort(key=lambda p: get_club_sort_key(p.club, bag_order))
    return profiles


def coverage_pct(count: int, total: int) -> str:
    """Format a coverage percentage."""
    if total == 0:
        return "0%"
    return f"{count / total * 100:.0f}%"


def print_report(
    profiles: List[ClubLoftProfile],
    carry_column: str,
    db_path: Path,
    min_shots: int,
) -> None:
    """Print the full loft management analysis report to stdout."""
    lines: List[str] = []

    lines.append("=" * 76)
    lines.append("LOFT MANAGEMENT ANALYSIS")
    lines.append("=" * 76)
    lines.append(f"Database: {db_path}")
    lines.append(
        f"Filters: exclude {', '.join(EXCLUDED_CLUBS)} | "
        f"{carry_column} >= {MIN_CARRY:.0f} | min shots >= {min_shots}"
    )
    lines.append(f"Clubs analyzed: {len(profiles)}")
    lines.append("")

    if not profiles:
        lines.append("No clubs have enough shots for analysis.")
        print("\n".join(lines))
        return

    # --- Per-club profiles ---
    for p in profiles:
        lines.append("-" * 76)
        lines.append(f"{p.club}  ({p.shot_count} shots)  avg carry: {fmt(p.avg_carry)} yd")
        lines.append("-" * 76)

        # Data coverage
        lines.append("  DATA COVERAGE")
        lines.append(
            f"    Attack angle:  {p.attack_angle_count}/{p.shot_count} "
            f"({coverage_pct(p.attack_angle_count, p.shot_count)})"
        )
        lines.append(
            f"    Dynamic loft:  {p.dynamic_loft_count}/{p.shot_count} "
            f"({coverage_pct(p.dynamic_loft_count, p.shot_count)})"
        )
        lines.append(
            f"    Launch angle:  {p.launch_angle_count}/{p.shot_count} "
            f"({coverage_pct(p.launch_angle_count, p.shot_count)})"
        )

        # Attack angle
        lines.append("  ATTACK ANGLE")
        if p.avg_attack_angle is not None:
            lines.append(
                f"    Avg: {fmt(p.avg_attack_angle, 1, True)} deg  "
                f"(std: {fmt(p.std_attack_angle)} deg)"
            )
            lines.append(f"    Assessment: {p.attack_assessment}")
        else:
            lines.append("    No attack angle data available")

        # Dynamic loft
        lines.append("  DYNAMIC LOFT")
        if p.avg_dynamic_loft is not None:
            expected = EXPECTED_LOFTS.get(p.club)
            expected_str = f"  (static loft ~{fmt(expected)} deg)" if expected else ""
            lines.append(
                f"    Avg: {fmt(p.avg_dynamic_loft)} deg  "
                f"(std: {fmt(p.std_dynamic_loft)} deg){expected_str}"
            )
            lines.append(f"    Assessment: {p.loft_assessment}")
        else:
            lines.append("    No dynamic loft data available")

        # Spin loft
        lines.append("  SPIN LOFT  (dynamic_loft - attack_angle)")
        if p.avg_spin_loft is not None:
            optimal = OPTIMAL_SPIN_LOFT.get(p.category, OPTIMAL_SPIN_LOFT["mid_iron"])
            lines.append(
                f"    Avg: {fmt(p.avg_spin_loft)} deg  "
                f"(std: {fmt(p.std_spin_loft)} deg)  "
                f"[from {p.spin_loft_count} shots]"
            )
            lines.append(
                f"    Optimal range: {fmt(optimal[0])}-{fmt(optimal[1])} deg  "
                f"| Efficiency score: {fmt(p.spin_loft_score, 0)}/100"
            )
        else:
            lines.append("    Cannot compute (requires both dynamic_loft and attack_angle)")

        # Launch angle reference
        lines.append("  LAUNCH ANGLE (reference)")
        if p.avg_launch_angle is not None:
            lines.append(f"    Avg: {fmt(p.avg_launch_angle)} deg")
        else:
            lines.append("    No launch angle data available")

        # Loft delta proxy
        lines.append("  LOFT DELTA PROXY  (launch_angle - attack_angle)")
        if p.avg_loft_delta is not None:
            lines.append(
                f"    Avg: {fmt(p.avg_loft_delta)} deg  "
                f"[from {p.loft_delta_count} shots]"
            )
            if p.avg_spin_loft is None:
                lines.append(
                    "    (Use as spin loft approximation when dynamic_loft is unavailable)"
                )
        else:
            lines.append("    Cannot compute (requires both launch_angle and attack_angle)")

        # Flags
        if p.flags:
            lines.append("  *** FLAGS ***")
            for flag in p.flags:
                lines.append(f"    ! {flag}")

        lines.append("")

    # --- Attack Angle Progression ---
    lines.append("=" * 76)
    lines.append("ATTACK ANGLE PROGRESSION  (should get more negative as clubs get shorter)")
    lines.append("=" * 76)

    profiles_with_attack = [p for p in profiles if p.avg_attack_angle is not None]
    if profiles_with_attack:
        # Visual bar chart
        max_abs = max(abs(p.avg_attack_angle) for p in profiles_with_attack if p.avg_attack_angle is not None)
        scale = 30.0 / max(max_abs, 1.0)  # fit bars in 30 chars

        for p in profiles_with_attack:
            aa = p.avg_attack_angle
            if aa is None:
                continue
            bar_len = int(abs(aa) * scale)
            if aa >= 0:
                bar = " " * 15 + "|" + "+" * bar_len
            else:
                pad = 15 - bar_len
                bar = " " * max(pad, 0) + "-" * bar_len + "|"
            lines.append(f"  {p.club:<20s} {bar}  {fmt(aa, 1, True)} deg")

        lines.append("")
        lines.append("  Legend: --- descending (negative) | +++ ascending (positive)")
    else:
        lines.append("  No attack angle data available.")
    lines.append("")

    # --- Spin Loft Efficiency Ranking ---
    lines.append("=" * 76)
    lines.append("SPIN LOFT EFFICIENCY RANKING")
    lines.append("=" * 76)
    lines.append(
        "  Score: 100 = center of optimal range, decays outside. "
        "Higher = more efficient."
    )
    lines.append("")

    profiles_with_score = [
        p for p in profiles if p.spin_loft_score is not None
    ]
    if profiles_with_score:
        ranked = sorted(profiles_with_score, key=lambda p: p.spin_loft_score or 0, reverse=True)
        for rank, p in enumerate(ranked, start=1):
            optimal = OPTIMAL_SPIN_LOFT.get(p.category, OPTIMAL_SPIN_LOFT["mid_iron"])
            in_range = ""
            if p.avg_spin_loft is not None:
                if optimal[0] <= p.avg_spin_loft <= optimal[1]:
                    in_range = " [IN RANGE]"
                elif p.avg_spin_loft < optimal[0]:
                    in_range = " [BELOW]"
                else:
                    in_range = " [ABOVE]"
            # Score bar
            bar_len = int((p.spin_loft_score or 0) / 100.0 * 20)
            bar = "#" * bar_len + "." * (20 - bar_len)
            lines.append(
                f"  {rank:2d}. {p.club:<20s} "
                f"[{bar}] {fmt(p.spin_loft_score, 0):>3s}/100  "
                f"spin loft {fmt(p.avg_spin_loft)} deg "
                f"(opt {fmt(optimal[0])}-{fmt(optimal[1])}){in_range}"
            )
    else:
        lines.append("  No spin loft data available (need both dynamic_loft and attack_angle).")
    lines.append("")

    # --- Dynamic Loft Coverage Summary ---
    lines.append("=" * 76)
    lines.append("DYNAMIC LOFT COVERAGE SUMMARY")
    lines.append("=" * 76)

    total_shots = sum(p.shot_count for p in profiles)
    total_dl = sum(p.dynamic_loft_count for p in profiles)
    total_aa = sum(p.attack_angle_count for p in profiles)
    total_la = sum(p.launch_angle_count for p in profiles)

    lines.append(f"  Total shots analyzed: {total_shots}")
    lines.append(
        f"  Dynamic loft coverage:  {total_dl}/{total_shots} "
        f"({coverage_pct(total_dl, total_shots)})"
    )
    lines.append(
        f"  Attack angle coverage:  {total_aa}/{total_shots} "
        f"({coverage_pct(total_aa, total_shots)})"
    )
    lines.append(
        f"  Launch angle coverage:  {total_la}/{total_shots} "
        f"({coverage_pct(total_la, total_shots)})"
    )
    lines.append("")

    low_coverage = [p for p in profiles if p.dynamic_loft_count < p.shot_count * 0.5]
    if low_coverage:
        lines.append("  Clubs with <50% dynamic loft coverage:")
        for p in low_coverage:
            lines.append(
                f"    - {p.club}: {coverage_pct(p.dynamic_loft_count, p.shot_count)} "
                f"({p.dynamic_loft_count}/{p.shot_count})"
            )
        lines.append(
            "  Tip: loft delta (launch - attack) is used as a proxy where dynamic loft is missing."
        )
    else:
        lines.append("  All clubs have >= 50% dynamic loft coverage.")
    lines.append("")

    # --- Flags Summary ---
    all_flags = [(p.club, flag) for p in profiles for flag in p.flags]
    lines.append("=" * 76)
    lines.append("FLAGS AND ALERTS")
    lines.append("=" * 76)

    if all_flags:
        for club, flag in all_flags:
            lines.append(f"  ! {club}: {flag}")
    else:
        lines.append("  No flags -- all clubs within expected patterns.")
    lines.append("")

    # --- Recommendations ---
    lines.append("=" * 76)
    lines.append("RECOMMENDATIONS")
    lines.append("=" * 76)

    recs: List[str] = []

    # Check driver attack angle
    driver_profiles = [p for p in profiles if p.club == "Driver"]
    if driver_profiles:
        dp = driver_profiles[0]
        if dp.avg_attack_angle is not None and dp.avg_attack_angle < 0:
            recs.append(
                f"Driver: attack angle is {fmt(dp.avg_attack_angle, 1, True)} deg (negative). "
                "Tee higher and move ball position forward to hit up on the ball."
            )

    # Check for scooping irons
    scoopy = [
        p for p in profiles
        if p.category in ("mid_iron", "short_iron", "wedge")
        and p.avg_attack_angle is not None
        and p.avg_attack_angle > 0
    ]
    if scoopy:
        names = ", ".join(p.club for p in scoopy)
        recs.append(
            f"Scooping detected in: {names}. Attack angle should be negative. "
            "Focus on ball-first contact and forward shaft lean at impact."
        )

    # Check spin loft efficiency
    low_eff = [
        p for p in profiles_with_score
        if p.spin_loft_score is not None and p.spin_loft_score < 50
    ]
    if low_eff:
        names = ", ".join(p.club for p in low_eff)
        recs.append(
            f"Low spin loft efficiency: {names}. "
            "Work on matching attack angle to loft presentation for better compression."
        )

    # Check for adding loft in irons
    adding_loft = [
        p for p in profiles
        if "Adding loft" in p.loft_assessment
        and p.category in ("mid_iron", "short_iron", "long_iron")
    ]
    if adding_loft:
        names = ", ".join(p.club for p in adding_loft)
        recs.append(
            f"Adding loft at impact: {names}. "
            "This often means flipping or early extension. Practice forward press drills."
        )

    # General
    if not recs:
        recs.append(
            "Loft management looks solid across the bag. "
            "Continue monitoring spin loft consistency as swing changes develop."
        )

    for i, rec in enumerate(recs, start=1):
        lines.append(f"  {i}. {rec}")

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
    print_report(profiles, carry_column, args.db, args.min_shots)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
