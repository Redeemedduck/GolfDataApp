#!/usr/bin/env python3
"""Analyze club gapping and recommend bag optimization actions from golf_stats.db."""

from __future__ import annotations

import argparse
import re
import sqlite3
from dataclasses import dataclass

EXCLUDED_CLUBS = ("Other", "Putter", "Sim Round")
OVERLAP_THRESHOLD = 10.0
GAP_THRESHOLD = 15.0
INVERSION_TOLERANCE = 2.0


@dataclass
class ClubStat:
    club: str
    avg_carry: float
    shot_count: int


@dataclass
class Issue:
    issue_type: str
    details: str
    action: str


def club_key(club: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", club.upper())


def parse_iron_number(club: str) -> int | None:
    match = re.search(r"\b(\d{1,2})\s*-?\s*I(?:RON)?\b", club.upper())
    if match:
        return int(match.group(1))

    compact = re.search(r"\b(\d{1,2})I\b", club.upper())
    if compact:
        return int(compact.group(1))

    return None


def parse_wood_number(club: str) -> int | None:
    upper = club.upper()
    match = re.search(r"\b(\d{1,2})\s*-?\s*W(?:OOD)?\b", upper)
    if match:
        return int(match.group(1))

    compact = re.search(r"\b(\d{1,2})W\b", upper)
    if compact:
        return int(compact.group(1))

    return None


def parse_hybrid_number(club: str) -> int | None:
    upper = club.upper()
    match = re.search(r"\b(\d{1,2})\s*-?\s*(?:H|HYBRID)\b", upper)
    if match:
        return int(match.group(1))

    compact = re.search(r"\b(\d{1,2})H\b", upper)
    if compact:
        return int(compact.group(1))

    return None


def parse_wedge_loft(club: str) -> int | None:
    upper = club.upper()
    loft = re.search(r"\b(4\d|5\d|6\d)\s*(?:DEG|°)?\b", upper)
    if loft:
        return int(loft.group(1))
    return None


def club_rank(club: str) -> int | None:
    upper = club.upper().strip()
    key = club_key(club)

    if "DRIVER" in upper or key == "1W":
        return 10

    wood_number = parse_wood_number(club)
    if wood_number is not None:
        return 20 + wood_number

    hybrid_number = parse_hybrid_number(club)
    if hybrid_number is not None:
        return 40 + hybrid_number

    iron_number = parse_iron_number(club)
    if iron_number is not None:
        return 60 + iron_number

    if key in {"PW", "PITCHINGWEDGE"}:
        return 110
    if key in {"AW", "GW", "UW", "APPROACHWEDGE", "GAPWEDGE", "UTILITYWEDGE"}:
        return 115
    if key in {"SW", "SANDWEDGE"}:
        return 120
    if key in {"LW", "LOBWEDGE"}:
        return 125

    wedge_loft = parse_wedge_loft(club)
    if wedge_loft is not None:
        return 100 + wedge_loft

    return None


def format_table(rows: list[list[str]], headers: list[str]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def fmt(row: list[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    separator = "-+-".join("-" * width for width in widths)
    output = [fmt(headers), separator]
    output.extend(fmt(row) for row in rows)
    return "\n".join(output)


def fetch_stats(db_path: str) -> tuple[int, int, list[ClubStat]]:
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()

        cursor.execute("PRAGMA table_info(shots)")
        column_names = {str(row[1]) for row in cursor.fetchall()}
        if "carry_distance" in column_names:
            carry_column = "carry_distance"
        elif "carry" in column_names:
            carry_column = "carry"
        else:
            raise RuntimeError(
                "shots table must contain carry_distance (or carry) column"
            )

        cursor.execute("SELECT COUNT(*) FROM shots")
        total_shots = int(cursor.fetchone()[0])

        placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM shots
            WHERE club IS NOT NULL
              AND TRIM(club) != ''
              AND TRIM(club) NOT IN ({placeholders})
              AND {carry_column} >= 10
            """,
            EXCLUDED_CLUBS,
        )
        included_shots = int(cursor.fetchone()[0])

        cursor.execute(
            f"""
            SELECT
                TRIM(club) AS club,
                AVG({carry_column}) AS avg_carry,
                COUNT(*) AS shot_count
            FROM shots
            WHERE club IS NOT NULL
              AND TRIM(club) != ''
              AND TRIM(club) NOT IN ({placeholders})
              AND {carry_column} >= 10
            GROUP BY TRIM(club)
            HAVING COUNT(*) > 0
            ORDER BY avg_carry DESC, club ASC
            """,
            EXCLUDED_CLUBS,
        )

        club_stats = [
            ClubStat(club=row[0], avg_carry=float(row[1]), shot_count=int(row[2]))
            for row in cursor.fetchall()
            if row[1] is not None
        ]

    return total_shots, included_shots, club_stats


def recommend_for_overlap(longer: ClubStat, shorter: ClubStat, gap: float) -> str:
    iron_num = parse_iron_number(shorter.club) or parse_iron_number(longer.club)
    if iron_num is not None and iron_num <= 4:
        iron_club = shorter.club if parse_iron_number(shorter.club) == iron_num else longer.club
        return (
            f"Replace {iron_club} with a {iron_num} Hybrid to separate these carries "
            f"(current gap {gap:.1f} yd)."
        )

    midpoint = (longer.avg_carry + shorter.avg_carry) / 2
    return (
        f"Choose one primary club between {longer.club} and {shorter.club}, then tune loft/shaft "
        f"or replace the weaker option with a club near {midpoint:.0f} yd carry."
    )


def recommend_for_gap(
    longer: ClubStat,
    shorter: ClubStat,
    gap: float,
    existing_iron_numbers: set[int],
) -> str:
    long_key = club_key(longer.club)
    short_key = club_key(shorter.club)
    pair = {long_key, short_key}

    if {"PW", "GW"}.issubset(pair) or {"PITCHINGWEDGE", "GAPWEDGE"}.issubset(pair):
        return "Add a 52-degree wedge between PW and GW to tighten wedge spacing."
    if {"GW", "SW"}.issubset(pair) or {"GAPWEDGE", "SANDWEDGE"}.issubset(pair):
        return "Add a 54-degree wedge between GW and SW to tighten wedge spacing."
    if {"SW", "LW"}.issubset(pair) or {"SANDWEDGE", "LOBWEDGE"}.issubset(pair):
        return "Add a 58-degree wedge between SW and LW to tighten wedge spacing."

    long_iron = parse_iron_number(longer.club)
    short_iron = parse_iron_number(shorter.club)
    if long_iron is not None and short_iron is not None and short_iron - long_iron > 1:
        missing_iron = long_iron + 1
        if missing_iron in existing_iron_numbers:
            return (
                f"Dial in loft/gapping on your {missing_iron} Iron so it sits between "
                f"{longer.club} and {shorter.club}."
            )
        return f"Add a {missing_iron} Iron between {longer.club} and {shorter.club}."

    if parse_wood_number(longer.club) is not None and parse_iron_number(shorter.club) is not None:
        return (
            f"Add a 4 Hybrid between {longer.club} and {shorter.club} to cover the {gap:.1f} yd gap."
        )

    midpoint = (longer.avg_carry + shorter.avg_carry) / 2
    return (
        f"Add a club that carries about {midpoint:.0f} yd between {longer.club} and {shorter.club}."
    )


def recommend_for_inversion(longer: ClubStat, shorter: ClubStat) -> str:
    long_iron = parse_iron_number(longer.club)
    if long_iron is not None and long_iron <= 5:
        return (
            f"Replace {longer.club} with a {long_iron} Hybrid, or check loft/shaft to restore "
            f"proper gapping below {shorter.club}."
        )

    return (
        f"Check loft/lie and strike quality: {longer.club} should carry farther than {shorter.club}. "
        "Adjust lofts or swap one club to restore order."
    )


def detect_issues(stats: list[ClubStat]) -> list[Issue]:
    issues: list[Issue] = []
    existing_iron_numbers = {
        iron_number
        for iron_number in (parse_iron_number(stat.club) for stat in stats)
        if iron_number is not None
    }

    for index in range(len(stats) - 1):
        longer = stats[index]
        shorter = stats[index + 1]
        gap = longer.avg_carry - shorter.avg_carry

        if gap < OVERLAP_THRESHOLD:
            issues.append(
                Issue(
                    issue_type="Overlap",
                    details=(
                        f"{longer.club} ({longer.avg_carry:.1f} yd) and {shorter.club} "
                        f"({shorter.avg_carry:.1f} yd) are only {gap:.1f} yd apart."
                    ),
                    action=recommend_for_overlap(longer, shorter, gap),
                )
            )

        if gap > GAP_THRESHOLD:
            issues.append(
                Issue(
                    issue_type="Excessive Gap",
                    details=(
                        f"{longer.club} ({longer.avg_carry:.1f} yd) to {shorter.club} "
                        f"({shorter.avg_carry:.1f} yd) leaves a {gap:.1f} yd gap."
                    ),
                    action=recommend_for_gap(longer, shorter, gap, existing_iron_numbers),
                )
            )

    ranked = [(club_rank(stat.club), stat) for stat in stats]
    ranked = [item for item in ranked if item[0] is not None]
    ranked.sort(key=lambda item: item[0])

    for index in range(len(ranked) - 1):
        _, longer = ranked[index]
        _, shorter = ranked[index + 1]

        if shorter.avg_carry > longer.avg_carry + INVERSION_TOLERANCE:
            issues.append(
                Issue(
                    issue_type="Inversion",
                    details=(
                        f"{shorter.club} ({shorter.avg_carry:.1f} yd) carries farther than "
                        f"{longer.club} ({longer.avg_carry:.1f} yd)."
                    ),
                    action=recommend_for_inversion(longer, shorter),
                )
            )

    return issues


def build_report(db_path: str) -> str:
    total_shots, included_shots, stats = fetch_stats(db_path)

    lines: list[str] = []
    lines.append("BAG OPTIMIZATION ADVISOR")
    lines.append(f"Database: {db_path}")
    lines.append(
        "Filters: exclude clubs {clubs}; carry_distance >= 10 yd".format(
            clubs=", ".join(EXCLUDED_CLUBS)
        )
    )
    lines.append(f"Shots analyzed: {included_shots} of {total_shots}")
    lines.append("")

    if not stats:
        lines.append("No qualifying shots found. Add data and rerun.")
        return "\n".join(lines)

    table_rows = [
        [
            str(index + 1),
            stat.club,
            f"{stat.avg_carry:.1f}",
            str(stat.shot_count),
        ]
        for index, stat in enumerate(stats)
    ]
    lines.append("Average Carry by Club (Longest to Shortest)")
    lines.append(format_table(table_rows, ["#", "Club", "Avg Carry (yd)", "Shots"]))
    lines.append("")

    issues = detect_issues(stats)
    if not issues:
        lines.append("No overlap, excessive gaps, or inversions detected with current thresholds.")
        return "\n".join(lines)

    lines.append("Recommendations")
    for index, issue in enumerate(issues, start=1):
        lines.append(f"{index}. [{issue.issue_type}] {issue.details}")
        lines.append(f"   Action: {issue.action}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recommend golf bag optimization actions from shots data")
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
