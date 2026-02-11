"""
ML Monitoring Package.

Provides model drift detection and performance tracking for ML models.

Components:
    - DriftDetector: Detects model performance drift using adaptive baselines
    - PerformanceTracker: Logs predictions and computes session metrics

Usage:
    from ml.monitoring import DriftDetector, PerformanceTracker

    tracker = PerformanceTracker()
    tracker.log_prediction(shot_id, club, predicted, actual, version)

    detector = DriftDetector()
    result = detector.check_session_drift(session_id)
    if result['has_drift']:
        print(f"Drift detected: {result['recommendation']}")
"""

# Graceful degradation pattern matching ml/__init__.py
try:
    from .drift_detector import DriftDetector
except ImportError as e:
    DriftDetector = None
    print(f"Warning: DriftDetector unavailable: {e}")

try:
    from .performance_tracker import PerformanceTracker
except ImportError as e:
    PerformanceTracker = None
    print(f"Warning: PerformanceTracker unavailable: {e}")

__all__ = [
    'DriftDetector',
    'PerformanceTracker',
]
