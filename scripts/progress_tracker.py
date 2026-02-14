#!/usr/bin/env python3
"""Track month-over-month golf improvement from golf_stats.db.

Analyzes carry distance, smash factor, face-to-path accuracy, and strike
quality trends per club over a configurable number of months. Highlights
most improved clubs, plateaus, and regressions.
"""

from __future__ import annotations

import argparse
import math
import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, NamedTuple, Optional, Tuple


EXCLUDED_CLUBS = {"Sim Round", "Other", "Putter"}
MIN_SHOTS_PER_MONTH = 5

# Thresholds for trend classification
IMPROVE_THRESHOLD = 0.02   # 2% improvement considered meaningful
REGRESS_THRESHOLD = -0.02  # 2% regression considered meaningful


class MonthMetrics(NamedTuple):
    """Aggregated metrics for a single club-month."""

    avg_carry: float
    avg_smash: float
    avg_face_to_path: float  # avg |face_to_path|
    avg_strike_distance: float  # avg |strike_distance|
    shot_count: int


class ClubTrend(NamedTuple):
    """Month-over-month trend for a single metric."""

    direction: str  # "up", "down", "flat"
    rate_per_month: float  # absolute change per month
    pct_change: float  # percentage change from first to last month


def detect_carry_column(cursor: sqlite3.Cursor) -> str:
    """Detect whether the carry column is named 'carry' or 'carry_distance'."""
    cursor.execute("PRAGMA table_info(shots)")
    columns = {row[1] for row in cursor.fetchall()}
    if "carry" in columns:
        return "carry"
    if "carry_distance" in columns:
        return "carry_distance"
    raise RuntimeError(
        "Cannot find carry column in shots table. "
        "Expected 'carry' or 'carry_distance'."
    )


def arrow(direction: str) -> str:
    """Return a directional arrow for a trend."""
    return {"up": "\u2191", "down": "\u2193", "flat": "\u2192"}.get(direction, "?")


def classify_trend(values: List[float]) -> Tuple[str, float, float]:
    """Classify a list of monthly values as improving, regressing, or flat.

    Returns (direction, rate_per_month, pct_change).
    For face_to_path and strike_distance, lower is better -- the caller
    must invert the sign before calling this function if needed.
    """
    if len(values) < 2:
        return "flat", 0.0, 0.0

    first = values[0]
    last = values[-1]

    if first == 0:
        pct = 0.0
    else:
        pct = (last - first) / abs(first)

    n = len(values) - 1
    rate = (last - first) / n if n > 0 else 0.0

    if pct > IMPROVE_THRESHOLD:
        return "up", rate, pct
    elif pct < REGRESS_THRESHOLD:
        return "down", rate, pct
    else:
        return "flat", rate, pct


def format_num(value: float, decimals: int = 1) -> str:
    """Format a number, returning 'N/A' for NaN."""
    if value is None or math.isnan(value):
        return "N/A"
    return f"{value:.{decimals}f}"


def format_pct(value: float) -> str:
    """Format a percentage change with sign."""
    if math.isnan(value):
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.1f}%"


def render_table(headers: List[str], rows: List[List[str]]) -> str:
    """Render a simple ASCII table."""
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
        formatted = []
        for i, cell in enumerate(row):
            if i == 0:
                formatted.append(cell.ljust(widths[i]))
            else:
                formatted.append(cell.rjust(widths[i]))
        out.append("| " + " | ".join(formatted) + " |")
    out.append(sep)
    return "\n".join(out)


def fetch_data(
    db_path: str, months: int
) -> Dict[str, Dict[str, MonthMetrics]]:
    """Fetch and aggregate shot data grouped by club and month.

    Returns: {club_name: {month_str: MonthMetrics}}
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Extra safety: read-only pragma
    cursor.execute("PRAGMA query_only = ON")

    carry_col = detect_carry_column(cursor)

    # Calculate cutoff date
    cutoff = datetime.now() - timedelta(days=months * 31)
    cutoff_str = cutoff.strftime("%Y-%m")

    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            club,
            strftime('%Y-%m', session_date) AS month,
            {carry_col} AS carry,
            smash,
            face_to_path,
            strike_distance
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND club NOT IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= 10
          AND session_date IS NOT NULL
          AND strftime('%Y-%m', session_date) >= ?
        ORDER BY session_date
    """
    params = tuple(EXCLUDED_CLUBS) + (cutoff_str,)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Group by club -> month
    raw: Dict[str, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        club = row["club"]
        month = row["month"]
        raw[club][month].append({
            "carry": row["carry"],
            "smash": row["smash"],
            "face_to_path": row["face_to_path"],
            "strike_distance": row["strike_distance"],
        })

    # Aggregate
    result: Dict[str, Dict[str, MonthMetrics]] = {}
    for club, months_data in raw.items():
        result[club] = {}
        for month, shots in months_data.items():
            if len(shots) < MIN_SHOTS_PER_MONTH:
                continue

            carries = [s["carry"] for s in shots if s["carry"] is not None]
            smashes = [s["smash"] for s in shots if s["smash"] is not None]
            f2p = [abs(s["face_to_path"]) for s in shots if s["face_to_path"] is not None]
            sd = [abs(s["strike_distance"]) for s in shots if s["strike_distance"] is not None]

            result[club][month] = MonthMetrics(
                avg_carry=statistics.fmean(carries) if carries else math.nan,
                avg_smash=statistics.fmean(smashes) if smashes else math.nan,
                avg_face_to_path=statistics.fmean(f2p) if f2p else math.nan,
                avg_strike_distance=statistics.fmean(sd) if sd else math.nan,
                shot_count=len(shots),
            )

    # Remove clubs with fewer than 2 months of data
    result = {c: m for c, m in result.items() if len(m) >= 2}
    return result


def analyze_club(
    club: str, monthly: Dict[str, MonthMetrics]
) -> Dict[str, object]:
    """Analyze trends for a single club across months."""
    sorted_months = sorted(monthly.keys())
    metrics = [monthly[m] for m in sorted_months]

    carry_vals = [m.avg_carry for m in metrics if not math.isnan(m.avg_carry)]
    smash_vals = [m.avg_smash for m in metrics if not math.isnan(m.avg_smash)]
    # For face_to_path and strike_distance, LOWER is better, so we negate for trend
    f2p_vals = [m.avg_face_to_path for m in metrics if not math.isnan(m.avg_face_to_path)]
    sd_vals = [m.avg_strike_distance for m in metrics if not math.isnan(m.avg_strike_distance)]

    carry_trend = classify_trend(carry_vals)
    smash_trend = classify_trend(smash_vals)

    # For accuracy metrics, negate so "down" (closer to zero) = improvement
    f2p_neg = [-v for v in f2p_vals]
    sd_neg = [-v for v in sd_vals]
    f2p_trend = classify_trend(f2p_neg)
    sd_trend = classify_trend(sd_neg)

    # Score: count of improving metrics minus regressing
    score = 0
    for t in [carry_trend, smash_trend, f2p_trend, sd_trend]:
        if t[0] == "up":
            score += 1
        elif t[0] == "down":
            score -= 1

    return {
        "club": club,
        "months": sorted_months,
        "monthly": monthly,
        "carry_trend": ClubTrend(*carry_trend),
        "smash_trend": ClubTrend(*smash_trend),
        "f2p_trend": ClubTrend(*f2p_trend),
        "sd_trend": ClubTrend(*sd_trend),
        "score": score,
        "total_shots": sum(m.shot_count for m in metrics),
    }


def generate_report(db_path: str, months: int) -> str:
    """Generate the full progress tracking report."""
    data = fetch_data(db_path, months)

    if not data:
        return (
            f"No clubs with {MIN_SHOTS_PER_MONTH}+ shots in at least 2 months "
            f"within the last {months} months."
        )

    analyses = []
    for club, monthly in data.items():
        analyses.append(analyze_club(club, monthly))

    # Sort by score descending, then by total shots
    analyses.sort(key=lambda a: (-a["score"], -a["total_shots"]))

    lines: List[str] = []
    lines.append("=" * 72)
    lines.append("  MONTH-OVER-MONTH PROGRESS TRACKER")
    lines.append(f"  Database: {db_path}")
    lines.append(f"  Period: last {months} months")
    lines.append(f"  Clubs tracked: {len(analyses)}")
    lines.append("=" * 72)
    lines.append("")

    # Per-club detail
    for a in analyses:
        club = a["club"]
        months_list = a["months"]
        monthly = a["monthly"]

        lines.append(f"--- {club} ({a['total_shots']} shots, {len(months_list)} months) ---")
        lines.append("")

        # Monthly breakdown table
        headers = ["Month", "Shots", "Carry", "Smash", "|F2P|", "|Strike|"]
        rows = []
        for m in months_list:
            met = monthly[m]
            rows.append([
                m,
                str(met.shot_count),
                format_num(met.avg_carry),
                format_num(met.avg_smash, 3),
                format_num(met.avg_face_to_path),
                format_num(met.avg_strike_distance, 2),
            ])
        lines.append(render_table(headers, rows))
        lines.append("")

        # Trend summary
        ct = a["carry_trend"]
        st = a["smash_trend"]
        ft = a["f2p_trend"]
        dt = a["sd_trend"]

        lines.append(f"  Carry:    {arrow(ct.direction)} {format_pct(ct.pct_change)}  ({format_num(ct.rate_per_month)} yds/mo)")
        lines.append(f"  Smash:    {arrow(st.direction)} {format_pct(st.pct_change)}  ({format_num(st.rate_per_month, 3)}/mo)")
        lines.append(f"  |F2P|:    {arrow(ft.direction)} {format_pct(ft.pct_change)}  (lower is better)")
        lines.append(f"  |Strike|: {arrow(dt.direction)} {format_pct(dt.pct_change)}  (lower is better)")
        lines.append("")

    # Summary sections
    lines.append("=" * 72)
    lines.append("  HIGHLIGHTS")
    lines.append("=" * 72)
    lines.append("")

    most_improved = [a for a in analyses if a["score"] >= 2]
    plateaued = [a for a in analyses if a["score"] == 0]
    regressed = [a for a in analyses if a["score"] <= -2]

    if most_improved:
        lines.append("  MOST IMPROVED:")
        for a in most_improved:
            improving = []
            if a["carry_trend"].direction == "up":
                improving.append(f"carry {format_pct(a['carry_trend'].pct_change)}")
            if a["smash_trend"].direction == "up":
                improving.append(f"smash {format_pct(a['smash_trend'].pct_change)}")
            if a["f2p_trend"].direction == "up":
                improving.append(f"face-to-path {format_pct(a['f2p_trend'].pct_change)}")
            if a["sd_trend"].direction == "up":
                improving.append(f"strike {format_pct(a['sd_trend'].pct_change)}")
            lines.append(f"    {arrow('up')} {a['club']}: {', '.join(improving)}")
        lines.append("")

    if plateaued:
        lines.append("  PLATEAUED (maintaining):")
        for a in plateaued:
            lines.append(f"    {arrow('flat')} {a['club']} ({a['total_shots']} shots)")
        lines.append("")

    if regressed:
        lines.append("  NEEDS ATTENTION:")
        for a in regressed:
            declining = []
            if a["carry_trend"].direction == "down":
                declining.append(f"carry {format_pct(a['carry_trend'].pct_change)}")
            if a["smash_trend"].direction == "down":
                declining.append(f"smash {format_pct(a['smash_trend'].pct_change)}")
            if a["f2p_trend"].direction == "down":
                declining.append(f"face-to-path {format_pct(a['f2p_trend'].pct_change)}")
            if a["sd_trend"].direction == "down":
                declining.append(f"strike {format_pct(a['sd_trend'].pct_change)}")
            lines.append(f"    {arrow('down')} {a['club']}: {', '.join(declining)}")
        lines.append("")

    if not most_improved and not plateaued and not regressed:
        lines.append("  Mixed results across clubs -- no strong patterns.")
        lines.append("")

    # Overall verdict
    lines.append("=" * 72)
    lines.append("  OVERALL ASSESSMENT")
    lines.append("=" * 72)
    lines.append("")

    total_score = sum(a["score"] for a in analyses)
    avg_score = total_score / len(analyses) if analyses else 0

    if avg_score > 0.5:
        verdict = "IMPROVING -- You are trending in the right direction across most clubs."
    elif avg_score < -0.5:
        verdict = "REGRESSING -- Several clubs are declining. Consider focused practice."
    else:
        verdict = "MAINTAINING -- Performance is stable. Look for specific areas to push."

    lines.append(f"  {verdict}")
    lines.append("")
    lines.append(f"  Improving: {len(most_improved)} club(s)")
    lines.append(f"  Plateaued: {len(plateaued)} club(s)")
    lines.append(f"  Regressed: {len(regressed)} club(s)")
    mixed = len(analyses) - len(most_improved) - len(plateaued) - len(regressed)
    if mixed > 0:
        lines.append(f"  Mixed:     {mixed} club(s)")
    lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track month-over-month golf improvement."
    )
    parser.add_argument(
        "--db",
        default="golf_stats.db",
        help="Path to SQLite database file (default: golf_stats.db)",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=6,
        help="Number of months to analyze (default: 6)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(generate_report(args.db, args.months))


if __name__ == "__main__":
    main()
