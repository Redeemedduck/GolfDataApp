"""
ML-based coaching system for personalized practice plans and weakness detection.

Provides structured practice plan generation that analyzes shot data to identify
weaknesses and maps them to curated drills.
"""

try:
    from ml.coaching.practice_planner import PracticePlanner, PracticePlan, Drill
    from ml.coaching.weakness_mapper import WeaknessMapper

    __all__ = ['PracticePlanner', 'PracticePlan', 'Drill', 'WeaknessMapper']
except ImportError as e:
    # Graceful degradation if dependencies not available
    import warnings
    warnings.warn(f"ML coaching module dependencies not available: {e}")

    PracticePlanner = None
    PracticePlan = None
    Drill = None
    WeaknessMapper = None

    __all__ = []
