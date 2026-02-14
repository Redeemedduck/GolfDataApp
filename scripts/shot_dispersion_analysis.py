#!/usr/bin/env python3
"""Analyze shot dispersion patterns per club from golf_stats.db.

Produces a per-club dispersion summary table (sorted by bag order), an overall
accuracy ranking, and actionable recommendations for alignment and consistency
work.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
MIN_SHOTS = 10
MIN_CARRY = 10.0

# Loaded lazily from my_bag.json (project root)
_BAG_ORDER: Optional[List[str]] = None


def _load_bag_order() -> List[str]:
    """Return bag_order list from my_bag.json, or a sensible default."""
    global _BAG_ORDER
    if _BAG_ORDER is not None:
        return _BAG_ORDER

    # Try project root relative to this script (scripts/ -> ..)
    bag_path = Path(__file__).resolve().parent.parent / "my_bag.json"
    if bag_path.exists():
        with open(bag_path) as f:
            data = json.load(f)
            _BAG_ORDER = data.get("bag_order", [])
            return _BAG_ORDER

    # Fallback
    _BAG_ORDER = [
        "Driver", "3 Wood (Cobra)", "3 Wood (TM)", "7 Wood",
        "3 Iron", "4 Iron", "5 Iron", "6 Iron", "7 Iron",
        "8 Iron", "9 Iron", "PW", "GW", "SW", "LW",
    ]
    return _BAG_ORDER


def bag_sort_key(club: str) -> Tuple[int, str]:
    """Sort key: clubs in bag_order first (by index), then alphabetical."""
    order = _load_bag_order()
    try:
        return (order.index(club), club)
    except ValueError:
        return (len(order), club)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(value)
        # Uneekor sentinel for "no data"
        if v == 99999.0 or v == -99999.0:
            return None
        return v
    except (TypeError, ValueError):
        return None


def fmean(values: List[float]) -> float:
    return statistics.fmean(values) if values else math.nan


def stdev(values: List[float]) -> float:
    if not values:
        return math.nan
    if len(values) == 1:
        return 0.0
    return statistics.stdev(values)


def fmt(value: float, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "N/A"
    return f"{value:.{decimals}f}"


def render_table(headers: List[str], rows: List[List[str]], right_align_from: int = 1) -> str:
    """Render an ASCII table.  Column 0 is left-aligned; the rest right-aligned."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    lines = [sep]
    lines.append(
        "| "
        + " | ".join(
            h.ljust(widths[i]) if i < right_align_from else h.rjust(widths[i])
            for i, h in enumerate(headers)
        )
        + " |"
    )
    lines.append(sep)
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if i < right_align_from:
                cells.append(cell.ljust(widths[i]))
            else:
                cells.append(cell.rjust(widths[i]))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append(sep)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Database access
# ---------------------------------------------------------------------------

def detect_carry_column(conn: sqlite3.Connection) -> str:
    """Return the actual carry column name (carry or carry_distance)."""
    cursor = conn.execute("PRAGMA table_info(shots)")
    columns = {row[1] for row in cursor.fetchall()}
    if "carry" in columns:
        return "carry"
    if "carry_distance" in columns:
        return "carry_distance"
    raise SystemExit("ERROR: No carry column found in shots table (expected 'carry' or 'carry_distance').")


def fetch_shots(conn: sqlite3.Connection, carry_col: str) -> List[Dict[str, Any]]:
    """Fetch relevant shots, excluding unwanted clubs and low-carry outliers."""
    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT club, {carry_col} AS carry, side_distance
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND club NOT IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
          AND side_distance IS NOT NULL
    """
    params = (*sorted(EXCLUDED_CLUBS), MIN_CARRY)
    cursor = conn.execute(query, params)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def classify_miss_tendency(side_mean: float, side_std: float) -> str:
    """Classify miss tendency based on side_distance stats.

    Convention: negative side_distance = left, positive = right.
    """
    if math.isnan(side_mean) or math.isnan(side_std):
        return "N/A"

    abs_mean = abs(side_mean)

    # If the standard deviation is large relative to the mean bias,
    # the pattern is inconsistent rather than a clear directional miss.
    if side_std > 15:
        if abs_mean < 5:
            return "Inconsistent (no bias)"
        elif side_mean < 0:
            return "Inconsistent (left bias)"
        else:
            return "Inconsistent (right bias)"

    if abs_mean < 3:
        if side_std < 8:
            return "Straight"
        return "Straight (some spread)"
    elif side_mean < 0:
        if abs_mean > 10:
            return "Strong draw/pull left"
        return "Draws left"
    else:
        if abs_mean > 10:
            return "Strong fade/push right"
        return "Fades right"


def analyze_club(club: str, shots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute dispersion statistics for a single club."""
    carries = [to_float(s["carry"]) for s in shots]
    carries = [c for c in carries if c is not None]
    sides = [to_float(s["side_distance"]) for s in shots]
    sides = [s for s in sides if s is not None]

    carry_mean = fmean(carries)
    carry_std = stdev(carries)
    carry_cv = (carry_std / carry_mean * 100) if carry_mean and not math.isnan(carry_mean) and carry_mean != 0 else math.nan

    side_mean = fmean(sides)
    side_std = stdev(sides)

    # Dispersion zones
    # 68% zone = mean +/- 1 sigma,  95% zone = mean +/- 2 sigma
    carry_68_lo = carry_mean - carry_std if not math.isnan(carry_mean) else math.nan
    carry_68_hi = carry_mean + carry_std if not math.isnan(carry_mean) else math.nan
    carry_95_lo = carry_mean - 2 * carry_std if not math.isnan(carry_mean) else math.nan
    carry_95_hi = carry_mean + 2 * carry_std if not math.isnan(carry_mean) else math.nan

    side_68_lo = side_mean - side_std if not math.isnan(side_mean) else math.nan
    side_68_hi = side_mean + side_std if not math.isnan(side_mean) else math.nan
    side_95_lo = side_mean - 2 * side_std if not math.isnan(side_mean) else math.nan
    side_95_hi = side_mean + 2 * side_std if not math.isnan(side_mean) else math.nan

    tendency = classify_miss_tendency(side_mean, side_std)

    # Accuracy score (lower = more accurate): combination of side bias and spread
    # sqrt(side_mean^2 + side_std^2) gives a single "dispersion radius"
    if not math.isnan(side_mean) and not math.isnan(side_std):
        accuracy_score = math.sqrt(side_mean ** 2 + side_std ** 2)
    else:
        accuracy_score = math.nan

    return {
        "club": club,
        "n": len(shots),
        "carry_mean": carry_mean,
        "carry_std": carry_std,
        "carry_cv": carry_cv,
        "carry_68": (carry_68_lo, carry_68_hi),
        "carry_95": (carry_95_lo, carry_95_hi),
        "side_mean": side_mean,
        "side_std": side_std,
        "side_bias": "left" if side_mean < -1 else ("right" if side_mean > 1 else "center"),
        "side_68": (side_68_lo, side_68_hi),
        "side_95": (side_95_lo, side_95_hi),
        "tendency": tendency,
        "accuracy_score": accuracy_score,
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_zone(lo: float, hi: float) -> str:
    if math.isnan(lo) or math.isnan(hi):
        return "N/A"
    return f"{lo:+.1f} to {hi:+.1f}"


def format_zone_carry(lo: float, hi: float) -> str:
    if math.isnan(lo) or math.isnan(hi):
        return "N/A"
    return f"{lo:.0f}-{hi:.0f}"


def build_dispersion_table(results: List[Dict[str, Any]]) -> str:
    headers = [
        "Club", "Shots",
        "Carry Avg", "Carry Std", "CV%",
        "Side Mean", "Side Std", "Side Bias",
        "68% Carry", "95% Carry",
        "68% Side", "95% Side",
        "Miss Tendency",
    ]
    rows = []
    for r in results:
        rows.append([
            r["club"],
            str(r["n"]),
            fmt(r["carry_mean"], 0),
            fmt(r["carry_std"], 1),
            fmt(r["carry_cv"], 1),
            fmt(r["side_mean"], 1),
            fmt(r["side_std"], 1),
            r["side_bias"],
            format_zone_carry(*r["carry_68"]),
            format_zone_carry(*r["carry_95"]),
            format_zone(*r["side_68"]),
            format_zone(*r["side_95"]),
            r["tendency"],
        ])
    return render_table(headers, rows)


def build_accuracy_ranking(results: List[Dict[str, Any]]) -> str:
    ranked = sorted(results, key=lambda r: r["accuracy_score"] if not math.isnan(r["accuracy_score"]) else 999)
    headers = ["Rank", "Club", "Accuracy Score", "Side Mean", "Side Std", "Miss Tendency"]
    rows = []
    for i, r in enumerate(ranked, 1):
        rows.append([
            str(i),
            r["club"],
            fmt(r["accuracy_score"], 1),
            fmt(r["side_mean"], 1),
            fmt(r["side_std"], 1),
            r["tendency"],
        ])
    return render_table(headers, rows)


def build_recommendations(results: List[Dict[str, Any]]) -> str:
    lines = []

    # Alignment issues: clubs with significant side bias (|mean| > 5)
    alignment_clubs = [r for r in results if not math.isnan(r["side_mean"]) and abs(r["side_mean"]) > 5]
    alignment_clubs.sort(key=lambda r: abs(r["side_mean"]), reverse=True)

    # Consistency issues: clubs with high side std (> 12) or high carry CV (> 8%)
    consistency_clubs = [
        r for r in results
        if (not math.isnan(r["side_std"]) and r["side_std"] > 12)
        or (not math.isnan(r["carry_cv"]) and r["carry_cv"] > 8)
    ]
    consistency_clubs.sort(key=lambda r: r.get("accuracy_score", 0), reverse=True)

    # Best performers
    clean = [r for r in results if not math.isnan(r["accuracy_score"])]
    best = sorted(clean, key=lambda r: r["accuracy_score"])[:3] if clean else []

    lines.append("=" * 70)
    lines.append("ACTIONABLE RECOMMENDATIONS")
    lines.append("=" * 70)

    # --- Alignment work ---
    lines.append("")
    lines.append("ALIGNMENT WORK NEEDED (side bias > 5 yards)")
    lines.append("-" * 50)
    if alignment_clubs:
        for r in alignment_clubs:
            direction = "LEFT" if r["side_mean"] < 0 else "RIGHT"
            lines.append(
                f"  {r['club']:20s}  avg {abs(r['side_mean']):.1f} yds {direction}"
                f"  -- check face angle at impact, aim alignment"
            )
    else:
        lines.append("  None -- all clubs have reasonable alignment.")

    # --- Consistency work ---
    lines.append("")
    lines.append("CONSISTENCY WORK NEEDED (high spread or high carry CV)")
    lines.append("-" * 50)
    if consistency_clubs:
        for r in consistency_clubs:
            issues = []
            if not math.isnan(r["side_std"]) and r["side_std"] > 12:
                issues.append(f"side spread {r['side_std']:.1f} yds")
            if not math.isnan(r["carry_cv"]) and r["carry_cv"] > 8:
                issues.append(f"carry CV {r['carry_cv']:.1f}%")
            lines.append(f"  {r['club']:20s}  {', '.join(issues)}")
    else:
        lines.append("  None -- all clubs are reasonably consistent.")

    # --- Best performers ---
    lines.append("")
    lines.append("MOST ACCURATE CLUBS (top 3)")
    lines.append("-" * 50)
    for r in best:
        lines.append(
            f"  {r['club']:20s}  accuracy score {r['accuracy_score']:.1f}"
            f"  ({r['tendency']})"
        )

    # --- Overall summary ---
    lines.append("")
    lines.append("SUMMARY")
    lines.append("-" * 50)
    avg_accuracy = fmean([r["accuracy_score"] for r in clean]) if clean else math.nan
    if not math.isnan(avg_accuracy):
        lines.append(f"  Average accuracy score across all clubs: {avg_accuracy:.1f}")
    if alignment_clubs:
        lines.append(f"  {len(alignment_clubs)} club(s) need alignment work.")
    if consistency_clubs:
        lines.append(f"  {len(consistency_clubs)} club(s) need consistency work.")
    if not alignment_clubs and not consistency_clubs:
        lines.append("  Overall dispersion looks solid. Focus on maintaining current patterns.")

    lines.append("")
    lines.append("NOTE: Accuracy score = sqrt(side_mean^2 + side_std^2). Lower is better.")
    lines.append("      Side distance: negative = left, positive = right.")
    lines.append("      CV% = carry standard deviation / carry mean * 100.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_analysis(db_path: str) -> str:
    if not os.path.exists(db_path):
        raise SystemExit(f"ERROR: Database not found: {db_path}")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")

    carry_col = detect_carry_column(conn)

    shots = fetch_shots(conn, carry_col)
    conn.close()

    if not shots:
        return "No qualifying shots found in the database."

    # Group by club
    by_club: Dict[str, List[Dict[str, Any]]] = {}
    for s in shots:
        by_club.setdefault(s["club"], []).append(s)

    # Analyze clubs with enough data
    results = []
    skipped = []
    for club, club_shots in by_club.items():
        if len(club_shots) < MIN_SHOTS:
            skipped.append((club, len(club_shots)))
            continue
        results.append(analyze_club(club, club_shots))

    if not results:
        return f"No clubs have {MIN_SHOTS}+ qualifying shots."

    # Sort by bag order
    results.sort(key=lambda r: bag_sort_key(r["club"]))

    # Build output
    sections = []
    sections.append("=" * 70)
    sections.append("SHOT DISPERSION ANALYSIS")
    sections.append("=" * 70)
    sections.append(f"Database: {db_path}")
    sections.append(f"Total qualifying shots: {len(shots)}")
    sections.append(f"Clubs analyzed: {len(results)} (min {MIN_SHOTS} shots, carry >= {MIN_CARRY:.0f} yds)")
    if skipped:
        skipped.sort(key=lambda x: x[1])
        skip_str = ", ".join(f"{c} ({n})" for c, n in skipped)
        sections.append(f"Skipped (too few shots): {skip_str}")
    sections.append("")

    sections.append("PER-CLUB DISPERSION SUMMARY (sorted by bag order)")
    sections.append("")
    sections.append(build_dispersion_table(results))
    sections.append("")

    sections.append("OVERALL ACCURACY RANKING (most accurate first)")
    sections.append("")
    sections.append(build_accuracy_ranking(results))
    sections.append("")

    sections.append(build_recommendations(results))

    return "\n".join(sections)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze shot dispersion patterns per club from golf_stats.db."
    )
    parser.add_argument(
        "--db",
        default="golf_stats.db",
        help="Path to SQLite database file (default: golf_stats.db)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(run_analysis(args.db))


if __name__ == "__main__":
    main()
