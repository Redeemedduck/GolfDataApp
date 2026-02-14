#!/usr/bin/env python3
"""Analyze landing positions and roll distances per club from golf_stats.db.

Uses optix_x, optix_y for landing position dispersion, carry/total for roll
distance calculations, and descent_angle for descent-to-roll correlation.
Produces a formatted text report to stdout.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
MIN_CARRY = 10.0
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
DEFAULT_MIN_SHOTS = 10

# Sentinel values from Uneekor (means "no data")
SENTINEL_VALUES = {99999.0, -99999.0}

# Thresholds for flagging
EXCESSIVE_ROLL_PCT = 20.0      # Roll > 20% of carry = "excessive roll"
HIGH_ROLL_STDEV_YARDS = 8.0    # Roll stdev > 8 yards = "inconsistent roll"

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
    """Convert to float, returning None for nulls, sentinels, and zeros."""
    if value is None:
        return None
    try:
        v = float(value)
        if v in SENTINEL_VALUES:
            return None
        return v
    except (TypeError, ValueError):
        return None


def to_float_nonzero(value: Any) -> Optional[float]:
    """Convert to float, also filtering out zero values (invalid for optix)."""
    v = to_float(value)
    if v is not None and v == 0.0:
        return None
    return v


def safe_mean(values: List[float]) -> float:
    """Return mean or NaN if empty."""
    return statistics.fmean(values) if values else math.nan


def safe_stdev(values: List[float]) -> float:
    """Return sample standard deviation, 0 for single value, NaN if empty."""
    if not values:
        return math.nan
    if len(values) == 1:
        return 0.0
    return statistics.stdev(values)


def fmt(value: float, decimals: int = 1) -> str:
    """Format a float, returning N/A for NaN/None/Inf."""
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "N/A"
    return f"{value:.{decimals}f}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    """Format a percentage value."""
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "N/A"
    return f"{value:.{decimals}f}%"


def pearson_r(xs: List[float], ys: List[float]) -> Optional[float]:
    """Compute Pearson correlation coefficient. Returns None if insufficient data."""
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


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
    """Open a read-only connection with busy timeout."""
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA query_only = ON")
    return conn


def resolve_carry_column(conn: sqlite3.Connection) -> str:
    """Auto-detect whether the carry column is 'carry_distance' or 'carry'."""
    cols = {str(row["name"]) for row in conn.execute("PRAGMA table_info(shots)").fetchall()}
    if "carry_distance" in cols:
        return "carry_distance"
    if "carry" in cols:
        return "carry"
    raise RuntimeError("shots table must contain carry_distance or carry column")


def detect_total_column(conn: sqlite3.Connection) -> str:
    """Auto-detect total distance column name."""
    cols = {str(row["name"]) for row in conn.execute("PRAGMA table_info(shots)").fetchall()}
    if "total" in cols:
        return "total"
    if "total_distance" in cols:
        return "total_distance"
    raise RuntimeError("shots table must contain total or total_distance column")


def fetch_shots(
    conn: sqlite3.Connection,
    carry_col: str,
    total_col: str,
) -> List[Dict[str, Any]]:
    """Fetch shots with landing and roll columns, excluding unwanted clubs."""
    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            TRIM(club) AS club,
            {carry_col} AS carry,
            {total_col} AS total,
            optix_x,
            optix_y,
            side_distance,
            descent_angle
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND club NOT IN ({placeholders})
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
    """Compute landing position, roll, and dispersion stats for a single club."""

    # --- Landing position (optix_x, optix_y) ---
    # Filter out zeros and sentinels for optix values
    optix_xs = [v for s in shots if (v := to_float_nonzero(s["optix_x"])) is not None]
    optix_ys = [v for s in shots if (v := to_float_nonzero(s["optix_y"])) is not None]

    avg_optix_x = safe_mean(optix_xs)
    avg_optix_y = safe_mean(optix_ys)
    std_optix_x = safe_stdev(optix_xs)
    std_optix_y = safe_stdev(optix_ys)

    # Landing dispersion radius: sqrt(std_x^2 + std_y^2)
    if not math.isnan(std_optix_x) and not math.isnan(std_optix_y):
        dispersion_radius = math.sqrt(std_optix_x ** 2 + std_optix_y ** 2)
    else:
        dispersion_radius = math.nan

    # --- Roll distance (total - carry) ---
    rolls: List[float] = []
    carries_for_roll: List[float] = []
    for s in shots:
        carry = to_float(s["carry"])
        total = to_float(s["total"])
        if carry is not None and total is not None and total >= carry:
            roll = total - carry
            rolls.append(roll)
            carries_for_roll.append(carry)

    avg_roll = safe_mean(rolls)
    avg_carry_for_roll = safe_mean(carries_for_roll)
    roll_stdev = safe_stdev(rolls)

    # Roll as % of carry
    if not math.isnan(avg_roll) and not math.isnan(avg_carry_for_roll) and avg_carry_for_roll > 0:
        roll_pct = (avg_roll / avg_carry_for_roll) * 100.0
    else:
        roll_pct = math.nan

    # --- Descent-to-roll correlation ---
    descent_roll_pairs_x: List[float] = []
    descent_roll_pairs_y: List[float] = []
    for s in shots:
        carry = to_float(s["carry"])
        total = to_float(s["total"])
        descent = to_float(s["descent_angle"])
        if (carry is not None and total is not None and descent is not None
                and total >= carry and descent > 0):
            descent_roll_pairs_x.append(descent)
            descent_roll_pairs_y.append(total - carry)

    descent_roll_corr = pearson_r(descent_roll_pairs_x, descent_roll_pairs_y)

    # --- Side miss tendency from optix_x ---
    # Negative = left, positive = right
    side_values = [v for s in shots if (v := to_float(s["side_distance"])) is not None]
    avg_side = safe_mean(side_values)

    if not math.isnan(avg_side):
        if avg_side < -3:
            side_tendency = "Left"
        elif avg_side > 3:
            side_tendency = "Right"
        else:
            side_tendency = "Center"
    else:
        side_tendency = "N/A"

    # --- Distance miss tendency from optix_y ---
    if not math.isnan(avg_optix_y):
        if avg_optix_y < -2:
            dist_tendency = "Short"
        elif avg_optix_y > 2:
            dist_tendency = "Long"
        else:
            dist_tendency = "On target"
    else:
        dist_tendency = "N/A"

    # --- Flags ---
    excessive_roll = not math.isnan(roll_pct) and roll_pct > EXCESSIVE_ROLL_PCT
    inconsistent_roll = not math.isnan(roll_stdev) and roll_stdev > HIGH_ROLL_STDEV_YARDS

    return {
        "club": club,
        "n": len(shots),
        "n_optix": len(optix_xs),
        "n_roll": len(rolls),
        # Landing position
        "avg_optix_x": avg_optix_x,
        "avg_optix_y": avg_optix_y,
        "std_optix_x": std_optix_x,
        "std_optix_y": std_optix_y,
        "dispersion_radius": dispersion_radius,
        # Roll
        "avg_roll": avg_roll,
        "roll_pct": roll_pct,
        "roll_stdev": roll_stdev,
        # Descent-to-roll
        "descent_roll_corr": descent_roll_corr,
        "descent_roll_n": len(descent_roll_pairs_x),
        # Tendencies
        "avg_side": avg_side,
        "side_tendency": side_tendency,
        "dist_tendency": dist_tendency,
        # Flags
        "excessive_roll": excessive_roll,
        "inconsistent_roll": inconsistent_roll,
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def build_landing_table(results: List[Dict[str, Any]]) -> str:
    """Per-club landing position and dispersion table."""
    headers = [
        "Club", "Shots", "Optix",
        "Avg X", "Avg Y", "Std X", "Std Y",
        "Dispersion R",
    ]
    rows = []
    for r in results:
        rows.append([
            r["club"],
            str(r["n"]),
            str(r["n_optix"]),
            fmt(r["avg_optix_x"]),
            fmt(r["avg_optix_y"]),
            fmt(r["std_optix_x"]),
            fmt(r["std_optix_y"]),
            fmt(r["dispersion_radius"]),
        ])
    return render_table(headers, rows)


def build_roll_table(results: List[Dict[str, Any]]) -> str:
    """Per-club roll distance table, sorted by roll ratio (highest first)."""
    # Sort by roll_pct descending for this table
    sorted_results = sorted(
        results,
        key=lambda r: r["roll_pct"] if not math.isnan(r["roll_pct"]) else -1,
        reverse=True,
    )
    headers = [
        "Club", "Roll N", "Avg Roll", "Roll %", "Roll Stdev", "Flags",
    ]
    rows = []
    for r in sorted_results:
        flags = []
        if r["excessive_roll"]:
            flags.append("EXCESSIVE")
        if r["inconsistent_roll"]:
            flags.append("INCONSISTENT")
        rows.append([
            r["club"],
            str(r["n_roll"]),
            fmt(r["avg_roll"]),
            fmt_pct(r["roll_pct"]),
            fmt(r["roll_stdev"]),
            ", ".join(flags) if flags else "OK",
        ])
    return render_table(headers, rows)


def build_descent_table(results: List[Dict[str, Any]]) -> str:
    """Per-club descent angle to roll correlation table."""
    # Only show clubs with enough paired data
    filtered = [r for r in results if r["descent_roll_corr"] is not None]
    if not filtered:
        return "  No clubs have sufficient descent angle + roll data for correlation analysis."

    # Sort by bag order
    filtered.sort(key=lambda r: bag_sort_key(r["club"]))

    headers = ["Club", "Pairs", "Correlation", "Steeper = Less Roll?"]
    rows = []
    for r in filtered:
        corr = r["descent_roll_corr"]
        # Negative correlation means steeper descent -> less roll (expected)
        if corr is not None and corr < -0.15:
            verdict = "Yes (r={:.2f})".format(corr)
        elif corr is not None and corr > 0.15:
            verdict = "No -- steeper = MORE roll (r={:.2f})".format(corr)
        elif corr is not None:
            verdict = "Weak/no relationship (r={:.2f})".format(corr)
        else:
            verdict = "N/A"

        rows.append([
            r["club"],
            str(r["descent_roll_n"]),
            fmt(corr, 3) if corr is not None else "N/A",
            verdict,
        ])
    return render_table(headers, rows)


def build_accuracy_table(results: List[Dict[str, Any]]) -> str:
    """Landing accuracy ranking -- best and worst dispersion, miss tendencies."""
    # Sort by dispersion radius (lowest = best)
    ranked = sorted(
        results,
        key=lambda r: r["dispersion_radius"] if not math.isnan(r["dispersion_radius"]) else 9999,
    )

    headers = ["Rank", "Club", "Dispersion R", "Side Tend", "Dist Tend", "Avg Side"]
    rows = []
    for i, r in enumerate(ranked, 1):
        rows.append([
            str(i),
            r["club"],
            fmt(r["dispersion_radius"]),
            r["side_tendency"],
            r["dist_tendency"],
            fmt(r["avg_side"]),
        ])
    return render_table(headers, rows)


def build_recommendations(results: List[Dict[str, Any]]) -> str:
    """Generate actionable recommendations based on analysis."""
    lines: List[str] = []

    # --- Clubs needing tighter landing patterns ---
    lines.append("CLUBS NEEDING TIGHTER LANDING PATTERNS")
    lines.append("-" * 50)

    # High dispersion radius
    dispersion_sorted = sorted(
        [r for r in results if not math.isnan(r["dispersion_radius"])],
        key=lambda r: r["dispersion_radius"],
        reverse=True,
    )
    loose_clubs = [r for r in dispersion_sorted if r["dispersion_radius"] > 10]
    if loose_clubs:
        for r in loose_clubs[:5]:
            issues = []
            if not math.isnan(r["std_optix_x"]) and r["std_optix_x"] > 8:
                issues.append(f"lateral spread {r['std_optix_x']:.1f}")
            if not math.isnan(r["std_optix_y"]) and r["std_optix_y"] > 8:
                issues.append(f"depth spread {r['std_optix_y']:.1f}")
            issue_str = f" ({', '.join(issues)})" if issues else ""
            lines.append(
                f"  {r['club']:20s}  dispersion radius {r['dispersion_radius']:.1f}{issue_str}"
            )
    else:
        lines.append("  None -- all clubs have reasonable landing dispersion.")

    # --- Excessive roll clubs ---
    lines.append("")
    lines.append("EXCESSIVE ROLL (> {:.0f}% of carry)".format(EXCESSIVE_ROLL_PCT))
    lines.append("-" * 50)
    excessive = [r for r in results if r["excessive_roll"]]
    excessive.sort(key=lambda r: r["roll_pct"], reverse=True)
    if excessive:
        for r in excessive:
            lines.append(
                f"  {r['club']:20s}  roll {r['avg_roll']:.1f} yds = {r['roll_pct']:.1f}% of carry"
                f"  -- consider landing angle/spin adjustments"
            )
    else:
        lines.append("  None -- all clubs have roll within normal range.")

    # --- Inconsistent roll clubs ---
    lines.append("")
    lines.append("INCONSISTENT ROLL (stdev > {:.0f} yds)".format(HIGH_ROLL_STDEV_YARDS))
    lines.append("-" * 50)
    inconsistent = [r for r in results if r["inconsistent_roll"]]
    inconsistent.sort(key=lambda r: r["roll_stdev"], reverse=True)
    if inconsistent:
        for r in inconsistent:
            lines.append(
                f"  {r['club']:20s}  roll stdev {r['roll_stdev']:.1f} yds"
                f"  -- unpredictable ground behavior"
            )
    else:
        lines.append("  None -- all clubs have consistent roll distances.")

    # --- Good control clubs ---
    lines.append("")
    lines.append("CLUBS WITH GOOD CONTROL")
    lines.append("-" * 50)
    good = [
        r for r in results
        if not math.isnan(r["dispersion_radius"])
        and r["dispersion_radius"] <= 10
        and not r["excessive_roll"]
        and not r["inconsistent_roll"]
    ]
    good.sort(key=lambda r: r["dispersion_radius"])
    if good:
        for r in good[:5]:
            lines.append(
                f"  {r['club']:20s}  dispersion {r['dispersion_radius']:.1f}"
                f", roll {fmt_pct(r['roll_pct'])}"
                f"  -- well controlled"
            )
    else:
        lines.append("  No clubs meet all control criteria.")

    # --- Side miss patterns ---
    lines.append("")
    lines.append("SIDE MISS PATTERNS")
    lines.append("-" * 50)
    left_miss = [r for r in results if r["side_tendency"] == "Left"]
    right_miss = [r for r in results if r["side_tendency"] == "Right"]
    if left_miss:
        clubs_str = ", ".join(r["club"] for r in left_miss)
        lines.append(f"  Tend LEFT:  {clubs_str}")
    if right_miss:
        clubs_str = ", ".join(r["club"] for r in right_miss)
        lines.append(f"  Tend RIGHT: {clubs_str}")
    if not left_miss and not right_miss:
        lines.append("  No significant side bias detected across clubs.")

    # --- Distance miss patterns ---
    lines.append("")
    lines.append("DISTANCE MISS PATTERNS")
    lines.append("-" * 50)
    short_miss = [r for r in results if r["dist_tendency"] == "Short"]
    long_miss = [r for r in results if r["dist_tendency"] == "Long"]
    if short_miss:
        clubs_str = ", ".join(r["club"] for r in short_miss)
        lines.append(f"  Tend SHORT: {clubs_str}")
    if long_miss:
        clubs_str = ", ".join(r["club"] for r in long_miss)
        lines.append(f"  Tend LONG:  {clubs_str}")
    if not short_miss and not long_miss:
        lines.append("  No significant distance bias detected across clubs.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze landing positions and roll distances per club."
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

    with build_connection(args.db) as conn:
        carry_col = resolve_carry_column(conn)
        total_col = detect_total_column(conn)
        shots = fetch_shots(conn, carry_col, total_col)

    if not shots:
        print("No qualifying shots found in the database.")
        return 1

    # Group by club
    by_club: Dict[str, List[Dict[str, Any]]] = {}
    for s in shots:
        club = s["club"].strip()
        if club:
            by_club.setdefault(club, []).append(s)

    # Analyze clubs with enough data
    results: List[Dict[str, Any]] = []
    skipped: List[Tuple[str, int]] = []
    for club, club_shots in by_club.items():
        if len(club_shots) < args.min_shots:
            skipped.append((club, len(club_shots)))
            continue
        results.append(analyze_club(club, club_shots))

    if not results:
        print(f"No clubs have {args.min_shots}+ qualifying shots.")
        return 1

    # Sort by bag order (primary sort for per-club tables)
    results.sort(key=lambda r: bag_sort_key(r["club"]))

    # Build report
    sections: List[str] = []

    sections.append("=" * 70)
    sections.append("LANDING ZONE & ROLL DISTANCE ANALYSIS")
    sections.append("=" * 70)
    sections.append(f"Database: {args.db}")
    sections.append(f"Total qualifying shots: {len(shots)}")
    sections.append(f"Clubs analyzed: {len(results)} (min {args.min_shots} shots, carry >= {MIN_CARRY:.0f} yds)")
    sections.append(f"Excluded: {', '.join(sorted(EXCLUDED_CLUBS))}")
    if skipped:
        skipped.sort(key=lambda x: x[1])
        skip_str = ", ".join(f"{c} ({n})" for c, n in skipped)
        sections.append(f"Skipped (too few shots): {skip_str}")
    sections.append("")

    # Section 1: Landing position stats
    sections.append("-" * 70)
    sections.append("1) LANDING POSITION (optix_x / optix_y)")
    sections.append("-" * 70)
    sections.append("   Optix X = lateral landing position, Optix Y = depth landing position")
    sections.append("   Dispersion R = sqrt(std_x^2 + std_y^2) -- lower is tighter")
    sections.append("   Zeros and sentinel values (99999) filtered out")
    sections.append("")
    sections.append(build_landing_table(results))
    sections.append("")

    # Section 2: Roll analysis
    sections.append("-" * 70)
    sections.append("2) ROLL DISTANCE (total - carry)")
    sections.append("-" * 70)
    sections.append("   Ranked by roll % of carry (highest first)")
    sections.append(f"   Excessive = roll > {EXCESSIVE_ROLL_PCT:.0f}% of carry")
    sections.append(f"   Inconsistent = roll stdev > {HIGH_ROLL_STDEV_YARDS:.0f} yds")
    sections.append("")
    sections.append(build_roll_table(results))
    sections.append("")

    # Section 3: Descent-to-roll correlation
    sections.append("-" * 70)
    sections.append("3) DESCENT ANGLE vs ROLL CORRELATION")
    sections.append("-" * 70)
    sections.append("   Expected: steeper descent -> less roll (negative correlation)")
    sections.append("   r < -0.15 confirms the pattern; r > 0.15 contradicts it")
    sections.append("")
    sections.append(build_descent_table(results))
    sections.append("")

    # Section 4: Landing accuracy ranking
    sections.append("-" * 70)
    sections.append("4) LANDING ACCURACY RANKING (tightest dispersion first)")
    sections.append("-" * 70)
    sections.append("   Side tendency from side_distance (neg = left, pos = right)")
    sections.append("   Distance tendency from optix_y (neg = short, pos = long)")
    sections.append("")
    sections.append(build_accuracy_table(results))
    sections.append("")

    # Section 5: Recommendations
    sections.append("=" * 70)
    sections.append("5) RECOMMENDATIONS")
    sections.append("=" * 70)
    sections.append("")
    sections.append(build_recommendations(results))

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
