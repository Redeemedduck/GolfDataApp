#!/usr/bin/env python3
"""Identify data patterns that suggest club fitting issues from golf_stats.db."""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

BAG_JSON_PATH = Path(__file__).resolve().parents[1] / "my_bag.json"
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "golf_stats.db"
EXCLUDED_CLUBS = ("Other", "Putter", "Sim Round")
MIN_CARRY = 10.0

# ---------- Reference windows for spin / launch by club type ----------
# Format: (min_spin, max_spin, min_launch, max_launch)
# These are general tour-average windows; not exact for every player.

REFERENCE_WINDOWS: Dict[str, tuple] = {
    "Driver":          (2000, 3000, 10.0, 15.0),
    "3 Wood (Cobra)":  (3000, 4500, 10.0, 14.0),
    "3 Wood (TM)":     (3000, 4500, 10.0, 14.0),
    "7 Wood":          (4000, 5500, 13.0, 18.0),
    "3 Iron":          (3500, 5000, 12.0, 17.0),
    "4 Iron":          (4000, 5500, 13.0, 18.0),
    "5 Iron":          (4500, 6000, 14.0, 19.0),
    "6 Iron":          (5000, 6500, 16.0, 21.0),
    "7 Iron":          (5500, 7500, 17.0, 23.0),
    "8 Iron":          (6500, 8500, 19.0, 26.0),
    "9 Iron":          (7500, 9500, 22.0, 30.0),
    "PW":              (8500, 10500, 24.0, 33.0),
    "GW":              (9000, 11000, 26.0, 35.0),
    "SW":              (9500, 11500, 28.0, 37.0),
    "LW":              (10000, 12500, 30.0, 40.0),
}

# Thresholds
FACE_BIAS_THRESHOLD = 1.5       # degrees — possible lie angle issue
SMASH_GAP_THRESHOLD = 0.05      # below target — possible shaft/head issue
SPIN_MARGIN_PCT = 0.15           # 15% outside window
LAUNCH_MARGIN = 2.0              # degrees outside window
SIDE_SPIN_THRESHOLD = 200.0      # rpm consistent bias
IMPACT_X_THRESHOLD = 5.0         # mm heel/toe bias
IMPACT_Y_THRESHOLD = 5.0         # mm high/low bias
CLUB_SPEED_CV_THRESHOLD = 3.0    # percent — control issues


# ---------- Data classes ----------

@dataclass
class FittingFlag:
    flag_type: str          # LIE_ANGLE, SHAFT_FLEX, LOFT_GAP, CLUB_LENGTH, SHAFT_WEIGHT
    severity: int           # 1 = minor, 2 = moderate, 3 = significant
    evidence: str           # data-based explanation
    recommendation: str     # specific adjustment suggestion


@dataclass
class ClubMetrics:
    club: str
    shot_count: int
    avg_face_angle: Optional[float] = None
    avg_smash: Optional[float] = None
    smash_target: Optional[float] = None
    avg_back_spin: Optional[float] = None
    avg_launch_angle: Optional[float] = None
    avg_side_spin: Optional[float] = None
    avg_impact_x: Optional[float] = None
    avg_impact_y: Optional[float] = None
    avg_club_speed: Optional[float] = None
    cv_club_speed: Optional[float] = None
    stdev_carry: Optional[float] = None
    avg_carry: Optional[float] = None
    flags: List[FittingFlag] = field(default_factory=list)


# ---------- Helpers ----------

def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (TypeError, ValueError):
        return None


def safe_fmt(value: Optional[float], digits: int = 1) -> str:
    if value is None:
        return "-"
    return f"{value:.{digits}f}"


def load_bag_config() -> Dict:
    with open(BAG_JSON_PATH, "r") as f:
        return json.load(f)


def get_bag_order_list(bag: Dict) -> List[str]:
    return bag.get("bag_order", [])


def get_smash_targets(bag: Dict) -> Dict[str, float]:
    return dict(bag.get("smash_targets", {}))


def club_sort_key(club: str, bag_order: List[str]) -> int:
    try:
        return bag_order.index(club)
    except ValueError:
        return len(bag_order)


def mean_of(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def stdev_of(values: List[float]) -> Optional[float]:
    if len(values) < 2:
        return None
    avg = sum(values) / len(values)
    variance = sum((v - avg) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def cv_of(values: List[float]) -> Optional[float]:
    """Coefficient of variation as a percentage."""
    avg = mean_of(values)
    sd = stdev_of(values)
    if avg is None or sd is None or avg == 0:
        return None
    return (sd / avg) * 100.0


# ---------- Database ----------

def build_connection(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA query_only = ON")
    return conn


def detect_carry_column(conn: sqlite3.Connection) -> str:
    cursor = conn.execute("PRAGMA table_info(shots)")
    columns = {str(row[1]) for row in cursor.fetchall()}
    if "carry_distance" in columns:
        return "carry_distance"
    if "carry" in columns:
        return "carry"
    raise RuntimeError("shots table must contain a carry_distance or carry column")


def fetch_club_data(
    conn: sqlite3.Connection,
    carry_col: str,
    min_shots: int,
) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch per-shot data grouped by club."""
    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            TRIM(club) AS club,
            {carry_col} AS carry,
            face_angle,
            smash,
            back_spin,
            launch_angle,
            side_spin,
            impact_x,
            impact_y,
            club_speed
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND TRIM(club) NOT IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
        ORDER BY club
    """
    rows = conn.execute(query, (*EXCLUDED_CLUBS, MIN_CARRY)).fetchall()

    clubs: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        club_name = str(row[0]).strip()
        if not club_name:
            continue
        shot = {
            "carry": safe_float(row[1]),
            "face_angle": safe_float(row[2]),
            "smash": safe_float(row[3]),
            "back_spin": safe_float(row[4]),
            "launch_angle": safe_float(row[5]),
            "side_spin": safe_float(row[6]),
            "impact_x": safe_float(row[7]),
            "impact_y": safe_float(row[8]),
            "club_speed": safe_float(row[9]),
        }
        if club_name not in clubs:
            clubs[club_name] = []
        clubs[club_name].append(shot)

    # Filter by min shots
    return {c: shots for c, shots in clubs.items() if len(shots) >= min_shots}


# ---------- Analysis ----------

def compute_metrics(
    club: str,
    shots: List[Dict[str, Any]],
    smash_targets: Dict[str, float],
) -> ClubMetrics:
    """Compute aggregate metrics for a single club."""
    carries = [s["carry"] for s in shots if s["carry"] is not None]
    face_angles = [s["face_angle"] for s in shots if s["face_angle"] is not None]
    smash_values = [s["smash"] for s in shots if s["smash"] is not None]
    back_spins = [s["back_spin"] for s in shots if s["back_spin"] is not None]
    launch_angles = [s["launch_angle"] for s in shots if s["launch_angle"] is not None]
    side_spins = [s["side_spin"] for s in shots if s["side_spin"] is not None]
    impact_xs = [s["impact_x"] for s in shots if s["impact_x"] is not None]
    impact_ys = [s["impact_y"] for s in shots if s["impact_y"] is not None]
    club_speeds = [s["club_speed"] for s in shots if s["club_speed"] is not None]

    return ClubMetrics(
        club=club,
        shot_count=len(shots),
        avg_face_angle=mean_of(face_angles),
        avg_smash=mean_of(smash_values),
        smash_target=smash_targets.get(club),
        avg_back_spin=mean_of(back_spins),
        avg_launch_angle=mean_of(launch_angles),
        avg_side_spin=mean_of(side_spins),
        avg_impact_x=mean_of(impact_xs),
        avg_impact_y=mean_of(impact_ys),
        avg_club_speed=mean_of(club_speeds),
        cv_club_speed=cv_of(club_speeds),
        stdev_carry=stdev_of(carries),
        avg_carry=mean_of(carries),
    )


def detect_flags(m: ClubMetrics) -> List[FittingFlag]:
    """Analyze metrics and return fitting indicator flags."""
    flags: List[FittingFlag] = []

    # ---- a) Face angle bias (lie angle indicator) ----
    face_biased = (
        m.avg_face_angle is not None
        and abs(m.avg_face_angle) > FACE_BIAS_THRESHOLD
    )
    side_biased = (
        m.avg_side_spin is not None
        and abs(m.avg_side_spin) > SIDE_SPIN_THRESHOLD
    )

    # LIE_ANGLE: face bias + side miss in same direction
    if face_biased and side_biased:
        face_dir = "open" if m.avg_face_angle > 0 else "closed"
        side_dir = "right" if m.avg_side_spin > 0 else "left"
        same_direction = (
            (m.avg_face_angle > 0 and m.avg_side_spin > 0)
            or (m.avg_face_angle < 0 and m.avg_side_spin < 0)
        )
        if same_direction:
            severity = 3 if abs(m.avg_face_angle) > 3.0 else 2
            flags.append(FittingFlag(
                flag_type="LIE_ANGLE",
                severity=severity,
                evidence=(
                    f"Avg face angle {m.avg_face_angle:+.1f} deg ({face_dir}) with "
                    f"avg side spin {m.avg_side_spin:+.0f} rpm ({side_dir})"
                ),
                recommendation=(
                    f"Consider {'flattening' if m.avg_face_angle > 0 else 'upright adjustment to'} "
                    f"lie angle for {m.club} based on consistent {face_dir} face and {side_dir} miss pattern"
                ),
            ))
    elif face_biased:
        # Weaker signal: face bias alone
        face_dir = "open" if m.avg_face_angle > 0 else "closed"
        flags.append(FittingFlag(
            flag_type="LIE_ANGLE",
            severity=1,
            evidence=f"Avg face angle {m.avg_face_angle:+.1f} deg ({face_dir}) exceeds {FACE_BIAS_THRESHOLD} deg threshold",
            recommendation=(
                f"Consider lie angle check for {m.club} -- consistent {face_dir} face "
                f"may indicate {'too upright' if m.avg_face_angle > 0 else 'too flat'} lie"
            ),
        ))

    # ---- b) Smash factor gap (shaft/head issue) ----
    if m.avg_smash is not None and m.smash_target is not None:
        smash_gap = m.smash_target - m.avg_smash
        if smash_gap > SMASH_GAP_THRESHOLD:
            # SHAFT_FLEX: smash below target + high spin + inconsistent carry
            high_spin = False
            ref = REFERENCE_WINDOWS.get(m.club)
            if ref is not None and m.avg_back_spin is not None:
                high_spin = m.avg_back_spin > ref[1]

            carry_inconsistent = (
                m.stdev_carry is not None
                and m.avg_carry is not None
                and m.avg_carry > 0
                and (m.stdev_carry / m.avg_carry * 100) > 8.0
            )

            if high_spin or carry_inconsistent:
                severity = 3 if smash_gap > 0.10 else 2
                evidence_parts = [f"Avg smash {m.avg_smash:.3f} vs target {m.smash_target:.2f} (gap {smash_gap:.3f})"]
                if high_spin:
                    evidence_parts.append(f"high avg spin {m.avg_back_spin:.0f} rpm")
                if carry_inconsistent:
                    carry_cv = m.stdev_carry / m.avg_carry * 100
                    evidence_parts.append(f"carry CV {carry_cv:.1f}%")
                flags.append(FittingFlag(
                    flag_type="SHAFT_FLEX",
                    severity=severity,
                    evidence="; ".join(evidence_parts),
                    recommendation=(
                        f"Consider shaft flex or weight change for {m.club} -- "
                        f"low smash with {'high spin and ' if high_spin else ''}"
                        f"{'inconsistent carry ' if carry_inconsistent else ''}"
                        f"suggests the shaft may be too stiff or too heavy"
                    ),
                ))
            else:
                # Smash gap alone is still notable
                flags.append(FittingFlag(
                    flag_type="SHAFT_FLEX",
                    severity=1,
                    evidence=f"Avg smash {m.avg_smash:.3f} vs target {m.smash_target:.2f} (gap {smash_gap:.3f})",
                    recommendation=(
                        f"Consider head or shaft evaluation for {m.club} -- "
                        f"smash factor {smash_gap:.3f} below target"
                    ),
                ))

    # ---- c) Spin rate check ----
    ref = REFERENCE_WINDOWS.get(m.club)
    if ref is not None and m.avg_back_spin is not None:
        min_spin, max_spin = ref[0], ref[1]
        spin_low = min_spin * (1.0 - SPIN_MARGIN_PCT)
        spin_high = max_spin * (1.0 + SPIN_MARGIN_PCT)

        if m.avg_back_spin > spin_high:
            overshoot = m.avg_back_spin - max_spin
            severity = 3 if overshoot > 1500 else (2 if overshoot > 500 else 1)
            flags.append(FittingFlag(
                flag_type="LOFT_GAP",
                severity=severity,
                evidence=(
                    f"Avg spin {m.avg_back_spin:.0f} rpm exceeds optimal window "
                    f"({min_spin}-{max_spin} rpm) by {overshoot:.0f} rpm"
                ),
                recommendation=(
                    f"Consider reducing loft or moving to a stiffer shaft for {m.club} "
                    f"to bring spin down into the {min_spin}-{max_spin} rpm range"
                ),
            ))
        elif m.avg_back_spin < spin_low:
            undershoot = min_spin - m.avg_back_spin
            severity = 2 if undershoot > 500 else 1
            flags.append(FittingFlag(
                flag_type="LOFT_GAP",
                severity=severity,
                evidence=(
                    f"Avg spin {m.avg_back_spin:.0f} rpm below optimal window "
                    f"({min_spin}-{max_spin} rpm) by {undershoot:.0f} rpm"
                ),
                recommendation=(
                    f"Consider adding loft or softer shaft for {m.club} "
                    f"to bring spin up into the {min_spin}-{max_spin} rpm range"
                ),
            ))

    # ---- d) Launch angle check ----
    if ref is not None and m.avg_launch_angle is not None:
        min_launch, max_launch = ref[2], ref[3]
        if m.avg_launch_angle > max_launch + LAUNCH_MARGIN:
            over = m.avg_launch_angle - max_launch
            # Only flag if not already covered by LOFT_GAP spin flag
            has_loft_flag = any(f.flag_type == "LOFT_GAP" for f in flags)
            if has_loft_flag:
                # Strengthen existing LOFT_GAP flag
                for f in flags:
                    if f.flag_type == "LOFT_GAP":
                        f.evidence += f"; launch angle {m.avg_launch_angle:.1f} deg also high (window {min_launch}-{max_launch})"
                        f.severity = min(3, f.severity + 1)
                        break
            else:
                flags.append(FittingFlag(
                    flag_type="LOFT_GAP",
                    severity=2 if over > 4.0 else 1,
                    evidence=(
                        f"Avg launch {m.avg_launch_angle:.1f} deg exceeds optimal "
                        f"window ({min_launch}-{max_launch} deg) by {over:.1f} deg"
                    ),
                    recommendation=(
                        f"Consider reducing loft for {m.club} -- launch angle "
                        f"{over:.1f} deg above expected range"
                    ),
                ))
        elif m.avg_launch_angle < min_launch - LAUNCH_MARGIN:
            under = min_launch - m.avg_launch_angle
            has_loft_flag = any(f.flag_type == "LOFT_GAP" for f in flags)
            if has_loft_flag:
                for f in flags:
                    if f.flag_type == "LOFT_GAP":
                        f.evidence += f"; launch angle {m.avg_launch_angle:.1f} deg also low (window {min_launch}-{max_launch})"
                        f.severity = min(3, f.severity + 1)
                        break
            else:
                flags.append(FittingFlag(
                    flag_type="LOFT_GAP",
                    severity=2 if under > 4.0 else 1,
                    evidence=(
                        f"Avg launch {m.avg_launch_angle:.1f} deg below optimal "
                        f"window ({min_launch}-{max_launch} deg) by {under:.1f} deg"
                    ),
                    recommendation=(
                        f"Consider adding loft for {m.club} -- launch angle "
                        f"{under:.1f} deg below expected range"
                    ),
                ))

    # ---- e) Side spin pattern ----
    # Already used for LIE_ANGLE above; add standalone flag if side bias without face bias
    if side_biased and not face_biased:
        side_dir = "right" if m.avg_side_spin > 0 else "left"
        flags.append(FittingFlag(
            flag_type="LIE_ANGLE",
            severity=1,
            evidence=f"Avg side spin {m.avg_side_spin:+.0f} rpm -- consistent {side_dir} miss",
            recommendation=(
                f"Consider alignment and lie angle check for {m.club} -- "
                f"consistent {side_dir} side spin may indicate lie or aim issue"
            ),
        ))

    # ---- f) Strike pattern (club length indicator) ----
    if m.avg_impact_x is not None and abs(m.avg_impact_x) > IMPACT_X_THRESHOLD:
        direction = "toe" if m.avg_impact_x > 0 else "heel"
        severity = 3 if abs(m.avg_impact_x) > 10 else 2
        flags.append(FittingFlag(
            flag_type="CLUB_LENGTH",
            severity=severity,
            evidence=f"Avg impact_x {m.avg_impact_x:+.1f} mm -- consistent {direction} strikes",
            recommendation=(
                f"Consider {'shortening' if m.avg_impact_x > 0 else 'lengthening'} "
                f"{m.club} -- consistent {direction} contact (avg {abs(m.avg_impact_x):.1f} mm off-center) "
                f"suggests length or lie adjustment"
            ),
        ))

    if m.avg_impact_y is not None and abs(m.avg_impact_y) > IMPACT_Y_THRESHOLD:
        direction = "high" if m.avg_impact_y > 0 else "low"
        severity = 2 if abs(m.avg_impact_y) > 10 else 1
        flags.append(FittingFlag(
            flag_type="CLUB_LENGTH",
            severity=severity,
            evidence=f"Avg impact_y {m.avg_impact_y:+.1f} mm -- consistent {direction} strikes",
            recommendation=(
                f"Consider {'shorter shaft or more upright lie' if m.avg_impact_y > 0 else 'longer shaft or flatter lie'} "
                f"for {m.club} -- consistent {direction} face contact"
            ),
        ))

    # ---- g) Club speed consistency (shaft weight indicator) ----
    if m.cv_club_speed is not None and m.cv_club_speed > CLUB_SPEED_CV_THRESHOLD:
        severity = 3 if m.cv_club_speed > 5.0 else 2
        flags.append(FittingFlag(
            flag_type="SHAFT_WEIGHT",
            severity=severity,
            evidence=f"Club speed CV {m.cv_club_speed:.1f}% (threshold {CLUB_SPEED_CV_THRESHOLD}%) -- speed varies widely",
            recommendation=(
                f"Consider shaft weight change for {m.club} -- "
                f"high speed variability ({m.cv_club_speed:.1f}% CV) suggests "
                f"the shaft weight or balance may not match your tempo"
            ),
        ))

    return flags


def rank_clubs_by_priority(club_metrics: List[ClubMetrics]) -> List[ClubMetrics]:
    """Sort clubs by number and severity of flags (worst first)."""
    def priority_score(m: ClubMetrics) -> tuple:
        total_severity = sum(f.severity for f in m.flags)
        flag_count = len(m.flags)
        max_sev = max((f.severity for f in m.flags), default=0)
        return (-max_sev, -total_severity, -flag_count)

    flagged = [m for m in club_metrics if m.flags]
    flagged.sort(key=priority_score)
    return flagged


# ---------- Report formatting ----------

def format_table(headers: List[str], rows: List[List[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"

    def fmt_row(row: List[str]) -> str:
        cells = []
        for i, cell in enumerate(row):
            if i == 0:
                cells.append(cell.ljust(widths[i]))
            else:
                cells.append(cell.rjust(widths[i]))
        return "| " + " | ".join(cells) + " |"

    lines = [sep, fmt_row(headers), sep]
    lines.extend(fmt_row(row) for row in rows)
    lines.append(sep)
    return "\n".join(lines)


def severity_label(severity: int) -> str:
    return {1: "Minor", 2: "Moderate", 3: "Significant"}.get(severity, "Unknown")


def build_report(db_path: Path, min_shots: int) -> str:
    bag = load_bag_config()
    bag_order = get_bag_order_list(bag)
    smash_targets = get_smash_targets(bag)

    conn = build_connection(db_path)
    carry_col = detect_carry_column(conn)

    # Total shot count for header
    total_shots = int(conn.execute("SELECT COUNT(*) FROM shots").fetchone()[0])

    club_data = fetch_club_data(conn, carry_col, min_shots)
    conn.close()

    # Compute metrics and flags for each club
    all_metrics: List[ClubMetrics] = []
    for club_name, shots in club_data.items():
        m = compute_metrics(club_name, shots, smash_targets)
        m.flags = detect_flags(m)
        all_metrics.append(m)

    # Sort by bag order
    all_metrics.sort(key=lambda m: club_sort_key(m.club, bag_order))

    included_shots = sum(m.shot_count for m in all_metrics)

    lines: List[str] = []
    lines.append("CLUB FITTING INDICATORS")
    lines.append("=" * 70)
    lines.append(f"Database: {db_path}")
    lines.append(
        f"Filters: exclude {', '.join(EXCLUDED_CLUBS)}; "
        f"{carry_col} >= {MIN_CARRY:.0f}; min {min_shots} shots/club"
    )
    lines.append(f"Shots analyzed: {included_shots} of {total_shots} total")
    lines.append("")

    if not all_metrics:
        lines.append(f"No clubs with at least {min_shots} qualifying shots found.")
        return "\n".join(lines)

    # ---- Section 1: Metrics overview ----
    lines.append("CLUB METRICS OVERVIEW")
    lines.append("-" * 70)

    headers = [
        "Club", "Shots", "Carry", "Face", "Smash", "Target",
        "Spin", "Launch", "SideSp", "Imp X", "Imp Y", "Spd CV%",
    ]
    table_rows: List[List[str]] = []
    for m in all_metrics:
        smash_gap_str = "-"
        if m.avg_smash is not None and m.smash_target is not None:
            smash_gap_str = safe_fmt(m.smash_target, 2)
        table_rows.append([
            m.club,
            str(m.shot_count),
            safe_fmt(m.avg_carry, 1),
            safe_fmt(m.avg_face_angle, 1),
            safe_fmt(m.avg_smash, 3),
            smash_gap_str,
            safe_fmt(m.avg_back_spin, 0),
            safe_fmt(m.avg_launch_angle, 1),
            safe_fmt(m.avg_side_spin, 0),
            safe_fmt(m.avg_impact_x, 1),
            safe_fmt(m.avg_impact_y, 1),
            safe_fmt(m.cv_club_speed, 1),
        ])

    lines.append(format_table(headers, table_rows))
    lines.append("")
    lines.append(
        "Legend: Face=avg face angle (deg), Smash=avg smash factor, "
        "Target=smash target from bag config"
    )
    lines.append(
        "        Spin=avg back spin (rpm), Launch=avg launch angle (deg), "
        "SideSp=avg side spin (rpm)"
    )
    lines.append(
        "        Imp X/Y=avg impact position (mm, +=toe/high), "
        "Spd CV%=club speed coefficient of variation"
    )
    lines.append("")

    # ---- Section 2: Flags per club ----
    lines.append("FITTING FLAGS BY CLUB")
    lines.append("-" * 70)

    any_flags = False
    for m in all_metrics:
        if not m.flags:
            continue
        any_flags = True
        total_sev = sum(f.severity for f in m.flags)
        lines.append(
            f"\n{m.club} ({m.shot_count} shots) -- "
            f"{len(m.flags)} flag(s), total severity {total_sev}"
        )
        for f in sorted(m.flags, key=lambda x: -x.severity):
            lines.append(
                f"  [{f.flag_type}] ({severity_label(f.severity)})"
            )
            lines.append(f"    Evidence: {f.evidence}")
            lines.append(f"    -> {f.recommendation}")

    if not any_flags:
        lines.append("No fitting indicators detected. All clubs look well-fitted to your swing data.")
    lines.append("")

    # ---- Section 3: Priority ranking ----
    ranked = rank_clubs_by_priority(all_metrics)
    if ranked:
        lines.append("FITTING PRIORITY (highest concern first)")
        lines.append("-" * 70)

        priority_headers = ["Rank", "Club", "Flags", "Max Sev", "Total Sev", "Flag Types"]
        priority_rows: List[List[str]] = []
        for i, m in enumerate(ranked, start=1):
            max_sev = max(f.severity for f in m.flags)
            total_sev = sum(f.severity for f in m.flags)
            flag_types = ", ".join(sorted(set(f.flag_type for f in m.flags)))
            priority_rows.append([
                str(i),
                m.club,
                str(len(m.flags)),
                severity_label(max_sev),
                str(total_sev),
                flag_types,
            ])

        lines.append(format_table(priority_headers, priority_rows))
        lines.append("")

    # ---- Section 4: Top recommendations ----
    if ranked:
        lines.append("TOP RECOMMENDATIONS")
        lines.append("-" * 70)

        rec_count = 0
        seen_recs: set = set()
        for m in ranked:
            for f in sorted(m.flags, key=lambda x: -x.severity):
                if f.recommendation not in seen_recs:
                    rec_count += 1
                    lines.append(f"  {rec_count}. {f.recommendation}")
                    lines.append(f"     Evidence: {f.evidence}")
                    seen_recs.add(f.recommendation)
                    if rec_count >= 10:
                        break
            if rec_count >= 10:
                break

        lines.append("")

    # ---- Section 5: Clean clubs ----
    clean = [m for m in all_metrics if not m.flags]
    if clean:
        lines.append("CLUBS WITH NO FITTING CONCERNS")
        lines.append("-" * 70)
        for m in clean:
            lines.append(f"  {m.club} ({m.shot_count} shots) -- no issues detected")
        lines.append("")

    return "\n".join(lines)


# ---------- CLI ----------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Identify data patterns that suggest club fitting issues from golf shot data."
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
        default=20,
        help="Minimum shots per club to include in analysis (default: 20)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(build_report(args.db, args.min_shots))


if __name__ == "__main__":
    main()
