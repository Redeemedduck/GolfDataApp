#!/usr/bin/env python3
"""Analyze spin characteristics per club using back_spin, side_spin, and related columns.

Produces a per-club spin profile report (sorted by bag order) with optimal spin
window analysis, consistency metrics, side-spin tendencies, spin efficiency,
and an overall summary highlighting clubs with spin issues.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
MIN_CARRY = 10.0
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
DEFAULT_MIN_SHOTS = 10

# Optimal back-spin windows (rpm) per club type
OPTIMAL_SPIN: Dict[str, Tuple[int, int]] = {
    "Driver": (2000, 2800),
    "3 Wood (Cobra)": (2500, 3500),
    "3 Wood (TM)": (2500, 3500),
    "7 Wood": (2500, 3500),
    "3 Iron": (4000, 5500),
    "4 Iron": (4000, 5500),
    "5 Iron": (4000, 5500),
    "6 Iron": (5500, 7500),
    "7 Iron": (5500, 7500),
    "8 Iron": (5500, 7500),
    "9 Iron": (7500, 9500),
    "PW": (7500, 9500),
    "GW": (8000, 11000),
    "SW": (8000, 11000),
    "LW": (8000, 11000),
}

# Loaded lazily from my_bag.json (project root)
_BAG_ORDER: Optional[List[str]] = None


def _load_bag_order() -> List[str]:
    """Return bag_order list from my_bag.json, or a sensible default."""
    global _BAG_ORDER
    if _BAG_ORDER is not None:
        return _BAG_ORDER

    bag_path = Path(__file__).resolve().parent.parent / "my_bag.json"
    if bag_path.exists():
        with open(bag_path) as f:
            data = json.load(f)
            _BAG_ORDER = data.get("bag_order", [])
            return _BAG_ORDER

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
        if v == 99999.0 or v == -99999.0:
            return None
        return v
    except (TypeError, ValueError):
        return None


def fmt(value: Optional[float], decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "N/A"
    return f"{value:.{decimals}f}"


def safe_mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def safe_median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    return s[mid]


def safe_stdev(values: List[float]) -> Optional[float]:
    """Population standard deviation (not sample) -- consistent with CV% usage."""
    if len(values) < 2:
        return None
    avg = sum(values) / len(values)
    variance = sum((x - avg) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def safe_correlation(xs: List[float], ys: List[float]) -> Optional[float]:
    """Pearson correlation coefficient between two lists of equal length."""
    if len(xs) != len(ys) or len(xs) < 3:
        return None

    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    cov = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)

    denom = math.sqrt(var_x * var_y)
    if denom < 1e-12:
        return None
    return cov / denom


def render_table(headers: List[str], rows: List[List[str]], right_align_from: int = 1) -> str:
    """Render an ASCII table. Column 0 is left-aligned; the rest right-aligned."""
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


def fetch_shots(conn: sqlite3.Connection, carry_col: str) -> List[Dict[str, Any]]:
    """Fetch all qualifying shots with spin-relevant columns."""
    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            TRIM(club) AS club,
            {carry_col} AS carry,
            back_spin,
            side_spin
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND TRIM(club) NOT IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
    """
    params = (*sorted(EXCLUDED_CLUBS), MIN_CARRY)
    cursor = conn.execute(query, params)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_club(club: str, shots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute spin profile metrics for a single club."""
    back_spins: List[float] = []
    side_spins: List[float] = []
    carries: List[float] = []

    # Paired lists for correlation (only shots with both back_spin and carry)
    corr_back: List[float] = []
    corr_carry: List[float] = []

    for s in shots:
        bs = to_float(s["back_spin"])
        ss = to_float(s["side_spin"])
        c = to_float(s["carry"])

        if bs is not None:
            back_spins.append(bs)
            if c is not None:
                corr_back.append(bs)
                corr_carry.append(c)
        if ss is not None:
            side_spins.append(ss)
        if c is not None:
            carries.append(c)

    # Back spin stats
    bs_avg = safe_mean(back_spins)
    bs_median = safe_median(back_spins)
    bs_std = safe_stdev(back_spins)
    bs_min = min(back_spins) if back_spins else None
    bs_max = max(back_spins) if back_spins else None

    # Side spin stats
    ss_avg = safe_mean(side_spins)
    ss_median = safe_median(side_spins)
    ss_std = safe_stdev(side_spins)

    # Total spin rate estimate: sqrt(back_spin^2 + side_spin^2) per shot, then average
    total_spins: List[float] = []
    for s in shots:
        bs = to_float(s["back_spin"])
        ss = to_float(s["side_spin"])
        if bs is not None and ss is not None:
            total_spins.append(math.sqrt(bs ** 2 + ss ** 2))

    total_spin_avg = safe_mean(total_spins)

    # Spin axis estimate: atan2(side_spin, back_spin) in degrees per shot, then average
    spin_axes: List[float] = []
    for s in shots:
        bs = to_float(s["back_spin"])
        ss = to_float(s["side_spin"])
        if bs is not None and ss is not None:
            spin_axes.append(math.degrees(math.atan2(ss, bs)))

    spin_axis_avg = safe_mean(spin_axes)

    # Spin-to-carry correlation
    spin_carry_corr = safe_correlation(corr_back, corr_carry)

    # Spin consistency: CV% of back_spin
    cv_pct: Optional[float] = None
    if bs_avg is not None and bs_std is not None and bs_avg > 0:
        cv_pct = (bs_std / bs_avg) * 100.0

    # Side spin tendency
    if ss_avg is not None:
        if ss_avg < -200:
            side_tendency = "Draw Spin"
        elif ss_avg > 200:
            side_tendency = "Fade Spin"
        else:
            side_tendency = "Neutral"
    else:
        side_tendency = "N/A"

    # Spin efficiency: % of total spin that is backspin
    # Average per-shot ratio for accuracy
    efficiency_ratios: List[float] = []
    for s in shots:
        bs = to_float(s["back_spin"])
        ss = to_float(s["side_spin"])
        if bs is not None and ss is not None:
            total = math.sqrt(bs ** 2 + ss ** 2)
            if total > 0:
                efficiency_ratios.append(bs / total * 100.0)

    spin_efficiency = safe_mean(efficiency_ratios)

    # Optimal window check
    optimal = OPTIMAL_SPIN.get(club)
    window_status: Optional[str] = None
    if optimal is not None and bs_avg is not None:
        low, high = optimal
        if bs_avg < low:
            window_status = f"LOW (avg {bs_avg:.0f} < {low})"
        elif bs_avg > high:
            window_status = f"HIGH (avg {bs_avg:.0f} > {high})"
        else:
            window_status = "OK"

    return {
        "club": club,
        "n": len(shots),
        "n_back_spin": len(back_spins),
        "n_side_spin": len(side_spins),
        "bs_avg": bs_avg,
        "bs_median": bs_median,
        "bs_std": bs_std,
        "bs_min": bs_min,
        "bs_max": bs_max,
        "ss_avg": ss_avg,
        "ss_median": ss_median,
        "ss_std": ss_std,
        "total_spin_avg": total_spin_avg,
        "spin_axis_avg": spin_axis_avg,
        "spin_carry_corr": spin_carry_corr,
        "cv_pct": cv_pct,
        "side_tendency": side_tendency,
        "spin_efficiency": spin_efficiency,
        "optimal_window": optimal,
        "window_status": window_status,
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def build_backspin_table(results: List[Dict[str, Any]]) -> str:
    """Build the back-spin statistics table."""
    headers = ["Club", "Shots", "Avg", "Median", "Std", "Min", "Max"]
    rows = []
    for r in results:
        rows.append([
            r["club"],
            str(r["n_back_spin"]),
            fmt(r["bs_avg"], 0),
            fmt(r["bs_median"], 0),
            fmt(r["bs_std"], 0),
            fmt(r["bs_min"], 0),
            fmt(r["bs_max"], 0),
        ])
    return render_table(headers, rows)


def build_sidespin_table(results: List[Dict[str, Any]]) -> str:
    """Build the side-spin statistics table."""
    headers = ["Club", "Shots", "Avg", "Median", "Std", "Tendency"]
    rows = []
    for r in results:
        rows.append([
            r["club"],
            str(r["n_side_spin"]),
            fmt(r["ss_avg"], 0),
            fmt(r["ss_median"], 0),
            fmt(r["ss_std"], 0),
            r["side_tendency"],
        ])
    return render_table(headers, rows)


def build_derived_table(results: List[Dict[str, Any]]) -> str:
    """Build the derived metrics table (total spin, axis, correlation)."""
    headers = ["Club", "TotalSpin", "SpinAxis", "BS-Carry r", "CV%", "Effic%"]
    rows = []
    for r in results:
        corr_str = fmt(r["spin_carry_corr"], 3) if r["spin_carry_corr"] is not None else "N/A"
        rows.append([
            r["club"],
            fmt(r["total_spin_avg"], 0),
            fmt(r["spin_axis_avg"], 1) + " deg" if r["spin_axis_avg"] is not None else "N/A",
            corr_str,
            fmt(r["cv_pct"], 1) + "%" if r["cv_pct"] is not None else "N/A",
            fmt(r["spin_efficiency"], 1) + "%" if r["spin_efficiency"] is not None else "N/A",
        ])
    return render_table(headers, rows)


def build_optimal_window_table(results: List[Dict[str, Any]]) -> str:
    """Build the optimal spin window analysis table."""
    headers = ["Club", "AvgBackSpin", "Optimal Low", "Optimal High", "Status"]
    rows = []
    for r in results:
        opt = r["optimal_window"]
        if opt is None:
            continue
        rows.append([
            r["club"],
            fmt(r["bs_avg"], 0),
            str(opt[0]),
            str(opt[1]),
            r["window_status"] or "N/A",
        ])
    if not rows:
        return "  No clubs matched known optimal spin windows."
    return render_table(headers, rows)


def build_summary(results: List[Dict[str, Any]]) -> str:
    """Build the overall summary section."""
    lines: List[str] = []

    if not results:
        lines.append("  No clubs with enough data for summary.")
        return "\n".join(lines)

    total_shots = sum(r["n"] for r in results)
    lines.append(f"  Total shots analyzed: {total_shots}")
    lines.append(f"  Clubs analyzed: {len(results)}")
    lines.append("")

    # Most consistent spinner (lowest CV%)
    clubs_with_cv = [r for r in results if r["cv_pct"] is not None]
    if clubs_with_cv:
        most_consistent = min(clubs_with_cv, key=lambda r: r["cv_pct"])
        least_consistent = max(clubs_with_cv, key=lambda r: r["cv_pct"])
        lines.append(f"  Most consistent spinner:  {most_consistent['club']}")
        lines.append(f"    Back-spin CV: {most_consistent['cv_pct']:.1f}% (lower = better)")
        lines.append("")
        lines.append(f"  Least consistent spinner: {least_consistent['club']}")
        lines.append(f"    Back-spin CV: {least_consistent['cv_pct']:.1f}%")
        lines.append("")

    # Highest and lowest average back spin
    clubs_with_bs = [r for r in results if r["bs_avg"] is not None]
    if clubs_with_bs:
        highest_spin = max(clubs_with_bs, key=lambda r: r["bs_avg"])
        lowest_spin = min(clubs_with_bs, key=lambda r: r["bs_avg"])
        lines.append(f"  Highest avg back-spin: {highest_spin['club']}")
        lines.append(f"    {highest_spin['bs_avg']:.0f} rpm")
        lines.append("")
        lines.append(f"  Lowest avg back-spin:  {lowest_spin['club']}")
        lines.append(f"    {lowest_spin['bs_avg']:.0f} rpm")
        lines.append("")

    # Clubs with spin issues (outside optimal window)
    issues = [r for r in results if r["window_status"] is not None and r["window_status"] != "OK"]
    if issues:
        lines.append("  Clubs outside optimal spin window:")
        for r in issues:
            opt = r["optimal_window"]
            lines.append(
                f"    {r['club']}: avg {r['bs_avg']:.0f} rpm "
                f"(target: {opt[0]}-{opt[1]} rpm) -- {r['window_status']}"
            )
        lines.append("")
    else:
        ok_clubs = [r for r in results if r["window_status"] == "OK"]
        if ok_clubs:
            lines.append("  All clubs with defined windows are within optimal spin range.")
            lines.append("")

    # Side spin tendency overview
    tendency_counts: Dict[str, int] = defaultdict(int)
    for r in results:
        tendency_counts[r["side_tendency"]] += 1
    if tendency_counts:
        lines.append("  Side-spin tendency breakdown:")
        for tendency in ["Draw Spin", "Neutral", "Fade Spin", "N/A"]:
            count = tendency_counts.get(tendency, 0)
            if count > 0:
                club_names = [r["club"] for r in results if r["side_tendency"] == tendency]
                lines.append(f"    {tendency}: {count} club(s) -- {', '.join(club_names)}")
        lines.append("")

    # Spin efficiency overview
    clubs_with_eff = [r for r in results if r["spin_efficiency"] is not None]
    if clubs_with_eff:
        best_eff = max(clubs_with_eff, key=lambda r: r["spin_efficiency"])
        worst_eff = min(clubs_with_eff, key=lambda r: r["spin_efficiency"])
        lines.append(f"  Best spin efficiency:  {best_eff['club']} at {best_eff['spin_efficiency']:.1f}%")
        lines.append(f"  Worst spin efficiency: {worst_eff['club']} at {worst_eff['spin_efficiency']:.1f}%")
        lines.append("  (Higher = more backspin vs sidespin = better)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze spin characteristics per club (back_spin, side_spin)."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--min-shots",
        type=int,
        default=DEFAULT_MIN_SHOTS,
        help=f"Minimum shots per club to include (default: {DEFAULT_MIN_SHOTS})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    min_shots = args.min_shots

    with build_connection(args.db) as conn:
        carry_col = resolve_carry_column(conn)
        shots = fetch_shots(conn, carry_col)

    if not shots:
        print("No qualifying shots found in the database.")
        return 0

    # Group by club
    by_club: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for s in shots:
        club = str(s["club"]).strip()
        if club:
            by_club[club].append(s)

    # Analyze each club
    results: List[Dict[str, Any]] = []
    skipped: List[Tuple[str, int]] = []
    for club, club_shots in by_club.items():
        if len(club_shots) < min_shots:
            skipped.append((club, len(club_shots)))
            continue
        results.append(analyze_club(club, club_shots))

    if not results:
        print(f"No clubs have {min_shots}+ qualifying shots.")
        return 0

    # Sort by bag order
    results.sort(key=lambda r: bag_sort_key(r["club"]))

    # Build report
    sections: List[str] = []
    sections.append("=" * 78)
    sections.append("SPIN PROFILE ANALYSIS")
    sections.append("=" * 78)
    sections.append(f"Database: {args.db}")
    sections.append(f"Total qualifying shots: {len(shots)}")
    sections.append(
        f"Clubs analyzed: {len(results)} (min {min_shots} shots, "
        f"{carry_col} >= {MIN_CARRY:.0f} yds)"
    )
    sections.append(f"Excluded: {', '.join(sorted(EXCLUDED_CLUBS))}")
    if skipped:
        skipped.sort(key=lambda x: x[1])
        skip_str = ", ".join(f"{c} ({n})" for c, n in skipped)
        sections.append(f"Skipped (too few shots): {skip_str}")
    sections.append("")

    # 1) Back-spin statistics
    sections.append("-" * 78)
    sections.append("1) BACK-SPIN STATISTICS (rpm)")
    sections.append("-" * 78)
    sections.append("")
    sections.append(build_backspin_table(results))
    sections.append("")

    # 2) Side-spin statistics
    sections.append("-" * 78)
    sections.append("2) SIDE-SPIN STATISTICS (rpm)")
    sections.append("   Negative = draw spin, Positive = fade spin")
    sections.append("-" * 78)
    sections.append("")
    sections.append(build_sidespin_table(results))
    sections.append("")

    # 3) Derived metrics
    sections.append("-" * 78)
    sections.append("3) DERIVED SPIN METRICS")
    sections.append("   TotalSpin = sqrt(back^2 + side^2)")
    sections.append("   SpinAxis  = atan2(side, back) in degrees")
    sections.append("   BS-Carry r = Pearson correlation (back_spin vs carry)")
    sections.append("   CV%       = back-spin coefficient of variation (lower = more consistent)")
    sections.append("   Effic%    = backspin / total spin (higher = less sidespin waste)")
    sections.append("-" * 78)
    sections.append("")
    sections.append(build_derived_table(results))
    sections.append("")

    # 4) Optimal spin windows
    sections.append("-" * 78)
    sections.append("4) OPTIMAL SPIN WINDOW ANALYSIS")
    sections.append("   Driver: 2000-2800 | Woods: 2500-3500 | Long Irons (3-5): 4000-5500")
    sections.append("   Mid Irons (6-8): 5500-7500 | Short Irons (9,PW): 7500-9500")
    sections.append("   Wedges (GW,SW,LW): 8000-11000")
    sections.append("-" * 78)
    sections.append("")
    sections.append(build_optimal_window_table(results))
    sections.append("")

    # 5) Summary
    sections.append("=" * 78)
    sections.append("SUMMARY")
    sections.append("=" * 78)
    sections.append("")
    sections.append(build_summary(results))
    sections.append("")

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
