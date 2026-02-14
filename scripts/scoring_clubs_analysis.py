#!/usr/bin/env python3
"""Scoring clubs (wedges) deep analysis for golf_stats.db.

Analyzes PW, GW, SW, LW across distance control, spin, accuracy,
strike quality, gapping, and scoring zone precision.
"""

from __future__ import annotations

import argparse
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Constants ────────────────────────────────────────────────────────────

SCORING_CLUBS = ("PW", "GW", "SW", "LW")
SCORING_CLUBS_ORDER = {club: idx for idx, club in enumerate(SCORING_CLUBS)}
MISHIT_CARRY_THRESHOLD = 10.0
GAP_TOO_LARGE = 15.0
GAP_TOO_SMALL = 8.0
SCORING_ZONE_TIGHT = 5.0
SCORING_ZONE_WIDE = 10.0


# ── Data classes ─────────────────────────────────────────────────────────

@dataclass
class WedgeShot:
    club: str
    carry: float
    back_spin: float | None
    side_distance: float | None
    impact_x: float | None
    impact_y: float | None
    strike_distance: float | None


@dataclass
class WedgeStats:
    club: str
    shot_count: int = 0
    carry_mean: float = 0.0
    carry_std: float = 0.0
    carry_cv: float = 0.0
    precision_score: str = ""
    spin_mean: float | None = None
    spin_std: float | None = None
    side_mean: float = 0.0
    side_std: float = 0.0
    miss_tendency: str = ""
    avg_abs_strike: float | None = None
    avg_abs_impact_x: float | None = None
    avg_abs_impact_y: float | None = None
    pct_within_5: float = 0.0
    pct_within_10: float = 0.0


# ── Math helpers ─────────────────────────────────────────────────────────

def _mean(values: list[float]) -> float:
    if not values:
        return float("nan")
    return sum(values) / len(values)


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((v - avg) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _cv(std: float, mean: float) -> float:
    if mean == 0 or math.isnan(mean):
        return float("nan")
    return (std / abs(mean)) * 100.0


def _fmt(value: float | None, decimals: int = 1, na: str = "-") -> str:
    if value is None:
        return na
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return na
    return f"{value:.{decimals}f}"


def _precision_label(cv: float) -> str:
    if math.isnan(cv):
        return "-"
    if cv < 4.0:
        return "Elite"
    if cv < 6.0:
        return "Good"
    if cv < 8.0:
        return "Average"
    if cv < 10.0:
        return "Below Avg"
    return "Poor"


# ── Display helpers ──────────────────────────────────────────────────────

def _print_header(title: str) -> None:
    width = 70
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def _print_section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def _print_table(headers: list[str], rows: list[list[str]]) -> None:
    if not rows:
        print("(no data)")
        return

    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(str(cell)))

    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    divider = "  ".join("-" * w for w in widths)
    print(header_line)
    print(divider)
    for row in rows:
        print("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)))


# ── Database ─────────────────────────────────────────────────────────────

def _detect_carry_column(cursor: sqlite3.Cursor) -> str:
    """Detect whether the carry column is named 'carry' or 'carry_distance'."""
    cursor.execute("PRAGMA table_info(shots)")
    columns = {row[1] for row in cursor.fetchall()}
    if "carry" in columns:
        return "carry"
    if "carry_distance" in columns:
        return "carry_distance"
    raise RuntimeError("No carry column found in shots table (expected 'carry' or 'carry_distance')")


def _has_column(cursor: sqlite3.Cursor, table: str, col: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    return col in columns


def _build_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_wedge_shots(conn: sqlite3.Connection, carry_col: str, has_spin: bool) -> list[WedgeShot]:
    placeholders = ",".join("?" for _ in SCORING_CLUBS)
    spin_select = ", back_spin" if has_spin else ""

    query = f"""
        SELECT club, {carry_col} AS carry, side_distance,
               impact_x, impact_y, strike_distance{spin_select}
        FROM shots
        WHERE club IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
    """
    params: tuple[Any, ...] = (*SCORING_CLUBS, MISHIT_CARRY_THRESHOLD)
    rows = conn.execute(query, params).fetchall()

    shots: list[WedgeShot] = []
    for r in rows:
        shots.append(WedgeShot(
            club=r["club"],
            carry=float(r["carry"]),
            back_spin=float(r["back_spin"]) if has_spin and r["back_spin"] is not None else None,
            side_distance=float(r["side_distance"]) if r["side_distance"] is not None else None,
            impact_x=float(r["impact_x"]) if r["impact_x"] is not None else None,
            impact_y=float(r["impact_y"]) if r["impact_y"] is not None else None,
            strike_distance=float(r["strike_distance"]) if r["strike_distance"] is not None else None,
        ))
    return shots


# ── Analysis ─────────────────────────────────────────────────────────────

def _compute_wedge_stats(shots_by_club: dict[str, list[WedgeShot]]) -> list[WedgeStats]:
    results: list[WedgeStats] = []

    for club in SCORING_CLUBS:
        club_shots = shots_by_club.get(club, [])
        if not club_shots:
            continue

        carries = [s.carry for s in club_shots]
        carry_avg = _mean(carries)
        carry_sd = _std(carries)
        cv = _cv(carry_sd, carry_avg)

        # Spin
        spin_vals = [s.back_spin for s in club_shots if s.back_spin is not None]
        spin_mean = _mean(spin_vals) if spin_vals else None
        spin_sd = _std(spin_vals) if len(spin_vals) >= 2 else None

        # Accuracy (side distance)
        side_vals = [s.side_distance for s in club_shots if s.side_distance is not None]
        side_mean = _mean(side_vals) if side_vals else float("nan")
        side_sd = _std(side_vals) if len(side_vals) >= 2 else 0.0

        if side_vals:
            left_count = sum(1 for v in side_vals if v < 0)
            right_count = sum(1 for v in side_vals if v > 0)
            if left_count > right_count * 1.3:
                tendency = f"Left ({left_count}/{len(side_vals)})"
            elif right_count > left_count * 1.3:
                tendency = f"Right ({right_count}/{len(side_vals)})"
            else:
                tendency = "Balanced"
        else:
            tendency = "-"

        # Strike quality
        abs_strike = [abs(s.strike_distance) for s in club_shots if s.strike_distance is not None]
        abs_ix = [abs(s.impact_x) for s in club_shots if s.impact_x is not None]
        abs_iy = [abs(s.impact_y) for s in club_shots if s.impact_y is not None]

        # Scoring zone
        within_5 = sum(1 for c in carries if abs(c - carry_avg) <= SCORING_ZONE_TIGHT)
        within_10 = sum(1 for c in carries if abs(c - carry_avg) <= SCORING_ZONE_WIDE)
        pct_5 = (within_5 / len(carries)) * 100.0
        pct_10 = (within_10 / len(carries)) * 100.0

        results.append(WedgeStats(
            club=club,
            shot_count=len(club_shots),
            carry_mean=carry_avg,
            carry_std=carry_sd,
            carry_cv=cv,
            precision_score=_precision_label(cv),
            spin_mean=spin_mean,
            spin_std=spin_sd,
            side_mean=side_mean,
            side_std=side_sd,
            miss_tendency=tendency,
            avg_abs_strike=_mean(abs_strike) if abs_strike else None,
            avg_abs_impact_x=_mean(abs_ix) if abs_ix else None,
            avg_abs_impact_y=_mean(abs_iy) if abs_iy else None,
            pct_within_5=pct_5,
            pct_within_10=pct_10,
        ))

    return results


def _analyze_gapping(stats: list[WedgeStats]) -> list[dict[str, Any]]:
    ordered = sorted(stats, key=lambda s: s.carry_mean, reverse=True)
    gaps: list[dict[str, Any]] = []
    for i in range(len(ordered) - 1):
        higher = ordered[i]
        lower = ordered[i + 1]
        gap = higher.carry_mean - lower.carry_mean

        if gap > GAP_TOO_LARGE:
            flag = "TOO LARGE"
        elif gap < GAP_TOO_SMALL:
            flag = "TOO SMALL"
        else:
            flag = "OK"

        gaps.append({
            "from": higher.club,
            "to": lower.club,
            "gap": gap,
            "flag": flag,
        })
    return gaps


def _generate_recommendations(
    stats: list[WedgeStats],
    gaps: list[dict[str, Any]],
) -> list[str]:
    recs: list[str] = []

    # 1. Worst CV club
    sorted_by_cv = sorted(stats, key=lambda s: s.carry_cv if not math.isnan(s.carry_cv) else 999, reverse=True)
    worst = sorted_by_cv[0] if sorted_by_cv else None
    if worst and not math.isnan(worst.carry_cv):
        recs.append(
            f"Distance control priority: {worst.club} has the highest CV "
            f"({_fmt(worst.carry_cv)}%). Do 3x10-ball ladder drills with "
            f"{worst.club} targeting {_fmt(worst.carry_mean, 0)}yd. Goal: "
            f"get 7/10 shots within +/-5 yards of target."
        )

    # 2. Gapping issues
    for g in gaps:
        if g["flag"] == "TOO LARGE":
            recs.append(
                f"Gap too large: {g['from']}->{g['to']} is {_fmt(g['gap'])}yd "
                f"(target {_fmt(GAP_TOO_SMALL, 0)}-{_fmt(GAP_TOO_LARGE, 0)}yd). "
                f"Develop a 3/4 swing with {g['from']} or adjust loft to close "
                f"the gap. Practice 20-ball blocks at the midpoint distance."
            )
        elif g["flag"] == "TOO SMALL":
            recs.append(
                f"Gap too small: {g['from']}->{g['to']} is only {_fmt(g['gap'])}yd. "
                f"Consider adjusting setup or loft to separate these clubs by "
                f"at least {_fmt(GAP_TOO_SMALL, 0)}yd."
            )

    # 3. Worst strike quality
    strike_clubs = [s for s in stats if s.avg_abs_strike is not None]
    if strike_clubs:
        worst_strike = max(strike_clubs, key=lambda s: s.avg_abs_strike or 0)
        if worst_strike.avg_abs_strike and worst_strike.avg_abs_strike > 8.0:
            recs.append(
                f"Strike quality: {worst_strike.club} has avg strike distance "
                f"of {_fmt(worst_strike.avg_abs_strike)}mm from center. Use "
                f"face tape/spray to track impact and aim for under 8mm average."
            )

    # 4. Accuracy tendency
    for s in stats:
        if s.miss_tendency.startswith("Left") or s.miss_tendency.startswith("Right"):
            direction = "left" if s.miss_tendency.startswith("Left") else "right"
            recs.append(
                f"Accuracy: {s.club} tends to miss {direction} ({s.miss_tendency}). "
                f"Check alignment and face angle at impact. Practice with an "
                f"alignment stick drill to improve directional consistency."
            )

    # 5. Scoring zone improvement
    worst_zone = min(stats, key=lambda s: s.pct_within_5)
    if worst_zone.pct_within_5 < 40.0:
        recs.append(
            f"Scoring zone: Only {_fmt(worst_zone.pct_within_5)}% of {worst_zone.club} "
            f"shots land within 5 yards of your average. Target: 50%+. "
            f"Do 'clock drill' at 3 distances (50%, 75%, 100% swing) "
            f"with 10 balls each, recording landing distances."
        )

    if not recs:
        recs.append("Your wedge game looks solid! Maintain current practice patterns.")

    return recs


# ── Report output ────────────────────────────────────────────────────────

def _print_report(
    db_path: Path,
    stats: list[WedgeStats],
    gaps: list[dict[str, Any]],
    total_shots: int,
    recs: list[str],
) -> None:

    _print_header("SCORING CLUBS (WEDGE) ANALYSIS")
    print(f"  Database: {db_path}")
    print(f"  Clubs analyzed: {', '.join(SCORING_CLUBS)}")
    print(f"  Total qualifying shots: {total_shots}")
    print(f"  Minimum carry filter: {MISHIT_CARRY_THRESHOLD:.0f} yards")

    # ── Section 1: Distance Control ──────────────────────────────────
    _print_section("1) DISTANCE CONTROL")
    rows = []
    for s in stats:
        rows.append([
            s.club,
            str(s.shot_count),
            _fmt(s.carry_mean),
            _fmt(s.carry_std),
            _fmt(s.carry_cv),
            s.precision_score,
        ])
    _print_table(
        ["Club", "Shots", "Avg Carry", "Std Dev", "CV%", "Precision"],
        rows,
    )

    # ── Section 2: Spin Analysis ─────────────────────────────────────
    has_any_spin = any(s.spin_mean is not None for s in stats)
    if has_any_spin:
        _print_section("2) SPIN ANALYSIS")
        rows = []
        for s in stats:
            rows.append([
                s.club,
                str(s.shot_count),
                _fmt(s.spin_mean),
                _fmt(s.spin_std),
            ])
        _print_table(
            ["Club", "Shots", "Avg Back Spin", "Spin Std Dev"],
            rows,
        )
    else:
        _print_section("2) SPIN ANALYSIS")
        print("(back_spin data not available)")

    # ── Section 3: Accuracy ──────────────────────────────────────────
    _print_section("3) ACCURACY (Side Distance)")
    rows = []
    for s in stats:
        rows.append([
            s.club,
            str(s.shot_count),
            _fmt(s.side_mean),
            _fmt(s.side_std),
            s.miss_tendency,
        ])
    _print_table(
        ["Club", "Shots", "Avg Side", "Side Std", "Miss Tendency"],
        rows,
    )

    # ── Section 4: Strike Quality ────────────────────────────────────
    _print_section("4) STRIKE QUALITY")
    rows = []
    for s in stats:
        rows.append([
            s.club,
            str(s.shot_count),
            _fmt(s.avg_abs_strike),
            _fmt(s.avg_abs_impact_x),
            _fmt(s.avg_abs_impact_y),
        ])
    _print_table(
        ["Club", "Shots", "Avg |Strike|", "Avg |Impact X|", "Avg |Impact Y|"],
        rows,
    )

    # ── Section 5: Wedge Gapping ─────────────────────────────────────
    _print_section("5) WEDGE GAPPING")
    if gaps:
        rows = []
        for g in gaps:
            flag_display = g["flag"]
            if flag_display == "TOO LARGE":
                flag_display = f"!! {flag_display} (>{GAP_TOO_LARGE:.0f}yd)"
            elif flag_display == "TOO SMALL":
                flag_display = f"!! {flag_display} (<{GAP_TOO_SMALL:.0f}yd)"
            rows.append([
                f"{g['from']} -> {g['to']}",
                _fmt(g["gap"]),
                flag_display,
            ])
        _print_table(["Transition", "Gap (yd)", "Status"], rows)

        # Average gap
        avg_gap = _mean([g["gap"] for g in gaps])
        print(f"\n  Average gap: {_fmt(avg_gap)} yards (ideal: {GAP_TOO_SMALL:.0f}-{GAP_TOO_LARGE:.0f})")
    else:
        print("(fewer than 2 wedges with data)")

    # ── Section 6: Precision Ranking ─────────────────────────────────
    _print_section("6) PRECISION RANKING (lower CV% = better)")
    ranked = sorted(stats, key=lambda s: s.carry_cv if not math.isnan(s.carry_cv) else 999)
    rows = []
    for rank, s in enumerate(ranked, 1):
        rows.append([
            str(rank),
            s.club,
            _fmt(s.carry_cv),
            s.precision_score,
            str(s.shot_count),
        ])
    _print_table(["Rank", "Club", "CV%", "Rating", "Shots"], rows)

    # ── Section 7: Scoring Zone Analysis ─────────────────────────────
    _print_section("7) SCORING ZONE (% shots within target)")
    rows = []
    for s in stats:
        rows.append([
            s.club,
            str(s.shot_count),
            _fmt(s.carry_mean),
            f"{_fmt(s.pct_within_5)}%",
            f"{_fmt(s.pct_within_10)}%",
        ])
    _print_table(
        ["Club", "Shots", "Avg Carry", f"Within {SCORING_ZONE_TIGHT:.0f}yd", f"Within {SCORING_ZONE_WIDE:.0f}yd"],
        rows,
    )

    # ── Section 8: Recommendations ───────────────────────────────────
    _print_section("8) SHORT GAME IMPROVEMENT RECOMMENDATIONS")
    for i, rec in enumerate(recs, 1):
        print(f"  {i}. {rec}")

    print()


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deep analysis of scoring clubs (PW, GW, SW, LW) from golf_stats.db"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("golf_stats.db"),
        help="Path to SQLite database (default: golf_stats.db)",
    )
    args = parser.parse_args()

    if not args.db.exists():
        raise FileNotFoundError(f"Database not found: {args.db}")

    conn = _build_connection(args.db)
    try:
        cur = conn.cursor()
        carry_col = _detect_carry_column(cur)
        has_spin = _has_column(cur, "shots", "back_spin")
        shots = _fetch_wedge_shots(conn, carry_col, has_spin)
    finally:
        conn.close()

    if not shots:
        print("No scoring club shots found in database.")
        return

    # Group by club
    shots_by_club: dict[str, list[WedgeShot]] = defaultdict(list)
    for s in shots:
        shots_by_club[s.club].append(s)

    # Compute stats
    stats = _compute_wedge_stats(shots_by_club)
    gaps = _analyze_gapping(stats)
    recs = _generate_recommendations(stats, gaps)

    _print_report(args.db, stats, gaps, len(shots), recs)


if __name__ == "__main__":
    main()
