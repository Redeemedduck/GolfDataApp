#!/usr/bin/env python3
"""Create a D-plane scatter plot from the shots table in golf_stats.db."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import seaborn as sns


EXCLUDED_CLUBS = ("Sim Round", "Other", "Putter")
OUTPUT_PATH = Path("/tmp/golf_dplane_scatter.png")


def classify_shot_shape(face_to_path: float) -> str:
    if face_to_path < -2:
        return "Draw"
    if face_to_path > 2:
        return "Fade"
    return "Straight"


def load_shots(db_path: Path) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in EXCLUDED_CLUBS)
    query = f"""
        SELECT face_angle, club_path, face_to_path
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND club NOT IN ({placeholders})
          AND carry >= 10
          AND face_angle IS NOT NULL
          AND club_path IS NOT NULL
          AND face_to_path IS NOT NULL
    """

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, EXCLUDED_CLUBS).fetchall()

    records: list[dict[str, Any]] = []
    for row in rows:
        face_angle = float(row["face_angle"])
        club_path = float(row["club_path"])
        face_to_path = float(row["face_to_path"])
        records.append(
            {
                "face_angle": face_angle,
                "club_path": club_path,
                "shot_shape": classify_shot_shape(face_to_path),
            }
        )
    return records


def create_plot(records: list[dict[str, Any]], output_path: Path) -> None:
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 8))

    palette = {"Draw": "blue", "Fade": "red", "Straight": "green"}
    hue_order = ["Draw", "Fade", "Straight"]

    if records:
        plot_data = {
            "face_angle": [row["face_angle"] for row in records],
            "club_path": [row["club_path"] for row in records],
            "shot_shape": [row["shot_shape"] for row in records],
        }
        sns.scatterplot(
            data=plot_data,
            x="face_angle",
            y="club_path",
            hue="shot_shape",
            hue_order=hue_order,
            palette=palette,
            alpha=0.3,
            edgecolor=None,
            ax=ax,
            legend=False,
        )

        x_vals = plot_data["face_angle"]
        y_vals = plot_data["club_path"]
        diagonal_min = min(min(x_vals), min(y_vals))
        diagonal_max = max(max(x_vals), max(y_vals))
    else:
        diagonal_min, diagonal_max = -5.0, 5.0
        ax.text(
            0.5,
            0.5,
            "No shots matched filters",
            transform=ax.transAxes,
            ha="center",
            va="center",
        )

    ax.axvline(0, color="black", linestyle="--", linewidth=1, alpha=0.8)
    ax.axhline(0, color="black", linestyle="--", linewidth=1, alpha=0.8)
    ax.plot(
        [diagonal_min, diagonal_max],
        [diagonal_min, diagonal_max],
        color="gray",
        linestyle="-",
        linewidth=1.5,
    )

    ax.set_title("D-Plane Scatter: Face Angle vs Club Path")
    ax.set_xlabel("Face Angle")
    ax.set_ylabel("Club Path")

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=palette["Draw"],
            markeredgecolor="none",
            markersize=8,
            alpha=0.3,
            label="Draw (face_to_path < -2)",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=palette["Fade"],
            markeredgecolor="none",
            markersize=8,
            alpha=0.3,
            label="Fade (face_to_path > 2)",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=palette["Straight"],
            markeredgecolor="none",
            markersize=8,
            alpha=0.3,
            label="Straight (-2 to 2)",
        ),
        Line2D([0], [0], color="gray", linestyle="-", linewidth=1.5, label="Face = Path"),
    ]
    ax.legend(handles=legend_handles, title="Legend")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("golf_stats.db"),
        help="Path to SQLite DB file (default: golf_stats.db).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUTPUT_PATH,
        help=f"Output image path (default: {OUTPUT_PATH}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_shots(args.db)
    create_plot(records, args.out)
    print(str(args.out))


if __name__ == "__main__":
    main()
