#!/usr/bin/env python3
"""Analyze warmup patterns across golf practice sessions from golf_stats.db.

Detects how many shots it takes to reach peak performance in each session
using rolling averages and stabilization detection. Aggregates warmup lengths
across all qualifying sessions and recommends an optimal warmup routine.
"""

from __future__ import annotations

import argparse
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

EXCLUDED_CLUBS = {"Other", "Putter", "Sim Round"}
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
MIN_CARRY = 10.0
MIN_SESSION_SHOTS = 15
ROLLING_WINDOW = 5
STABILIZATION_THRESHOLD = 0.95  # within 5% of session peak
CONSECUTIVE_WINDOWS_REQUIRED = 3


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ShotRow:
    """Single qualifying shot with the metrics we track during warmup."""
    session_id: str
    session_date: str
    shot_number: int  # 1-based position within session
    carry: float
    smash: float | None
    strike_distance: float | None


@dataclass
class SessionWarmup:
    """Warmup analysis result for a single session."""
    session_id: str
    session_date: str
    shot_count: int
    warmup_length: int | None  # shot number where performance stabilized
    peak_carry: float
    peak_smash: float | None
    peak_strike: float | None  # lower is better for strike
    first5_carry: float
    first5_smash: float | None
    first5_strike: float | None
    post_warmup_carry: float | None
    post_warmup_smash: float | None
    post_warmup_strike: float | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze warmup patterns from golf_stats.db. "
            "Detects how many shots it takes to reach peak performance "
            "and recommends an optimal warmup length."
        )
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to SQLite database (default: ./golf_stats.db)",
    )
    parser.add_argument(
        "--min-shots",
        type=int,
        default=MIN_SESSION_SHOTS,
        help=f"Minimum shots per session to analyze (default: {MIN_SESSION_SHOTS})",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=ROLLING_WINDOW,
        help=f"Rolling average window size (default: {ROLLING_WINDOW})",
    )
    return parser.parse_args()


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def safe_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def safe_mean_nonnull(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return safe_mean(clean)


def format_num(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"


def pct_diff(before: float | None, after: float | None) -> str:
    """Return percentage difference string: after vs before."""
    if before is None or after is None or before == 0:
        return "N/A"
    delta = ((after - before) / abs(before)) * 100.0
    return f"{delta:+.1f}%"


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "(no data)"

    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    lines = [sep]
    lines.append(
        "| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |"
    )
    lines.append(sep)
    for row in rows:
        formatted = []
        for idx, cell in enumerate(row):
            # Left-align text columns, right-align numeric
            if idx <= 1:
                formatted.append(cell.ljust(widths[idx]))
            else:
                formatted.append(cell.rjust(widths[idx]))
        lines.append("| " + " | ".join(formatted) + " |")
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


def get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row["name"]) for row in rows}


def carry_column_name(columns: set[str]) -> str:
    if "carry_distance" in columns:
        return "carry_distance"
    if "carry" in columns:
        return "carry"
    raise RuntimeError("shots table is missing both carry_distance and carry columns")


def normalize_session_date(raw: Any) -> str:
    if raw is None:
        return "N/A"
    text = str(raw).strip()
    if not text:
        return "N/A"
    if len(text) >= 10:
        return text[:10]
    return text


def load_sessions(
    conn: sqlite3.Connection,
    min_shots: int,
) -> dict[str, list[ShotRow]]:
    """Load shots grouped by session, filtered and ordered by rowid."""
    columns = get_table_columns(conn, "shots")
    carry_col = carry_column_name(columns)

    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            rowid AS row_order,
            session_id,
            session_date,
            {carry_col} AS carry_value,
            smash,
            strike_distance
        FROM shots
        WHERE session_id IS NOT NULL
          AND club IS NOT NULL
          AND TRIM(club) <> ''
          AND club NOT IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
        ORDER BY session_id ASC, row_order ASC
    """

    params: tuple[Any, ...] = (*tuple(EXCLUDED_CLUBS), MIN_CARRY)
    rows = conn.execute(query, params).fetchall()

    by_session: dict[str, list[ShotRow]] = {}
    shot_counters: dict[str, int] = {}

    for row in rows:
        session_id = str(row["session_id"])
        carry = to_float(row["carry_value"])
        if carry is None:
            continue

        shot_counters[session_id] = shot_counters.get(session_id, 0) + 1
        shot_num = shot_counters[session_id]

        shot = ShotRow(
            session_id=session_id,
            session_date=normalize_session_date(row["session_date"]),
            shot_number=shot_num,
            carry=carry,
            smash=to_float(row["smash"]),
            strike_distance=to_float(row["strike_distance"]),
        )
        by_session.setdefault(session_id, []).append(shot)

    # Filter to sessions with enough shots
    return {
        sid: shots
        for sid, shots in by_session.items()
        if len(shots) >= min_shots
    }


# ---------------------------------------------------------------------------
# Rolling average and stabilization
# ---------------------------------------------------------------------------

def rolling_averages(values: list[float | None], window: int) -> list[float | None]:
    """Compute rolling averages. Returns None for positions without enough data."""
    result: list[float | None] = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(None)
            continue
        window_vals = values[i - window + 1: i + 1]
        clean = [v for v in window_vals if v is not None]
        if not clean:
            result.append(None)
        else:
            result.append(sum(clean) / len(clean))
    return result


def find_stabilization_point(
    rolling_carry: list[float | None],
    rolling_smash: list[float | None],
    rolling_strike: list[float | None],
    threshold: float,
    consecutive: int,
) -> int | None:
    """Find the shot number where performance stabilizes.

    Stabilization = rolling carry avg is within (threshold * peak) for
    `consecutive` windows in a row. Smash and strike are secondary checks
    but carry is the primary signal.
    """
    # Find peak carry rolling average
    carry_values = [v for v in rolling_carry if v is not None]
    if not carry_values:
        return None

    peak_carry = max(carry_values)
    carry_threshold = peak_carry * threshold

    streak = 0
    for i, val in enumerate(rolling_carry):
        if val is None:
            streak = 0
            continue
        if val >= carry_threshold:
            streak += 1
            if streak >= consecutive:
                # The stabilization point is where the streak started
                start_idx = i - consecutive + 1
                # Return 1-based shot number
                return start_idx + 1
        else:
            streak = 0

    return None


def analyze_session(shots: list[ShotRow], window: int) -> SessionWarmup:
    """Analyze warmup pattern for a single session."""
    carries = [s.carry for s in shots]
    smashes = [s.smash for s in shots]
    strikes = [abs(s.strike_distance) if s.strike_distance is not None else None for s in shots]

    roll_carry = rolling_averages(carries, window)
    roll_smash = rolling_averages(smashes, window)
    roll_strike = rolling_averages(strikes, window)

    warmup_shot = find_stabilization_point(
        roll_carry, roll_smash, roll_strike,
        threshold=STABILIZATION_THRESHOLD,
        consecutive=CONSECUTIVE_WINDOWS_REQUIRED,
    )

    # Peak values (from rolling averages to smooth out outliers)
    carry_rolling_clean = [v for v in roll_carry if v is not None]
    smash_rolling_clean = [v for v in roll_smash if v is not None]
    strike_rolling_clean = [v for v in roll_strike if v is not None]

    peak_carry = max(carry_rolling_clean) if carry_rolling_clean else 0.0
    peak_smash = max(smash_rolling_clean) if smash_rolling_clean else None
    # For strike distance, lower is better, so "peak" is min
    peak_strike = min(strike_rolling_clean) if strike_rolling_clean else None

    # First 5 shots performance
    first5 = shots[:5]
    first5_carry = safe_mean([s.carry for s in first5]) or 0.0
    first5_smash = safe_mean_nonnull([s.smash for s in first5])
    first5_strike = safe_mean_nonnull(
        [abs(s.strike_distance) if s.strike_distance is not None else None for s in first5]
    )

    # Post-warmup performance
    if warmup_shot is not None and warmup_shot < len(shots):
        post = shots[warmup_shot:]
        post_carry = safe_mean([s.carry for s in post])
        post_smash = safe_mean_nonnull([s.smash for s in post])
        post_strike = safe_mean_nonnull(
            [abs(s.strike_distance) if s.strike_distance is not None else None for s in post]
        )
    else:
        post_carry = None
        post_smash = None
        post_strike = None

    return SessionWarmup(
        session_id=shots[0].session_id,
        session_date=shots[0].session_date,
        shot_count=len(shots),
        warmup_length=warmup_shot,
        peak_carry=peak_carry,
        peak_smash=peak_smash,
        peak_strike=peak_strike,
        first5_carry=first5_carry,
        first5_smash=first5_smash,
        first5_strike=first5_strike,
        post_warmup_carry=post_carry,
        post_warmup_smash=post_smash,
        post_warmup_strike=post_strike,
    )


# ---------------------------------------------------------------------------
# Aggregation and report
# ---------------------------------------------------------------------------

def warmup_length_bucket(length: int) -> str:
    if length < 5:
        return "<5"
    if length <= 10:
        return "5-10"
    if length <= 15:
        return "10-15"
    return "15+"


def build_report(db_path: Path, min_shots: int, window: int) -> str:
    with build_connection(db_path) as conn:
        sessions_map = load_sessions(conn, min_shots=min_shots)

    if not sessions_map:
        return (
            f"No qualifying sessions found (need >= {min_shots} shots per session, "
            f"carry >= {MIN_CARRY}, excluding {', '.join(sorted(EXCLUDED_CLUBS))})."
        )

    # Analyze each session
    results: list[SessionWarmup] = []
    for _sid, shots in sessions_map.items():
        results.append(analyze_session(shots, window))

    results.sort(key=lambda r: (r.session_date, r.session_id))

    # Sessions with detected warmup
    detected = [r for r in results if r.warmup_length is not None]
    warmup_lengths = [r.warmup_length for r in detected if r.warmup_length is not None]

    lines: list[str] = []
    lines.append("WARMUP PATTERN ANALYSIS")
    lines.append("=" * 60)
    lines.append(f"Database: {db_path}")
    lines.append(
        f"Filters: exclude clubs [{', '.join(sorted(EXCLUDED_CLUBS))}], "
        f"carry >= {MIN_CARRY:.0f}, min {min_shots} shots/session"
    )
    lines.append(f"Rolling window: {window} shots")
    lines.append(
        f"Stabilization: within {(1 - STABILIZATION_THRESHOLD) * 100:.0f}% of peak "
        f"for {CONSECUTIVE_WINDOWS_REQUIRED}+ consecutive windows"
    )
    lines.append(f"Total qualifying sessions: {len(results)}")
    lines.append(f"Sessions with detected warmup: {len(detected)}")
    lines.append("")

    # --- Section 1: Warmup Length Summary ---
    lines.append("WARMUP LENGTH SUMMARY")
    lines.append("-" * 40)

    if warmup_lengths:
        avg_warmup = sum(warmup_lengths) / len(warmup_lengths)
        med_warmup = median(warmup_lengths)
        lines.append(f"  Average warmup length: {avg_warmup:.1f} shots")
        lines.append(f"  Median warmup length:  {med_warmup:.0f} shots")
        lines.append(f"  Shortest warmup:       {min(warmup_lengths)} shots")
        lines.append(f"  Longest warmup:        {max(warmup_lengths)} shots")
        lines.append("")

        # Distribution buckets
        buckets = {"<5": 0, "5-10": 0, "10-15": 0, "15+": 0}
        for length in warmup_lengths:
            bucket = warmup_length_bucket(length)
            buckets[bucket] += 1

        total = len(warmup_lengths)
        lines.append("  Distribution:")
        for bucket_name in ["<5", "5-10", "10-15", "15+"]:
            count = buckets[bucket_name]
            pct = 100.0 * count / total if total > 0 else 0.0
            bar = "#" * int(pct / 2)
            lines.append(f"    {bucket_name:>5} shots: {count:3d} ({pct:5.1f}%) {bar}")

        # Sessions where warmup was NOT detected
        no_warmup = len(results) - len(detected)
        if no_warmup > 0:
            lines.append("")
            lines.append(
                f"  * {no_warmup} session(s) did not show a clear warmup pattern "
                "(performance may have been consistent from the start)."
            )
    else:
        lines.append("  No warmup patterns detected in any session.")
        lines.append("  Performance may be consistent from the first shot.")

    lines.append("")

    # --- Section 2: First 5 vs Post-Warmup Comparison ---
    lines.append("PERFORMANCE COMPARISON: FIRST 5 SHOTS vs POST-WARMUP")
    lines.append("-" * 60)

    comp_sessions = [r for r in detected if r.post_warmup_carry is not None]
    if comp_sessions:
        avg_first5_carry = safe_mean([r.first5_carry for r in comp_sessions]) or 0.0
        avg_post_carry = safe_mean(
            [r.post_warmup_carry for r in comp_sessions if r.post_warmup_carry is not None]
        ) or 0.0

        avg_first5_smash = safe_mean_nonnull([r.first5_smash for r in comp_sessions])
        avg_post_smash = safe_mean_nonnull([r.post_warmup_smash for r in comp_sessions])

        avg_first5_strike = safe_mean_nonnull([r.first5_strike for r in comp_sessions])
        avg_post_strike = safe_mean_nonnull([r.post_warmup_strike for r in comp_sessions])

        comp_headers = ["Metric", "First 5 Avg", "Post-Warmup Avg", "Difference"]
        comp_rows = [
            [
                "Carry (yards)",
                format_num(avg_first5_carry, 1),
                format_num(avg_post_carry, 1),
                pct_diff(avg_first5_carry, avg_post_carry),
            ],
            [
                "Smash Factor",
                format_num(avg_first5_smash, 3),
                format_num(avg_post_smash, 3),
                pct_diff(avg_first5_smash, avg_post_smash),
            ],
            [
                "Strike Distance",
                format_num(avg_first5_strike, 2),
                format_num(avg_post_strike, 2),
                pct_diff(avg_first5_strike, avg_post_strike),
            ],
        ]
        lines.append(render_table(comp_headers, comp_rows))
    else:
        lines.append("  Insufficient data for comparison.")

    lines.append("")

    # --- Section 3: Per-Session Details ---
    lines.append("PER-SESSION WARMUP DETAILS")
    lines.append("-" * 60)

    detail_headers = [
        "Date",
        "Session ID",
        "Shots",
        "Warmup",
        "Peak Carry",
        "1st-5 Carry",
        "Post Carry",
        "Carry Gain",
    ]
    detail_rows: list[list[str]] = []
    for r in results:
        warmup_str = str(r.warmup_length) if r.warmup_length is not None else "---"
        post_carry_str = format_num(r.post_warmup_carry, 1)
        gain = pct_diff(r.first5_carry, r.post_warmup_carry)

        detail_rows.append([
            r.session_date,
            r.session_id[:12],
            str(r.shot_count),
            warmup_str,
            format_num(r.peak_carry, 1),
            format_num(r.first5_carry, 1),
            post_carry_str,
            gain,
        ])

    lines.append(render_table(detail_headers, detail_rows))
    lines.append("")

    # --- Section 4: Recommendation ---
    lines.append("RECOMMENDATION")
    lines.append("-" * 40)
    lines.append(build_recommendation(results, warmup_lengths))

    return "\n".join(lines)


def build_recommendation(
    results: list[SessionWarmup],
    warmup_lengths: list[int],
) -> str:
    if not warmup_lengths:
        return (
            "  No clear warmup pattern was detected across your sessions.\n"
            "  Your performance appears consistent from the first shot, which\n"
            "  is a positive sign. Consider a brief 3-5 shot warmup for feel\n"
            "  and injury prevention."
        )

    avg_warmup = sum(warmup_lengths) / len(warmup_lengths)
    med_warmup = median(warmup_lengths)

    # Check first-5 vs post-warmup improvement
    detected = [r for r in results if r.warmup_length is not None and r.post_warmup_carry is not None]
    if detected:
        improvements = []
        for r in detected:
            if r.post_warmup_carry is not None and r.first5_carry > 0:
                improvements.append(
                    (r.post_warmup_carry - r.first5_carry) / r.first5_carry * 100.0
                )

        avg_improvement = safe_mean(improvements)
    else:
        avg_improvement = None

    # Determine recommendation
    recommended = int(round(med_warmup))
    # Add a small buffer
    recommended_with_buffer = recommended + 2

    text_lines = []
    text_lines.append(
        f"  Based on {len(warmup_lengths)} sessions with detectable warmup patterns:"
    )
    text_lines.append("")
    text_lines.append(
        f"  Your typical warmup is {avg_warmup:.0f} shots "
        f"(median: {med_warmup:.0f} shots)."
    )

    if avg_improvement is not None:
        if avg_improvement >= 0:
            text_lines.append(
                f"  Post-warmup carry is {avg_improvement:+.1f}% higher than your first 5 shots."
            )
        else:
            text_lines.append(
                f"  Post-warmup carry averages {abs(avg_improvement):.1f}% lower than first 5 shots."
            )
            text_lines.append(
                "  (This is normal in mixed-club sessions where you start with longer clubs.)"
            )

    text_lines.append("")
    text_lines.append(
        f"  --> Recommended warmup: {recommended_with_buffer} shots"
    )
    text_lines.append(
        f"      ({recommended} to reach peak + 2 shot buffer)"
    )

    if avg_improvement is not None and 0 <= avg_improvement < 2.0:
        text_lines.append("")
        text_lines.append(
            "  Note: Your warmup improvement is modest (<2%). You may already "
            "be performing well from the start. A short 5-shot warmup should suffice."
        )
    elif avg_improvement is not None and avg_improvement < 0:
        text_lines.append("")
        text_lines.append(
            "  Note: The negative carry delta reflects club transitions within sessions "
            "(e.g., starting with Driver then moving to irons), not a true warmup issue. "
            "Focus on the stabilization point for your warmup length."
        )
    elif recommended_with_buffer > 15:
        text_lines.append("")
        text_lines.append(
            "  Note: Your warmup is on the longer side. Consider starting with"
            " short irons or wedges to speed up your warmup phase."
        )

    return "\n".join(text_lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    try:
        report = build_report(
            db_path=args.db,
            min_shots=args.min_shots,
            window=args.window,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
    except sqlite3.Error as exc:
        print(f"Database error: {exc}")
        return 1

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
