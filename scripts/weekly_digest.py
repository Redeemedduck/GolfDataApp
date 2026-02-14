#!/usr/bin/env python3
"""Generate a weekly golf practice digest from golf_stats.db."""

from __future__ import annotations

import argparse
import math
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import stdev
from typing import Any, Iterable

EXCLUDED_CLUBS = ("Other", "Putter", "Sim Round")
MIN_CARRY = 10.0
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"


@dataclass
class Shot:
    session_day: date
    session_id: str
    club: str
    carry: float
    smash: float | None
    face_to_path: float | None
    strike_distance: float | None


@dataclass
class SessionSummary:
    key: str
    day: date
    session_id: str
    shot_count: int
    carry_avg: float
    smash_avg: float | None
    face_abs_avg: float | None
    strike_abs_avg: float | None
    score: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a weekly practice summary report from shots table data.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=1,
        help="Number of weeks to summarize (default: 1).",
    )
    return parser.parse_args()


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values: Iterable[float]) -> float | None:
    values_list = list(values)
    if not values_list:
        return None
    return sum(values_list) / len(values_list)


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


def load_shots(
    conn: sqlite3.Connection,
    carry_column: str,
    start_day: date,
    end_day: date,
) -> list[Shot]:
    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            DATE(session_date) AS session_day,
            COALESCE(CAST(session_id AS TEXT), '') AS session_id,
            TRIM(club) AS club,
            {carry_column} AS carry_value,
            smash,
            face_to_path,
            strike_distance
        FROM shots
        WHERE session_date IS NOT NULL
          AND club IS NOT NULL
          AND TRIM(club) != ''
          AND TRIM(club) NOT IN ({placeholders})
          AND {carry_column} IS NOT NULL
          AND {carry_column} >= ?
          AND DATE(session_date) BETWEEN ? AND ?
        ORDER BY session_day, session_id
    """
    params = (*EXCLUDED_CLUBS, MIN_CARRY, start_day.isoformat(), end_day.isoformat())
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

        shots.append(
            Shot(
                session_day=shot_day,
                session_id=str(row["session_id"] or "").strip(),
                club=club,
                carry=carry,
                smash=to_float(row["smash"]),
                face_to_path=to_float(row["face_to_path"]),
                strike_distance=to_float(row["strike_distance"]),
            )
        )

    return shots


def quality_score(shots: list[Shot]) -> float:
    smash_avg = mean(shot.smash for shot in shots if shot.smash is not None)
    face_abs_avg = mean(abs(shot.face_to_path) for shot in shots if shot.face_to_path is not None)
    strike_abs_avg = mean(
        abs(shot.strike_distance) for shot in shots if shot.strike_distance is not None
    )

    carries = [shot.carry for shot in shots]
    carry_cv: float | None = None
    if len(carries) >= 2:
        carry_avg = mean(carries)
        if carry_avg is not None and carry_avg > 0:
            carry_cv = stdev(carries) / carry_avg

    smash_component = normalize_higher_better(smash_avg, floor=1.05, ceiling=1.45)
    face_component = normalize_lower_better(face_abs_avg, best=0.5, worst=6.0)
    strike_component = normalize_lower_better(strike_abs_avg, best=3.0, worst=15.0)
    carry_component = normalize_lower_better(carry_cv, best=0.06, worst=0.28)

    weighted = (
        0.35 * smash_component
        + 0.30 * face_component
        + 0.25 * strike_component
        + 0.10 * carry_component
    )
    return round(clamp(weighted * 100.0, 0.0, 100.0), 1)


def summarize_period(shots: list[Shot]) -> dict[str, Any]:
    session_buckets: dict[str, list[Shot]] = defaultdict(list)
    for shot in shots:
        session_suffix = shot.session_id if shot.session_id else "unknown"
        key = f"{shot.session_day.isoformat()}::{session_suffix}"
        session_buckets[key].append(shot)

    sessions: list[SessionSummary] = []
    for key, session_shots in session_buckets.items():
        first = session_shots[0]
        sessions.append(
            SessionSummary(
                key=key,
                day=first.session_day,
                session_id=first.session_id if first.session_id else "unknown",
                shot_count=len(session_shots),
                carry_avg=mean(s.carry for s in session_shots) or 0.0,
                smash_avg=mean(s.smash for s in session_shots if s.smash is not None),
                face_abs_avg=mean(
                    abs(s.face_to_path) for s in session_shots if s.face_to_path is not None
                ),
                strike_abs_avg=mean(
                    abs(s.strike_distance) for s in session_shots if s.strike_distance is not None
                ),
                score=quality_score(session_shots),
            )
        )

    clubs = Counter(shot.club for shot in shots)
    carry_avg = mean(shot.carry for shot in shots)
    smash_avg = mean(shot.smash for shot in shots if shot.smash is not None)
    face_control = mean(abs(shot.face_to_path) for shot in shots if shot.face_to_path is not None)
    strike_quality = mean(
        abs(shot.strike_distance) for shot in shots if shot.strike_distance is not None
    )

    return {
        "total_shots": len(shots),
        "total_sessions": len(session_buckets),
        "clubs": clubs,
        "sessions": sessions,
        "carry_avg": carry_avg,
        "smash_avg": smash_avg,
        "face_control": face_control,
        "strike_quality": strike_quality,
    }


def metric_change(
    label: str,
    current: float | None,
    previous: float | None,
    higher_is_better: bool,
    precision: int = 2,
) -> tuple[str, bool | None]:
    if current is None and previous is None:
        return f"- {label}: N/A (no data in either window)", None
    if current is None:
        return f"- {label}: N/A this period (prev {previous:.{precision}f})", False
    if previous is None:
        return f"- {label}: {current:.{precision}f} (no previous baseline)", None

    delta = current - previous
    epsilon = 0.5 * (10 ** (-precision))
    if abs(delta) < epsilon:
        delta = 0.0
    pct = 0.0 if previous == 0 else (delta / previous) * 100.0
    improved = delta > 0 if higher_is_better else delta < 0

    direction = "improved" if improved else "declined" if delta != 0 else "flat"
    return (
        f"- {label}: {current:.{precision}f} vs {previous:.{precision}f} "
        f"({delta:+.{precision}f}, {pct:+.1f}%) [{direction}]",
        improved if delta != 0 else None,
    )


def session_label(session: SessionSummary) -> str:
    return (
        f"{session.day.isoformat()} | session_id={session.session_id} | "
        f"shots={session.shot_count} | score={session.score:.1f}"
    )


def build_focus_suggestions(
    current: dict[str, Any],
    previous: dict[str, Any],
    trend_flags: dict[str, bool | None],
) -> list[str]:
    suggestions: list[str] = []

    if current["total_sessions"] == 0:
        return [
            "Book at least 2 sessions next week and log 60+ shots to re-establish a baseline.",
        ]

    face_now = current["face_control"]
    strike_now = current["strike_quality"]
    smash_now = current["smash_avg"]

    if trend_flags.get("face_control") is False or (face_now is not None and face_now > 3.5):
        suggestions.append(
            "Face control: run a 30-ball face-to-path gate drill; goal is average |face-to-path| <= 3.0 deg."
        )

    if trend_flags.get("strike_quality") is False or (strike_now is not None and strike_now > 9.0):
        suggestions.append(
            "Strike quality: add centered-contact work (spray/powder) for 20-30 reps per session."
        )

    if trend_flags.get("smash_avg") is False or (smash_now is not None and smash_now < 1.20):
        suggestions.append(
            "Efficiency: prioritize strike-first speed blocks to lift smash by ~0.02 next week."
        )

    if trend_flags.get("carry_avg") is False:
        suggestions.append(
            "Distance: run a carry ladder (3 target distances per focus club) and track average carry by set."
        )

    if not suggestions:
        prev_sessions = previous["total_sessions"]
        if prev_sessions > 0:
            suggestions.append(
                "Maintain current improvements and increase volume slightly (+10-15% shots) without sacrificing quality."
            )
        else:
            suggestions.append(
                "Build baseline consistency with repeatable session structure (warm-up, block, random, review)."
            )

    return suggestions[:3]


def fmt(value: float | None, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{value:.{digits}f}"


def main() -> int:
    args = parse_args()
    if args.weeks < 1:
        raise SystemExit("--weeks must be >= 1")

    days = args.weeks * 7
    end_day = date.today()
    current_start = end_day - timedelta(days=days - 1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)

    with build_connection(args.db) as conn:
        carry_column = resolve_carry_column(conn)
        current_shots = load_shots(conn, carry_column, current_start, end_day)
        previous_shots = load_shots(conn, carry_column, previous_start, previous_end)

    current = summarize_period(current_shots)
    previous = summarize_period(previous_shots)

    lines: list[str] = []
    lines.append("WEEKLY PRACTICE DIGEST")
    lines.append(
        f"Window: {current_start.isoformat()} to {end_day.isoformat()} ({days} days, {args.weeks} week(s))"
    )
    lines.append(
        f"Comparison: {previous_start.isoformat()} to {previous_end.isoformat()} ({days} days)"
    )
    lines.append(
        f"Filters: exclude {', '.join(EXCLUDED_CLUBS)} | {carry_column} >= {MIN_CARRY:.0f}"
    )
    lines.append("")

    lines.append("1) Total sessions and shots")
    lines.append(
        f"- Current: {current['total_sessions']} sessions, {current['total_shots']} shots"
    )
    lines.append(
        f"- Previous: {previous['total_sessions']} sessions, {previous['total_shots']} shots"
    )
    lines.append("")

    lines.append("2) Most practiced clubs (current window)")
    top_clubs = current["clubs"].most_common(5)
    if top_clubs:
        for rank, (club, count) in enumerate(top_clubs, start=1):
            lines.append(f"- {rank}. {club}: {count} shots")
    else:
        lines.append("- No qualifying shots in current window.")
    lines.append("")

    lines.append("3) Key metrics vs previous window")
    trend_flags: dict[str, bool | None] = {}
    metric_lines = [
        ("carry_avg", "Carry avg (yd)", True, 1),
        ("smash_avg", "Smash avg", True, 3),
        ("face_control", "Face control avg |face-to-path| (deg)", False, 2),
        ("strike_quality", "Strike quality avg |strike_distance|", False, 2),
    ]
    for key, label, higher_is_better, precision in metric_lines:
        line, trend = metric_change(
            label=label,
            current=current[key],
            previous=previous[key],
            higher_is_better=higher_is_better,
            precision=precision,
        )
        trend_flags[key] = trend
        lines.append(line)
    lines.append("")

    lines.append("4) Best and worst sessions (simple quality score)")
    sessions = sorted(current["sessions"], key=lambda item: item.score, reverse=True)
    if sessions:
        best_session = sessions[0]
        worst_session = sessions[-1]
        lines.append(f"- Best:  {session_label(best_session)}")
        lines.append(
            f"  carry={best_session.carry_avg:.1f}, smash={fmt(best_session.smash_avg, 3)}, "
            f"|f2p|={fmt(best_session.face_abs_avg, 2)}, |strike|={fmt(best_session.strike_abs_avg, 2)}"
        )
        lines.append(f"- Worst: {session_label(worst_session)}")
        lines.append(
            f"  carry={worst_session.carry_avg:.1f}, smash={fmt(worst_session.smash_avg, 3)}, "
            f"|f2p|={fmt(worst_session.face_abs_avg, 2)}, |strike|={fmt(worst_session.strike_abs_avg, 2)}"
        )
    else:
        lines.append("- No sessions available in current window.")
    lines.append("")

    lines.append("5) Areas that improved vs declined")
    improved: list[str] = []
    declined: list[str] = []
    label_map = {
        "carry_avg": "Carry avg",
        "smash_avg": "Smash avg",
        "face_control": "Face control",
        "strike_quality": "Strike quality",
    }
    for key, trend in trend_flags.items():
        label = label_map[key]
        if trend is True:
            improved.append(label)
        elif trend is False:
            declined.append(label)

    lines.append(f"- Improved: {', '.join(improved) if improved else 'None'}")
    lines.append(f"- Declined: {', '.join(declined) if declined else 'None'}")
    lines.append("")

    lines.append("6) Suggested focus for next week")
    for item in build_focus_suggestions(current, previous, trend_flags):
        lines.append(f"- {item}")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
