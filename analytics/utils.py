"""
Core analytics utility functions for golf shot data analysis.

Provides statistical functions for outlier filtering, normalization,
and data quality checks.
"""
import pandas as pd
from scipy.stats import iqr
from typing import Tuple, Dict, Optional


def filter_outliers_iqr(df: pd.DataFrame, column: str, multiplier: float = 1.5) -> pd.DataFrame:
    """
    Filter outliers using Interquartile Range (IQR) method.

    Args:
        df: DataFrame to filter
        column: Column name to apply IQR filtering on
        multiplier: IQR multiplier for bounds (default 1.5, standard)

    Returns:
        Filtered DataFrame with outliers removed

    Notes:
        - Returns unfiltered data if fewer than 3 values
        - Handles NaN values gracefully (excluded from calculation)
        - Uses scipy.stats.iqr with nan_policy='omit'
    """
    if df.empty or column not in df.columns:
        return df

    # Drop NaN values for calculation
    values = df[column].dropna()

    # Need at least 3 values for meaningful IQR
    if len(values) < 3:
        return df

    # Calculate IQR using scipy
    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr_value = iqr(values, nan_policy='omit')

    # Calculate bounds
    lower_bound = q1 - multiplier * iqr_value
    upper_bound = q3 + multiplier * iqr_value

    # Filter DataFrame
    mask = (df[column] >= lower_bound) & (df[column] <= upper_bound)
    return df[mask]


def check_min_samples(data, min_n: int = 3, context: str = "") -> Tuple[bool, str]:
    """
    Check if dataset has minimum required samples for analysis.

    Args:
        data: DataFrame, Series, or list to check
        min_n: Minimum required samples (default 3)
        context: Optional context string for message (e.g., "Driver")

    Returns:
        Tuple of (is_sufficient, message)
        - is_sufficient: True if data has >= min_n samples
        - message: Empty string if sufficient, error message otherwise
    """
    if isinstance(data, pd.DataFrame):
        count = len(data)
    elif isinstance(data, (pd.Series, list)):
        count = len(data)
    else:
        count = 0

    if count >= min_n:
        return True, ""

    if context:
        msg = f"Need {min_n}+ shots for {context} analysis (have {count})"
    else:
        msg = f"Need {min_n}+ shots for analysis (have {count})"

    return False, msg


def normalize_score(value: float, min_val: float, max_val: float) -> float:
    """
    Normalize value to 0-100 scale.

    Args:
        value: Value to normalize
        min_val: Minimum value in range
        max_val: Maximum value in range

    Returns:
        Normalized score in range [0, 100]

    Notes:
        - Returns 50.0 if min_val == max_val
        - Clamps result to [0, 100]
    """
    if min_val == max_val:
        return 50.0

    normalized = 100 * (value - min_val) / (max_val - min_val)
    return max(0.0, min(100.0, normalized))


def normalize_inverse(value: float, min_val: float, max_val: float) -> float:
    """
    Inverse normalize value to 0-100 scale (lower raw value = higher score).

    Args:
        value: Value to normalize
        min_val: Minimum value in range
        max_val: Maximum value in range

    Returns:
        Inverse normalized score in range [0, 100]

    Notes:
        - Lower raw values produce higher scores
        - Useful for metrics where lower is better (e.g., dispersion)
    """
    return 100 - normalize_score(value, min_val, max_val)


def calculate_distance_stats(df: pd.DataFrame, club: str) -> Optional[Dict]:
    """
    Calculate distance statistics for a specific club with outlier filtering.

    Args:
        df: DataFrame with shot data (must have 'club' and 'carry' columns)
        club: Club name to filter for

    Returns:
        Dictionary with distance statistics or None if insufficient data:
        - median: Median carry distance
        - q25: 25th percentile
        - q75: 75th percentile
        - iqr: Interquartile range (Q75 - Q25)
        - max: Maximum carry distance
        - sample_size: Number of shots after filtering
        - outliers_removed: Number of outliers filtered
        - confidence: 'low' (<5), 'medium' (<10), 'high' (>=10)

    Notes:
        - Requires 3+ shots for analysis
        - Applies IQR outlier filtering
        - Also calculates total distance stats if 'total' column exists
    """
    if df.empty or 'club' not in df.columns or 'carry' not in df.columns:
        return None

    # Filter to club
    club_data = df[df['club'] == club].copy()

    # Drop NaN carry values
    club_data = club_data.dropna(subset=['carry'])

    # Check minimum samples
    if len(club_data) < 3:
        return None

    # Track original count
    original_count = len(club_data)

    # Apply IQR filtering
    filtered_data = filter_outliers_iqr(club_data, 'carry')

    if filtered_data.empty or len(filtered_data) < 3:
        return None

    # Calculate carry stats
    carry_values = filtered_data['carry']
    q25 = carry_values.quantile(0.25)
    q75 = carry_values.quantile(0.75)

    stats = {
        'median': carry_values.median(),
        'q25': q25,
        'q75': q75,
        'iqr': q75 - q25,
        'max': carry_values.max(),
        'sample_size': len(filtered_data),
        'outliers_removed': original_count - len(filtered_data)
    }

    # Determine confidence level
    if stats['sample_size'] >= 10:
        stats['confidence'] = 'high'
    elif stats['sample_size'] >= 5:
        stats['confidence'] = 'medium'
    else:
        stats['confidence'] = 'low'

    # Calculate total distance stats if available
    if 'total' in filtered_data.columns:
        total_values = filtered_data['total'].dropna()
        if len(total_values) >= 3:
            stats['total_median'] = total_values.median()
            stats['total_q25'] = total_values.quantile(0.25)
            stats['total_q75'] = total_values.quantile(0.75)

    return stats



def analyze_big3_impact_rules(df: pd.DataFrame) -> Dict:
    """Analyze Adam Young-style Big 3 impact rules for shot quality.

    Big 3 heuristics used here:
    1) Center Contact: impact strike location close to center.
    2) Face Control: face angle near square at impact.
    3) Speed Efficiency: smash factor in an efficient range.

    Returns:
        Dict with pass counts/percentages and per-rule breakdown.
    """
    if df.empty:
        return {
            'shots_analyzed': 0,
            'all_three_pass_count': 0,
            'all_three_pass_pct': 0.0,
            'rules': {
                'center_contact': {'pass_count': 0, 'pass_pct': 0.0},
                'face_control': {'pass_count': 0, 'pass_pct': 0.0},
                'speed_efficiency': {'pass_count': 0, 'pass_pct': 0.0},
            }
        }

    work = df.copy()

    # Rule 1: Center contact using Optix (preferred) or impact coordinates fallback.
    x_col = 'optix_x' if 'optix_x' in work.columns else ('impact_x' if 'impact_x' in work.columns else None)
    y_col = 'optix_y' if 'optix_y' in work.columns else ('impact_y' if 'impact_y' in work.columns else None)

    if x_col and y_col:
        strike_radius = (work[x_col].fillna(999).abs() ** 2 + work[y_col].fillna(999).abs() ** 2) ** 0.5
        center_mask = strike_radius <= 12.0
    else:
        center_mask = pd.Series([False] * len(work), index=work.index)

    # Rule 2: Face control near square.
    if 'face_angle' in work.columns:
        face_mask = work['face_angle'].fillna(999).abs() <= 2.5
    else:
        face_mask = pd.Series([False] * len(work), index=work.index)

    # Rule 3: Speed efficiency via smash factor.
    if 'smash' in work.columns:
        speed_mask = work['smash'].fillna(0).between(1.20, 1.55, inclusive='both')
    else:
        speed_mask = pd.Series([False] * len(work), index=work.index)

    analyzed = len(work)

    def _pct(mask: pd.Series) -> float:
        return round((int(mask.sum()) / analyzed) * 100, 1) if analyzed else 0.0

    all_three = center_mask & face_mask & speed_mask

    return {
        'shots_analyzed': analyzed,
        'all_three_pass_count': int(all_three.sum()),
        'all_three_pass_pct': _pct(all_three),
        'rules': {
            'center_contact': {'pass_count': int(center_mask.sum()), 'pass_pct': _pct(center_mask)},
            'face_control': {'pass_count': int(face_mask.sum()), 'pass_pct': _pct(face_mask)},
            'speed_efficiency': {'pass_count': int(speed_mask.sum()), 'pass_pct': _pct(speed_mask)},
        }
    }
