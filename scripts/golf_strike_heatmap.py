#!/usr/bin/env python3
"""Generate strike-location KDE heatmaps for top clubs from golf_stats.db."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns


DB_PATH = Path("golf_stats.db")
OUTPUT_PATH = Path("/tmp/golf_strike_heatmap.png")
EXCLUDED_CLUBS = ("Sim Round", "Other", "Putter")
CARRY_MIN = 10.0


def fetch_top_clubs(connection: sqlite3.Connection, limit: int = 4) -> list[tuple[str, int]]:
    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT club, COUNT(*) AS shot_count
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND club NOT IN ({placeholders})
          AND carry >= ?
        GROUP BY club
        ORDER BY shot_count DESC, club
        LIMIT ?
    """
    params = (*EXCLUDED_CLUBS, CARRY_MIN, limit)
    return [(str(row[0]), int(row[1])) for row in connection.execute(query, params).fetchall()]


def fetch_impact_points(connection: sqlite3.Connection, club: str) -> tuple[list[float], list[float]]:
    placeholders = ", ".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT impact_x, impact_y
        FROM shots
        WHERE club = ?
          AND club NOT IN ({placeholders})
          AND carry >= ?
          AND impact_x IS NOT NULL
          AND impact_y IS NOT NULL
          AND impact_x != 0
          AND impact_y != 0
    """
    params = (club, *EXCLUDED_CLUBS, CARRY_MIN)
    rows = connection.execute(query, params).fetchall()
    x_values = [float(row[0]) for row in rows]
    y_values = [float(row[1]) for row in rows]
    return x_values, y_values


def plot_heatmaps(top_clubs: list[tuple[str, int]], club_points: dict[str, tuple[list[float], list[float]]]) -> None:
    sns.set_theme(style="white")
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), constrained_layout=True)
    axes_flat = axes.flatten()

    all_x = [x for club, _ in top_clubs for x in club_points.get(club, ([], []))[0]]
    all_y = [y for club, _ in top_clubs for y in club_points.get(club, ([], []))[1]]

    x_limits = None
    y_limits = None
    if all_x and all_y:
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        x_pad = max((x_max - x_min) * 0.08, 0.5)
        y_pad = max((y_max - y_min) * 0.08, 0.5)
        x_limits = (x_min - x_pad, x_max + x_pad)
        y_limits = (y_min - y_pad, y_max + y_pad)

    for index, axis in enumerate(axes_flat):
        if index >= len(top_clubs):
            axis.axis("off")
            continue

        club_name, _shot_count = top_clubs[index]
        x_values, y_values = club_points.get(club_name, ([], []))
        plotted_count = len(x_values)

        if plotted_count >= 2 and len(set(x_values)) > 1 and len(set(y_values)) > 1:
            sns.kdeplot(
                x=x_values,
                y=y_values,
                fill=True,
                cmap="hot",
                levels=100,
                thresh=0.05,
                bw_adjust=1.0,
                ax=axis,
            )
        elif plotted_count > 0:
            axis.scatter(x_values, y_values, color="orangered", alpha=0.85, s=14)
            axis.set_facecolor("#120000")
        else:
            axis.text(0.5, 0.5, "No valid impact data", ha="center", va="center", transform=axis.transAxes)

        axis.axhline(0, color="white", linestyle="--", linewidth=1.0, alpha=0.9)
        axis.axvline(0, color="white", linestyle="--", linewidth=1.0, alpha=0.9)
        axis.set_title(f"{club_name} (n={plotted_count})")
        axis.set_xlabel("impact_x")
        axis.set_ylabel("impact_y")

        if x_limits is not None and y_limits is not None:
            axis.set_xlim(x_limits)
            axis.set_ylim(y_limits)

    fig.suptitle("Strike Location KDE Heatmaps (Top 4 Clubs)", fontsize=14)
    fig.savefig(OUTPUT_PATH, dpi=150)
    plt.close(fig)


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as connection:
        top_clubs = fetch_top_clubs(connection, limit=4)
        club_points: dict[str, tuple[list[float], list[float]]] = {}
        for club_name, _ in top_clubs:
            club_points[club_name] = fetch_impact_points(connection, club_name)

    plot_heatmaps(top_clubs, club_points)
    print(OUTPUT_PATH.as_posix())


if __name__ == "__main__":
    main()
