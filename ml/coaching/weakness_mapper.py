"""
Weakness detection module for golf swing analysis.

Analyzes shot data to identify weaknesses using Phase 2 analytics utilities.
Maps detected weaknesses to severity scores for practice plan generation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional

try:
    from analytics.utils import filter_outliers_iqr, calculate_distance_stats
    from components.miss_tendency import _classify_shot_shape
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False


class WeaknessMapper:
    """
    Detect swing weaknesses from shot data using analytics-based metrics.

    Uses Phase 2 analytics utilities to compute:
    - Dispersion patterns (IQR-based)
    - Shot shape tendencies (D-plane classification)
    - Impact quality (smash factor)
    - Distance consistency (coefficient of variation)
    - Launch characteristics (driver-specific)
    """

    def __init__(self):
        """Initialize WeaknessMapper."""
        if not ANALYTICS_AVAILABLE:
            import warnings
            warnings.warn("Analytics utilities not available - weakness detection limited")

    def detect_weaknesses(
        self,
        df: pd.DataFrame,
        clubs: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        Detect weaknesses from shot data and return severity scores.

        Args:
            df: DataFrame with shot data
            clubs: Optional list of clubs to analyze (default: top 3 most-used)

        Returns:
            Dictionary of {weakness_key: severity_score (0.0-1.0)},
            sorted by severity descending

        Weakness types:
            - high_dispersion: Lateral inconsistency (IQR > 15 yards)
            - fade_pattern: Consistent fade tendency (>60% fades)
            - slice_pattern: Slice tendency (>40% slices)
            - hook_pattern: Hook tendency (>40% hooks)
            - low_smash_factor: Poor contact quality (avg < 1.40)
            - inconsistent_distance: Variable carry (CV > 8%)
            - high_launch: Driver launch too high (>16 degrees)
            - low_launch: Driver launch too low (<10 degrees)

        Notes:
            - Requires minimum 5 shots per check
            - Handles missing columns gracefully (skips check)
            - Cleans sentinel values (0, 99999) before computing
        """
        if not ANALYTICS_AVAILABLE:
            return {}

        if df.empty:
            return {}

        weaknesses = {}

        # Minimum samples check
        if len(df) < 5:
            return weaknesses

        # Determine clubs to analyze
        if clubs is None and 'club' in df.columns:
            # Use top 3 most-used clubs
            club_counts = df['club'].value_counts()
            clubs = club_counts.head(3).index.tolist()
        elif clubs is None:
            clubs = []

        # Check 1: High dispersion (lateral inconsistency)
        if 'side_total' in df.columns and clubs:
            for club in clubs:
                club_df = df[df['club'] == club].copy() if 'club' in df.columns else df.copy()

                if len(club_df) >= 5:
                    # Clean sentinel values
                    club_df['side_total'] = club_df['side_total'].replace([0, 99999], np.nan)
                    club_df = club_df.dropna(subset=['side_total'])

                    if len(club_df) >= 5:
                        # Apply IQR filtering
                        filtered = filter_outliers_iqr(club_df, 'side_total')

                        if len(filtered) >= 3:
                            q1 = filtered['side_total'].quantile(0.25)
                            q3 = filtered['side_total'].quantile(0.75)
                            iqr_value = abs(q3 - q1)

                            if iqr_value > 15:
                                severity = min(1.0, iqr_value / 25.0)
                                if 'high_dispersion' not in weaknesses or severity > weaknesses['high_dispersion']:
                                    weaknesses['high_dispersion'] = severity

        # Check 2-4: Shot shape patterns (fade, slice, hook)
        if all(col in df.columns for col in ['face_angle', 'club_path', 'side_spin']):
            # Clean data
            shape_df = df.copy()
            shape_df = shape_df.dropna(subset=['face_angle', 'club_path', 'side_spin'])

            if len(shape_df) >= 5:
                # Classify each shot
                shapes = shape_df.apply(
                    lambda row: _classify_shot_shape(
                        row['face_angle'],
                        row['club_path'],
                        row['side_spin']
                    ),
                    axis=1
                )

                total_shots = len(shapes)
                shape_counts = shapes.value_counts(normalize=True)

                # Fade pattern (>60%)
                if 'Fade' in shape_counts and shape_counts['Fade'] > 0.6:
                    weaknesses['fade_pattern'] = float(shape_counts['Fade'])

                # Slice pattern (>40%)
                if 'Slice' in shape_counts and shape_counts['Slice'] > 0.4:
                    weaknesses['slice_pattern'] = float(shape_counts['Slice'])

                # Hook pattern (>40%)
                if 'Hook' in shape_counts and shape_counts['Hook'] > 0.4:
                    weaknesses['hook_pattern'] = float(shape_counts['Hook'])

        # Check 5: Low smash factor
        if 'smash' in df.columns:
            smash_df = df.copy()
            smash_df['smash'] = smash_df['smash'].replace([0, 99999], np.nan)
            smash_values = smash_df['smash'].dropna()

            if len(smash_values) >= 5:
                avg_smash = smash_values.mean()

                if avg_smash < 1.40:
                    severity = 1.0 - (avg_smash / 1.45)
                    weaknesses['low_smash_factor'] = max(0.0, min(1.0, severity))

        # Check 6: Inconsistent distance
        if 'carry' in df.columns and clubs:
            for club in clubs:
                club_df = df[df['club'] == club].copy() if 'club' in df.columns else df.copy()

                if len(club_df) >= 5:
                    # Clean sentinel values
                    club_df['carry'] = club_df['carry'].replace([0, 99999], np.nan)
                    carry_values = club_df['carry'].dropna()

                    if len(carry_values) >= 5:
                        mean_carry = carry_values.mean()
                        std_carry = carry_values.std()

                        if mean_carry > 0:
                            cv = std_carry / mean_carry

                            if cv > 0.08:
                                severity = min(1.0, cv / 0.15)
                                if 'inconsistent_distance' not in weaknesses or severity > weaknesses['inconsistent_distance']:
                                    weaknesses['inconsistent_distance'] = severity

        # Check 7-8: Launch angle (Driver-specific)
        if 'launch_angle' in df.columns and 'club' in df.columns:
            driver_df = df[df['club'] == 'Driver'].copy()

            if len(driver_df) >= 5:
                # Clean sentinel values
                driver_df['launch_angle'] = driver_df['launch_angle'].replace([0, 99999], np.nan)
                launch_values = driver_df['launch_angle'].dropna()

                if len(launch_values) >= 5:
                    avg_launch = launch_values.mean()

                    # High launch (>16 degrees)
                    if avg_launch > 16:
                        severity = min(1.0, (avg_launch - 16) / 5.0)
                        weaknesses['high_launch'] = severity

                    # Low launch (<10 degrees)
                    elif avg_launch < 10:
                        severity = min(1.0, (10 - avg_launch) / 5.0)
                        weaknesses['low_launch'] = severity

        # Sort by severity descending
        sorted_weaknesses = dict(
            sorted(weaknesses.items(), key=lambda x: x[1], reverse=True)
        )

        return sorted_weaknesses
