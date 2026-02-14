#!/usr/bin/env python3
"""Classify every shot by shape using face_to_path, side_spin, and side_angle.

Produces a per-club shape distribution report (sorted by bag order), trend
analysis for clubs with enough data, and an overall summary highlighting
consistency and dominant tendencies.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
MIN_CARRY = 10.0
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
DEFAULT_MIN_SHOTS = 10
TREND_MIN_SHOTS = 50

SHAPE_NAMES = ["Straight", "Draw", "Fade", "Hook", "Slice", "Pull", "Push"]

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


def fmt(value: float, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "N/A"
    return f"{value:.{decimals}f}"


def pct_str(count: int, total: int) -> str:
    """Format a count as a percentage of total."""
    if total == 0:
        return "0.0%"
    return f"{count / total * 100:.1f}%"


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
    """Fetch all qualifying shots with shape-relevant columns."""
    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            TRIM(club) AS club,
            {carry_col} AS carry,
            face_to_path,
            side_spin,
            side_angle
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
# Shot shape classification
# ---------------------------------------------------------------------------

def classify_shape(face_to_path: Optional[float],
                   side_spin: Optional[float],
                   side_angle: Optional[float]) -> str:
    """Classify a single shot's shape.

    Priority order matters: Hook/Slice are checked before Draw/Fade because
    they are more extreme versions. Pull/Push are checked last because they
    depend on side_angle with a narrow face_to_path condition.
    """
    f2p = face_to_path
    ss = side_spin
    sa = side_angle

    # Need at least face_to_path or side_spin for curvature classification
    if f2p is None and ss is None:
        return "Unknown"

    # Default missing values to neutral so combined checks work
    f2p_val = f2p if f2p is not None else 0.0
    ss_val = ss if ss is not None else 0.0
    sa_val = sa if sa is not None else 0.0

    # Hook: extreme draw -- face_to_path < -4.0 AND side_spin < -800
    if f2p_val < -4.0 and ss_val < -800:
        return "Hook"

    # Slice: extreme fade -- face_to_path > 4.0 AND side_spin > 800
    if f2p_val > 4.0 and ss_val > 800:
        return "Slice"

    # Pull: starts left with minimal curvature
    if sa_val < -3.0 and abs(f2p_val) < 2.0:
        return "Pull"

    # Push: starts right with minimal curvature
    if sa_val > 3.0 and abs(f2p_val) < 2.0:
        return "Push"

    # Straight: minimal face_to_path AND minimal side_spin
    if abs(f2p_val) < 1.5 and abs(ss_val) < 300:
        return "Straight"

    # Draw: negative face_to_path OR negative side_spin (right-handed)
    if f2p_val < -1.5 or ss_val < -300:
        return "Draw"

    # Fade: positive face_to_path OR positive side_spin
    if f2p_val > 1.5 or ss_val > 300:
        return "Fade"

    return "Straight"


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_club(club: str, shots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Classify all shots for a club and compute shape distribution."""
    shape_counts: Counter = Counter()
    for s in shots:
        shape = classify_shape(
            to_float(s["face_to_path"]),
            to_float(s["side_spin"]),
            to_float(s["side_angle"]),
        )
        shape_counts[shape] += 1

    total = len(shots)
    dominant = shape_counts.most_common(1)[0] if shape_counts else ("Unknown", 0)
    consistency = dominant[1] / total * 100.0 if total > 0 else 0.0

    return {
        "club": club,
        "n": total,
        "shape_counts": shape_counts,
        "dominant": dominant[0],
        "consistency": consistency,
    }


def analyze_trend(club: str, shots: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Split shots into first/second half and compare dominant shape shift.

    Returns None if the club has fewer than TREND_MIN_SHOTS shots.
    """
    if len(shots) < TREND_MIN_SHOTS:
        return None

    mid = len(shots) // 2
    first_half = shots[:mid]
    second_half = shots[mid:]

    def half_summary(half: List[Dict[str, Any]]) -> Tuple[str, float, Counter]:
        counts: Counter = Counter()
        for s in half:
            shape = classify_shape(
                to_float(s["face_to_path"]),
                to_float(s["side_spin"]),
                to_float(s["side_angle"]),
            )
            counts[shape] += 1
        total = len(half)
        dom = counts.most_common(1)[0] if counts else ("Unknown", 0)
        pct = dom[1] / total * 100.0 if total > 0 else 0.0
        return dom[0], pct, counts

    first_dom, first_pct, first_counts = half_summary(first_half)
    second_dom, second_pct, second_counts = half_summary(second_half)

    changing = first_dom != second_dom
    direction = "CHANGING" if changing else "STABLE"

    return {
        "club": club,
        "first_n": len(first_half),
        "second_n": len(second_half),
        "first_dominant": first_dom,
        "first_pct": first_pct,
        "second_dominant": second_dom,
        "second_pct": second_pct,
        "direction": direction,
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def build_distribution_table(results: List[Dict[str, Any]]) -> str:
    """Build the main per-club shape distribution table."""
    headers = ["Club", "Shots"] + SHAPE_NAMES + ["Dominant", "Consist%"]
    rows = []
    for r in results:
        row = [r["club"], str(r["n"])]
        for shape in SHAPE_NAMES:
            count = r["shape_counts"].get(shape, 0)
            if count > 0:
                row.append(f"{count} ({pct_str(count, r['n'])})")
            else:
                row.append("-")
        row.append(r["dominant"])
        row.append(f"{r['consistency']:.1f}%")
        rows.append(row)
    return render_table(headers, rows)


def build_trend_table(trends: List[Dict[str, Any]]) -> str:
    """Build the trend analysis table for clubs with 50+ shots."""
    headers = [
        "Club", "1st Half (n)", "1st Dominant", "1st %",
        "2nd Half (n)", "2nd Dominant", "2nd %", "Status",
    ]
    rows = []
    for t in trends:
        rows.append([
            t["club"],
            str(t["first_n"]),
            t["first_dominant"],
            f"{t['first_pct']:.1f}%",
            str(t["second_n"]),
            t["second_dominant"],
            f"{t['second_pct']:.1f}%",
            t["direction"],
        ])
    return render_table(headers, rows)


def build_summary(results: List[Dict[str, Any]]) -> str:
    """Build the overall summary section."""
    lines = []

    if not results:
        lines.append("  No clubs with enough data for summary.")
        return "\n".join(lines)

    # Most consistent club
    best = max(results, key=lambda r: r["consistency"])
    worst = min(results, key=lambda r: r["consistency"])

    # Overall dominant tendency (across all shots)
    total_counts: Counter = Counter()
    total_shots = 0
    for r in results:
        total_counts.update(r["shape_counts"])
        total_shots += r["n"]

    overall_dom = total_counts.most_common(1)[0] if total_counts else ("Unknown", 0)
    overall_pct = overall_dom[1] / total_shots * 100.0 if total_shots > 0 else 0.0

    lines.append(f"  Total shots classified: {total_shots}")
    lines.append(f"  Clubs analyzed: {len(results)}")
    lines.append("")
    lines.append(f"  Most consistent club:  {best['club']}")
    lines.append(f"    Dominant shape: {best['dominant']} at {best['consistency']:.1f}%")
    lines.append("")
    lines.append(f"  Least consistent club: {worst['club']}")
    lines.append(f"    Dominant shape: {worst['dominant']} at {worst['consistency']:.1f}%")
    lines.append("")
    lines.append(f"  Overall dominant tendency: {overall_dom[0]}")
    lines.append(f"    {overall_dom[1]} of {total_shots} shots ({overall_pct:.1f}%)")

    # Shape breakdown across all clubs
    lines.append("")
    lines.append("  Overall shape breakdown:")
    for shape, count in total_counts.most_common():
        pct = count / total_shots * 100.0 if total_shots > 0 else 0.0
        bar_len = int(pct / 2)  # 50% = 25 chars
        bar = "#" * bar_len
        lines.append(f"    {shape:10s}  {count:5d}  ({pct:5.1f}%)  {bar}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify shot shapes using face_to_path, side_spin, and side_angle."
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

    # Trend analysis for clubs with 50+ shots
    trends: List[Dict[str, Any]] = []
    for club in [r["club"] for r in results]:
        trend = analyze_trend(club, by_club[club])
        if trend is not None:
            trends.append(trend)

    # Build report
    sections: List[str] = []
    sections.append("=" * 78)
    sections.append("SHOT SHAPE CLASSIFICATION REPORT")
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

    # Classification rules
    sections.append("-" * 78)
    sections.append("CLASSIFICATION RULES")
    sections.append("-" * 78)
    sections.append("  Hook:     face_to_path < -4.0  AND  side_spin < -800")
    sections.append("  Slice:    face_to_path >  4.0  AND  side_spin >  800")
    sections.append("  Pull:     side_angle   < -3.0  AND  |face_to_path| < 2.0")
    sections.append("  Push:     side_angle   >  3.0  AND  |face_to_path| < 2.0")
    sections.append("  Straight: |face_to_path| < 1.5 AND  |side_spin| < 300")
    sections.append("  Draw:     face_to_path < -1.5  OR   side_spin < -300")
    sections.append("  Fade:     face_to_path >  1.5  OR   side_spin >  300")
    sections.append("  (Hook/Slice checked before Draw/Fade; Pull/Push before Straight)")
    sections.append("")

    # Per-club distribution
    sections.append("=" * 78)
    sections.append("PER-CLUB SHAPE DISTRIBUTION (sorted by bag order)")
    sections.append("=" * 78)
    sections.append("")
    sections.append(build_distribution_table(results))
    sections.append("")

    # Trend analysis
    if trends:
        sections.append("=" * 78)
        sections.append(f"TREND ANALYSIS (clubs with {TREND_MIN_SHOTS}+ shots: first half vs second half)")
        sections.append("=" * 78)
        sections.append("")
        sections.append(build_trend_table(trends))
        sections.append("")

        changing = [t for t in trends if t["direction"] == "CHANGING"]
        if changing:
            sections.append("  Clubs with shifting shape patterns:")
            for t in changing:
                sections.append(
                    f"    {t['club']}: {t['first_dominant']} ({t['first_pct']:.0f}%) "
                    f"--> {t['second_dominant']} ({t['second_pct']:.0f}%)"
                )
            sections.append("")
        else:
            sections.append("  All clubs with 50+ shots show stable shape patterns.")
            sections.append("")
    else:
        sections.append(f"  No clubs have {TREND_MIN_SHOTS}+ shots for trend analysis.")
        sections.append("")

    # Overall summary
    sections.append("=" * 78)
    sections.append("OVERALL SUMMARY")
    sections.append("=" * 78)
    sections.append("")
    sections.append(build_summary(results))
    sections.append("")

    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
