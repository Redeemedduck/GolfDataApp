#!/usr/bin/env python3
"""Run ML insights against golf_stats.db shots data."""

from __future__ import annotations

import argparse
import math
import os
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 1))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split


EXCLUDED_CLUBS = ("Sim Round", "Other", "Putter")
FIGURE_PATH = Path("/tmp/golf_ml_insights.png")
RANDOM_STATE = 42


def to_float(value: Any) -> float:
    if value is None:
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def sql_placeholders(n: int) -> str:
    return ", ".join("?" for _ in range(n))


def load_rows(db_path: str) -> list[dict[str, Any]]:
    query = f"""
        SELECT
            shot_id,
            club,
            carry,
            club_speed,
            ball_speed,
            launch_angle,
            back_spin,
            smash,
            attack_angle,
            face_angle,
            club_path,
            face_to_path,
            side_spin,
            session_type,
            shot_type
        FROM shots
        WHERE club IS NOT NULL
          AND TRIM(club) != ''
          AND club NOT IN ({sql_placeholders(len(EXCLUDED_CLUBS))})
          AND carry IS NOT NULL
          AND carry >= 10
          AND (session_type IS NULL OR session_type != 'Sim Round')
          AND (shot_type IS NULL OR shot_type != 'Other')
    """

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, EXCLUDED_CLUBS)
        rows = [dict(row) for row in cursor.fetchall()]
    return rows


def build_matrix(rows: list[dict[str, Any]], columns: list[str]) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.array([[to_float(row.get(col)) for col in columns] for row in rows], dtype=float)
    valid_mask = np.isfinite(matrix).all(axis=1)
    return matrix, valid_mask


def render_simple_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def fmt(row: list[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    sep = "-+-".join("-" * width for width in widths)
    out = [fmt(headers), sep]
    out.extend(fmt(row) for row in rows)
    return "\n".join(out)


def cluster_label_from_centroid(centroid: np.ndarray) -> str:
    face_angle, club_path, face_to_path, side_spin = centroid

    if club_path > 1.0 and face_angle > 0.5:
        direction = "Push"
    elif club_path < -1.0 and face_angle < -0.5:
        direction = "Pull"
    else:
        direction = "Neutral"

    if face_to_path > 1.0 or side_spin > 200:
        shape = "Fade"
    elif face_to_path < -1.0 or side_spin < -200:
        shape = "Draw"
    else:
        shape = "Straight"

    if direction == "Neutral":
        if shape == "Straight":
            return "Stock Straight"
        return f"Stock {shape}"
    return f"{direction} {shape}"


def dedupe_labels(labels: list[str]) -> list[str]:
    seen: dict[str, int] = defaultdict(int)
    deduped: list[str] = []
    for label in labels:
        seen[label] += 1
        count = seen[label]
        deduped.append(label if count == 1 else f"{label} {count}")
    return deduped


def main() -> None:
    parser = argparse.ArgumentParser(description="Golf ML Insights")
    parser.add_argument("--db", default="golf_stats.db", help="Path to SQLite database")
    args = parser.parse_args()

    rows = load_rows(args.db)
    if not rows:
        raise SystemExit("No rows available after filters.")

    print("GOLF ML INSIGHTS")
    print(f"DB: {args.db}")
    print(f"Filters: exclude clubs {', '.join(EXCLUDED_CLUBS)}; exclude session_type='Sim Round'; exclude shot_type='Other'; carry >= 10")
    print(f"Rows after filters: {len(rows)}")

    # 1) Carry prediction
    carry_features = ["club_speed", "ball_speed", "launch_angle", "back_spin", "smash", "attack_angle"]
    carry_target = "carry"
    carry_matrix, carry_mask = build_matrix(rows, carry_features + [carry_target])
    carry_valid = carry_matrix[carry_mask]
    if len(carry_valid) < 20:
        raise SystemExit("Not enough valid rows for carry prediction.")

    X = carry_valid[:, :-1]
    y = carry_valid[:, -1]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )
    rf = RandomForestRegressor(
        n_estimators=400,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)
    r2 = r2_score(y_test, y_pred)

    importance_order = np.argsort(rf.feature_importances_)[::-1]
    print("\n1) CARRY PREDICTION (RandomForestRegressor)")
    print(f"Valid rows used: {len(carry_valid)}")
    print(f"Train/Test split: {len(X_train)}/{len(X_test)} (80/20)")
    print(f"R-squared (test): {r2:.4f}")
    imp_rows = [
        [carry_features[idx], f"{rf.feature_importances_[idx]:.4f}"]
        for idx in importance_order
    ]
    print("Feature importances:")
    print(render_simple_table(["Feature", "Importance"], imp_rows))

    # 2) Anomaly detection
    anomaly_features = ["carry", "ball_speed", "smash", "launch_angle"]
    anomaly_matrix, anomaly_mask = build_matrix(rows, anomaly_features)
    anomaly_X = anomaly_matrix[anomaly_mask]
    anomaly_indices = np.where(anomaly_mask)[0]
    if len(anomaly_X) < 20:
        raise SystemExit("Not enough valid rows for anomaly detection.")

    iso = IsolationForest(
        n_estimators=300,
        contamination=0.06,
        random_state=RANDOM_STATE,
    )
    anomaly_labels = iso.fit_predict(anomaly_X)
    anomaly_scores = iso.decision_function(anomaly_X)

    outlier_positions = np.where(anomaly_labels == -1)[0]
    outlier_rows = [rows[anomaly_indices[pos]] for pos in outlier_positions]
    outlier_scores = anomaly_scores[outlier_positions]

    outlier_by_club: Counter[str] = Counter(str(row["club"]) for row in outlier_rows)
    print("\n2) ANOMALY DETECTION (IsolationForest)")
    print(f"Valid rows used: {len(anomaly_X)}")
    print(f"Outliers detected: {len(outlier_rows)} ({100.0 * len(outlier_rows) / len(anomaly_X):.2f}%)")

    if outlier_by_club:
        club_rows = [[club, str(count)] for club, count in outlier_by_club.most_common()]
        print("Outliers per club:")
        print(render_simple_table(["Club", "Outliers"], club_rows))
    else:
        print("Outliers per club: none")

    if outlier_rows:
        hardest = np.argsort(outlier_scores)[:12]
        example_rows: list[list[str]] = []
        for idx in hardest:
            shot = outlier_rows[idx]
            example_rows.append(
                [
                    str(shot["shot_id"]),
                    str(shot["club"]),
                    f"{to_float(shot['carry']):.1f}",
                    f"{to_float(shot['ball_speed']):.1f}",
                    f"{to_float(shot['smash']):.3f}",
                    f"{to_float(shot['launch_angle']):.1f}",
                    f"{outlier_scores[idx]:.4f}",
                ]
            )
        print("Example outlier shots (most anomalous first):")
        print(
            render_simple_table(
                ["shot_id", "club", "carry", "ball_speed", "smash", "launch", "anomaly_score"],
                example_rows,
            )
        )

    # 3) Shot clustering
    cluster_features = ["face_angle", "club_path", "face_to_path", "side_spin"]
    cluster_matrix, cluster_mask = build_matrix(rows, cluster_features)
    cluster_X = cluster_matrix[cluster_mask]
    cluster_indices = np.where(cluster_mask)[0]
    if len(cluster_X) < 20:
        raise SystemExit("Not enough valid rows for shot clustering.")

    kmeans = KMeans(n_clusters=4, n_init=20, random_state=RANDOM_STATE)
    cluster_ids = kmeans.fit_predict(cluster_X)
    centroids = kmeans.cluster_centers_

    base_cluster_names = [cluster_label_from_centroid(c) for c in centroids]
    cluster_names = dedupe_labels(base_cluster_names)
    cluster_counts = Counter(cluster_ids)

    print("\n3) SHOT CLUSTERING (KMeans, k=4)")
    print(f"Valid rows used: {len(cluster_X)}")
    centroid_rows: list[list[str]] = []
    for cid in range(4):
        centroid = centroids[cid]
        centroid_rows.append(
            [
                str(cid),
                cluster_names[cid],
                str(cluster_counts[cid]),
                f"{centroid[0]:.2f}",
                f"{centroid[1]:.2f}",
                f"{centroid[2]:.2f}",
                f"{centroid[3]:.1f}",
            ]
        )
    print("Cluster sizes and centroids:")
    print(
        render_simple_table(
            ["Cluster", "Name", "Size", "face_angle", "club_path", "face_to_path", "side_spin"],
            centroid_rows,
        )
    )

    # Plots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=150)
    ax1, ax2, ax3, ax4 = axes.flat

    sorted_features = [carry_features[idx] for idx in importance_order]
    sorted_importances = [rf.feature_importances_[idx] for idx in importance_order]
    ax1.bar(sorted_features, sorted_importances, color="#2f6f95")
    ax1.set_title("Feature Importances (Carry Prediction)")
    ax1.set_ylabel("Importance")
    ax1.tick_params(axis="x", rotation=30)

    ax2.scatter(y_test, y_pred, alpha=0.6, s=18, color="#20639b")
    min_val = min(float(np.min(y_test)), float(np.min(y_pred)))
    max_val = max(float(np.max(y_test)), float(np.max(y_pred)))
    ax2.plot([min_val, max_val], [min_val, max_val], linestyle="--", color="#d62828", linewidth=1)
    ax2.set_title(f"Predicted vs Actual Carry (R²={r2:.3f})")
    ax2.set_xlabel("Actual Carry")
    ax2.set_ylabel("Predicted Carry")

    cluster_colors = ["#ef476f", "#118ab2", "#06d6a0", "#ffd166"]
    for cid in range(4):
        points = cluster_X[cluster_ids == cid]
        ax3.scatter(
            points[:, 0],
            points[:, 1],
            alpha=0.45,
            s=14,
            label=cluster_names[cid],
            color=cluster_colors[cid],
        )
    ax3.axhline(0, color="#888", linewidth=0.8, linestyle=":")
    ax3.axvline(0, color="#888", linewidth=0.8, linestyle=":")
    ax3.set_title("Shot Clusters (Face Angle vs Club Path)")
    ax3.set_xlabel("Face Angle")
    ax3.set_ylabel("Club Path")
    ax3.legend(fontsize=7, loc="best")

    if outlier_by_club:
        clubs_sorted = [club for club, _ in outlier_by_club.most_common()]
        counts_sorted = [outlier_by_club[club] for club in clubs_sorted]
        ax4.bar(clubs_sorted, counts_sorted, color="#f77f00")
        ax4.tick_params(axis="x", rotation=45)
    ax4.set_title("Anomaly Distribution per Club")
    ax4.set_xlabel("Club")
    ax4.set_ylabel("Outlier Count")

    fig.tight_layout()
    fig.savefig(FIGURE_PATH, dpi=150)
    plt.close(fig)

    print(f"\nSaved figure: {FIGURE_PATH}")


if __name__ == "__main__":
    main()
