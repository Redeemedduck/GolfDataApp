#!/usr/bin/env python3
"""Compare two golf practice sessions side-by-side with metric deltas."""

from __future__ import annotations

import argparse
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from statistics import mean, stdev
from typing import Any

EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
MIN_CARRY = 10.0
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Shot:
    session_id: str
    session_date: date
    club: str
    carry: float
    smash: float | None
    face_to_path: float | None
    strike_distance: float | None


@dataclass
class SessionInfo:
    session_id: str
    session_date: date
    shots: list[Shot] = field(default_factory=list)

    @property
    def total_shots(self) -> int:
        return len(self.shots)

    @property
    def clubs_used(self) -> list[str]:
        seen: dict[str, None] = {}
        for s in self.shots:
            seen.setdefault(s.club, None)
        return list(seen)

    @property
    def duration_estimate_min(self) -> int:
        """Rough estimate: ~1.5 minutes per shot."""
        return round(self.total_shots * 1.5)


@dataclass
class ClubStats:
    club: str
    count: int
    carry_avg: float
    smash_avg: float | None
    face_control: float | None  # avg |face_to_path|
    strike_quality: float | None  # avg |strike_distance|


# ---------------------------------------------------------------------------
# Helpers (reused patterns from weekly_digest.py)
# ---------------------------------------------------------------------------

def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


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


def quality_score(shots: list[Shot]) -> float:
    """Session quality 0-100 (weekly_digest formula: 35% smash, 30% face, 25% strike, 10% carry CV)."""
    smash_avg = safe_mean([s.smash for s in shots if s.smash is not None])
    face_abs_avg = safe_mean([abs(s.face_to_path) for s in shots if s.face_to_path is not None])
    strike_abs_avg = safe_mean([abs(s.strike_distance) for s in shots if s.strike_distance is not None])

    carries = [s.carry for s in shots]
    carry_cv: float | None = None
    if len(carries) >= 2:
        carry_avg = mean(carries)
        if carry_avg > 0:
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


def fmt(value: float | None, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    return f"{value:.{digits}f}"


def delta_arrow(delta: float, higher_is_better: bool, threshold: float = 0.005) -> str:
    if abs(delta) < threshold:
        return "  --"
    if higher_is_better:
        return f" {chr(0x2191)}" if delta > 0 else f" {chr(0x2193)}"
    else:
        return f" {chr(0x2191)}" if delta < 0 else f" {chr(0x2193)}"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

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


def parse_session_date(raw: Any) -> date | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    if len(text) >= 10:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def list_recent_sessions(conn: sqlite3.Connection, carry_col: str, limit: int = 20) -> list[tuple[str, str]]:
    """Return (session_id, session_date) pairs ordered by most recent first."""
    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            COALESCE(CAST(session_id AS TEXT), '') AS sid,
            session_date
        FROM shots
        WHERE session_date IS NOT NULL
          AND club IS NOT NULL
          AND TRIM(club) NOT IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
        GROUP BY session_id
        ORDER BY session_date DESC, session_id DESC
        LIMIT ?
    """
    params = (*sorted(EXCLUDED_CLUBS), MIN_CARRY, limit)
    rows = conn.execute(query, params).fetchall()
    return [(str(r["sid"]), str(r["session_date"])) for r in rows]


def load_session(conn: sqlite3.Connection, carry_col: str, session_id: str) -> SessionInfo | None:
    """Load all qualifying shots for a single session_id."""
    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            COALESCE(CAST(session_id AS TEXT), '') AS sid,
            session_date,
            TRIM(club) AS club,
            {carry_col} AS carry_value,
            smash,
            face_to_path,
            strike_distance
        FROM shots
        WHERE CAST(session_id AS TEXT) = ?
          AND session_date IS NOT NULL
          AND club IS NOT NULL
          AND TRIM(club) != ''
          AND TRIM(club) NOT IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
        ORDER BY rowid
    """
    params = (session_id, *sorted(EXCLUDED_CLUBS), MIN_CARRY)
    rows = conn.execute(query, params).fetchall()

    if not rows:
        return None

    shots: list[Shot] = []
    session_date_value: date | None = None
    for row in rows:
        day = parse_session_date(row["session_date"])
        if day is None:
            continue
        if session_date_value is None:
            session_date_value = day
        carry = to_float(row["carry_value"])
        if carry is None or carry < MIN_CARRY:
            continue
        shots.append(Shot(
            session_id=str(row["sid"]),
            session_date=day,
            club=str(row["club"]).strip(),
            carry=carry,
            smash=to_float(row["smash"]),
            face_to_path=to_float(row["face_to_path"]),
            strike_distance=to_float(row["strike_distance"]),
        ))

    if not shots or session_date_value is None:
        return None

    return SessionInfo(session_id=session_id, session_date=session_date_value, shots=shots)


# ---------------------------------------------------------------------------
# Per-club stats
# ---------------------------------------------------------------------------

def compute_club_stats(shots: list[Shot]) -> dict[str, ClubStats]:
    by_club: dict[str, list[Shot]] = defaultdict(list)
    for s in shots:
        by_club[s.club].append(s)

    result: dict[str, ClubStats] = {}
    for club, club_shots in by_club.items():
        carries = [s.carry for s in club_shots]
        smash_vals = [s.smash for s in club_shots if s.smash is not None]
        face_vals = [abs(s.face_to_path) for s in club_shots if s.face_to_path is not None]
        strike_vals = [abs(s.strike_distance) for s in club_shots if s.strike_distance is not None]

        result[club] = ClubStats(
            club=club,
            count=len(club_shots),
            carry_avg=mean(carries),
            smash_avg=safe_mean(smash_vals),
            face_control=safe_mean(face_vals),
            strike_quality=safe_mean(strike_vals),
        )
    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def render_overview(s1: SessionInfo, s2: SessionInfo) -> list[str]:
    lines: list[str] = []
    lines.append("SESSION OVERVIEW")
    lines.append("=" * 60)
    lines.append("")

    col_w = 28
    header = f"{'':20s} {'Session 1':>{col_w}s} {'Session 2':>{col_w}s}"
    lines.append(header)
    lines.append("-" * len(header))

    lines.append(
        f"{'Session ID':20s} {s1.session_id:>{col_w}s} {s2.session_id:>{col_w}s}"
    )
    lines.append(
        f"{'Date':20s} {s1.session_date.isoformat():>{col_w}s} {s2.session_date.isoformat():>{col_w}s}"
    )
    lines.append(
        f"{'Total shots':20s} {str(s1.total_shots):>{col_w}s} {str(s2.total_shots):>{col_w}s}"
    )
    lines.append(
        f"{'Clubs used':20s} {str(len(s1.clubs_used)):>{col_w}s} {str(len(s2.clubs_used)):>{col_w}s}"
    )
    dur1 = f"~{s1.duration_estimate_min} min"
    dur2 = f"~{s2.duration_estimate_min} min"
    lines.append(
        f"{'Duration (est)':20s} {dur1:>{col_w}s} {dur2:>{col_w}s}"
    )
    lines.append("")
    return lines


def render_shared_clubs(stats1: dict[str, ClubStats], stats2: dict[str, ClubStats]) -> list[str]:
    shared = sorted(set(stats1) & set(stats2))
    if not shared:
        return ["No shared clubs between sessions.", ""]

    lines: list[str] = []
    lines.append("PER-CLUB COMPARISON (shared clubs)")
    lines.append("=" * 60)
    lines.append("")

    for club in shared:
        c1 = stats1[club]
        c2 = stats2[club]

        carry_delta = c2.carry_avg - c1.carry_avg
        carry_arr = delta_arrow(carry_delta, higher_is_better=True, threshold=0.5)

        smash_delta: float | None = None
        smash_arr = ""
        if c1.smash_avg is not None and c2.smash_avg is not None:
            smash_delta = c2.smash_avg - c1.smash_avg
            smash_arr = delta_arrow(smash_delta, higher_is_better=True, threshold=0.005)

        face_delta: float | None = None
        face_arr = ""
        if c1.face_control is not None and c2.face_control is not None:
            face_delta = c2.face_control - c1.face_control
            face_arr = delta_arrow(face_delta, higher_is_better=False, threshold=0.05)

        strike_delta: float | None = None
        strike_arr = ""
        if c1.strike_quality is not None and c2.strike_quality is not None:
            strike_delta = c2.strike_quality - c1.strike_quality
            strike_arr = delta_arrow(strike_delta, higher_is_better=False, threshold=0.05)

        lines.append(f"  {club}")
        lines.append(f"    Shots:          S1={c1.count:<4d}  S2={c2.count:<4d}")
        lines.append(
            f"    Carry avg:      S1={c1.carry_avg:<8.1f} S2={c2.carry_avg:<8.1f} "
            f"delta={carry_delta:+.1f}{carry_arr}"
        )
        lines.append(
            f"    Smash avg:      S1={fmt(c1.smash_avg, 3):<8s} S2={fmt(c2.smash_avg, 3):<8s} "
            f"delta={fmt(smash_delta, 3) if smash_delta is not None else 'N/A':>6s}{smash_arr}"
        )
        lines.append(
            f"    Face control:   S1={fmt(c1.face_control):<8s} S2={fmt(c2.face_control):<8s} "
            f"delta={fmt(face_delta) if face_delta is not None else 'N/A':>6s}{face_arr}"
        )
        lines.append(
            f"    Strike quality: S1={fmt(c1.strike_quality):<8s} S2={fmt(c2.strike_quality):<8s} "
            f"delta={fmt(strike_delta) if strike_delta is not None else 'N/A':>6s}{strike_arr}"
        )
        lines.append("")

    return lines


def render_exclusive_clubs(stats1: dict[str, ClubStats], stats2: dict[str, ClubStats]) -> list[str]:
    only1 = sorted(set(stats1) - set(stats2))
    only2 = sorted(set(stats2) - set(stats1))

    if not only1 and not only2:
        return []

    lines: list[str] = []
    lines.append("CLUBS UNIQUE TO ONE SESSION")
    lines.append("=" * 60)
    lines.append("")

    if only1:
        lines.append("  Only in Session 1:")
        for club in only1:
            c = stats1[club]
            lines.append(
                f"    {club}: {c.count} shots, carry avg {c.carry_avg:.1f}, "
                f"smash {fmt(c.smash_avg, 3)}"
            )
    else:
        lines.append("  Only in Session 1: (none)")

    lines.append("")

    if only2:
        lines.append("  Only in Session 2:")
        for club in only2:
            c = stats2[club]
            lines.append(
                f"    {club}: {c.count} shots, carry avg {c.carry_avg:.1f}, "
                f"smash {fmt(c.smash_avg, 3)}"
            )
    else:
        lines.append("  Only in Session 2: (none)")

    lines.append("")
    return lines


def render_quality_scores(s1: SessionInfo, s2: SessionInfo) -> tuple[list[str], float, float]:
    score1 = quality_score(s1.shots)
    score2 = quality_score(s2.shots)

    lines: list[str] = []
    lines.append("OVERALL SESSION QUALITY")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Session 1 ({s1.session_id}):  {score1:.1f} / 100")
    lines.append(f"  Session 2 ({s2.session_id}):  {score2:.1f} / 100")

    delta = score2 - score1
    if abs(delta) < 0.5:
        lines.append(f"  Delta: {delta:+.1f}  (essentially equal)")
    else:
        better = "Session 2" if delta > 0 else "Session 1"
        lines.append(f"  Delta: {delta:+.1f}  ({better} scored higher)")

    lines.append("")
    return lines, score1, score2


def render_verdict(
    s1: SessionInfo,
    s2: SessionInfo,
    score1: float,
    score2: float,
    stats1: dict[str, ClubStats],
    stats2: dict[str, ClubStats],
) -> list[str]:
    shared = sorted(set(stats1) & set(stats2))

    # Count per-area wins (across shared clubs)
    carry_wins_s2 = 0
    smash_wins_s2 = 0
    face_wins_s2 = 0
    strike_wins_s2 = 0
    total_comparisons = 0

    for club in shared:
        c1, c2 = stats1[club], stats2[club]
        total_comparisons += 1

        if c2.carry_avg > c1.carry_avg + 0.5:
            carry_wins_s2 += 1
        elif c1.carry_avg > c2.carry_avg + 0.5:
            carry_wins_s2 -= 1

        if c1.smash_avg is not None and c2.smash_avg is not None:
            if c2.smash_avg > c1.smash_avg + 0.005:
                smash_wins_s2 += 1
            elif c1.smash_avg > c2.smash_avg + 0.005:
                smash_wins_s2 -= 1

        if c1.face_control is not None and c2.face_control is not None:
            if c2.face_control < c1.face_control - 0.05:
                face_wins_s2 += 1
            elif c1.face_control < c2.face_control - 0.05:
                face_wins_s2 -= 1

        if c1.strike_quality is not None and c2.strike_quality is not None:
            if c2.strike_quality < c1.strike_quality - 0.05:
                strike_wins_s2 += 1
            elif c1.strike_quality < c2.strike_quality - 0.05:
                strike_wins_s2 -= 1

    lines: list[str] = []
    lines.append("VERDICT")
    lines.append("=" * 60)
    lines.append("")

    # Overall winner
    if abs(score2 - score1) < 0.5:
        lines.append("  Overall: Too close to call -- sessions are roughly equal.")
    elif score2 > score1:
        lines.append(
            f"  Overall: Session 2 ({s2.session_id}, {s2.session_date.isoformat()}) "
            f"was the better session by {score2 - score1:.1f} points."
        )
    else:
        lines.append(
            f"  Overall: Session 1 ({s1.session_id}, {s1.session_date.isoformat()}) "
            f"was the better session by {score1 - score2:.1f} points."
        )

    # Area breakdown
    def area_verdict(name: str, s2_advantage: int) -> str:
        if s2_advantage > 0:
            return f"Session 2 ({s2.session_id})"
        elif s2_advantage < 0:
            return f"Session 1 ({s1.session_id})"
        return "Tie"

    if total_comparisons > 0:
        lines.append("")
        lines.append("  Area breakdown (across shared clubs):")
        lines.append(f"    Carry distance:   {area_verdict('Carry', carry_wins_s2)}")
        lines.append(f"    Smash factor:     {area_verdict('Smash', smash_wins_s2)}")
        lines.append(f"    Face control:     {area_verdict('Face', face_wins_s2)}")
        lines.append(f"    Strike quality:   {area_verdict('Strike', strike_wins_s2)}")

    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Session resolution
# ---------------------------------------------------------------------------

def resolve_sessions(
    conn: sqlite3.Connection,
    carry_col: str,
    args: argparse.Namespace,
) -> tuple[SessionInfo, SessionInfo]:
    """Resolve which two sessions to compare based on CLI args."""
    if args.session1 and args.session2:
        s1 = load_session(conn, carry_col, args.session1)
        s2 = load_session(conn, carry_col, args.session2)
        if s1 is None:
            raise SystemExit(f"Session {args.session1} not found or has no qualifying shots.")
        if s2 is None:
            raise SystemExit(f"Session {args.session2} not found or has no qualifying shots.")
        return s1, s2

    # For --last N or default: find the Nth and (N+1)th most recent sessions
    n = args.last
    needed = n + 1
    recent = list_recent_sessions(conn, carry_col, limit=needed + 5)

    if len(recent) < needed:
        raise SystemExit(
            f"Need at least {needed} sessions for --last {n}, "
            f"but only found {len(recent)} qualifying sessions."
        )

    # Index: n-1 is the more recent, n is the older
    newer_id = recent[n - 1][0]
    older_id = recent[n][0]

    s1 = load_session(conn, carry_col, older_id)
    s2 = load_session(conn, carry_col, newer_id)

    if s1 is None:
        raise SystemExit(f"Session {older_id} has no qualifying shots after filtering.")
    if s2 is None:
        raise SystemExit(f"Session {newer_id} has no qualifying shots after filtering.")

    return s1, s2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two golf practice sessions side-by-side with metric deltas.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--session1",
        type=str,
        default=None,
        help="Session ID for the first (older/baseline) session.",
    )
    parser.add_argument(
        "--session2",
        type=str,
        default=None,
        help="Session ID for the second (newer/comparison) session.",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=1,
        help=(
            "Compare the Nth most recent session with the (N+1)th. "
            "Default 1 = compare latest two sessions."
        ),
    )

    args = parser.parse_args()

    # Validate: both or neither session IDs
    if bool(args.session1) != bool(args.session2):
        parser.error("--session1 and --session2 must be used together.")

    if args.last < 1:
        parser.error("--last must be >= 1.")

    return args


def main() -> int:
    args = parse_args()

    try:
        conn = build_connection(args.db)
    except (sqlite3.Error, FileNotFoundError) as exc:
        print(f"Error opening database: {exc}")
        return 1

    try:
        carry_col = resolve_carry_column(conn)
        s1, s2 = resolve_sessions(conn, carry_col, args)
    except (sqlite3.Error, RuntimeError) as exc:
        print(f"Error: {exc}")
        return 1
    finally:
        conn.close()

    stats1 = compute_club_stats(s1.shots)
    stats2 = compute_club_stats(s2.shots)

    # Build report
    output: list[str] = []
    output.append("SESSION COMPARISON REPORT")
    output.append(
        f"Database: {args.db} | Filters: exclude {', '.join(sorted(EXCLUDED_CLUBS))}, "
        f"carry >= {MIN_CARRY:.0f}"
    )
    output.append("")

    output.extend(render_overview(s1, s2))
    output.extend(render_shared_clubs(stats1, stats2))
    output.extend(render_exclusive_clubs(stats1, stats2))

    quality_lines, score1, score2 = render_quality_scores(s1, s2)
    output.extend(quality_lines)

    output.extend(render_verdict(s1, s2, score1, score2, stats1, stats2))

    print("\n".join(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
