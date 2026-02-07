"""Shared Big 3 Impact Laws thresholds and label functions.

Thresholds based on Adam Young's teaching:
- Face Angle std: <1.5 consistent, <3.0 moderate, >3.0 scattered
- Club Path std: <2.0 consistent, <4.0 moderate, >4.0 scattered
- Strike Distance: <0.25 center, <0.5 decent, >0.5 scattered
"""

# Color constants
GREEN = "#2ca02c"
YELLOW = "#ff7f0e"
RED = "#d62728"
GRAY = "gray"

# Threshold constants (exported for direct use in big3_summary.py etc.)
FACE_STD_GREEN = 1.5   # degrees
FACE_STD_YELLOW = 3.0
PATH_STD_GREEN = 2.0
PATH_STD_YELLOW = 4.0
STRIKE_DIST_GREEN = 0.25   # inches from center
STRIKE_DIST_YELLOW = 0.5


def face_label(std):
    """Classify face angle consistency."""
    if std is None:
        return "---", GRAY
    if std < FACE_STD_GREEN:
        return "Consistent", GREEN
    if std < FACE_STD_YELLOW:
        return "Moderate", YELLOW
    return "Scattered", RED


def path_label(std):
    """Classify club path consistency."""
    if std is None:
        return "---", GRAY
    if std < PATH_STD_GREEN:
        return "Consistent", GREEN
    if std < PATH_STD_YELLOW:
        return "Moderate", YELLOW
    return "Scattered", RED


def strike_label(avg_dist):
    """Classify strike location quality."""
    if avg_dist is None:
        return "---", GRAY
    if avg_dist < STRIKE_DIST_GREEN:
        return "Center", GREEN
    if avg_dist < STRIKE_DIST_YELLOW:
        return "Decent", YELLOW
    return "Scattered", RED


def color_for_threshold(val, green, yellow):
    """Return CSS color based on threshold.

    Args:
        val: The value to classify.
        green: Upper bound for green (good).
        yellow: Upper bound for yellow (moderate).

    Returns:
        CSS color string.
    """
    if val is None:
        return "#888"
    if val <= green:
        return GREEN
    if val <= yellow:
        return YELLOW
    return RED
