#!/usr/bin/env python3
"""Generate a radar chart comparing top golf clubs from golf_stats.db."""

from __future__ import annotations

import argparse
import math
import os
import sqlite3
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


EXCLUDED_CLUBS = ("sim round", "other", "putter")
AXES = ["Carry", "Smash Factor", "Consistency", "Accuracy", "Strike Quality"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "golf_stats.db",
        help="Path to SQLite database (default: repo-root golf_stats.db)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/golf_radar.png"),
        help="Output PNG path",
    )
    return parser.parse_args()


def get_top_clubs(connection: sqlite3.Connection, limit: int = 6) -> list[str]:
    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT club, COUNT(*) AS shot_count
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) <> ''
          AND LOWER(TRIM(club)) NOT IN ({placeholders})
          AND carry >= 10
        GROUP BY club
        ORDER BY shot_count DESC, club ASC
        LIMIT ?
    """
    params = (*EXCLUDED_CLUBS, limit)
    rows = connection.execute(query, params).fetchall()
    return [row[0] for row in rows]


def get_raw_metrics(connection: sqlite3.Connection, clubs: list[str]) -> dict[str, dict[str, float]]:
    if not clubs:
        return {}

    placeholders = ",".join("?" for _ in clubs)
    query = f"""
        SELECT
            club,
            COUNT(*) AS shot_count,
            AVG(carry) AS avg_carry,
            AVG(smash) AS avg_smash,
            AVG(ABS(side_distance)) AS avg_abs_side_distance,
            AVG(ABS(strike_distance)) AS avg_abs_strike_distance,
            AVG(carry * carry) AS avg_carry_sq
        FROM shots
        WHERE club IN ({placeholders})
          AND carry >= 10
        GROUP BY club
    """
    rows = connection.execute(query, clubs).fetchall()
    by_club: dict[str, dict[str, float]] = {}
    for row in rows:
        club = row[0]
        avg_carry = float(row[2] or 0.0)
        avg_carry_sq = float(row[6] or 0.0)
        variance = max(avg_carry_sq - (avg_carry * avg_carry), 0.0)
        std_dev = math.sqrt(variance)
        cv = std_dev / avg_carry if avg_carry > 0 else 0.0
        consistency = max(0.0, min(1.0, 1.0 - cv))
        by_club[club] = {
            "Carry": avg_carry,
            "Smash Factor": float(row[3] or 0.0),
            "Consistency": consistency,
            "avg_abs_side_distance": float(row[4] or 0.0),
            "avg_abs_strike_distance": float(row[5] or 0.0),
        }

    if not by_club:
        return {}

    max_side = max(values["avg_abs_side_distance"] for values in by_club.values())
    max_strike = max(values["avg_abs_strike_distance"] for values in by_club.values())

    for values in by_club.values():
        if max_side > 0:
            values["Accuracy"] = 1.0 - (values["avg_abs_side_distance"] / max_side)
        else:
            values["Accuracy"] = 1.0
        if max_strike > 0:
            values["Strike Quality"] = 1.0 - (values["avg_abs_strike_distance"] / max_strike)
        else:
            values["Strike Quality"] = 1.0

    return by_club


def min_max_normalize(metric_values: dict[str, float]) -> dict[str, float]:
    values = list(metric_values.values())
    low = min(values)
    high = max(values)
    if math.isclose(low, high):
        return {club: 1.0 for club in metric_values}
    span = high - low
    return {club: (value - low) / span for club, value in metric_values.items()}


def normalize_axes(raw_metrics: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    clubs = list(raw_metrics.keys())
    normalized = {club: {} for club in clubs}
    for axis in AXES:
        axis_raw = {club: raw_metrics[club][axis] for club in clubs}
        axis_normalized = min_max_normalize(axis_raw)
        for club in clubs:
            normalized[club][axis] = axis_normalized[club]
    return normalized


def build_radar_chart(normalized_metrics: dict[str, dict[str, float]], output_path: Path) -> None:
    clubs = list(normalized_metrics.keys())
    if not clubs:
        raise RuntimeError("No eligible clubs found to chart.")

    angles = np.linspace(0, 2 * np.pi, len(AXES), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw={"polar": True})
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(AXES)
    ax.set_ylim(0, 1)
    ax.set_yticks(np.linspace(0.2, 1.0, 5))
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"])
    ax.grid(True, linestyle="--", alpha=0.5)

    color_map = plt.get_cmap("tab10", len(clubs))
    for index, club in enumerate(clubs):
        values = [normalized_metrics[club][axis] for axis in AXES]
        values += values[:1]
        color = color_map(index)
        ax.plot(angles, values, color=color, linewidth=2, label=club)
        ax.fill(angles, values, color=color, alpha=0.15)

    ax.set_title("Top 6 Most-Hit Clubs Radar Profile", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    with sqlite3.connect(args.db) as connection:
        top_clubs = get_top_clubs(connection, limit=6)
        raw_metrics = get_raw_metrics(connection, top_clubs)

    if not raw_metrics:
        raise RuntimeError("No shot data found for requested filters.")

    normalized_metrics = normalize_axes(raw_metrics)
    build_radar_chart(normalized_metrics, args.output)
    print(str(args.output))


if __name__ == "__main__":
    main()
