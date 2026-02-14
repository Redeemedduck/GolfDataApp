#!/usr/bin/env python3
"""Score golf practice sessions (A-F) from golf_stats.db."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
MIN_CARRY_DISTANCE = 10.0
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
DEFAULT_BAG_PATH = Path(__file__).resolve().parents[1] / "my_bag.json"

WEIGHTS = {
    "carry_consistency": 0.30,
    "smash_vs_target": 0.20,
    "face_angle_control": 0.20,
    "strike_centering": 0.15,
    "club_path_neutrality": 0.15,
}

DEFAULT_SMASH_TARGET = 1.33
FALLBACK_SMASH_TARGETS = {
    "Driver": 1.49,
    "3 Wood": 1.45,
    "7 Wood": 1.42,
    "3 Iron": 1.36,
    "4 Iron": 1.35,
    "5 Iron": 1.34,
    "6 Iron": 1.34,
    "7 Iron": 1.33,
    "8 Iron": 1.31,
    "9 Iron": 1.29,
    "PW": 1.24,
    "GW": 1.22,
    "SW": 1.20,
    "LW": 1.18,
}

CARRY_CV_BEST = 0.03
CARRY_CV_WORST = 0.20
SMASH_DEVIATION_BEST = 0.00
SMASH_DEVIATION_WORST = 0.20
FACE_ABS_BEST = 0.5
FACE_ABS_WORST = 5.0
STRIKE_DISTANCE_BEST = 3.0
STRIKE_DISTANCE_WORST = 20.0
PATH_ABS_BEST = 0.8
PATH_ABS_WORST = 6.0


@dataclass
class ShotRow:
    session_key: str
    club: str
    carry_distance: float
    smash: float | None
    face_angle: float | None
    club_path: float | None
    strike_distance: float | None
    session_date: date
    session_name: str


@dataclass
class SessionScore:
    session_date: date
    session_key: str
    session_name: str
    shot_count: int
    carry_score: float
    smash_score: float
    face_score: float
    strike_score: float
    path_score: float
    total_score: float
    grade: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Grade golf practice sessions A-F using carry consistency, smash factor, "
            "face angle control, strike centering, and club path neutrality."
        )
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Path to SQLite database")
    parser.add_argument("--limit", type=int, default=10, help="Number of most recent sessions to show")
    parser.add_argument(
        "--bag-config",
        type=Path,
        default=DEFAULT_BAG_PATH,
        help="Path to my_bag.json for smash targets",
    )
    return parser.parse_args()


def parse_session_date(raw_value: Any) -> date | None:
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    if len(text) >= 10:
        iso_day = text[:10]
        try:
            return datetime.strptime(iso_day, "%Y-%m-%d").date()
        except ValueError:
            return None

    return None


def sample_std_dev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def inverse_linear_score(value: float, best: float, worst: float) -> float:
    """Map lower-is-better metric to 0-100 score using linear interpolation."""
    if value <= best:
        return 100.0
    if value >= worst:
        return 0.0
    span = worst - best
    return clamp(100.0 * (worst - value) / span, 0.0, 100.0)


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


def build_readonly_connection(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    # Use a standard connection for WAL compatibility, then enforce query-only mode.
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA query_only = ON")
    return conn


def get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row["name"]) for row in rows}


def load_smash_targets(bag_config_path: Path) -> dict[str, float]:
    targets = dict(FALLBACK_SMASH_TARGETS)

    if not bag_config_path.exists():
        return targets

    try:
        with bag_config_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return targets

    config_targets = payload.get("smash_targets", {})
    if isinstance(config_targets, dict):
        for club_name, target in config_targets.items():
            try:
                targets[str(club_name).strip()] = float(target)
            except (TypeError, ValueError):
                continue

    return targets


def build_alias_map(bag_config_path: Path) -> dict[str, str]:
    alias_map: dict[str, str] = {}
    if not bag_config_path.exists():
        return alias_map

    try:
        with bag_config_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return alias_map

    clubs = payload.get("clubs", [])
    if not isinstance(clubs, list):
        return alias_map

    for club in clubs:
        if not isinstance(club, dict):
            continue
        canonical = club.get("canonical")
        if not isinstance(canonical, str) or not canonical.strip():
            continue

        canonical_clean = canonical.strip()
        alias_map[canonical_clean.lower()] = canonical_clean

        aliases = club.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                if isinstance(alias, str) and alias.strip():
                    alias_map[alias.strip().lower()] = canonical_clean

        uneekor_name = club.get("uneekor")
        if isinstance(uneekor_name, str) and uneekor_name.strip():
            alias_map[uneekor_name.strip().lower()] = canonical_clean

    return alias_map


def normalize_club_name(club: str, alias_map: dict[str, str]) -> str:
    raw = club.strip()
    if not raw:
        return raw

    lowered = raw.lower()
    if lowered in alias_map:
        return alias_map[lowered]

    if "|" in raw:
        left = raw.split("|", 1)[0].strip().lower()
        if left in alias_map:
            return alias_map[left]

    # Basic fallbacks for common label variants
    upper = raw.upper()
    if upper in {"DR", "1W", "DRIVER"}:
        return "Driver"
    if upper.replace(" ", "") in {"PW", "GW", "SW", "LW"}:
        return upper.replace(" ", "")

    return raw


def target_smash_for_club(club: str, targets: dict[str, float], alias_map: dict[str, str]) -> float:
    normalized = normalize_club_name(club, alias_map)
    if normalized in targets:
        return targets[normalized]

    upper = normalized.upper()
    if "DRIVER" in upper:
        return 1.49
    if "WOOD" in upper:
        return 1.44

    for iron_number in ("3", "4", "5", "6", "7", "8", "9"):
        if f"{iron_number} IRON" in upper or f"IRON {iron_number}" in upper:
            return FALLBACK_SMASH_TARGETS[f"{iron_number} Iron"]

    return DEFAULT_SMASH_TARGET


def fetch_filtered_shots(conn: sqlite3.Connection) -> list[ShotRow]:
    columns = get_table_columns(conn, "shots")

    if "carry_distance" in columns:
        carry_col = "carry_distance"
    elif "carry" in columns:
        carry_col = "carry"
    else:
        raise RuntimeError("shots table is missing both carry_distance and carry columns")

    if "session_name" in columns:
        session_name_expr = "session_name"
    elif "session_id" in columns:
        session_name_expr = "session_id"
    else:
        session_name_expr = "'Unnamed Session'"

    if "session_id" in columns:
        session_key_expr = "session_id"
    elif "session_name" in columns:
        session_key_expr = "session_name"
    else:
        session_key_expr = "session_date"

    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            club,
            {carry_col} AS carry_distance,
            smash,
            face_angle,
            club_path,
            strike_distance,
            session_date,
            COALESCE(NULLIF({session_key_expr}, ''), 'session-unknown') AS session_key,
            COALESCE(NULLIF({session_name_expr}, ''), 'Unnamed Session') AS session_name
        FROM shots
        WHERE session_date IS NOT NULL
          AND club IS NOT NULL
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
          AND club NOT IN ({placeholders})
    """

    params: list[Any] = [MIN_CARRY_DISTANCE]
    params.extend(sorted(EXCLUDED_CLUBS))

    raw_rows = conn.execute(query, params).fetchall()

    rows: list[ShotRow] = []
    for row in raw_rows:
        session_day = parse_session_date(row["session_date"])
        if session_day is None:
            continue

        rows.append(
            ShotRow(
                session_key=str(row["session_key"]),
                club=str(row["club"]),
                carry_distance=float(row["carry_distance"]),
                smash=float(row["smash"]) if row["smash"] is not None else None,
                face_angle=float(row["face_angle"]) if row["face_angle"] is not None else None,
                club_path=float(row["club_path"]) if row["club_path"] is not None else None,
                strike_distance=float(row["strike_distance"]) if row["strike_distance"] is not None else None,
                session_date=session_day,
                session_name=str(row["session_name"]),
            )
        )

    return rows


def session_component_scores(
    shots: list[ShotRow],
    smash_targets: dict[str, float],
    alias_map: dict[str, str],
) -> tuple[float, float, float, float, float, float]:
    carries = [shot.carry_distance for shot in shots]
    carry_mean = mean(carries) if carries else 0.0
    carry_cv = (sample_std_dev(carries) / carry_mean) if carry_mean > 0 else 1.0
    carry_score = inverse_linear_score(carry_cv, best=CARRY_CV_BEST, worst=CARRY_CV_WORST)

    smash_deviations: list[float] = []
    for shot in shots:
        if shot.smash is None:
            continue
        if shot.smash <= 0 or shot.smash >= 2.5:
            continue
        target = target_smash_for_club(shot.club, smash_targets, alias_map)
        smash_deviations.append(abs(shot.smash - target))

    if smash_deviations:
        smash_dev_avg = mean(smash_deviations)
        smash_score = inverse_linear_score(
            smash_dev_avg,
            best=SMASH_DEVIATION_BEST,
            worst=SMASH_DEVIATION_WORST,
        )
    else:
        smash_score = 50.0

    face_abs = [abs(shot.face_angle) for shot in shots if shot.face_angle is not None]
    face_metric = mean(face_abs) if face_abs else 2.0
    face_score = inverse_linear_score(face_metric, best=FACE_ABS_BEST, worst=FACE_ABS_WORST)

    strike_values = [abs(shot.strike_distance) for shot in shots if shot.strike_distance is not None]
    strike_metric = mean(strike_values) if strike_values else STRIKE_DISTANCE_WORST
    strike_score = inverse_linear_score(
        strike_metric,
        best=STRIKE_DISTANCE_BEST,
        worst=STRIKE_DISTANCE_WORST,
    )

    path_abs = [abs(shot.club_path) for shot in shots if shot.club_path is not None]
    path_metric = mean(path_abs) if path_abs else 3.0
    path_score = inverse_linear_score(path_metric, best=PATH_ABS_BEST, worst=PATH_ABS_WORST)

    total_score = (
        carry_score * WEIGHTS["carry_consistency"]
        + smash_score * WEIGHTS["smash_vs_target"]
        + face_score * WEIGHTS["face_angle_control"]
        + strike_score * WEIGHTS["strike_centering"]
        + path_score * WEIGHTS["club_path_neutrality"]
    )

    return carry_score, smash_score, face_score, strike_score, path_score, total_score


def build_session_scores(shots: list[ShotRow], bag_config_path: Path) -> list[SessionScore]:
    by_session: dict[tuple[date, str], list[ShotRow]] = {}
    session_names: dict[tuple[date, str], str] = {}
    for shot in shots:
        key = (shot.session_date, shot.session_key)
        by_session.setdefault(key, []).append(shot)
        session_names[key] = shot.session_name

    smash_targets = load_smash_targets(bag_config_path)
    alias_map = build_alias_map(bag_config_path)

    sessions: list[SessionScore] = []
    for (session_day, session_key), session_shots in by_session.items():
        carry_score, smash_score, face_score, strike_score, path_score, total_score = session_component_scores(
            session_shots,
            smash_targets,
            alias_map,
        )
        session_name = session_names.get((session_day, session_key), "Unnamed Session")
        sessions.append(
            SessionScore(
                session_date=session_day,
                session_key=session_key,
                session_name=session_name,
                shot_count=len(session_shots),
                carry_score=carry_score,
                smash_score=smash_score,
                face_score=face_score,
                strike_score=strike_score,
                path_score=path_score,
                total_score=total_score,
                grade=grade_for_score(total_score),
            )
        )

    sessions.sort(key=lambda session: (session.session_date, session.session_key), reverse=True)
    return sessions


def trend_vs_30_day_average(current: SessionScore, all_sessions: Iterable[SessionScore]) -> str:
    window_start = current.session_date - timedelta(days=30)
    prior_scores = [
        session.total_score
        for session in all_sessions
        if window_start <= session.session_date < current.session_date
    ]

    if not prior_scores:
        return "→ no baseline"

    baseline = mean(prior_scores)
    delta = current.total_score - baseline

    if delta >= 1.0:
        return f"↑ improving ({delta:+.1f})"
    if delta <= -1.0:
        return f"↓ declining ({delta:+.1f})"
    return f"→ flat ({delta:+.1f})"


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "(no sessions match filter criteria)"

    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    header_line = "  ".join(headers[i].ljust(widths[i]) for i in range(len(headers)))
    divider = "  ".join("-" * widths[i] for i in range(len(headers)))
    data_lines = ["  ".join(row[i].ljust(widths[i]) for i in range(len(headers))) for row in rows]

    return "\n".join([header_line, divider, *data_lines])


def render_report(db_path: Path, sessions: list[SessionScore], limit: int) -> str:
    shown = sessions[: max(0, limit)]
    headers = [
        "Date",
        "Session",
        "Shots",
        "Grade",
        "Total",
        "Carry",
        "Smash",
        "Face",
        "Strike",
        "Path",
        "Trend vs 30d",
    ]

    rows: list[list[str]] = []
    for session in shown:
        rows.append(
            [
                session.session_date.isoformat(),
                session.session_name,
                str(session.shot_count),
                session.grade,
                f"{session.total_score:.1f}",
                f"{session.carry_score:.1f}",
                f"{session.smash_score:.1f}",
                f"{session.face_score:.1f}",
                f"{session.strike_score:.1f}",
                f"{session.path_score:.1f}",
                trend_vs_30_day_average(session, sessions),
            ]
        )

    lines = [
        "Session Quality Report",
        "======================",
        f"Database: {db_path}",
        (
            "Filters: exclude clubs [Other, Putter, Sim Round], "
            "carry_distance >= 10"
        ),
        (
            "Weights: Carry 30%, Smash 20%, Face 20%, "
            "Strike 15%, Path 15%"
        ),
        "Grade scale: A>=90, B>=80, C>=70, D>=60, F<60",
        "",
        f"Most recent {len(shown)} sessions",
        "",
        format_table(headers, rows),
    ]

    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    try:
        conn = build_readonly_connection(args.db)
    except (sqlite3.Error, FileNotFoundError) as exc:
        print(f"Error opening database: {exc}")
        return 1

    try:
        shots = fetch_filtered_shots(conn)
    except (sqlite3.Error, RuntimeError) as exc:
        print(f"Error fetching shots: {exc}")
        return 1
    finally:
        conn.close()

    sessions = build_session_scores(shots, args.bag_config)
    print(render_report(args.db, sessions, args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
