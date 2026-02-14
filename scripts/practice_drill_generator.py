#!/usr/bin/env python3
"""Generate personalized golf practice drills from shot data in SQLite."""

from __future__ import annotations

import argparse
import math
import sqlite3
import statistics
from dataclasses import dataclass
from typing import Any


EXCLUDED_CLUBS = ("Other", "Putter", "Sim Round")


@dataclass
class ClubStats:
    club: str
    shots: int
    face_avg: float
    face_std: float
    path_avg: float
    path_std: float
    ftp_avg: float
    ftp_std: float
    impact_x_abs_avg: float
    impact_y_abs_avg: float
    strike_distance_avg: float
    carry_cv: float


@dataclass
class Weakness:
    kind: str
    severity: float
    summary: str
    evidence: str
    hotspot_club: str | None
    hotspot_value: str | None
    shots_used: int


@dataclass
class Drill:
    severity: float
    weakness_kind: str
    name: str
    fixes: str
    equipment: str
    reps: str
    success_criteria: str
    description: str
    evidence: str
    hotspot: str | None


def safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values: list[float]) -> float:
    if not values:
        return math.nan
    return statistics.fmean(values)


def stdev(values: list[float]) -> float:
    if not values:
        return math.nan
    if len(values) == 1:
        return 0.0
    return statistics.stdev(values)


def cv(values: list[float]) -> float:
    if len(values) < 2:
        return math.nan
    avg = mean(values)
    if avg <= 0:
        return math.nan
    return stdev(values) / avg


def reliability(shots: int, target: int = 120) -> float:
    if shots <= 0:
        return 0.0
    return math.sqrt(min(shots, target) / target)


def severity_score(ratio: float, shots: int) -> float:
    if ratio <= 0:
        return 0.0
    return min(10.0, ratio * 5.0 * reliability(shots))


def format_float(value: float, digits: int = 2) -> str:
    if value is None or math.isnan(value):
        return "N/A"
    return f"{value:.{digits}f}"


def resolve_carry_column(conn: sqlite3.Connection) -> str:
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(shots)")
    columns = {row[1] for row in cursor.fetchall()}
    if "carry_distance" in columns:
        return "carry_distance"
    if "carry" in columns:
        return "carry"
    raise RuntimeError("shots table is missing both carry_distance and carry columns")


def fetch_rows(db_path: str, min_carry: float) -> tuple[list[sqlite3.Row], str]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    carry_col = resolve_carry_column(conn)

    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT
            club,
            {carry_col} AS carry_distance,
            ball_speed,
            smash,
            launch_angle,
            face_angle,
            club_path,
            face_to_path,
            impact_x,
            impact_y,
            strike_distance,
            session_date
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND club NOT IN ({placeholders})
          AND {carry_col} IS NOT NULL
          AND {carry_col} >= ?
    """
    params: tuple[Any, ...] = (*EXCLUDED_CLUBS, min_carry)

    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows, carry_col


def build_club_stats(rows: list[sqlite3.Row], min_shots_per_club: int) -> list[ClubStats]:
    bucket: dict[str, dict[str, list[float]]] = {}
    for row in rows:
        club = str(row["club"]).strip()
        if not club:
            continue
        club_data = bucket.setdefault(
            club,
            {
                "carry": [],
                "face": [],
                "path": [],
                "ftp": [],
                "impact_x_abs": [],
                "impact_y_abs": [],
                "strike_distance": [],
            },
        )
        carry_value = safe_float(row["carry_distance"])
        if carry_value is not None:
            club_data["carry"].append(carry_value)

        face_value = safe_float(row["face_angle"])
        if face_value is not None:
            club_data["face"].append(face_value)

        path_value = safe_float(row["club_path"])
        if path_value is not None:
            club_data["path"].append(path_value)

        ftp_value = safe_float(row["face_to_path"])
        if ftp_value is not None:
            club_data["ftp"].append(ftp_value)

        impact_x_value = safe_float(row["impact_x"])
        if impact_x_value is not None:
            club_data["impact_x_abs"].append(abs(impact_x_value))

        impact_y_value = safe_float(row["impact_y"])
        if impact_y_value is not None:
            club_data["impact_y_abs"].append(abs(impact_y_value))

        strike_value = safe_float(row["strike_distance"])
        if strike_value is not None:
            club_data["strike_distance"].append(strike_value)

    club_stats: list[ClubStats] = []
    for club, values in bucket.items():
        shot_count = len(values["carry"])
        if shot_count < min_shots_per_club:
            continue
        club_stats.append(
            ClubStats(
                club=club,
                shots=shot_count,
                face_avg=mean(values["face"]),
                face_std=stdev(values["face"]),
                path_avg=mean(values["path"]),
                path_std=stdev(values["path"]),
                ftp_avg=mean(values["ftp"]),
                ftp_std=stdev(values["ftp"]),
                impact_x_abs_avg=mean(values["impact_x_abs"]),
                impact_y_abs_avg=mean(values["impact_y_abs"]),
                strike_distance_avg=mean(values["strike_distance"]),
                carry_cv=cv(values["carry"]),
            )
        )

    return sorted(club_stats, key=lambda c: c.shots, reverse=True)


def detect_weaknesses(rows: list[sqlite3.Row], club_stats: list[ClubStats]) -> list[Weakness]:
    face_vals = [v for v in (safe_float(r["face_angle"]) for r in rows) if v is not None]
    path_vals = [v for v in (safe_float(r["club_path"]) for r in rows) if v is not None]
    ftp_vals = [v for v in (safe_float(r["face_to_path"]) for r in rows) if v is not None]
    impact_x_abs_vals = [abs(v) for v in (safe_float(r["impact_x"]) for r in rows) if v is not None]
    impact_y_abs_vals = [abs(v) for v in (safe_float(r["impact_y"]) for r in rows) if v is not None]
    strike_vals = [v for v in (safe_float(r["strike_distance"]) for r in rows) if v is not None]

    weaknesses: list[Weakness] = []

    def max_by(metric: str, transform: callable) -> ClubStats | None:
        candidates = [c for c in club_stats if not math.isnan(getattr(c, metric))]
        if not candidates:
            return None
        return max(candidates, key=transform)

    face_avg = mean(face_vals)
    face_std = stdev(face_vals)
    if not math.isnan(face_avg) and abs(face_avg) >= 1.2:
        hotspot = max_by("face_avg", lambda c: abs(c.face_avg))
        ratio = abs(face_avg) / 1.2
        summary = "Face angle bias (consistently open/closed face at impact)."
        direction = "open" if face_avg > 0 else "closed"
        evidence = f"avg face_angle={face_avg:.2f}° ({direction})"
        weaknesses.append(
            Weakness(
                kind="face_bias",
                severity=severity_score(ratio, len(face_vals)),
                summary=summary,
                evidence=evidence,
                hotspot_club=hotspot.club if hotspot else None,
                hotspot_value=f"{hotspot.face_avg:.2f}°" if hotspot else None,
                shots_used=len(face_vals),
            )
        )

    if not math.isnan(face_std) and face_std >= 3.6:
        hotspot = max_by("face_std", lambda c: c.face_std)
        ratio = face_std / 3.6
        weaknesses.append(
            Weakness(
                kind="face_variability",
                severity=severity_score(ratio, len(face_vals)),
                summary="Face control variability (start-line inconsistency).",
                evidence=f"face_angle std dev={face_std:.2f}°",
                hotspot_club=hotspot.club if hotspot else None,
                hotspot_value=f"{hotspot.face_std:.2f}° std" if hotspot else None,
                shots_used=len(face_vals),
            )
        )

    path_avg = mean(path_vals)
    path_std = stdev(path_vals)
    if not math.isnan(path_avg) and abs(path_avg) >= 1.5:
        hotspot = max_by("path_avg", lambda c: abs(c.path_avg))
        ratio = abs(path_avg) / 1.5
        tendency = "in-to-out" if path_avg > 0 else "out-to-in"
        weaknesses.append(
            Weakness(
                kind="path_bias",
                severity=severity_score(ratio, len(path_vals)),
                summary="Club path bias (directional path tendency).",
                evidence=f"avg club_path={path_avg:.2f}° ({tendency})",
                hotspot_club=hotspot.club if hotspot else None,
                hotspot_value=f"{hotspot.path_avg:.2f}°" if hotspot else None,
                shots_used=len(path_vals),
            )
        )

    if not math.isnan(path_std) and path_std >= 3.2:
        hotspot = max_by("path_std", lambda c: c.path_std)
        ratio = path_std / 3.2
        weaknesses.append(
            Weakness(
                kind="path_variability",
                severity=severity_score(ratio, len(path_vals)),
                summary="Club path variability (delivery pattern not repeatable).",
                evidence=f"club_path std dev={path_std:.2f}°",
                hotspot_club=hotspot.club if hotspot else None,
                hotspot_value=f"{hotspot.path_std:.2f}° std" if hotspot else None,
                shots_used=len(path_vals),
            )
        )

    ftp_avg = mean(ftp_vals)
    ftp_std = stdev(ftp_vals)
    if not math.isnan(ftp_avg) and abs(ftp_avg) >= 1.5:
        hotspot = max_by("ftp_avg", lambda c: abs(c.ftp_avg))
        ratio = abs(ftp_avg) / 1.5
        tendency = "open-to-path / fade bias" if ftp_avg > 0 else "closed-to-path / draw bias"
        weaknesses.append(
            Weakness(
                kind="ftp_bias",
                severity=severity_score(ratio, len(ftp_vals)),
                summary="Face-to-path bias (shape tendency).",
                evidence=f"avg face_to_path={ftp_avg:.2f}° ({tendency})",
                hotspot_club=hotspot.club if hotspot else None,
                hotspot_value=f"{hotspot.ftp_avg:.2f}°" if hotspot else None,
                shots_used=len(ftp_vals),
            )
        )

    if not math.isnan(ftp_std) and ftp_std >= 4.2:
        hotspot = max_by("ftp_std", lambda c: c.ftp_std)
        ratio = ftp_std / 4.2
        weaknesses.append(
            Weakness(
                kind="ftp_variability",
                severity=severity_score(ratio, len(ftp_vals)),
                summary="Face-to-path variability (shot-shape volatility).",
                evidence=f"face_to_path std dev={ftp_std:.2f}°",
                hotspot_club=hotspot.club if hotspot else None,
                hotspot_value=f"{hotspot.ftp_std:.2f}° std" if hotspot else None,
                shots_used=len(ftp_vals),
            )
        )

    impact_x_abs_avg = mean(impact_x_abs_vals)
    impact_y_abs_avg = mean(impact_y_abs_vals)
    strike_avg = mean(strike_vals)

    if not math.isnan(impact_x_abs_avg) and impact_x_abs_avg >= 4.5:
        hotspot = max_by("impact_x_abs_avg", lambda c: c.impact_x_abs_avg)
        ratio = impact_x_abs_avg / 4.5
        weaknesses.append(
            Weakness(
                kind="strike_horizontal",
                severity=severity_score(ratio, len(impact_x_abs_vals)),
                summary="Horizontal strike dispersion (toe/heel contact spread).",
                evidence=f"avg |impact_x|={impact_x_abs_avg:.2f}",
                hotspot_club=hotspot.club if hotspot else None,
                hotspot_value=f"{hotspot.impact_x_abs_avg:.2f}" if hotspot else None,
                shots_used=len(impact_x_abs_vals),
            )
        )

    if not math.isnan(impact_y_abs_avg) and impact_y_abs_avg >= 4.5:
        hotspot = max_by("impact_y_abs_avg", lambda c: c.impact_y_abs_avg)
        ratio = impact_y_abs_avg / 4.5
        weaknesses.append(
            Weakness(
                kind="strike_vertical",
                severity=severity_score(ratio, len(impact_y_abs_vals)),
                summary="Vertical strike dispersion (high/low face contact spread).",
                evidence=f"avg |impact_y|={impact_y_abs_avg:.2f}",
                hotspot_club=hotspot.club if hotspot else None,
                hotspot_value=f"{hotspot.impact_y_abs_avg:.2f}" if hotspot else None,
                shots_used=len(impact_y_abs_vals),
            )
        )

    if not math.isnan(strike_avg) and strike_avg >= 7.5:
        hotspot = max_by("strike_distance_avg", lambda c: c.strike_distance_avg)
        ratio = strike_avg / 7.5
        weaknesses.append(
            Weakness(
                kind="strike_distance",
                severity=severity_score(ratio, len(strike_vals)),
                summary="Overall strike quality is inconsistent (contact far from center).",
                evidence=f"avg strike_distance={strike_avg:.2f}",
                hotspot_club=hotspot.club if hotspot else None,
                hotspot_value=f"{hotspot.strike_distance_avg:.2f}" if hotspot else None,
                shots_used=len(strike_vals),
            )
        )

    valid_cv = [c for c in club_stats if not math.isnan(c.carry_cv)]
    if valid_cv:
        weighted_cv_num = sum(c.carry_cv * c.shots for c in valid_cv)
        weighted_cv_den = sum(c.shots for c in valid_cv)
        weighted_cv = weighted_cv_num / weighted_cv_den if weighted_cv_den else math.nan
        worst_cv = max(valid_cv, key=lambda c: c.carry_cv)
        trigger = (
            (not math.isnan(weighted_cv) and weighted_cv >= 0.20)
            or worst_cv.carry_cv >= 0.28
        )
        if trigger:
            ratio = max(
                (weighted_cv / 0.20) if not math.isnan(weighted_cv) else 0.0,
                worst_cv.carry_cv / 0.28,
            )
            evidence = (
                f"weighted carry CV={weighted_cv:.3f}; "
                f"worst club={worst_cv.club} ({worst_cv.carry_cv:.3f})"
            )
            weaknesses.append(
                Weakness(
                    kind="carry_consistency",
                    severity=severity_score(ratio, weighted_cv_den),
                    summary="Carry consistency issue (distance dispersion too high).",
                    evidence=evidence,
                    hotspot_club=worst_cv.club,
                    hotspot_value=f"CV {worst_cv.carry_cv:.3f}",
                    shots_used=weighted_cv_den,
                )
            )

    return weaknesses


def weakness_to_drill(weakness: Weakness) -> Drill:
    if weakness.kind == "face_bias":
        open_bias = "open" in weakness.evidence
        return Drill(
            severity=weakness.severity,
            weakness_kind=weakness.kind,
            name="Start-Line Gate Face Control",
            fixes="Face angle bias at impact (start-line misses).",
            equipment="2 alignment sticks, 4 tees, mid-iron.",
            reps="4 sets x 10 balls.",
            success_criteria="Session avg face_angle moves inside +/-1.0 deg and 7/10 balls start through gate.",
            description=(
                "Set a tee gate 2 feet in front of the ball just wider than a ball. "
                "Hit controlled shots through the gate, rehearsing a square face feeling."
                if open_bias
                else "Set a tee gate 2 feet in front of the ball just wider than a ball. "
                "Hit controlled shots through the gate with a softer release to avoid closing too early."
            ),
            evidence=weakness.evidence,
            hotspot=(
                f"{weakness.hotspot_club} ({weakness.hotspot_value})"
                if weakness.hotspot_club and weakness.hotspot_value
                else None
            ),
        )

    if weakness.kind == "face_variability":
        return Drill(
            severity=weakness.severity,
            weakness_kind=weakness.kind,
            name="Three-Speed Face Stability Ladder",
            fixes="Inconsistent face delivery shot-to-shot.",
            equipment="Alignment stick, impact tape, short or mid-iron.",
            reps="3 ladders x 9 balls (3 slow, 3 normal, 3 full).",
            success_criteria="Face-angle std dev drops below 3.0 deg for the session segment.",
            description="Alternate swing speeds while keeping the same start line. Reset setup after every 3 balls and keep one face cue constant.",
            evidence=weakness.evidence,
            hotspot=(
                f"{weakness.hotspot_club} ({weakness.hotspot_value})"
                if weakness.hotspot_club and weakness.hotspot_value
                else None
            ),
        )

    if weakness.kind == "path_bias":
        out_to_in = "out-to-in" in weakness.evidence
        return Drill(
            severity=weakness.severity,
            weakness_kind=weakness.kind,
            name="Path Gate Neutralizer",
            fixes="Club-path directional tendency.",
            equipment="2 alignment sticks, headcover, 7-iron.",
            reps="5 sets x 8 balls.",
            success_criteria="Avg club_path moves inside +/-1.0 deg with at least 60% neutral-path shots.",
            description=(
                "Place a headcover just outside the target line behind the ball to block steep out-to-in delivery; swing through an inside gate."
                if out_to_in
                else "Place an inside obstacle to prevent the club getting too far under plane, then send the club through a neutral gate."
            ),
            evidence=weakness.evidence,
            hotspot=(
                f"{weakness.hotspot_club} ({weakness.hotspot_value})"
                if weakness.hotspot_club and weakness.hotspot_value
                else None
            ),
        )

    if weakness.kind == "path_variability":
        return Drill(
            severity=weakness.severity,
            weakness_kind=weakness.kind,
            name="Split-Stance Path Calibration",
            fixes="Path control variability.",
            equipment="Alignment stick, 8-iron.",
            reps="4 sets x 9 balls.",
            success_criteria="Club-path std dev improves by at least 15% vs current baseline.",
            description="Hit 3 balls with lead foot back, 3 neutral, 3 trail foot back. Keep chest rotation tempo constant and track path windows.",
            evidence=weakness.evidence,
            hotspot=(
                f"{weakness.hotspot_club} ({weakness.hotspot_value})"
                if weakness.hotspot_club and weakness.hotspot_value
                else None
            ),
        )

    if weakness.kind == "ftp_bias":
        fade_bias = "open-to-path" in weakness.evidence
        return Drill(
            severity=weakness.severity,
            weakness_kind=weakness.kind,
            name="Face-to-Path Matchup Drill",
            fixes="Shot-shape bias from face/path mismatch.",
            equipment="Alignment sticks, face spray, preferred scoring iron.",
            reps="4 blocks x 12 balls.",
            success_criteria="Avg face_to_path moves into -1.0 to +1.0 deg window.",
            description=(
                "Build neutral setup, then rehearse a slightly earlier release so face and path arrive closer together."
                if fade_bias
                else "Build neutral setup, then rehearse a held-off release so face does not outrun path."
            ),
            evidence=weakness.evidence,
            hotspot=(
                f"{weakness.hotspot_club} ({weakness.hotspot_value})"
                if weakness.hotspot_club and weakness.hotspot_value
                else None
            ),
        )

    if weakness.kind == "ftp_variability":
        return Drill(
            severity=weakness.severity,
            weakness_kind=weakness.kind,
            name="Nine-Window Shape Control Matrix",
            fixes="Unstable curve pattern (face-to-path volatility).",
            equipment="Range targets, alignment stick, launch monitor.",
            reps="9 windows x 3 balls each.",
            success_criteria="At least 6/9 windows completed with face_to_path inside target window.",
            description="Cycle through straight, baby fade, baby draw windows at three trajectories while keeping setup and tempo repeatable.",
            evidence=weakness.evidence,
            hotspot=(
                f"{weakness.hotspot_club} ({weakness.hotspot_value})"
                if weakness.hotspot_club and weakness.hotspot_value
                else None
            ),
        )

    if weakness.kind == "strike_horizontal":
        return Drill(
            severity=weakness.severity,
            weakness_kind=weakness.kind,
            name="Toe-Heel Strike Ladder",
            fixes="Horizontal face-contact spread.",
            equipment="Face spray or tape, 2 tees, mid-iron.",
            reps="5 rounds x 6 balls.",
            success_criteria=">=70% center-third strikes on impact map.",
            description="Mark strike location every ball and alternate center-focus and slight toe-focus reps to learn centered delivery.",
            evidence=weakness.evidence,
            hotspot=(
                f"{weakness.hotspot_club} ({weakness.hotspot_value})"
                if weakness.hotspot_club and weakness.hotspot_value
                else None
            ),
        )

    if weakness.kind == "strike_vertical":
        return Drill(
            severity=weakness.severity,
            weakness_kind=weakness.kind,
            name="Low-Point Towel Strike Drill",
            fixes="Vertical strike spread and low-point control.",
            equipment="Small towel, face spray, short/mid iron.",
            reps="4 sets x 10 balls.",
            success_criteria="High/low strike misses reduced by at least 30% in the session.",
            description="Place towel 3-4 inches behind ball and strike without touching towel while centering contact vertically.",
            evidence=weakness.evidence,
            hotspot=(
                f"{weakness.hotspot_club} ({weakness.hotspot_value})"
                if weakness.hotspot_club and weakness.hotspot_value
                else None
            ),
        )

    if weakness.kind == "strike_distance":
        return Drill(
            severity=weakness.severity,
            weakness_kind=weakness.kind,
            name="Center-Contact 3x3 Matrix",
            fixes="Overall strike quality and centeredness.",
            equipment="Impact tape/spray, 9-box face chart.",
            reps="27 balls (3 per box target).",
            success_criteria="Average strike_distance improves by at least 20% from baseline.",
            description="Track contact location on a 3x3 face grid; bias effort toward center box while maintaining stock tempo.",
            evidence=weakness.evidence,
            hotspot=(
                f"{weakness.hotspot_club} ({weakness.hotspot_value})"
                if weakness.hotspot_club and weakness.hotspot_value
                else None
            ),
        )

    if weakness.kind == "carry_consistency":
        return Drill(
            severity=weakness.severity,
            weakness_kind=weakness.kind,
            name="Carry Ladder Combine",
            fixes="Carry-distance variability and gapping inconsistency.",
            equipment="Launch monitor, alignment stick, 2 target distances.",
            reps="6 rounds x 5 balls (30 total).",
            success_criteria="Carry CV for focus club drops under 0.20 over next 2 sessions.",
            description="Alternate two carry targets with the same club, committing to one stock shape and tempo; log carry each rep and reset after misses.",
            evidence=weakness.evidence,
            hotspot=(
                f"{weakness.hotspot_club} ({weakness.hotspot_value})"
                if weakness.hotspot_club and weakness.hotspot_value
                else None
            ),
        )

    return Drill(
        severity=weakness.severity,
        weakness_kind=weakness.kind,
        name="Baseline Recalibration Block",
        fixes=weakness.summary,
        equipment="Launch monitor and one stock club.",
        reps="3 sets x 12 balls.",
        success_criteria="Metric improves relative to baseline.",
        description="Run slow-to-full progression and lock one setup variable at a time.",
        evidence=weakness.evidence,
        hotspot=weakness.hotspot_club,
    )


def render_report(
    db_path: str,
    carry_column: str,
    rows: list[sqlite3.Row],
    club_stats: list[ClubStats],
    drills: list[Drill],
) -> str:
    session_dates = [str(r["session_date"]) for r in rows if r["session_date"]]
    earliest = min(session_dates) if session_dates else "N/A"
    latest = max(session_dates) if session_dates else "N/A"

    lines: list[str] = []
    lines.append("PERSONALIZED PRACTICE DRILL PRESCRIPTIONS")
    lines.append(f"Database: {db_path}")
    lines.append(f"Carry source column: {carry_column}")
    lines.append(f"Shots analyzed: {len(rows)}")
    lines.append(f"Clubs analyzed (min sample met): {len(club_stats)}")
    lines.append(f"Session range: {earliest} -> {latest}")
    lines.append("")

    if not drills:
        lines.append("No major weaknesses crossed the alert thresholds in the filtered data.")
        lines.append("Recommendation: run a maintenance block with center-contact and carry-ladder drills.")
        return "\n".join(lines)

    lines.append(f"Top drills by severity (showing {len(drills)}):")
    for idx, drill in enumerate(drills, start=1):
        lines.append("")
        lines.append(f"{idx}. {drill.name}  [Severity {drill.severity:.1f}/10]")
        lines.append(f"   Fixes: {drill.fixes}")
        lines.append(f"   Equipment: {drill.equipment}")
        lines.append(f"   Rep Count: {drill.reps}")
        lines.append(f"   Success Criteria: {drill.success_criteria}")
        lines.append(f"   Description: {drill.description}")
        lines.append(f"   Data Signal: {drill.evidence}")
        if drill.hotspot:
            lines.append(f"   Priority Club: {drill.hotspot}")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="golf_stats.db", help="Path to SQLite DB.")
    parser.add_argument(
        "--min-carry",
        type=float,
        default=10.0,
        help="Minimum carry distance to include shots (default: 10).",
    )
    parser.add_argument(
        "--min-shots-per-club",
        type=int,
        default=20,
        help="Minimum shots per club for club-level hotspot analysis (default: 20).",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=7,
        help="Number of highest-severity drills to print (default: 7; minimum 5 when available).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, carry_column = fetch_rows(args.db_path, args.min_carry)
    if not rows:
        print("No shots available after filters (club exclusions + minimum carry).")
        return

    club_stats = build_club_stats(rows, args.min_shots_per_club)
    weaknesses = detect_weaknesses(rows, club_stats)
    drills = sorted((weakness_to_drill(w) for w in weaknesses), key=lambda d: d.severity, reverse=True)

    max_drills = max(5, args.top_n)
    drills = drills[: max_drills if len(drills) >= max_drills else len(drills)]
    report = render_report(args.db_path, carry_column, rows, club_stats, drills)
    print(report)


if __name__ == "__main__":
    main()
