#!/usr/bin/env python3
"""Compute correlation matrices between numeric shot columns and identify carry drivers per club.

Uses only Python stdlib — no pandas, numpy, or scipy.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path
from typing import Any

EXCLUDED_CLUBS = ("Other", "Putter", "Sim Round")
MIN_CARRY = 10.0
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
BAG_CONFIG_PATH = Path(__file__).resolve().parents[1] / "my_bag.json"

# Numeric columns to attempt loading (order matters for display).
# The carry column name is resolved dynamically.
CANDIDATE_COLUMNS = [
    "carry",  # placeholder — replaced by resolve_carry_column()
    "total",
    "smash",
    "club_speed",
    "ball_speed",
    "launch_angle",
    "back_spin",
    "side_spin",
    "attack_angle",
    "face_angle",
    "club_path",
    "face_to_path",
    "side_distance",
    "descent_angle",
    "apex",
    "flight_time",
    "impact_x",
    "impact_y",
    "strike_distance",
    "dynamic_loft",
]

# Column pairs whose high correlation is trivially obvious and should be
# excluded from the "top correlations" lists (and from the surprises list).
TRIVIAL_PAIRS: set[frozenset[str]] = {
    frozenset({"carry", "total"}),
    frozenset({"carry", "ball_speed"}),
    frozenset({"carry", "club_speed"}),
    frozenset({"ball_speed", "club_speed"}),
    frozenset({"ball_speed", "total"}),
    frozenset({"club_speed", "total"}),
    frozenset({"smash", "ball_speed"}),
    frozenset({"smash", "club_speed"}),
    frozenset({"smash", "carry"}),
    frozenset({"smash", "total"}),
    frozenset({"face_angle", "face_to_path"}),
    frozenset({"club_path", "face_to_path"}),
    frozenset({"apex", "carry"}),
    frozenset({"apex", "total"}),
    frozenset({"flight_time", "carry"}),
    frozenset({"flight_time", "total"}),
    frozenset({"flight_time", "apex"}),
    frozenset({"descent_angle", "apex"}),
    frozenset({"descent_angle", "flight_time"}),
    frozenset({"back_spin", "descent_angle"}),
}

# Friendly display names for columns.
DISPLAY_NAMES: dict[str, str] = {
    "carry": "Carry",
    "total": "Total",
    "smash": "Smash",
    "club_speed": "Club Speed",
    "ball_speed": "Ball Speed",
    "launch_angle": "Launch Angle",
    "back_spin": "Back Spin",
    "side_spin": "Side Spin",
    "attack_angle": "Attack Angle",
    "face_angle": "Face Angle",
    "club_path": "Club Path",
    "face_to_path": "Face-to-Path",
    "side_distance": "Side Distance",
    "descent_angle": "Descent Angle",
    "apex": "Apex",
    "flight_time": "Flight Time",
    "impact_x": "Impact X",
    "impact_y": "Impact Y",
    "strike_distance": "Strike Distance",
    "dynamic_loft": "Dynamic Loft",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def display(col: str) -> str:
    """Return human-friendly column name."""
    return DISPLAY_NAMES.get(col, col)


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def pearson_r(xs: list[float], ys: list[float]) -> float | None:
    """Compute Pearson correlation coefficient from two equal-length lists.

    Returns None if fewer than 3 pairs or zero variance in either series.
    """
    n = len(xs)
    if n < 3 or n != len(ys):
        return None

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    sum_xy = 0.0
    sum_xx = 0.0
    sum_yy = 0.0
    for i in range(n):
        dx = xs[i] - mean_x
        dy = ys[i] - mean_y
        sum_xy += dx * dy
        sum_xx += dx * dx
        sum_yy += dy * dy

    denom = math.sqrt(sum_xx * sum_yy)
    if denom < 1e-12:
        return None
    r = sum_xy / denom
    # Clamp to [-1, 1] in case of floating-point drift
    return max(-1.0, min(1.0, r))


def load_bag_order() -> list[str]:
    """Load bag_order from my_bag.json."""
    try:
        with open(BAG_CONFIG_PATH) as f:
            data = json.load(f)
        return list(data.get("bag_order", []))
    except (OSError, json.JSONDecodeError):
        return []


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


def get_available_columns(conn: sqlite3.Connection, carry_col: str) -> list[str]:
    """Return the subset of CANDIDATE_COLUMNS that actually exist in the table."""
    existing = {str(row["name"]) for row in conn.execute("PRAGMA table_info(shots)").fetchall()}
    available: list[str] = []
    for col in CANDIDATE_COLUMNS:
        actual = carry_col if col == "carry" else col
        if actual in existing:
            available.append(col)
    return available


def load_shot_data(
    conn: sqlite3.Connection,
    carry_col: str,
    columns: list[str],
) -> tuple[list[dict[str, float]], dict[str, int]]:
    """Load all qualifying shots as dicts of {column: float}.

    Returns (rows, club_counts) where club_counts maps club name -> shot count.
    """
    # Build SELECT expression list.
    select_parts: list[str] = ["TRIM(club) AS club"]
    for col in columns:
        db_col = carry_col if col == "carry" else col
        select_parts.append(f"{db_col} AS {col}")

    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT {', '.join(select_parts)}
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND TRIM(club) NOT IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
    """
    params: tuple[Any, ...] = (*EXCLUDED_CLUBS, MIN_CARRY)
    raw_rows = conn.execute(query, params).fetchall()

    rows: list[dict[str, float]] = []
    club_counts: dict[str, int] = {}
    club_rows: dict[str, list[dict[str, float]]] = {}

    for raw in raw_rows:
        club = str(raw["club"]).strip()
        if not club:
            continue

        row: dict[str, float] = {"_club": 0.0}  # placeholder so club name sticks around
        row["_club_name"] = club  # type: ignore[assignment]  # we'll handle this
        valid = True
        for col in columns:
            val = to_float(raw[col])
            if col == "carry" and (val is None or val < MIN_CARRY):
                valid = False
                break
            if val is not None:
                row[col] = val

        if not valid:
            continue

        # Only include rows that have at least carry + one other column.
        numeric_keys = [k for k in row if not k.startswith("_")]
        if len(numeric_keys) < 2:
            continue

        rows.append(row)
        club_counts[club] = club_counts.get(club, 0) + 1
        club_rows.setdefault(club, []).append(row)

    return rows, club_counts, club_rows  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Correlation computation
# ---------------------------------------------------------------------------

def compute_pairwise(
    rows: list[dict[str, float]],
    columns: list[str],
) -> dict[tuple[str, str], tuple[float, int]]:
    """Compute Pearson r for every column pair.

    Returns {(col_a, col_b): (r, n)} where col_a < col_b alphabetically.
    """
    results: dict[tuple[str, str], tuple[float, int]] = {}
    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            col_a, col_b = columns[i], columns[j]
            xs: list[float] = []
            ys: list[float] = []
            for row in rows:
                va = row.get(col_a)
                vb = row.get(col_b)
                if va is not None and vb is not None:
                    xs.append(va)
                    ys.append(vb)
            r = pearson_r(xs, ys)
            if r is not None:
                key = (col_a, col_b) if col_a < col_b else (col_b, col_a)
                results[key] = (r, len(xs))
    return results


def correlations_with_target(
    rows: list[dict[str, float]],
    target: str,
    columns: list[str],
) -> list[tuple[str, float, int]]:
    """Compute correlation of every other column with target.

    Returns sorted list of (column, r, n) by |r| descending.
    """
    results: list[tuple[str, float, int]] = []
    for col in columns:
        if col == target:
            continue
        xs: list[float] = []
        ys: list[float] = []
        for row in rows:
            vt = row.get(target)
            vc = row.get(col)
            if vt is not None and vc is not None:
                xs.append(vt)
                ys.append(vc)
        r = pearson_r(xs, ys)
        if r is not None:
            results.append((col, r, len(xs)))
    results.sort(key=lambda t: abs(t[1]), reverse=True)
    return results


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_r(r: float) -> str:
    """Format correlation coefficient with sign."""
    return f"{r:+.3f}"


def is_trivial(col_a: str, col_b: str) -> bool:
    return frozenset({col_a, col_b}) in TRIVIAL_PAIRS


def build_report(
    all_rows: list[dict[str, float]],
    club_counts: dict[str, int],
    club_rows: dict[str, list[dict[str, float]]],
    columns: list[str],
    top_clubs_count: int,
) -> str:
    lines: list[str] = []
    bag_order = load_bag_order()

    lines.append("=" * 72)
    lines.append("CORRELATION ANALYSIS REPORT")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"Total qualifying shots: {len(all_rows)}")
    lines.append(f"Clubs represented: {len(club_counts)}")
    lines.append(f"Numeric columns analyzed: {len(columns)}")
    lines.append(f"  {', '.join(display(c) for c in columns)}")
    lines.append(f"Filters: exclude {', '.join(EXCLUDED_CLUBS)} | carry >= {MIN_CARRY:.0f}")
    lines.append("")

    # ------------------------------------------------------------------
    # 1. Overall correlation matrix — top positive and negative
    # ------------------------------------------------------------------
    lines.append("-" * 72)
    lines.append("1) OVERALL CORRELATION HIGHLIGHTS")
    lines.append("-" * 72)
    lines.append("")

    pairwise = compute_pairwise(all_rows, columns)

    # Non-trivial pairs sorted by r.
    non_trivial = [
        (pair, r, n)
        for pair, (r, n) in pairwise.items()
        if not is_trivial(pair[0], pair[1])
    ]

    positive = sorted(non_trivial, key=lambda t: t[1], reverse=True)
    negative = sorted(non_trivial, key=lambda t: t[1])

    lines.append("Top 10 strongest POSITIVE correlations (non-trivial):")
    for rank, (pair, r, n) in enumerate(positive[:10], 1):
        lines.append(
            f"  {rank:2d}. {display(pair[0]):16s} <-> {display(pair[1]):16s}  "
            f"r = {format_r(r)}  (n={n})"
        )
    lines.append("")

    lines.append("Top 10 strongest NEGATIVE correlations (non-trivial):")
    for rank, (pair, r, n) in enumerate(negative[:10], 1):
        lines.append(
            f"  {rank:2d}. {display(pair[0]):16s} <-> {display(pair[1]):16s}  "
            f"r = {format_r(r)}  (n={n})"
        )
    lines.append("")

    # ------------------------------------------------------------------
    # 2. Per-club analysis
    # ------------------------------------------------------------------
    lines.append("-" * 72)
    lines.append(f"2) PER-CLUB ANALYSIS (top {top_clubs_count} clubs by shot count, bag order)")
    lines.append("-" * 72)
    lines.append("")

    # Sort clubs: first by shot count to pick top N, then sort those by bag order.
    sorted_by_count = sorted(club_counts.items(), key=lambda t: t[1], reverse=True)
    top_club_names = [name for name, _ in sorted_by_count[:top_clubs_count]]

    # Bag-order sort: clubs in bag_order come first in that order; others at the end.
    bag_index = {name: i for i, name in enumerate(bag_order)}
    top_club_names.sort(key=lambda c: bag_index.get(c, 999))

    for club in top_club_names:
        count = club_counts[club]
        rows_club = club_rows[club]
        lines.append(f"  {club} ({count} shots)")
        lines.append(f"  {'~' * (len(club) + len(str(count)) + 9)}")

        # a) Top 5 factors correlated with carry
        carry_corrs = correlations_with_target(rows_club, "carry", columns)
        lines.append("    Top 5 factors correlated with CARRY:")
        for col, r, n in carry_corrs[:5]:
            lines.append(f"      {display(col):18s}  r = {format_r(r)}  (n={n})")

        # b) Top 3 factors correlated with smash
        smash_corrs = correlations_with_target(rows_club, "smash", columns)
        lines.append("    Top 3 factors correlated with SMASH (efficiency):")
        for col, r, n in smash_corrs[:3]:
            lines.append(f"      {display(col):18s}  r = {format_r(r)}  (n={n})")

        # c) Top 3 factors correlated with face_to_path
        f2p_corrs = correlations_with_target(rows_club, "face_to_path", columns)
        lines.append("    Top 3 factors correlated with FACE-TO-PATH (accuracy):")
        for col, r, n in f2p_corrs[:3]:
            lines.append(f"      {display(col):18s}  r = {format_r(r)}  (n={n})")

        lines.append("")

    # ------------------------------------------------------------------
    # 3. Key insights
    # ------------------------------------------------------------------
    lines.append("-" * 72)
    lines.append("3) KEY INSIGHTS: What matters most for YOUR game")
    lines.append("-" * 72)
    lines.append("")

    # Overall carry drivers (excluding trivially obvious ones).
    carry_corrs_all = correlations_with_target(all_rows, "carry", columns)
    non_trivial_carry = [
        (col, r, n)
        for col, r, n in carry_corrs_all
        if not is_trivial("carry", col)
    ]

    if non_trivial_carry:
        lines.append("  Across all clubs, YOUR carry distance is most influenced by:")
        for rank, (col, r, n) in enumerate(non_trivial_carry[:5], 1):
            direction = "more = longer" if r > 0 else "more = shorter"
            lines.append(
                f"    {rank}. {display(col):18s}  r = {format_r(r)}  ({direction})"
            )
        lines.append("")

    # Smash factor drivers overall.
    smash_corrs_all = correlations_with_target(all_rows, "smash", columns)
    non_trivial_smash = [
        (col, r, n)
        for col, r, n in smash_corrs_all
        if not is_trivial("smash", col)
    ]

    if non_trivial_smash:
        lines.append("  YOUR smash factor (efficiency) is most influenced by:")
        for rank, (col, r, n) in enumerate(non_trivial_smash[:3], 1):
            direction = "more = better" if r > 0 else "more = worse"
            lines.append(
                f"    {rank}. {display(col):18s}  r = {format_r(r)}  ({direction})"
            )
        lines.append("")

    # Face-to-path drivers overall.
    f2p_corrs_all = correlations_with_target(all_rows, "face_to_path", columns)
    non_trivial_f2p = [
        (col, r, n)
        for col, r, n in f2p_corrs_all
        if not is_trivial("face_to_path", col)
    ]

    if non_trivial_f2p:
        lines.append("  YOUR face-to-path (accuracy) is most influenced by:")
        for rank, (col, r, n) in enumerate(non_trivial_f2p[:3], 1):
            lines.append(
                f"    {rank}. {display(col):18s}  r = {format_r(r)}"
            )
        lines.append("")

    # ------------------------------------------------------------------
    # 4. Surprising correlations
    # ------------------------------------------------------------------
    lines.append("-" * 72)
    lines.append("4) SURPRISING CORRELATIONS (|r| > 0.5, non-trivial)")
    lines.append("-" * 72)
    lines.append("")

    # Define what counts as "expected" beyond TRIVIAL_PAIRS.
    # Physics dictates some relationships are well-known.
    EXPECTED_STRONG: set[frozenset[str]] = TRIVIAL_PAIRS | {
        frozenset({"launch_angle", "descent_angle"}),
        frozenset({"launch_angle", "apex"}),
        frozenset({"launch_angle", "back_spin"}),
        frozenset({"attack_angle", "launch_angle"}),
        frozenset({"attack_angle", "dynamic_loft"}),
        frozenset({"back_spin", "apex"}),
        frozenset({"back_spin", "flight_time"}),
        frozenset({"carry", "apex"}),
        frozenset({"carry", "flight_time"}),
        frozenset({"total", "apex"}),
        frozenset({"total", "flight_time"}),
        frozenset({"club_speed", "apex"}),
        frozenset({"club_speed", "flight_time"}),
        frozenset({"ball_speed", "apex"}),
        frozenset({"ball_speed", "flight_time"}),
        frozenset({"descent_angle", "carry"}),
        frozenset({"descent_angle", "total"}),
    }

    surprises = [
        (pair, r, n)
        for pair, (r, n) in pairwise.items()
        if abs(r) > 0.5 and frozenset(pair) not in EXPECTED_STRONG
    ]
    surprises.sort(key=lambda t: abs(t[1]), reverse=True)

    if surprises:
        for pair, r, n in surprises:
            emoji_flag = "(!)" if abs(r) > 0.7 else "   "
            lines.append(
                f"  {emoji_flag} {display(pair[0]):16s} <-> {display(pair[1]):16s}  "
                f"r = {format_r(r)}  (n={n})"
            )
        lines.append("")
        lines.append("  (!) = especially strong unexpected correlation (|r| > 0.7)")
    else:
        lines.append("  No surprising strong correlations found.")

    lines.append("")
    lines.append("=" * 72)
    lines.append("END OF REPORT")
    lines.append("=" * 72)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute correlation matrices between shot metrics and identify carry drivers.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--top-clubs",
        type=int,
        default=5,
        help="Number of top clubs (by shot count) to analyze individually (default: 5).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.top_clubs < 1:
        raise SystemExit("--top-clubs must be >= 1")

    with build_connection(args.db) as conn:
        carry_col = resolve_carry_column(conn)
        columns = get_available_columns(conn, carry_col)
        all_rows, club_counts, club_rows = load_shot_data(conn, carry_col, columns)

    if not all_rows:
        print("No qualifying shots found. Check your database and filters.")
        return 1

    report = build_report(all_rows, club_counts, club_rows, columns, args.top_clubs)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
