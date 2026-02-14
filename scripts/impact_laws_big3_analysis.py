#!/usr/bin/env python3
"""Impact Laws (Big 3) analysis for golf_stats.db shots table."""

from __future__ import annotations

import argparse
import math
import sqlite3
from typing import Any


EXCLUDED_CLUBS = ("Sim Round", "Other", "Putter")


def safe_round(value: Any, digits: int = 2) -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "-"
    return f"{value:.{digits}f}"


def render_table(title: str, headers: list[str], rows: list[list[Any]]) -> str:
    str_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in str_rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def fmt_row(row: list[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    separator = "-+-".join("-" * w for w in widths)
    lines = [f"\n{title}", fmt_row(headers), separator]
    lines.extend(fmt_row(row) for row in str_rows)
    return "\n".join(lines)


def fetch_all_dicts(cursor: sqlite3.Cursor, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cursor.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Impact Laws (Big 3) from golf_stats.db")
    parser.add_argument("--db", default="golf_stats.db", help="Path to SQLite DB (default: golf_stats.db)")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)

    totals_query = f"""
    WITH filtered AS (
        SELECT *
        FROM shots
        WHERE club NOT IN ({placeholders})
          AND carry >= 10
    )
    SELECT
        COUNT(*) AS kept_shots,
        COUNT(DISTINCT club) AS clubs_analyzed
    FROM filtered;
    """

    overall_counts_query = f"""
    SELECT
        COUNT(*) AS total_shots,
        SUM(CASE WHEN club IN ({placeholders}) THEN 1 ELSE 0 END) AS excluded_club_shots,
        SUM(CASE WHEN carry < 10 THEN 1 ELSE 0 END) AS mishits_lt_10
    FROM shots;
    """

    face_angle_query = f"""
    WITH filtered AS (
        SELECT club, face_angle
        FROM shots
        WHERE club NOT IN ({placeholders})
          AND carry >= 10
    )
    SELECT
        club,
        COUNT(*) AS shots,
        COUNT(face_angle) AS n_face,
        AVG(face_angle) AS face_avg,
        SQRT(MAX(AVG(face_angle * face_angle) - AVG(face_angle) * AVG(face_angle), 0)) AS face_std,
        100.0 * SUM(CASE WHEN face_angle > 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(face_angle), 0) AS pct_open,
        100.0 * SUM(CASE WHEN face_angle < -1 THEN 1 ELSE 0 END) / NULLIF(COUNT(face_angle), 0) AS pct_closed,
        100.0 * SUM(CASE WHEN ABS(face_angle) <= 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(face_angle), 0) AS pct_square
    FROM filtered
    GROUP BY club
    ORDER BY shots DESC, club;
    """

    club_path_query = f"""
    WITH filtered AS (
        SELECT club, club_path
        FROM shots
        WHERE club NOT IN ({placeholders})
          AND carry >= 10
    )
    SELECT
        club,
        COUNT(*) AS shots,
        COUNT(club_path) AS n_path,
        AVG(club_path) AS path_avg,
        SQRT(MAX(AVG(club_path * club_path) - AVG(club_path) * AVG(club_path), 0)) AS path_std,
        100.0 * SUM(CASE WHEN club_path > 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(club_path), 0) AS pct_in_to_out,
        100.0 * SUM(CASE WHEN club_path < -1 THEN 1 ELSE 0 END) / NULLIF(COUNT(club_path), 0) AS pct_out_to_in,
        100.0 * SUM(CASE WHEN ABS(club_path) <= 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(club_path), 0) AS pct_neutral
    FROM filtered
    GROUP BY club
    ORDER BY shots DESC, club;
    """

    face_to_path_query = f"""
    WITH filtered AS (
        SELECT club, face_to_path
        FROM shots
        WHERE club NOT IN ({placeholders})
          AND carry >= 10
    )
    SELECT
        club,
        COUNT(*) AS shots,
        COUNT(face_to_path) AS n_ftp,
        AVG(face_to_path) AS ftp_avg,
        100.0 * SUM(CASE WHEN face_to_path < -2 THEN 1 ELSE 0 END) / NULLIF(COUNT(face_to_path), 0) AS pct_draw,
        100.0 * SUM(CASE WHEN face_to_path > 2 THEN 1 ELSE 0 END) / NULLIF(COUNT(face_to_path), 0) AS pct_fade,
        100.0 * SUM(CASE WHEN face_to_path >= -2 AND face_to_path <= 2 THEN 1 ELSE 0 END) / NULLIF(COUNT(face_to_path), 0) AS pct_straight
    FROM filtered
    GROUP BY club
    ORDER BY shots DESC, club;
    """

    strike_quality_query = f"""
    WITH filtered AS (
        SELECT club, impact_x, impact_y, strike_distance
        FROM shots
        WHERE club NOT IN ({placeholders})
          AND carry >= 10
    )
    SELECT
        club,
        COUNT(*) AS shots,
        AVG(impact_x) AS impact_x_avg,
        AVG(impact_y) AS impact_y_avg,
        AVG(strike_distance) AS strike_distance_avg
    FROM filtered
    GROUP BY club
    ORDER BY shots DESC, club;
    """

    top_clubs_query = f"""
    SELECT club, COUNT(*) AS shots
    FROM shots
    WHERE club NOT IN ({placeholders})
      AND carry >= 10
    GROUP BY club
    ORDER BY shots DESC, club
    LIMIT 5;
    """

    params = EXCLUDED_CLUBS

    overall_counts = fetch_all_dicts(cur, overall_counts_query, params)[0]
    totals = fetch_all_dicts(cur, totals_query, params)[0]
    face_rows = fetch_all_dicts(cur, face_angle_query, params)
    path_rows = fetch_all_dicts(cur, club_path_query, params)
    ftp_rows = fetch_all_dicts(cur, face_to_path_query, params)
    strike_rows = fetch_all_dicts(cur, strike_quality_query, params)
    top_clubs = fetch_all_dicts(cur, top_clubs_query, params)

    conn.close()

    face_by_club = {row["club"]: row for row in face_rows}
    path_by_club = {row["club"]: row for row in path_rows}
    ftp_by_club = {row["club"]: row for row in ftp_rows}
    strike_by_club = {row["club"]: row for row in strike_rows}

    print("IMPACT LAWS (BIG 3) ANALYSIS")
    print(f"DB: {args.db}")
    print(
        "Filters: exclude clubs {clubs}; carry >= 10\n"
        "Shots total={total}, excluded clubs={excluded}, carry<10={mishits}, analyzed={kept}, clubs analyzed={club_count}".format(
            clubs=", ".join(EXCLUDED_CLUBS),
            total=overall_counts["total_shots"],
            excluded=overall_counts["excluded_club_shots"],
            mishits=overall_counts["mishits_lt_10"],
            kept=totals["kept_shots"],
            club_count=totals["clubs_analyzed"],
        )
    )

    face_table = []
    for row in face_rows:
        face_table.append(
            [
                row["club"],
                row["shots"],
                row["n_face"],
                safe_round(row["face_avg"]),
                safe_round(row["face_std"]),
                safe_round(row["pct_open"]),
                safe_round(row["pct_closed"]),
                safe_round(row["pct_square"]),
            ]
        )

    path_table = []
    for row in path_rows:
        path_table.append(
            [
                row["club"],
                row["shots"],
                row["n_path"],
                safe_round(row["path_avg"]),
                safe_round(row["path_std"]),
                safe_round(row["pct_in_to_out"]),
                safe_round(row["pct_out_to_in"]),
                safe_round(row["pct_neutral"]),
            ]
        )

    ftp_table = []
    for row in ftp_rows:
        ftp_table.append(
            [
                row["club"],
                row["shots"],
                row["n_ftp"],
                safe_round(row["ftp_avg"]),
                safe_round(row["pct_draw"]),
                safe_round(row["pct_fade"]),
                safe_round(row["pct_straight"]),
            ]
        )

    strike_table = []
    for row in strike_rows:
        strike_table.append(
            [
                row["club"],
                row["shots"],
                safe_round(row["impact_x_avg"]),
                safe_round(row["impact_y_avg"]),
                safe_round(row["strike_distance_avg"]),
            ]
        )

    print(
        render_table(
            "1) FACE ANGLE",
            ["Club", "Shots", "N Face", "Avg", "Std Dev", "% Open", "% Closed", "% Square"],
            face_table,
        )
    )

    print(
        render_table(
            "2) CLUB PATH",
            ["Club", "Shots", "N Path", "Avg", "Std Dev", "% In-to-Out", "% Out-to-In", "% Neutral"],
            path_table,
        )
    )

    print(
        render_table(
            "3) FACE-TO-PATH (D-PLANE)",
            ["Club", "Shots", "N FTP", "Avg FTP", "% Draw", "% Fade", "% Straight"],
            ftp_table,
        )
    )

    print(
        render_table(
            "4) STRIKE QUALITY",
            ["Club", "Shots", "Avg Impact X", "Avg Impact Y", "Avg Strike Dist"],
            strike_table,
        )
    )

    tendency_rows: list[list[Any]] = []
    for row in top_clubs:
        club = row["club"]
        shots = row["shots"]

        face = face_by_club.get(club, {})
        path = path_by_club.get(club, {})
        ftp = ftp_by_club.get(club, {})
        strike = strike_by_club.get(club, {})

        face_tendency = "N/A"
        if face:
            face_options = {
                "Open": face.get("pct_open") or 0.0,
                "Closed": face.get("pct_closed") or 0.0,
                "Square": face.get("pct_square") or 0.0,
            }
            face_tendency = max(face_options, key=face_options.get)

        path_tendency = "N/A"
        if path:
            path_options = {
                "In-to-Out": path.get("pct_in_to_out") or 0.0,
                "Out-to-In": path.get("pct_out_to_in") or 0.0,
                "Neutral": path.get("pct_neutral") or 0.0,
            }
            path_tendency = max(path_options, key=path_options.get)

        shape_tendency = "N/A"
        if ftp:
            shape_options = {
                "Draw": ftp.get("pct_draw") or 0.0,
                "Fade": ftp.get("pct_fade") or 0.0,
                "Straight": ftp.get("pct_straight") or 0.0,
            }
            shape_tendency = max(shape_options, key=shape_options.get)

        tendency_rows.append(
            [
                club,
                shots,
                face_tendency,
                path_tendency,
                shape_tendency,
                safe_round(face.get("face_avg") if face else None),
                safe_round(path.get("path_avg") if path else None),
                safe_round(ftp.get("ftp_avg") if ftp else None),
                safe_round(strike.get("strike_distance_avg") if strike else None),
            ]
        )

    print(
        render_table(
            "5) TOP-5 MOST-HIT CLUBS: TENDENCY SUMMARY",
            [
                "Club",
                "Shots",
                "Face Tendency",
                "Path Tendency",
                "Shape Tendency",
                "Avg Face",
                "Avg Path",
                "Avg FTP",
                "Avg Strike Dist",
            ],
            tendency_rows,
        )
    )


if __name__ == "__main__":
    main()
