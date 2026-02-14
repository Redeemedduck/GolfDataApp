#!/usr/bin/env python3
"""Find optimal launch conditions per club by analyzing top-performing shots in golf_stats.db."""

from __future__ import annotations

import argparse
import math
import sqlite3
from dataclasses import dataclass, field
from typing import Any, List


EXCLUDED_CLUBS = ("Other", "Putter", "Sim Round")
MIN_SHOTS = 15
MIN_CARRY = 10
TOP_PERCENTILE = 0.10  # top 10%


@dataclass
class LaunchConditions:
    launch_angle: float = math.nan
    ball_speed: float = math.nan
    back_spin: float = math.nan
    attack_angle: float = math.nan
    carry: float = math.nan


@dataclass
class ClubAnalysis:
    club: str
    shot_count: int
    current: LaunchConditions
    optimal: LaunchConditions
    efficiency: float  # current avg carry / top 10% avg carry * 100
    adjustments: List[str] = field(default_factory=list)


def safe_float(value: Any) -> float | None:
    """Convert a database value to float, returning None for NULL/invalid."""
    if value is None:
        return None
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def safe_round(value: float, digits: int = 1) -> str:
    """Format a float for display, returning '-' for NaN/None."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "-"
    return f"{value:.{digits}f}"


def detect_carry_column(cursor: sqlite3.Cursor) -> str:
    """Detect whether the carry column is named carry_distance or carry."""
    cursor.execute("PRAGMA table_info(shots)")
    columns = {str(row[1]) for row in cursor.fetchall()}
    if "carry_distance" in columns:
        return "carry_distance"
    if "carry" in columns:
        return "carry"
    raise RuntimeError("shots table must contain a carry_distance or carry column")


def mean_of(values: list[float]) -> float:
    """Mean of a list, or NaN if empty."""
    if not values:
        return math.nan
    return sum(values) / len(values)


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render an ASCII table with aligned columns."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"

    def fmt_row(row: list[str]) -> str:
        cells = []
        for i, cell in enumerate(row):
            if i == 0:
                cells.append(cell.ljust(widths[i]))
            else:
                cells.append(cell.rjust(widths[i]))
        return "| " + " | ".join(cells) + " |"

    lines = [sep, fmt_row(headers), sep]
    lines.extend(fmt_row(row) for row in rows)
    lines.append(sep)
    return "\n".join(lines)


def compute_adjustments(current: LaunchConditions, optimal: LaunchConditions, club: str) -> list[str]:
    """Generate specific adjustment recommendations comparing current vs optimal."""
    adjustments: list[str] = []

    # Launch angle
    if not math.isnan(current.launch_angle) and not math.isnan(optimal.launch_angle):
        diff = optimal.launch_angle - current.launch_angle
        if abs(diff) >= 0.5:
            direction = "increase" if diff > 0 else "decrease"
            adjustments.append(f"{direction} launch angle by {abs(diff):.1f} deg")

    # Ball speed
    if not math.isnan(current.ball_speed) and not math.isnan(optimal.ball_speed):
        diff = optimal.ball_speed - current.ball_speed
        if abs(diff) >= 1.0:
            direction = "increase" if diff > 0 else "decrease"
            adjustments.append(f"{direction} ball speed by {abs(diff):.1f} mph")

    # Spin rate
    if not math.isnan(current.back_spin) and not math.isnan(optimal.back_spin):
        diff = optimal.back_spin - current.back_spin
        if abs(diff) >= 100:
            direction = "increase" if diff > 0 else "reduce"
            adjustments.append(f"{direction} spin by {abs(diff):.0f} rpm")

    # Attack angle
    if not math.isnan(current.attack_angle) and not math.isnan(optimal.attack_angle):
        diff = optimal.attack_angle - current.attack_angle
        if abs(diff) >= 0.3:
            if diff > 0:
                adjustments.append(f"shallow attack angle by {abs(diff):.1f} deg (more upward)")
            else:
                adjustments.append(f"steepen attack angle by {abs(diff):.1f} deg (more downward)")

    if not adjustments:
        adjustments.append("launch conditions are near-optimal -- maintain current swing")

    return adjustments


def analyze_clubs(db_path: str) -> tuple[int, int, list[ClubAnalysis]]:
    """Query the database and compute per-club launch optimization data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read-only mode
    cursor.execute("PRAGMA query_only = ON")

    carry_col = detect_carry_column(cursor)

    # Total shot count
    cursor.execute("SELECT COUNT(*) FROM shots")
    total_shots = int(cursor.fetchone()[0])

    # Fetch qualifying shots
    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    cursor.execute(
        f"""
        SELECT
            TRIM(club) AS club,
            {carry_col} AS carry,
            launch_angle,
            ball_speed,
            back_spin,
            attack_angle
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND TRIM(club) NOT IN ({placeholders})
          AND {carry_col} >= ?
        ORDER BY club, {carry_col} DESC
        """,
        (*EXCLUDED_CLUBS, MIN_CARRY),
    )
    rows = cursor.fetchall()
    conn.close()

    # Group by club
    clubs: dict[str, list[tuple]] = {}
    for row in rows:
        club_name = row[0]
        if club_name not in clubs:
            clubs[club_name] = []
        clubs[club_name].append(row)

    included_shots = sum(len(shots) for shots in clubs.values())
    results: list[ClubAnalysis] = []

    for club_name, shots in sorted(clubs.items()):
        if len(shots) < MIN_SHOTS:
            continue

        # Extract numeric values
        carries = [safe_float(s[1]) for s in shots]
        launch_angles = [safe_float(s[2]) for s in shots]
        ball_speeds = [safe_float(s[3]) for s in shots]
        back_spins = [safe_float(s[4]) for s in shots]
        attack_angles = [safe_float(s[5]) for s in shots]

        valid_carries = [c for c in carries if c is not None]
        if not valid_carries:
            continue

        # Current averages (all shots)
        current = LaunchConditions(
            launch_angle=mean_of([v for v in launch_angles if v is not None]),
            ball_speed=mean_of([v for v in ball_speeds if v is not None]),
            back_spin=mean_of([v for v in back_spins if v is not None]),
            attack_angle=mean_of([v for v in attack_angles if v is not None]),
            carry=mean_of(valid_carries),
        )

        # Top 10% of carry shots
        sorted_carries = sorted(valid_carries, reverse=True)
        top_n = max(1, int(math.ceil(len(sorted_carries) * TOP_PERCENTILE)))
        carry_threshold = sorted_carries[top_n - 1]

        # Find indices of top-carry shots
        top_launch = []
        top_speed = []
        top_spin = []
        top_attack = []
        top_carry_values = []
        for i, c in enumerate(carries):
            if c is not None and c >= carry_threshold and len(top_carry_values) < top_n:
                top_carry_values.append(c)
                if launch_angles[i] is not None:
                    top_launch.append(launch_angles[i])
                if ball_speeds[i] is not None:
                    top_speed.append(ball_speeds[i])
                if back_spins[i] is not None:
                    top_spin.append(back_spins[i])
                if attack_angles[i] is not None:
                    top_attack.append(attack_angles[i])

        optimal = LaunchConditions(
            launch_angle=mean_of(top_launch),
            ball_speed=mean_of(top_speed),
            back_spin=mean_of(top_spin),
            attack_angle=mean_of(top_attack),
            carry=mean_of(top_carry_values),
        )

        # Efficiency
        if math.isnan(current.carry) or math.isnan(optimal.carry) or optimal.carry == 0:
            efficiency = math.nan
        else:
            efficiency = (current.carry / optimal.carry) * 100.0

        adjustments = compute_adjustments(current, optimal, club_name)

        results.append(
            ClubAnalysis(
                club=club_name,
                shot_count=len(shots),
                current=current,
                optimal=optimal,
                efficiency=efficiency,
                adjustments=adjustments,
            )
        )

    # Sort by current carry descending (longest clubs first)
    results.sort(key=lambda a: a.current.carry if not math.isnan(a.current.carry) else 0, reverse=True)

    return total_shots, included_shots, results


def build_report(db_path: str) -> str:
    """Build the full text report."""
    total_shots, included_shots, analyses = analyze_clubs(db_path)

    lines: list[str] = []
    lines.append("LAUNCH CONDITION OPTIMIZER")
    lines.append("=" * 60)
    lines.append(f"Database: {db_path}")
    lines.append(f"Filters: exclude {', '.join(EXCLUDED_CLUBS)}; carry >= {MIN_CARRY}; min {MIN_SHOTS} shots/club")
    lines.append(f"Shots: {included_shots} of {total_shots} total (top {int(TOP_PERCENTILE * 100)}% = optimal)")
    lines.append("")

    if not analyses:
        lines.append("No clubs with enough qualifying shots found.")
        lines.append(f"Need at least {MIN_SHOTS} shots per club with carry >= {MIN_CARRY}.")
        return "\n".join(lines)

    # --- Summary Table ---
    lines.append("CURRENT vs OPTIMAL LAUNCH CONDITIONS")
    lines.append("-" * 60)

    headers = [
        "Club",
        "Shots",
        "Cur Carry",
        "Top Carry",
        "Eff %",
        "Cur LA",
        "Opt LA",
        "Cur BS",
        "Opt BS",
        "Cur Spin",
        "Opt Spin",
        "Cur AA",
        "Opt AA",
    ]

    table_rows: list[list[str]] = []
    for a in analyses:
        table_rows.append([
            a.club,
            str(a.shot_count),
            safe_round(a.current.carry),
            safe_round(a.optimal.carry),
            safe_round(a.efficiency),
            safe_round(a.current.launch_angle),
            safe_round(a.optimal.launch_angle),
            safe_round(a.current.ball_speed),
            safe_round(a.optimal.ball_speed),
            safe_round(a.current.back_spin, 0),
            safe_round(a.optimal.back_spin, 0),
            safe_round(a.current.attack_angle),
            safe_round(a.optimal.attack_angle),
        ])

    lines.append(format_table(headers, table_rows))
    lines.append("")

    # Legend
    lines.append("Legend: LA=Launch Angle (deg), BS=Ball Speed (mph), Spin (rpm), AA=Attack Angle (deg)")
    lines.append(f"        Eff %=Current Avg Carry / Top {int(TOP_PERCENTILE * 100)}% Avg Carry x 100")
    lines.append("")

    # --- Per-club recommendations ---
    lines.append("ADJUSTMENT RECOMMENDATIONS")
    lines.append("-" * 60)

    for a in analyses:
        carry_gap = a.optimal.carry - a.current.carry
        if math.isnan(carry_gap):
            carry_gap_str = "N/A"
        else:
            carry_gap_str = f"+{carry_gap:.1f}" if carry_gap > 0 else f"{carry_gap:.1f}"

        lines.append(f"\n{a.club} ({a.shot_count} shots) -- efficiency: {safe_round(a.efficiency)}%, carry gap: {carry_gap_str} yd")
        for adj in a.adjustments:
            lines.append(f"  -> {adj}")

    lines.append("")

    # --- Biggest opportunities ---
    lines.append("BIGGEST OPPORTUNITIES")
    lines.append("-" * 60)

    ranked = sorted(
        [a for a in analyses if not math.isnan(a.efficiency)],
        key=lambda a: a.efficiency,
    )

    if ranked:
        for i, a in enumerate(ranked[:5], start=1):
            carry_gap = a.optimal.carry - a.current.carry
            gap_str = f"+{carry_gap:.1f}" if not math.isnan(carry_gap) and carry_gap > 0 else (f"{carry_gap:.1f}" if not math.isnan(carry_gap) else "N/A")
            lines.append(
                f"  {i}. {a.club}: {safe_round(a.efficiency)}% efficient -- "
                f"{gap_str} yd potential gain"
            )
    else:
        lines.append("  Not enough data to rank opportunities.")

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find optimal launch conditions per club from golf shot data"
    )
    parser.add_argument(
        "--db",
        default="golf_stats.db",
        help="Path to SQLite database (default: golf_stats.db)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(build_report(args.db))


if __name__ == "__main__":
    main()
