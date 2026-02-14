#!/usr/bin/env python3
"""Analyze within-session performance degradation (fatigue) from golf_stats.db."""

from __future__ import annotations

import argparse
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
MIN_CARRY_DISTANCE = 10.0
MIN_SESSION_SHOTS = 20


@dataclass
class ShotRow:
    session_id: str
    session_date: str
    carry: float
    smash: float | None
    strike_distance: float | None
    abs_face_angle: float | None


@dataclass
class SessionFatigue:
    session_id: str
    session_date: str
    shot_count: int
    first_count: int
    second_count: int
    carry_first: float
    carry_second: float
    carry_delta: float
    cv_first: float
    cv_second: float
    cv_delta: float
    smash_first: float | None
    smash_second: float | None
    smash_delta: float | None
    strike_first: float | None
    strike_second: float | None
    strike_delta: float | None
    abs_face_first: float | None
    abs_face_second: float | None
    abs_face_delta: float | None
    worse_count: int
    comparable_metrics: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze within-session fatigue by comparing first-half vs second-half "
            "performance for each qualifying session."
        )
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to SQLite database (default: ./golf_stats.db)",
    )
    parser.add_argument(
        "--min-shots",
        type=int,
        default=MIN_SESSION_SHOTS,
        help="Minimum filtered shots required for a session to be analyzed (default: 20)",
    )
    return parser.parse_args()


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def sample_stddev(values: list[float]) -> float | None:
    if not values:
        return None
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    if avg is None:
        return None
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def coefficient_of_variation(values: list[float]) -> float | None:
    avg = mean(values)
    if avg is None or avg == 0:
        return None
    std = sample_stddev(values)
    if std is None:
        return None
    return std / avg


def format_num(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"


def format_arrow(first: float | None, second: float | None, decimals: int = 2) -> str:
    return f"{format_num(first, decimals)} -> {format_num(second, decimals)}"


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "(no rows)"

    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    sep = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    lines = [sep]
    lines.append("| " + " | ".join(headers[idx].ljust(widths[idx]) for idx in range(len(headers))) + " |")
    lines.append(sep)
    for row in rows:
        formatted = []
        for idx, cell in enumerate(row):
            if idx <= 2:
                formatted.append(cell.ljust(widths[idx]))
            else:
                formatted.append(cell.rjust(widths[idx]))
        lines.append("| " + " | ".join(formatted) + " |")
    lines.append(sep)
    return "\n".join(lines)


def get_table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def carry_column_name(columns: set[str]) -> str:
    if "carry_distance" in columns:
        return "carry_distance"
    if "carry" in columns:
        return "carry"
    raise RuntimeError("shots table is missing both carry_distance and carry columns")


def build_connection(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    connection = sqlite3.connect(str(db_path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA query_only = ON")
    return connection


def normalize_session_day(raw_value: Any) -> str:
    if raw_value is None:
        return "N/A"
    text = str(raw_value).strip()
    if not text:
        return "N/A"
    if len(text) >= 10:
        return text[:10]
    return text


def load_filtered_shots(
    connection: sqlite3.Connection,
    min_carry: float,
) -> tuple[dict[tuple[str, str], list[ShotRow]], int]:
    columns = get_table_columns(connection, "shots")
    carry_col = carry_column_name(columns)

    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            rowid AS row_order,
            session_id,
            session_date,
            {carry_col} AS carry_value,
            smash,
            strike_distance,
            face_angle
        FROM shots
        WHERE session_id IS NOT NULL
          AND club IS NOT NULL
          AND TRIM(club) <> ''
          AND club NOT IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
        ORDER BY session_id ASC, row_order ASC
    """

    params: tuple[Any, ...] = (*tuple(EXCLUDED_CLUBS), min_carry)
    rows = connection.execute(query, params).fetchall()

    by_session: dict[tuple[str, str], list[ShotRow]] = {}
    for row in rows:
        session_id = str(row["session_id"])
        session_day = normalize_session_day(row["session_date"])
        carry = to_float(row["carry_value"])
        if carry is None:
            continue

        shot = ShotRow(
            session_id=session_id,
            session_date=session_day,
            carry=carry,
            smash=to_float(row["smash"]),
            strike_distance=to_float(row["strike_distance"]),
            abs_face_angle=None,
        )
        face_angle = to_float(row["face_angle"])
        if face_angle is not None:
            shot.abs_face_angle = abs(face_angle)
        by_session.setdefault((session_id, session_day), []).append(shot)

    return by_session, len(rows)


def average_optional(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    return mean(clean)


def session_date_label(shots: list[ShotRow]) -> str:
    values = [shot.session_date for shot in shots if shot.session_date and shot.session_date != "N/A"]
    if not values:
        return "N/A"
    return values[-1]


def compute_session_fatigue(shots: list[ShotRow]) -> SessionFatigue:
    midpoint = len(shots) // 2
    first_half = shots[:midpoint]
    second_half = shots[midpoint:]

    carry_first_values = [shot.carry for shot in first_half]
    carry_second_values = [shot.carry for shot in second_half]

    carry_first = mean(carry_first_values) or 0.0
    carry_second = mean(carry_second_values) or 0.0
    carry_delta = carry_second - carry_first

    cv_first_value = coefficient_of_variation(carry_first_values)
    cv_second_value = coefficient_of_variation(carry_second_values)
    cv_first = cv_first_value if cv_first_value is not None else 0.0
    cv_second = cv_second_value if cv_second_value is not None else 0.0
    cv_delta = cv_second - cv_first

    smash_first = average_optional([shot.smash for shot in first_half])
    smash_second = average_optional([shot.smash for shot in second_half])
    smash_delta = (smash_second - smash_first) if smash_first is not None and smash_second is not None else None

    strike_first = average_optional([shot.strike_distance for shot in first_half])
    strike_second = average_optional([shot.strike_distance for shot in second_half])
    strike_delta = (strike_second - strike_first) if strike_first is not None and strike_second is not None else None

    abs_face_first = average_optional([shot.abs_face_angle for shot in first_half])
    abs_face_second = average_optional([shot.abs_face_angle for shot in second_half])
    abs_face_delta = (abs_face_second - abs_face_first) if abs_face_first is not None and abs_face_second is not None else None

    worse_count = 0
    comparable = 2  # carry delta + carry CV delta always available after filters

    if carry_delta < 0:
        worse_count += 1
    if cv_delta > 0:
        worse_count += 1

    if smash_delta is not None:
        comparable += 1
        if smash_delta < 0:
            worse_count += 1
    if strike_delta is not None:
        comparable += 1
        if strike_delta > 0:
            worse_count += 1
    if abs_face_delta is not None:
        comparable += 1
        if abs_face_delta > 0:
            worse_count += 1

    return SessionFatigue(
        session_id=shots[0].session_id,
        session_date=session_date_label(shots),
        shot_count=len(shots),
        first_count=len(first_half),
        second_count=len(second_half),
        carry_first=carry_first,
        carry_second=carry_second,
        carry_delta=carry_delta,
        cv_first=cv_first,
        cv_second=cv_second,
        cv_delta=cv_delta,
        smash_first=smash_first,
        smash_second=smash_second,
        smash_delta=smash_delta,
        strike_first=strike_first,
        strike_second=strike_second,
        strike_delta=strike_delta,
        abs_face_first=abs_face_first,
        abs_face_second=abs_face_second,
        abs_face_delta=abs_face_delta,
        worse_count=worse_count,
        comparable_metrics=comparable,
    )


def mean_or_none(values: list[float]) -> float | None:
    return mean(values)


def percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return 100.0 * numerator / denominator


def aggregate_block(name: str, first_values: list[float], second_values: list[float], worsened: int, better_when_higher: bool) -> list[str]:
    sample = min(len(first_values), len(second_values))
    if sample == 0:
        return [name, "0", "N/A", "N/A", "N/A", "N/A"]

    avg_first = mean_or_none(first_values)
    avg_second = mean_or_none(second_values)
    delta = (avg_second - avg_first) if avg_first is not None and avg_second is not None else None
    direction = "higher is better" if better_when_higher else "lower is better"
    return [
        name,
        str(sample),
        format_arrow(avg_first, avg_second, 3 if name == "Smash factor" else 2),
        format_num(delta, 3 if name == "Smash factor" else 2),
        f"{worsened} ({percent(worsened, sample):.1f}%)",
        direction,
    ]


def recommendation_text(sessions: list[SessionFatigue]) -> str:
    if not sessions:
        return "No qualifying sessions available to estimate fatigue onset."

    fatigue_onsets: list[int] = []
    for session in sessions:
        if session.comparable_metrics == 0:
            continue
        ratio = session.worse_count / session.comparable_metrics
        if ratio >= 0.60:
            # Degradation can only be localized to second-half boundary with this method.
            fatigue_onsets.append(session.first_count + 1)

    if not fatigue_onsets:
        median_length = int(round(median([session.shot_count for session in sessions])))
        return (
            "No strong fatigue signature was detected in most sessions "
            f"(>=60% metrics worsening threshold not met). A session length around {median_length} "
            "shots appears sustainable with current data."
        )

    onset_med = int(round(median(fatigue_onsets)))
    sorted_onsets = sorted(fatigue_onsets)
    p25_index = int(0.25 * (len(sorted_onsets) - 1))
    onset_early = int(round(sorted_onsets[p25_index]))

    recommended_low = max(10, onset_early - 2)
    recommended_high = max(recommended_low, onset_med - 2)

    return (
        "Fatigue most often appears around the midpoint of longer sessions. "
        f"Estimated onset: ~shot {onset_med} (median), with earlier onsets near shot {onset_early}. "
        f"Recommended practice block: {recommended_low}-{recommended_high} shots before taking a reset break."
    )


def build_report(db_path: Path, min_shots: int, min_carry: float) -> str:
    with build_connection(db_path) as connection:
        sessions_map, included_rows = load_filtered_shots(connection, min_carry=min_carry)

    qualifying_sessions: list[SessionFatigue] = []
    for _session_id, shots in sessions_map.items():
        if len(shots) < min_shots:
            continue
        qualifying_sessions.append(compute_session_fatigue(shots))

    qualifying_sessions.sort(key=lambda session: (session.session_date, session.session_id))

    carry_first_values = [session.carry_first for session in qualifying_sessions]
    carry_second_values = [session.carry_second for session in qualifying_sessions]
    carry_worsened = sum(1 for session in qualifying_sessions if session.carry_delta < 0)

    cv_first_values = [session.cv_first for session in qualifying_sessions]
    cv_second_values = [session.cv_second for session in qualifying_sessions]
    cv_worsened = sum(1 for session in qualifying_sessions if session.cv_delta > 0)

    smash_sessions = [session for session in qualifying_sessions if session.smash_first is not None and session.smash_second is not None]
    smash_first_values = [session.smash_first for session in smash_sessions if session.smash_first is not None]
    smash_second_values = [session.smash_second for session in smash_sessions if session.smash_second is not None]
    smash_worsened = sum(1 for session in smash_sessions if session.smash_delta is not None and session.smash_delta < 0)

    strike_sessions = [session for session in qualifying_sessions if session.strike_first is not None and session.strike_second is not None]
    strike_first_values = [session.strike_first for session in strike_sessions if session.strike_first is not None]
    strike_second_values = [session.strike_second for session in strike_sessions if session.strike_second is not None]
    strike_worsened = sum(1 for session in strike_sessions if session.strike_delta is not None and session.strike_delta > 0)

    face_sessions = [session for session in qualifying_sessions if session.abs_face_first is not None and session.abs_face_second is not None]
    face_first_values = [session.abs_face_first for session in face_sessions if session.abs_face_first is not None]
    face_second_values = [session.abs_face_second for session in face_sessions if session.abs_face_second is not None]
    face_worsened = sum(1 for session in face_sessions if session.abs_face_delta is not None and session.abs_face_delta > 0)

    aggregate_rows = [
        aggregate_block("Carry distance", carry_first_values, carry_second_values, carry_worsened, better_when_higher=True),
        aggregate_block("Carry CV", cv_first_values, cv_second_values, cv_worsened, better_when_higher=False),
        aggregate_block("Smash factor", smash_first_values, smash_second_values, smash_worsened, better_when_higher=True),
        aggregate_block("Strike distance", strike_first_values, strike_second_values, strike_worsened, better_when_higher=False),
        aggregate_block("|Face angle|", face_first_values, face_second_values, face_worsened, better_when_higher=False),
    ]

    session_rows: list[list[str]] = []
    for session in qualifying_sessions:
        session_rows.append(
            [
                session.session_date[:10] if session.session_date != "N/A" else "N/A",
                session.session_id,
                str(session.shot_count),
                f"{session.carry_first:.1f}->{session.carry_second:.1f} ({session.carry_delta:+.1f})",
                f"{session.cv_first:.3f}->{session.cv_second:.3f} ({session.cv_delta:+.3f})",
                (
                    f"{session.smash_first:.3f}->{session.smash_second:.3f} ({session.smash_delta:+.3f})"
                    if session.smash_delta is not None and session.smash_first is not None and session.smash_second is not None
                    else "N/A"
                ),
                (
                    f"{session.strike_first:.2f}->{session.strike_second:.2f} ({session.strike_delta:+.2f})"
                    if session.strike_delta is not None and session.strike_first is not None and session.strike_second is not None
                    else "N/A"
                ),
                (
                    f"{session.abs_face_first:.2f}->{session.abs_face_second:.2f} ({session.abs_face_delta:+.2f})"
                    if session.abs_face_delta is not None and session.abs_face_first is not None and session.abs_face_second is not None
                    else "N/A"
                ),
                f"{session.worse_count}/{session.comparable_metrics}",
            ]
        )

    header = [
        "FATIGUE ANALYSIS REPORT",
        f"Database: {db_path}",
        (
            "Filters: exclude clubs "
            + ", ".join(sorted(EXCLUDED_CLUBS))
            + f"; carry >= {min_carry:.0f}; minimum {min_shots} shots/session"
        ),
        f"Included filtered shots: {included_rows}",
        f"Sessions meeting minimum shot count: {len(qualifying_sessions)}",
        "",
        "AGGREGATE PATTERN (first half vs second half)",
        render_table(
            ["Metric", "Sessions", "First -> Second", "Avg Delta", "Worsened Sessions", "Interpretation"],
            aggregate_rows,
        ),
        "",
        "PER-SESSION DEGRADATION METRICS",
        render_table(
            [
                "Date",
                "Session ID",
                "Shots",
                "Carry (1H->2H, d)",
                "Carry CV (1H->2H, d)",
                "Smash (1H->2H, d)",
                "StrikeDist (1H->2H, d)",
                "|FaceAngle| (1H->2H, d)",
                "Worse",
            ],
            session_rows,
        ),
        "",
        "RECOMMENDED SESSION LENGTH",
        recommendation_text(qualifying_sessions),
    ]
    return "\n".join(header)


def main() -> None:
    args = parse_args()
    report = build_report(db_path=args.db, min_shots=args.min_shots, min_carry=MIN_CARRY_DISTANCE)
    print(report)


if __name__ == "__main__":
    main()
