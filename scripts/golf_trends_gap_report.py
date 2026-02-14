#!/usr/bin/env python3
"""Golf trends, gapping, and practice recommendation report."""

from __future__ import annotations

import argparse
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Iterable

EXCLUDED_CLUBS = {"Sim Round", "Other", "Putter"}
MISHIT_CARRY_THRESHOLD = 10.0
RELIABLE_SAMPLE_SIZE = 20


@dataclass
class Shot:
    club: str
    carry: float
    smash: float | None
    club_speed: float | None
    ball_speed: float | None
    launch_angle: float | None
    back_spin: float | None
    side_spin: float | None
    face_angle: float | None
    club_path: float | None
    face_to_path: float | None
    attack_angle: float | None
    impact_x: float | None
    impact_y: float | None
    strike_distance: float | None
    side_distance: float | None
    apex: float | None
    descent_angle: float | None
    session_date: str
    session_id: str


@dataclass
class ClubStats:
    club: str
    shots: int
    avg_carry: float
    std_carry: float
    cv: float


def mean(values: Iterable[float]) -> float:
    values_list = list(values)
    return sum(values_list) / len(values_list) if values_list else float("nan")


def std_dev_sample(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg_value = mean(values)
    variance = sum((value - avg_value) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def format_num(value: float | None, decimals: int = 1, nan_text: str = "-") -> str:
    if value is None:
        return nan_text
    if isinstance(value, float) and math.isnan(value):
        return nan_text
    return f"{value:.{decimals}f}"


def print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    if not rows:
        print("(no data)")
        return

    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(str(cell)))

    header_row = "  ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers))
    divider = "  ".join("-" * widths[idx] for idx in range(len(headers)))
    print(header_row)
    print(divider)

    for row in rows:
        print("  ".join(str(cell).ljust(widths[idx]) for idx, cell in enumerate(row)))


def build_connection(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def fetch_shots(connection: sqlite3.Connection) -> tuple[list[Shot], int, int]:
    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            session_id,
            session_date,
            club,
            carry,
            total,
            smash,
            club_speed,
            ball_speed,
            launch_angle,
            back_spin,
            side_spin,
            face_angle,
            club_path,
            face_to_path,
            attack_angle,
            impact_x,
            impact_y,
            strike_distance,
            side_distance,
            apex,
            descent_angle
        FROM shots
        WHERE club NOT IN ({placeholders})
          AND carry IS NOT NULL
          AND session_date IS NOT NULL
    """

    raw_rows = connection.execute(query, tuple(EXCLUDED_CLUBS)).fetchall()

    valid_shots: list[Shot] = []
    mishit_count = 0

    for row in raw_rows:
        carry = float(row["carry"])
        if carry < MISHIT_CARRY_THRESHOLD:
            mishit_count += 1
            continue

        valid_shots.append(
            Shot(
                club=row["club"],
                carry=carry,
                smash=row["smash"],
                club_speed=row["club_speed"],
                ball_speed=row["ball_speed"],
                launch_angle=row["launch_angle"],
                back_spin=row["back_spin"],
                side_spin=row["side_spin"],
                face_angle=row["face_angle"],
                club_path=row["club_path"],
                face_to_path=row["face_to_path"],
                attack_angle=row["attack_angle"],
                impact_x=row["impact_x"],
                impact_y=row["impact_y"],
                strike_distance=row["strike_distance"],
                side_distance=row["side_distance"],
                apex=row["apex"],
                descent_angle=row["descent_angle"],
                session_date=str(row["session_date"]),
                session_id=str(row["session_id"]),
            )
        )

    return valid_shots, mishit_count, len(raw_rows)


def monthly_trends(shots: list[Shot]) -> list[list[str]]:
    by_month: dict[str, list[Shot]] = defaultdict(list)
    for shot in shots:
        month = shot.session_date[:7]
        by_month[month].append(shot)

    rows: list[list[str]] = []
    for month in sorted(by_month):
        month_shots = by_month[month]
        avg_carry = mean(shot.carry for shot in month_shots)
        smash_values = [shot.smash for shot in month_shots if shot.smash is not None]
        avg_smash = mean(smash_values) if smash_values else float("nan")

        rows.append(
            [
                month,
                str(len(month_shots)),
                format_num(avg_carry, 1),
                format_num(avg_smash, 3),
            ]
        )

    return rows


def last_sessions(shots: list[Shot], limit: int = 5) -> list[list[str]]:
    sessions: dict[tuple[str, str], list[Shot]] = defaultdict(list)
    for shot in shots:
        session_day = shot.session_date[:10]
        key = (session_day, shot.session_id)
        sessions[key].append(shot)

    sorted_sessions = sorted(
        sessions.items(),
        key=lambda item: (item[0][0], item[0][1]),
        reverse=True,
    )

    rows: list[list[str]] = []
    for (session_day, _session_id), session_shots in sorted_sessions[:limit]:
        clubs = sorted({shot.club for shot in session_shots})
        rows.append(
            [
                session_day,
                str(len(session_shots)),
                ", ".join(clubs),
                format_num(mean(shot.carry for shot in session_shots), 1),
            ]
        )

    return rows


def club_carry_stats(shots: list[Shot]) -> list[ClubStats]:
    carries_by_club: dict[str, list[float]] = defaultdict(list)
    for shot in shots:
        carries_by_club[shot.club].append(shot.carry)

    stats: list[ClubStats] = []
    for club, carries in carries_by_club.items():
        avg_carry = mean(carries)
        std_carry = std_dev_sample(carries)
        cv = (std_carry / avg_carry) if avg_carry else float("nan")
        stats.append(
            ClubStats(
                club=club,
                shots=len(carries),
                avg_carry=avg_carry,
                std_carry=std_carry,
                cv=cv,
            )
        )

    return stats


def gapping_rows(club_stats: list[ClubStats]) -> tuple[list[list[str]], list[str], list[tuple[ClubStats, ClubStats, float, str]]]:
    ordered = sorted(club_stats, key=lambda stat: stat.avg_carry, reverse=True)
    rows: list[list[str]] = []
    flags: list[str] = []
    anomalies: list[tuple[ClubStats, ClubStats, float, str]] = []

    for index, stat in enumerate(ordered):
        if index == len(ordered) - 1:
            gap_text = "-"
            flag = "-"
        else:
            next_stat = ordered[index + 1]
            gap = stat.avg_carry - next_stat.avg_carry
            gap_text = format_num(gap, 1)

            if gap < 10:
                flag = "OVERLAP (<10yd)"
                anomalies.append((stat, next_stat, gap, flag))
            elif gap > 15:
                flag = "TOO LARGE (>15yd)"
                anomalies.append((stat, next_stat, gap, flag))
            else:
                flag = "OK"

        if flag not in {"OK", "-"}:
            flags.append(f"{stat.club}->{ordered[index + 1].club} {gap_text}yd ({flag})")

        rows.append(
            [
                str(index + 1),
                stat.club,
                str(stat.shots),
                format_num(stat.avg_carry, 1),
                gap_text,
                flag,
            ]
        )

    return rows, flags, anomalies


def consistency_rows(club_stats: list[ClubStats]) -> tuple[list[list[str]], list[ClubStats]]:
    ordered = sorted(club_stats, key=lambda stat: stat.cv)
    rows: list[list[str]] = []

    for index, stat in enumerate(ordered, start=1):
        rows.append(
            [
                str(index),
                stat.club,
                str(stat.shots),
                format_num(stat.avg_carry, 1),
                format_num(stat.std_carry, 1),
                format_num(stat.cv * 100, 1),
            ]
        )

    reliable = [stat for stat in club_stats if stat.shots >= RELIABLE_SAMPLE_SIZE]
    reliable_sorted_desc = sorted(reliable, key=lambda stat: stat.cv, reverse=True)
    return rows, reliable_sorted_desc


def face_path_summary(shots: list[Shot]) -> dict[str, float]:
    face_angles = [shot.face_angle for shot in shots if shot.face_angle is not None]
    club_paths = [shot.club_path for shot in shots if shot.club_path is not None]
    face_to_paths = [shot.face_to_path for shot in shots if shot.face_to_path is not None]

    ftp_open = sum(1 for value in face_to_paths if value > 2)
    ftp_closed = sum(1 for value in face_to_paths if value < -2)
    ftp_neutral = sum(1 for value in face_to_paths if -2 <= value <= 2)

    return {
        "avg_face_angle": mean(face_angles),
        "avg_club_path": mean(club_paths),
        "avg_face_to_path": mean(face_to_paths),
        "open_pct": (ftp_open / len(face_to_paths) * 100) if face_to_paths else float("nan"),
        "closed_pct": (ftp_closed / len(face_to_paths) * 100) if face_to_paths else float("nan"),
        "neutral_pct": (ftp_neutral / len(face_to_paths) * 100) if face_to_paths else float("nan"),
    }


def strike_quality_summary(shots: list[Shot]) -> dict[str, float]:
    strike_distances: list[float] = []
    impact_x_values: list[float] = []
    impact_y_values: list[float] = []

    for shot in shots:
        strike_distance = shot.strike_distance
        if strike_distance is None and shot.impact_x is not None and shot.impact_y is not None:
            strike_distance = math.sqrt((shot.impact_x ** 2) + (shot.impact_y ** 2))

        if strike_distance is not None:
            strike_distances.append(strike_distance)

        if shot.impact_x is not None:
            impact_x_values.append(shot.impact_x)
        if shot.impact_y is not None:
            impact_y_values.append(shot.impact_y)

    center_10_pct = (
        sum(1 for value in strike_distances if value <= 10) / len(strike_distances) * 100
        if strike_distances
        else float("nan")
    )
    center_20_pct = (
        sum(1 for value in strike_distances if value <= 20) / len(strike_distances) * 100
        if strike_distances
        else float("nan")
    )

    return {
        "avg_strike_distance": mean(strike_distances),
        "median_strike_distance": median(strike_distances) if strike_distances else float("nan"),
        "center_10_pct": center_10_pct,
        "center_20_pct": center_20_pct,
        "avg_impact_x": mean(impact_x_values),
        "avg_impact_y": mean(impact_y_values),
        "avg_abs_impact_x": mean(abs(value) for value in impact_x_values),
        "avg_abs_impact_y": mean(abs(value) for value in impact_y_values),
    }


def recommendations(
    reliable_worst: list[ClubStats],
    anomalies: list[tuple[ClubStats, ClubStats, float, str]],
    face_path: dict[str, float],
    strike_quality: dict[str, float],
    mishit_count: int,
    prefilter_count: int,
) -> list[str]:
    recs: list[str] = []

    if len(reliable_worst) >= 2:
        first = reliable_worst[0]
        second = reliable_worst[1]
        recs.append(
            (
                f"Consistency priority: {first.club} (CV {first.cv * 100:.1f}%, sd {first.std_carry:.1f}yd) and "
                f"{second.club} (CV {second.cv * 100:.1f}%, sd {second.std_carry:.1f}yd) are your least stable "
                f"high-sample clubs. Do 3x10-ball ladder sets with each and only move to the next distance "
                f"when 7/10 shots finish within +/-10yd of target carry."
            )
        )

    biggest_excessive = sorted(
        [item for item in anomalies if item[3].startswith("TOO LARGE")],
        key=lambda item: item[2],
        reverse=True,
    )
    if biggest_excessive:
        high, low, gap, _ = biggest_excessive[0]
        target_mid = (high.avg_carry - 12.5 + low.avg_carry + 12.5) / 2
        recs.append(
            (
                f"Largest gap fix: {high.club}->{low.club} is {gap:.1f}yd (target 10-15yd). Build a stock in-between "
                f"shot and calibrate it to ~{target_mid:.0f}yd carry using 20 reps and keep 70% inside +/-8yd."
            )
        )

    biggest_overlap = sorted(
        [item for item in anomalies if item[3].startswith("OVERLAP")],
        key=lambda item: item[2],
    )
    if biggest_overlap:
        high, low, gap, _ = biggest_overlap[0]
        recs.append(
            (
                f"Overlap fix: {high.club}->{low.club} is only {gap:.1f}yd. Re-baseline setup to separate these clubs "
                f"by at least 10yd: lower dynamic loft/ball position slightly for {high.club} and use 15-shot A/B "
                f"tests until average carry separation reaches >=10yd."
            )
        )

    recs.append(
        (
            f"Face/path pattern: mean club path is {face_path['avg_club_path']:.2f}deg and mean face-to-path is "
            f"{face_path['avg_face_to_path']:.2f}deg, with {face_path['open_pct']:.1f}% of shots > +2deg open-to-path. "
            "Run start-line practice (alignment stick + gate) for 40 balls and target reducing open-to-path rate below 30%."
        )
    )

    recs.append(
        (
            f"Strike quality: average strike distance is {strike_quality['avg_strike_distance']:.2f} (median "
            f"{strike_quality['median_strike_distance']:.2f}), and only {strike_quality['center_10_pct']:.1f}% "
            f"are within 10 units of center. Use face spray for 50-ball blocks aiming for >=75% within 10 and "
            f"reduce average abs impact offsets below {strike_quality['avg_abs_impact_x'] - 1:.1f} x / "
            f"{strike_quality['avg_abs_impact_y'] - 1:.1f} y."
        )
    )

    if len(recs) < 5:
        mishit_rate = (mishit_count / prefilter_count * 100) if prefilter_count else 0
        recs.append(
            (
                f"Contact floor: {mishit_count} shots ({mishit_rate:.1f}%) were <10yd and treated as mishits. "
                "Add a 15-ball low-point drill at session start and require >=12/15 solid strikes before full-speed work."
            )
        )

    return recs[:5]


def run_report(db_path: Path) -> None:
    connection = build_connection(db_path)
    try:
        valid_shots, mishit_count, prefilter_count = fetch_shots(connection)
    finally:
        connection.close()

    if not valid_shots:
        raise RuntimeError("No valid shots found after filtering.")

    print("GOLF SHOT PERFORMANCE REPORT")
    print("============================")
    print(f"Database: {db_path}")
    print(
        "Filters: excluded clubs = "
        f"{', '.join(sorted(EXCLUDED_CLUBS))}; mishits removed where carry < {MISHIT_CARRY_THRESHOLD:.0f}"
    )
    print(
        f"Rows considered: {len(valid_shots)} valid shots | {mishit_count} mishits removed "
        f"(from {prefilter_count} shots after club exclusions)"
    )

    print_section("1) MONTHLY TRENDS")
    monthly_rows = monthly_trends(valid_shots)
    print_table(["Month", "Shots", "Avg Carry (yd)", "Avg Smash"], monthly_rows)

    print_section("2) LAST 5 SESSIONS")
    recent_rows = last_sessions(valid_shots, limit=5)
    print_table(["Date", "Shot Count", "Clubs Used", "Avg Carry (yd)"], recent_rows)

    club_stats = club_carry_stats(valid_shots)

    print_section("3) GAPPING ANALYSIS")
    gap_rows, gap_flags, anomalies = gapping_rows(club_stats)
    print_table(
        ["Rank", "Club", "Shots", "Avg Carry (yd)", "Gap To Next (yd)", "Status"],
        gap_rows,
    )
    if gap_flags:
        print("\nFlags:")
        for entry in gap_flags:
            print(f"- {entry}")

    print_section("4) CONSISTENCY RANKING (lower CV = better)")
    consistency_table_rows, reliable_worst = consistency_rows(club_stats)
    print_table(
        ["Rank", "Club", "Shots", "Avg Carry (yd)", "Std Dev (yd)", "CV (%)"],
        consistency_table_rows,
    )

    face_path = face_path_summary(valid_shots)
    strike_quality = strike_quality_summary(valid_shots)

    print_section("5) PRACTICE RECOMMENDATIONS")
    recs = recommendations(
        reliable_worst=reliable_worst,
        anomalies=anomalies,
        face_path=face_path,
        strike_quality=strike_quality,
        mishit_count=mishit_count,
        prefilter_count=prefilter_count,
    )
    for index, rec in enumerate(recs, start=1):
        print(f"{index}. {rec}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze golf shot trends and practice priorities.")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("golf_stats.db"),
        help="Path to SQLite database (default: golf_stats.db)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_report(args.db)


if __name__ == "__main__":
    main()
