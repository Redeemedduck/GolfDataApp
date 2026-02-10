"""
Analytics utilities for golf shot data analysis.

This package provides shared utility functions for statistical analysis,
outlier filtering, normalization, and data quality checks used across
all analytics components.
"""
from .utils import (
    filter_outliers_iqr,
    check_min_samples,
    normalize_score,
    normalize_inverse,
    calculate_distance_stats
)

__all__ = [
    'filter_outliers_iqr',
    'check_min_samples',
    'normalize_score',
    'normalize_inverse',
    'calculate_distance_stats'
]
