#!/usr/bin/env python3
"""Generate carry-distance trend plots from golf_stats.db."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import Patch

EXCLUDED_CLUBS = ("Sim Round", "Other", "Putter")
CATEGORY_COLORS = {
    "woods": "#2e7d32",
    "irons": "#1565c0",
    "wedges": "#ef6c00",
}


def categorize_club(club_name: str) -> str:
    club = club_name.strip().upper()
    wedges = {"PW", "GW", "SW", "LW", "AW"}
    woods = {"DR", "D", "3W", "5W", "7W", "9W", "DRIVER"}

    if "WEDGE" in club or club in wedges:
        return "wedges"
    if "WOOD" in club or club in woods:
        return "woods"
    if "IRON" in club or (club.endswith("I") and club[:-1].isdigit()):
        return "irons"

    # Treat unknown clubs as irons so all bars remain color-coded by category.
    return "irons"


def load_shots_dataframe(db_path: Path) -> pd.DataFrame:
    query = """
    SELECT
        club,
        carry,
        COALESCE(session_date, date_added) AS shot_time
    FROM shots
    WHERE
        club IS NOT NULL
        AND TRIM(club) <> ''
        AND club NOT IN (?, ?, ?)
        AND carry >= 10
    """
    with sqlite3.connect(db_path) as connection:
        df = pd.read_sql_query(query, connection, params=EXCLUDED_CLUBS)

    df["shot_time"] = pd.to_datetime(df["shot_time"], errors="coerce")
    df["carry"] = pd.to_numeric(df["carry"], errors="coerce")
    df = df.dropna(subset=["shot_time", "carry", "club"])
    return df


def build_figure(shots_df: pd.DataFrame, output_path: Path) -> None:
    sns.set_theme(style="whitegrid")

    monthly = (
        shots_df.assign(month=shots_df["shot_time"].dt.to_period("M").astype(str))
        .groupby("month", as_index=False)
        .agg(avg_carry=("carry", "mean"), shot_count=("carry", "size"))
        .sort_values("month")
    )
    monthly["month_dt"] = pd.to_datetime(monthly["month"] + "-01")

    club_stats = (
        shots_df.groupby("club", as_index=False)
        .agg(avg_carry=("carry", "mean"), std_carry=("carry", "std"))
        .sort_values("avg_carry", ascending=False)
    )
    club_stats["std_carry"] = club_stats["std_carry"].fillna(0.0)
    club_stats["category"] = club_stats["club"].map(categorize_club)
    club_stats["color"] = club_stats["category"].map(CATEGORY_COLORS)

    fig, (ax_top, ax_bottom) = plt.subplots(
        2,
        1,
        figsize=(14, 10),
        gridspec_kw={"height_ratios": [2, 3]},
    )

    ax_top.plot(
        monthly["month_dt"],
        monthly["avg_carry"],
        color="#0d47a1",
        marker="o",
        linewidth=2,
        label="Avg Carry",
    )
    ax_top.set_ylabel("Average Carry Distance")
    ax_top.set_xlabel("Month (YYYY-MM)")
    ax_top.set_title("Monthly Average Carry Distance and Shot Volume")
    ax_top.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax_top.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=12))
    ax_top.tick_params(axis="x", rotation=45)

    ax_top_secondary = ax_top.twinx()
    ax_top_secondary.bar(
        monthly["month_dt"],
        monthly["shot_count"],
        width=20,
        alpha=0.28,
        color="#607d8b",
        label="Shot Count",
    )
    ax_top_secondary.set_ylabel("Shot Count")

    line_handles, line_labels = ax_top.get_legend_handles_labels()
    bar_handles, bar_labels = ax_top_secondary.get_legend_handles_labels()
    ax_top.legend(line_handles + bar_handles, line_labels + bar_labels, loc="upper left")

    y_positions = np.arange(len(club_stats))
    ax_bottom.barh(
        y_positions,
        club_stats["avg_carry"],
        xerr=club_stats["std_carry"],
        color=club_stats["color"],
        ecolor="#424242",
        capsize=3,
    )
    ax_bottom.set_yticks(y_positions)
    ax_bottom.set_yticklabels(club_stats["club"])
    ax_bottom.invert_yaxis()
    ax_bottom.set_xlabel("Average Carry Distance")
    ax_bottom.set_title("Average Carry by Club (Std Dev Error Bars)")

    category_legend = [
        Patch(facecolor=CATEGORY_COLORS["woods"], label="Woods"),
        Patch(facecolor=CATEGORY_COLORS["irons"], label="Irons"),
        Patch(facecolor=CATEGORY_COLORS["wedges"], label="Wedges"),
    ]
    ax_bottom.legend(handles=category_legend, loc="lower right")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    db_path = project_root / "golf_stats.db"
    output_path = Path("/tmp/golf_carry_trends.png")

    shots_df = load_shots_dataframe(db_path)
    if shots_df.empty:
        raise SystemExit("No qualifying shot data found after filtering.")

    build_figure(shots_df, output_path)
    print(output_path)


if __name__ == "__main__":
    main()
