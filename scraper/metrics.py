"""
Metric calculations for shot data.
"""


def calculate_smash(ball_speed: float, club_speed: float) -> float:
    """Calculate smash factor (ball speed / club speed)."""
    if club_speed and club_speed > 0:
        return round(ball_speed / club_speed, 2)
    return 0.0
