"""
ML Monitoring Package.

Provides model drift detection and performance tracking for ML models.

Components:
    - DriftDetector: Detects model performance drift using adaptive baselines
    - PerformanceTracker: Logs predictions and computes session metrics
    - check_and_trigger_retraining: Entry point for drift detection + retraining

Usage:
    from ml.monitoring import DriftDetector, PerformanceTracker, check_and_trigger_retraining

    tracker = PerformanceTracker()
    tracker.log_prediction(shot_id, club, predicted, actual, version)

    detector = DriftDetector()
    result = detector.check_session_drift(session_id)
    if result['has_drift']:
        print(f"Drift detected: {result['recommendation']}")

    # Or use integrated function
    drift_result = check_and_trigger_retraining(session_id, auto_retrain=False)
"""

# Graceful degradation pattern matching ml/__init__.py
try:
    from .drift_detector import DriftDetector, check_and_trigger_retraining
except ImportError as e:
    DriftDetector = None
    check_and_trigger_retraining = None
    print(f"Warning: DriftDetector unavailable: {e}")

try:
    from .performance_tracker import PerformanceTracker
except ImportError as e:
    PerformanceTracker = None
    print(f"Warning: PerformanceTracker unavailable: {e}")

__all__ = [
    'DriftDetector',
    'PerformanceTracker',
    'check_and_trigger_retraining',
]
