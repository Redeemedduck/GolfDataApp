#!/usr/bin/env python3
"""Generate a comprehensive club-by-club performance report from golf_stats.db."""

from __future__ import annotations

import argparse
import math
import sqlite3
import statistics
from collections import defaultdict
from typing import Dict, Iterable, List


EXCLUDED_CLUBS = {"Sim Round", "Other", "Putter"}


def to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values: List[float]) -> float:
    if not values:
        return math.nan
    return statistics.fmean(values)


def std_dev(values: List[float]) -> float:
    # Use sample standard deviation; return 0 for a single observation.
    if not values:
        return math.nan
    if len(values) == 1:
        return 0.0
    return statistics.stdev(values)


def format_num(value: float, decimals: int = 2) -> str:
    if value is None or math.isnan(value):
        return "N/A"
    return f"{value:.{decimals}f}"


def render_table(headers: List[str], rows: List[List[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    out = [sep]
    out.append(
        "| "
        + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers)))
        + " |"
    )
    out.append(sep)
    for row in rows:
        formatted_cells = []
        for i, cell in enumerate(row):
            if i == 0:
                formatted_cells.append(cell.ljust(widths[i]))
            else:
                formatted_cells.append(cell.rjust(widths[i]))
        out.append("| " + " | ".join(formatted_cells) + " |")
    out.append(sep)
    return "\n".join(out)


def generate_report(db_path: str) -> str:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS total_shots FROM shots")
        total_shots = int(cursor.fetchone()["total_shots"])

        cursor.execute("SELECT COUNT(DISTINCT session_date) AS sessions FROM shots")
        session_count = int(cursor.fetchone()["sessions"])

        placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
        cursor.execute(
            f"""
            SELECT club, carry, ball_speed, smash, launch_angle
            FROM shots
            WHERE club IS NOT NULL
              AND TRIM(club) != ''
              AND club NOT IN ({placeholders})
            """,
            tuple(EXCLUDED_CLUBS),
        )
        rows = cursor.fetchall()

    by_club: Dict[str, List[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        by_club[row["club"]].append(row)

    table_rows: List[List[str]] = []
    for club, shots in by_club.items():
        carry_values = [v for v in (to_float(r["carry"]) for r in shots) if v is not None]
        ball_speed_values = [v for v in (to_float(r["ball_speed"]) for r in shots) if v is not None]
        smash_values = [v for v in (to_float(r["smash"]) for r in shots) if v is not None]
        launch_values = [v for v in (to_float(r["launch_angle"]) for r in shots) if v is not None]

        avg_carry = mean(carry_values)
        std_carry = std_dev(carry_values)
        avg_ball_speed = mean(ball_speed_values)
        std_ball_speed = std_dev(ball_speed_values)
        avg_smash = mean(smash_values)
        std_smash = std_dev(smash_values)
        avg_launch = mean(launch_values)
        std_launch = std_dev(launch_values)

        best_carry = max(carry_values) if carry_values else math.nan
        worst_carry = min(carry_values) if carry_values else math.nan
        if math.isnan(avg_carry) or avg_carry == 0 or math.isnan(std_carry):
            consistency_score = math.nan
        else:
            consistency_score = 1 - (std_carry / avg_carry)

        table_rows.append(
            [
                club,
                format_num(avg_carry),
                format_num(std_carry),
                format_num(avg_ball_speed),
                format_num(std_ball_speed),
                format_num(avg_smash, 3),
                format_num(std_smash, 3),
                format_num(avg_launch),
                format_num(std_launch),
                format_num(consistency_score, 3),
                format_num(best_carry),
                format_num(worst_carry),
                str(len(shots)),
            ]
        )

    def sort_key(row: List[str]) -> float:
        try:
            return float(row[1])
        except ValueError:
            return float("-inf")

    table_rows.sort(key=sort_key, reverse=True)

    headers = [
        "Club",
        "Avg Carry",
        "Std Carry",
        "Avg BallSpd",
        "Std BallSpd",
        "Avg Smash",
        "Std Smash",
        "Avg Launch",
        "Std Launch",
        "Carry Consistency",
        "Best Carry",
        "Worst Carry",
        "Shot Count",
    ]

    lines = [
        "COMPREHENSIVE CLUB-BY-CLUB PERFORMANCE REPORT",
        f"Database: {db_path}",
        f"All shots: {total_shots}",
        f"All sessions (distinct session_date): {session_count}",
        f"Included shots (excluding {', '.join(sorted(EXCLUDED_CLUBS))}): {len(rows)}",
        "",
        render_table(headers, table_rows),
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path",
        default="golf_stats.db",
        help="Path to SQLite database file (default: golf_stats.db)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(generate_report(args.db_path))


if __name__ == "__main__":
    main()
